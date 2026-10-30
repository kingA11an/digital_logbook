from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from .forms import LogEntryForm
from .models import WeeklyReport, LogEntry
from datetime import date

def home_view(request): 
    return render(request, 'home.html')

# the @login_required decorator bounces unauthenticated users back to the login screen
@login_required(login_url='accounts:login')
def student_dashboard(request):
    # fetch the 5 most recent logs belonging to the currently logged-in student 
    recent_logs = LogEntry.objects.filter(
        weekly_report__student=request.user.student_profile
    ).order_by('-date')[:5]
    return render(request, 'logbook/student_dashboard.html', {'recent_logs': recent_logs})

@login_required(login_url='accounts:login')
def create_daily_log(request):
    if request.method == 'POST':
        form = LogEntryForm(request.POST)
        
        if form.is_valid():
            new_log = form.save(commit=False)
            
            report, created = WeeklyReport.objects.get_or_create(
                student=request.user.student_profile, 
                week_number=1,
                defaults={'start_date': date.today()}
            )
            
            new_log.weekly_report = report
            
            # --- NEW ERROR HANDLING BLOCK ---
            try:
                new_log.save()
                return redirect('logbook:student_dashboard')
            except IntegrityError:
                # If the database rejects it due to unique_together constraint, send an error to the form
                form.add_error('date', 'You have already submitted a log entry for this exact date.')
            # --------------------------------
    else:
        form = LogEntryForm()
        
    return render(request, 'logbook/create_log.html', {'form': form})