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



def register_student(request):
    # Redirect if they are already logged in 
    if request.user.is_authenticated:
        return redirect('logbook:student_dashboard')
    
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            # 1. Create the user (and set their role to Student) 
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])  # FIXED: cleaned_data
            user.role = User.Role.STUDENT
            user.save()
            
            # 2. create their student profile with the remaining dates/data
            StudentProfile.objects.create(
                user=user,
                registration_number=form.cleaned_data['registration_number'],
                course=form.cleaned_data['course'],
                attachment_start_date=form.cleaned_data['attachment_start_date'],
                attachment_end_date=form.cleaned_data['attachment_end_date']
            )
            
            # 3. log them in automatically and send to dashboard 
            login(request, user)
            return redirect('logbook:student_dashboard')
    else:
        # FIXED: This now properly runs on a GET request
        form = StudentRegistrationForm()
        
    # FIXED: This now properly returns the template for both GET and invalid POST requests
    return render(request, 'accounts/register.html', {'form': form})


@login_required(login_url='accounts:login')
def user_profile(request):
    # 1. FIELD SUPERVISOR PROFILE
    if request.user.role == 'FIELD_SUPERVISOR':
        profile = request.user.field_supervisor_profile
        return render(request, 'accounts/supervisor_profile.html', {'profile': profile})
        
    # 2. UNI SUPERVISOR PROFILE
    elif request.user.role == 'UNI_SUPERVISOR':
        # Safely fetch the profile directly from the model
        from django.shortcuts import get_object_or_404
        profile = get_object_or_404(UniversitySupervisorProfile, user=request.user)
        return render(request, 'accounts/uni_profile.html', {'profile': profile})
        
    # 3. STUDENT PROFILE (Default)
    profile = getattr(request.user, 'student_profile', None)
    if not profile:
        return redirect('accounts:login') # Safety fallback
        
    # Calculate Total Approved Hours for Student
    approved_reports = WeeklyReport.objects.filter(
        student=profile, 
        status=WeeklyReport.Status.APPROVED
    )
    from django.db.models import Sum # Ensure this is imported at the top!
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
    """
    Traffic cop: Routes users to their specific dashboards after login.
    """
    if request.user.role == User.Role.FIELD_SUPERVISOR:
        return redirect('logbook:supervisor_dashboard')
        
    elif request.user.role == User.Role.UNI_SUPERVISOR:
        return redirect('logbook:university_dashboard') # We will build this later
        
    # Default fallback is the student dashboard
    return redirect('logbook:student_dashboard')

@staff_member_required 
def send_supervisor_invite(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        role = request.POST.get('role')
        
        # 1. create or update the invitation 
        invitation, created = SupervisorInvitation.objects.update_or_create(
            email=email,
            defaults={'role': role, 'is_used': False, 'token': uuid.uuid4()}
        )
        
        # 2. Build the secure, clickable URL 
        invite_path = reverse('accounts:supervisor_register', kwargs={'token':invitation.token})
        full_link = request.build_absolute_uri(invite_path)
        
        # 3. send the email using your configured gmail smtp 
        role_name = "University" if role == "UNI" else "Field"
        send_mail(
            subject=f"Invitation to join Truelog as a {role_name} Supervisor",
            message=f"You have been invited to Truelog.\n\nClick here to set up your account: {full_link}\n\nThis link can only be used once.",
            from_email=None, # uses DEFAULT_FROM_EMAIL from settings 
            recipient_list=[email],
        )
        
        messages.success(request, f"Invitation sent successfully to {email}!")
        return redirect('accounts:send_supervisor_invite')
    return render(request, 'accounts/send_invite.html')

def supervisor_register(request, token):
    # 1. verify the token is valid and hasn't been used 
    invitation = get_object_or_404(SupervisorInvitation, token=token, is_used=False)
    
    if request.method == 'POST':
        form = SupervisorRegistrationForm(request.POST)
        if form.is_valid():
            # 2. Create the user 
            user = form.save(commit=False)
            user.email = invitation.email
            user.username = invitation.email
            user.set_password(form.cleaned_data['password'])
            
            # 3. assign role and create profile based on the invitation 
            if invitation.role == 'UNI':
                user.role = User.Role.UNI_SUPERVISOR
                user.save()
                UniversitySupervisorProfile.objects.create(user=user)
            else:
                user.role = User.Role.FIELD_SUPERVISOR
                user.save()
                FieldSupervisorProfile.objects.create(user=user)
            
            # 4. burn the token so it can't be used again
            invitation.is_used = True 
            invitation.save()
            
            # 5. Log them in and route them 
            login(request, user)
            return redirect('logbook:supervisor_dashboard')
        else:
            # pre-fill the form with their locked email 
            form = SupervisorRegistrationForm(initial={'email': invitation.email})
            
        return render(request, 'accounts/supervisor_register.html', {'form': form, 'email': invitation.email})