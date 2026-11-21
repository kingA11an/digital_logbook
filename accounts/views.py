from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from .forms import StudentRegistrationForm, SupervisorRegistrationForm
from .models import StudentProfile, User, FieldSupervisorProfile, UniversitySupervisorProfile
from django.db.models import Sum
from logbook.models import LogEntry, WeeklyReport
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.urls import reverse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import SupervisorInvitation
import uuid
from core.emails import send_brevo_email
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.db import IntegrityError, transaction
from django.utils.dateparse import parse_date



def register_student(request):
    # Redirect if they are already logged in
    if request.user.is_authenticated:
        return redirect('logbook:student_dashboard')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            email = (form.cleaned_data.get('email') or '').strip()
            username = (form.cleaned_data.get('username') or '').strip()
            registration_number = (form.cleaned_data.get('registration_number') or '').strip()
            start_date = form.cleaned_data.get('attachment_start_date')
            end_date = form.cleaned_data.get('attachment_end_date')

            # Case-insensitive pre-save validation so we never hit a raw DB error.
            validation_errors = []
            if User.objects.filter(email__iexact=email).exists():
                validation_errors.append(f"An account with the email {email} already exists.")
            if User.objects.filter(username__iexact=username).exists():
                validation_errors.append(f"The username {username} is already taken.")
            if StudentProfile.objects.filter(registration_number__iexact=registration_number).exists():
                validation_errors.append(f"The registration number {registration_number} is already registered.")
            if start_date and end_date and end_date < start_date:
                validation_errors.append("The attachment end date cannot be earlier than the start date.")

            if validation_errors:
                for error in validation_errors:
                    messages.error(request, error)
                return render(request, 'accounts/register.html', {
                    'form': form,
                    'form_data': request.POST,
                })

            try:
                with transaction.atomic():
                    # 1. Create the user (and set their role to Student)
                    user = form.save(commit=False)
                    user.set_password(form.cleaned_data['password'])
                    user.role = User.Role.STUDENT
                    user.save()

                    # 2. Create their student profile with the remaining dates/data
                    StudentProfile.objects.create(
                        user=user,
                        registration_number=registration_number,
                        course=form.cleaned_data['course'],
                        attachment_start_date=start_date,
                        attachment_end_date=end_date,
                    )
            except IntegrityError:
                messages.error(
                    request,
                    "We couldn't create your account because some details are already in use. "
                    "Please check your email, username, and registration number and try again.",
                )
                return render(request, 'accounts/register.html', {
                    'form': form,
                    'form_data': request.POST,
                })

            # 3. Log them in automatically and send to dashboard
            login(request, user)
            return redirect('logbook:student_dashboard')

        # Form-level validation failed (e.g. password mismatch, bad dates).
        messages.error(request, "Please correct the errors highlighted below and try again.")
        return render(request, 'accounts/register.html', {
            'form': form,
            'form_data': request.POST,
        })

    form = StudentRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required(login_url='accounts:login')
def user_profile(request):
    # 1. FIELD SUPERVISOR PROFILE
    if request.user.role == 'FIELD_SUPERVISOR':
        profile = getattr(request.user, 'field_supervisor_profile', None)
        if not profile:
            messages.error(request, "Your supervisor profile could not be found. Please contact the system administrator.")
            return redirect('accounts:login')
        return render(request, 'accounts/supervisor_profile.html', {'profile': profile})

    # 2. UNI SUPERVISOR PROFILE
    elif request.user.role == 'UNI_SUPERVISOR':
        profile = getattr(request.user, 'uni_supervisor_profile', None)
        if not profile:
            messages.error(request, "Your supervisor profile could not be found. Please contact the system administrator.")
            return redirect('accounts:login')
        return render(request, 'accounts/uni_profile.html', {'profile': profile})

    # 3. STUDENT PROFILE (Default)
    profile = getattr(request.user, 'student_profile', None)
    if not profile:
        messages.error(request, "Your student profile could not be found. Please contact the system administrator.")
        return redirect('accounts:login')

    # Calculate Total Approved Hours for Student
    approved_reports = WeeklyReport.objects.filter(
        student=profile,
        status=WeeklyReport.Status.APPROVED
    )
    total_approved_hours = LogEntry.objects.filter(
        weekly_report__in=approved_reports
    ).aggregate(Sum('hours_worked'))['hours_worked__sum'] or 0.0

    context = {
        'profile': profile,
        'total_approved_hours': total_approved_hours,
    }
    return render(request, 'accounts/profile.html', context)

