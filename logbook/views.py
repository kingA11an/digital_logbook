from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from .forms import LogEntryForm, EditLogEntryForm
from .models import WeeklyReport, LogEntry
from datetime import date, timedelta

def home_view(request): 
    return render(request, 'home.html')

# the @login_required decorator bounces unauthenticated users back to the login screen
@login_required(login_url='accounts:login')
def student_dashboard(request):
    # Use select_related to efficiently pull the weekly report data attached to these logs
    recent_logs = LogEntry.objects.filter(
        weekly_report__student=request.user.student_profile
    ).select_related('weekly_report').order_by('-date')[:5]
    
    return render(request, 'logbook/student_dashboard.html', {'recent_logs': recent_logs})

@login_required(login_url='accounts:login')
def create_daily_log(request):
    # Grab the logged-in student's profile
    student_profile = request.user.student_profile
    
    if request.method == 'POST':
        form = LogEntryForm(request.POST)
        
        if form.is_valid():
            log_date = form.cleaned_data['date']
            start_date = student_profile.attachment_start_date
            end_date = student_profile.attachment_end_date
            
            # Validation 1: Prevent logging on Sundays
            if log_date.weekday() == 6: 
                form.add_error('date', 'Corporate logs cannot be submitted for Sundays.')
                
            # Validation 2: Ensure the admin has set their attachment period
            elif not start_date or not end_date:
                form.add_error(None, 'Your official attachment period has not been configured. Please contact your supervisor.')
                
            # Validation 3: Ensure the log date falls within the official window
            elif log_date < start_date or log_date > end_date:
                form.add_error('date', f'Date must fall within your attachment period ({start_date.strftime("%b %d")} to {end_date.strftime("%b %d")}).')
                
            else:
                # Map Python's weekday integer to our LogEntry.Days choices
                day_mapping = {
                    0: 'MON',
                    1: 'TUE',
                    2: 'WED',
                    3: 'THU',
                    4: 'FRI',
                    5: 'SAT'
                }
                
                days_difference = (log_date - start_date).days
                calculated_week_number = (days_difference // 7) + 1
                report_start_date = start_date + timedelta(days=(calculated_week_number - 1) * 7)

                # Pause saving to attach our backend-calculated data
                new_log = form.save(commit=False)
                new_log.day_of_week = day_mapping[log_date.weekday()] # Auto-assign the day here!
                
                report, created = WeeklyReport.objects.get_or_create(
                    student=student_profile, 
                    week_number=calculated_week_number,
                    defaults={'start_date': report_start_date}
                )
                
                new_log.weekly_report = report
                
                try:
                    new_log.save()
                    return redirect('logbook:student_dashboard')
                except IntegrityError:
                    form.add_error('date', 'You have already submitted a log entry for this exact date.')
    else:
        form = LogEntryForm()
        
    return render(request, 'logbook/create_log.html', {'form': form})

@login_required(login_url='accounts:login')
def edit_daily_log(request, log_id):
    # Security: Ensure the log belongs to the currently logged-in student
    log = get_object_or_404(
        LogEntry, 
        id=log_id, 
        weekly_report__student=request.user.student_profile
    )
    
    if request.method == 'POST':
        form = EditLogEntryForm(request.POST, instance=log)
        if form.is_valid():
            form.save()
            return redirect('logbook:student_dashboard')
    else:
        form = EditLogEntryForm(instance=log)
        
    return render(request, 'logbook/edit_log.html', {'form': form, 'log': log})


@login_required(login_url='accounts:login')
def delete_daily_log(request, log_id):
    # Security check again
    log = get_object_or_404(
        LogEntry, 
        id=log_id, 
        weekly_report__student=request.user.student_profile
    )
    
    if request.method == 'POST':
        log.delete()
        return redirect('logbook:student_dashboard')
        
    # If they somehow hit this via GET, bounce them back to the dashboard
    return redirect('logbook:student_dashboard')