from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import StudentRegistrationForm
from .models import StudentProfile, User
from django.db.models import Sum
from logbook.models import LogEntry, WeeklyReport
from django.contrib.auth.decorators import login_required

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
        
    # 2. STUDENT PROFILE (Default)
    profile = getattr(request.user, 'student_profile', None)
    if not profile:
        return redirect('accounts:login') # Safety fallback
        
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
    """
    Traffic cop: Routes users to their specific dashboards after login.
    """
    if request.user.role == User.Role.FIELD_SUPERVISOR:
        return redirect('logbook:supervisor_dashboard')
        
    elif request.user.role == User.Role.UNI_SUPERVISOR:
        return redirect('logbook:university_dashboard') # We will build this later
        
    # Default fallback is the student dashboard
    return redirect('logbook:student_dashboard')