@login_required(login_url='accounts:login')
def role_redirect(request):
    user = request.user
    if user.is_superuser or user.is_staff:
        return redirect('admin_dashboard')
    elif user.role == User.Role.STUDENT:
        return redirect('logbook:student_dashboard')
    elif user.role == User.Role.UNI_SUPERVISOR:
        return redirect('logbook:university_dashboard')
    elif user.role == User.Role.FIELD_SUPERVISOR:
        return redirect('logbook:supervisor_dashboard')
    return redirect('accounts:login')


@staff_member_required
def send_supervisor_invite(request):
    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip().lower()
        role = request.POST.get('role')

        if not email or role not in ('UNI', 'FIELD'):
            messages.error(request, "Please provide a valid email address and supervisor role.")
            return redirect('accounts:send_supervisor_invite')

        try:
            # 1. Create or update the invitation token
            invitation, created = SupervisorInvitation.objects.update_or_create(
                email=email,
                defaults={'role': role, 'is_used': False, 'token': uuid.uuid4()}
            )
        except IntegrityError:
            messages.error(request, "An invitation for this email already exists and could not be updated. Please try again.")
            return redirect('accounts:send_supervisor_invite')

        try:
            # 2. Build the secure registration link
            invite_path = reverse('accounts:supervisor_register', kwargs={'token': invitation.token})
            full_link = request.build_absolute_uri(invite_path)

            # 3. Send the email via the Brevo HTTP API
            role_title = "University" if role == "UNI" else "Field"
            subject = f"Invitation to join TrueLog as {role_title} Supervisor"
            message = (
                f"Hello,\n\n"
                f"You have been invited to join TrueLog as a {role_title} Supervisor.\n\n"
                f"Please click the link below to set up your account:\n{full_link}\n\n"
                f"Note: This link can only be used once."
            )

            send_brevo_email(to_email=email, subject=subject, body_text=message)
            messages.success(request, f"Invitation email successfully sent to {email}.")
        except Exception:
            # Never let a mail provider outage crash the request.
            messages.error(
                request,
                f"The invitation was created, but the email could not be sent to {email}. "
                "Please try again or share the registration link manually.",
            )

        return redirect('accounts:send_supervisor_invite')
    return render(request, 'accounts/send_invite.html')

def supervisor_register(request, token):
    # 1. Resolve the invitation token safely (invalid tokens must not 404/500).
    try:
        token_uuid = uuid.UUID(str(token))
        invitation = SupervisorInvitation.objects.get(token=token_uuid)
    except (ValueError, TypeError, SupervisorInvitation.DoesNotExist):
        messages.error(request, "This invitation link is invalid or no longer exists. Please request a new invitation.")
        return redirect('accounts:login')

    # 2. Gracefully handle already-used links
    if invitation.is_used:
        messages.error(request, "This invitation link has already been used. Please log in instead.")
        return redirect('accounts:login')

    # 3. Handle active registration
    if request.method == 'POST':
        form = SupervisorRegistrationForm(request.POST)
        if form.is_valid():
            email = invitation.email
            staff_id = (request.POST.get('staff_id', '') or '').strip()

            # Case-insensitive pre-save validation.
            if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
                messages.error(request, f"An account with the email {email} already exists. Please log in instead.")
                return render(request, 'accounts/supervisor_register.html', {
                    'form': form,
                    'email': email,
                    'form_data': request.POST,
                })

            if invitation.role == 'UNI' and staff_id and UniversitySupervisorProfile.objects.filter(staff_id__iexact=staff_id).exists():
                messages.error(request, f"The staff ID {staff_id} is already in use. Please use a different one.")
                return render(request, 'accounts/supervisor_register.html', {
                    'form': form,
                    'email': email,
                    'form_data': request.POST,
                })

            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.email = email
                    user.username = email
                    user.set_password(form.cleaned_data['password'])

                    if invitation.role == 'UNI':
                        user.role = User.Role.UNI_SUPERVISOR
                        user.save()
                        staff_id = staff_id or f"STF-{uuid.uuid4().hex[:6].upper()}"
                        UniversitySupervisorProfile.objects.create(
                            user=user,
                            staff_id=staff_id,
                        )
                    else:
                        user.role = User.Role.FIELD_SUPERVISOR
                        user.save()
                        FieldSupervisorProfile.objects.create(user=user)

                    invitation.is_used = True
                    invitation.save()
            except IntegrityError:
                messages.error(
                    request,
                    "We couldn't create your account because some details are already in use. "
                    "Please contact the system administrator.",
                )
                return render(request, 'accounts/supervisor_register.html', {
                    'form': form,
                    'email': email,
                    'form_data': request.POST,
                })

            login(request, user)
            return redirect('logbook:supervisor_dashboard')

        messages.error(request, "Please correct the errors highlighted below and try again.")
        return render(request, 'accounts/supervisor_register.html', {
            'form': form,
            'email': invitation.email,
            'form_data': request.POST,
        })

    form = SupervisorRegistrationForm(initial={'email': invitation.email})
    return render(request, 'accounts/supervisor_register.html', {
        'form': form,
        'email': invitation.email,
    })

class TrueLogLoginView(LoginView):
    template_name = 'accounts/login.html'

    def get_success_url(self):
        return reverse_lazy('accounts:role_redirect')

@staff_member_required(login_url='accounts:login')
def create_user_admin(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '').strip()
        role = request.POST.get('role', 'STUDENT')
        registration_number = request.POST.get('registration_number', '').strip()
        staff_id = request.POST.get('staff_id', '').strip()

        start_raw = request.POST.get('attachment_start_date') or None
        end_raw = request.POST.get('attachment_end_date') or None
        start_date = parse_date(start_raw) if start_raw else None
        end_date = parse_date(end_raw) if end_raw else None

        if not email or not password:
            messages.error(request, "Email and password are required.")
            return redirect('accounts:create_user')

        # Case-insensitive pre-save validation.
        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
            messages.error(request, f"A user with email {email} already exists.")
            return redirect('accounts:create_user')

        if role == 'STUDENT':
            if not registration_number:
                messages.error(request, "A registration number is required for student accounts.")
                return redirect('accounts:create_user')
            if StudentProfile.objects.filter(registration_number__iexact=registration_number).exists():
                messages.error(request, f"The registration number {registration_number} is already in use.")
                return redirect('accounts:create_user')

        if role == 'UNI' and staff_id and UniversitySupervisorProfile.objects.filter(staff_id__iexact=staff_id).exists():
            messages.error(request, f"The staff ID {staff_id} is already in use.")
            return redirect('accounts:create_user')

        if start_date and end_date and end_date < start_date:
            messages.error(request, "The attachment end date cannot be earlier than the start date.")
            return redirect('accounts:create_user')

        role_map = {
            'STUDENT': User.Role.STUDENT,
            'UNI': User.Role.UNI_SUPERVISOR,
            'FIELD': User.Role.FIELD_SUPERVISOR,
        }

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    role=role_map.get(role, 'STUDENT'),
                )

                if role == 'STUDENT':
                    StudentProfile.objects.create(
                        user=user,
                        registration_number=registration_number,
                        course=request.POST.get('course', '').strip(),
                        attachment_start_date=start_date,
                        attachment_end_date=end_date,
                    )
                elif role == 'UNI':
                    staff_id = staff_id or f"STF-{uuid.uuid4().hex[:6].upper()}"
                    UniversitySupervisorProfile.objects.create(user=user, staff_id=staff_id)
                elif role == 'FIELD':
                    FieldSupervisorProfile.objects.create(user=user)

            messages.success(
                request,
                f"Account created for {first_name} {last_name} ({email}) - Password: {password}"
            )
            return redirect('accounts:create_user')

        except IntegrityError:
            messages.error(
                request,
                "Could not create the account because some details are already in use. "
                "Please verify the email, registration number, and staff ID.",
            )
        except Exception as e:
            messages.error(request, f"Error creating user: {str(e)}")

    return render(request, 'accounts/create_user.html')

@staff_member_required(login_url='accounts:login')
def manage_users_admin(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        target_user = get_object_or_404(User, id=user_id)

        if target_user == request.user:
            messages.error(request, "You cannot deactivate your own admin account.")
        else:
            target_user.is_active = not target_user.is_active
            target_user.save()
            status_label = "activated" if target_user.is_active else "deactivated"
            messages.success(request, f"Account for {target_user.email} has been {status_label}.")

        return redirect('accounts:manage_users')

    role_filter = request.GET.get('role', 'ALL')
    users = User.objects.select_related('student_profile').order_by('-date_joined')

    if role_filter == 'STUDENT':
        users = users.filter(role='STUDENT')
    elif role_filter == 'SUPERVISOR':
        users = users.filter(role__in=['UNI_SUPERVISOR', 'FIELD_SUPERVISOR'])
    elif role_filter == 'ADMIN':
        users = users.filter(is_superuser=True)

    return render(request, 'accounts/manage_users.html', {
        'users': users,
        'role_filter': role_filter,
    })
