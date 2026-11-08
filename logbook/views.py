from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Sum
from accounts.models import StudentProfile, FieldSupervisorProfile
from .forms import LogEntryForm, EditLogEntryForm, SubmitWeeklyReportForm
from .models import WeeklyReport, LogEntry
from datetime import date, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model, logout
from django.contrib import messages
from .models import Notification
from django.http import HttpResponse
from django.template.loader import get_template 
from xhtml2pdf import pisa
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()

@login_required(login_url='accounts:login')
def home_view(request):
    # 1. Send admins straight to the django admin panel 
    if request.user.is_superuser or request.user.is_staff:
        return redirect('/admin/')
    
    # 2. Check if they have a student profile safely
    if hasattr(request.user, 'student_profile'):
        return redirect('logbook:student_dashboard') 
    
    # 3. Check if they have a supervisor profile safely 
    if hasattr(request.user, 'field_supervisor'):
        return redirect('logbook:supervisor_dashboard')
    
    # 4. If they have no profile attached (the catch-all safety net)
    logout(request) # log them out so they don't get stuck in an infinite redirect loop 
    messages.error(request, "Your account is not linked to a Student or Supervisor profile. Please contact the system administrator.")
    return redirect('accounts:login')

# the @login_required decorator bounces unauthenticated users back to the login screen
@login_required(login_url='accounts:login')
def student_dashboard(request):
    # safely check if the user actually has a student profile 
    if not hasattr(request.user, 'student_profile'):
        return redirect('home')
    
    # Use select_related to efficiently pull the weekly report data attached to these logs
    recent_logs = LogEntry.objects.filter(
        weekly_report__student=request.user.student_profile
    ).select_related('weekly_report').order_by('-date')[:14]
    
    # calculate total hours logged accross all entries for this student 
    total_hours_data = LogEntry.objects.filter(
        weekly_report__student=request.user.student_profile
    ).aggregate(Sum('hours_worked'))
    
    total_hours = total_hours_data['hours_worked__sum'] or 0.0
    target_hours = 300 
    
    # calculate percentage (capped at 100 %)
    if target_hours > 0:
        progress_percentage = min(round((float(total_hours) / target_hours) * 100, 1), 100)
    else:
        progress_percentage = 0
    
    context = {
        'recent_logs': recent_logs, 
        'total_hours': total_hours,
        'target_hours': target_hours,
        'progress_percentage': progress_percentage,
    }
    
    return render(request, 'logbook/student_dashboard.html', context)

@login_required(login_url='accounts:login')
def create_daily_log(request):
    if not hasattr(request.user, 'student_profile'):
        return redirect('home')
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
    if not hasattr(request.user, 'student_profile'):
        return redirect('home')
    # Security: Ensure the log belongs to the currently logged-in student
    log = get_object_or_404(
        LogEntry, 
        id=log_id, 
        weekly_report__student=request.user.student_profile
    )
    
    # SECURITY LOCK: Only allow editing if the report is a DRAFT or was REJECTED
    if log.weekly_report.status not in [WeeklyReport.Status.DRAFT, WeeklyReport.Status.REJECTED]:
        messages.error(request, "You cannot edit logs for a report that has been submitted or approved.")
        return redirect('logbook:student_dashboard')
    
    if request.method == 'POST':
        form = EditLogEntryForm(request.POST, instance=log)
        if form.is_valid():
            form.save()
            messages.success(request, "Log updated successfully.")
            return redirect('logbook:student_dashboard')
    else:
        form = EditLogEntryForm(instance=log)
        
    return render(request, 'logbook/edit_log.html', {'form': form, 'log': log})


@login_required(login_url='accounts:login')
def delete_daily_log(request, log_id):
    if not hasattr(request.user, 'student_profile'):
        return redirect('home')
    # Security check again
    log = get_object_or_404(
        LogEntry, 
        id=log_id, 
        weekly_report__student=request.user.student_profile
    )
    
    # SECURITY LOCK: Only allow deleting if the report is a DRAFT or was REJECTED
    if log.weekly_report.status not in [WeeklyReport.Status.DRAFT, WeeklyReport.Status.REJECTED]:
        messages.error(request, "You cannot delete logs from a report that has been submitted or approved.")
        return redirect('logbook:student_dashboard')
        
    if request.method == 'POST':
        log.delete()
        messages.success(request, "Log deleted successfully.")
        return redirect('logbook:student_dashboard')
        
    # If they somehow hit this via GET, bounce them back to the dashboard
    return redirect('logbook:student_dashboard')

@login_required(login_url='accounts:login')
def weekly_reports_list(request):
    if not hasattr(request.user, 'student_profile'):
        return redirect('home')
    # Fetch all reports for this student, newest first
    reports = WeeklyReport.objects.filter(
        student=request.user.student_profile
    ).order_by('-week_number')
    
    return render(request, 'logbook/weekly_reports_list.html', {'reports': reports})


@login_required(login_url='accounts:login')
def submit_weekly_report(request, report_id):
    if not hasattr(request.user, 'student_profile'):
        return redirect('home')
    #securely grab the specific report and all its daily logs 
    report = get_object_or_404(WeeklyReport, id=report_id, student=request.user.student_profile)
    
    # security lock: bounce them immediately if it is already submitted/approved 
    if report.status not in [WeeklyReport.Status.DRAFT, WeeklyReport.Status.REJECTED]:
        messages.error(request, "This report has already been submitted or approved and cannot be modified.")
        return redirect('logbook:weekly_reports_list')
    
    logs = LogEntry.objects.filter(weekly_report=report).order_by('date')
    
    if request.method == 'POST':
        form = SubmitWeeklyReportForm(request.POST, instance=report)
        if form.is_valid():
            saved_report = form.save(commit=False)
            saved_report.status = WeeklyReport.Status.SUBMITTED
            saved_report.submitted_at = timezone.now()
            saved_report.save()
            
            # email trigger: notify supervisor 
            try: 
                # safely attempt to get the assigned supervisor's email 
                supervisor_email = report.student.field_supervisor.user.email
                
                if supervisor_email:
                    subject = f"Action Required: Truelog Week {report.week_number} Submission"
                    message = (
                        f"Hello,\n\n"
                        f"{request.user.first_name or request.user.username} has just submitted their "
                        f"Week {report.week_number} logbook report.\n\n"
                        f"Please log in to the Truelog portal to review and approve."
                    )
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [supervisor_email],
                        fail_silently=False,
                    )
            except AttributeError as e:
                # print the actual error so we know if it is a missing superviosr or a code bug 
                print(f"Failed to send supervisor email. Reason: {e}")
            except Exception as e:
                print(f"SMTP Error: {e}")
            
            messages.success(request, f"Week {report.week_number} report submitted successfully!")
            return redirect('logbook:weekly_reports_list')
        else: 
            print(f"FORM IVALID: {form.errors}")
            return redirect('logbook:weekly_reports_list')
    else:
        form = SubmitWeeklyReportForm(instance=report)
        
    context = {
        'report': report,
        'logs': logs,
        'form': form,
    }
    return render(request, 'logbook/submit_weekly_report.html', context)

@login_required(login_url='accounts:login')
def supervisor_dashboard(request):
    # Security: Kick out anyone who isn't a Field Supervisor
    if request.user.role != getattr(request.user.__class__.Role, 'FIELD_SUPERVISOR', 'FIELD_SUPERVISOR'):
        return redirect('logbook:student_dashboard')

    # Fetch reports waiting for this specific supervisor's approval
    # We query WeeklyReport, navigating through the StudentProfile to find matching supervisors
    pending_reports = WeeklyReport.objects.filter(
        student__field_supervisor__user=request.user,
        status=WeeklyReport.Status.SUBMITTED
    ).select_related('student__user', 'student').order_by('submitted_at')

    # Fetch reports they have already reviewed (Approved or Rejected)
    reviewed_reports = WeeklyReport.objects.filter(
        student__field_supervisor__user=request.user
    ).exclude(
        status__in=[WeeklyReport.Status.DRAFT, WeeklyReport.Status.SUBMITTED]
    ).select_related('student__user', 'student').order_by('-submitted_at')[:10] # Just the last 10

    context = {
        'pending_reports': pending_reports,
        'reviewed_reports': reviewed_reports,
    }
    return render(request, 'logbook/supervisor_dashboard.html', context)

@login_required(login_url='accounts:login')
def review_weekly_report(request, report_id):
    # Security: Kick out anyone who isn't a Field Supervisor
    if request.user.role != getattr(request.user.__class__.Role, 'FIELD_SUPERVISOR', 'FIELD_SUPERVISOR'):
        return redirect('logbook:student_dashboard')

    # Fetch the report, ensuring it belongs to a student assigned to THIS supervisor
    report = get_object_or_404(
        WeeklyReport, 
        id=report_id, 
        student__field_supervisor__user=request.user,
        status=WeeklyReport.Status.SUBMITTED
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            report.status = WeeklyReport.Status.APPROVED
            report.save()
            
            # --- NOTIFICATION TRIGGER ---
            Notification.objects.create(
                recipient=report.student.user,
                message=f"Your Week {report.week_number} report was APPROVED by your supervisor."
            )
            
            # --- EMAIL TRIGGER: Notify Student ---
            try:
                student_email = report.student.user.email
                student_name = report.student.user.first_name or report.student.user.username
                
                if student_email:  # Safety check in case the user has no email saved
                    send_mail(
                        f"Truelog Update: Week {report.week_number} Approved",
                        f"Hello {student_name},\n\nYour Week {report.week_number} attachment report has been approved by your field supervisor.\n\nLog in to the Truelog dashboard to view your progress and download your official PDF.",
                        settings.DEFAULT_FROM_EMAIL,
                        [student_email],
                        fail_silently=False,
                    )
            except Exception as e:
                print(f"Email failed to send: {e}")
            
            messages.success(request, f"Week {report.week_number} report for {report.student.user.username} approved.")
            
        elif action == 'reject':
            report.status = WeeklyReport.Status.REJECTED
            report.save()
            
            # --- NOTIFICATION TRIGGER ---
            Notification.objects.create(
                recipient=report.student.user,
                message=f"Your Week {report.week_number} report was REJECTED by your supervisor. Please review and resubmit."
            )
            
            # --- EMAIL TRIGGER: Notify Student ---
            try:
                student_email = report.student.user.email
                student_name = report.student.user.first_name or report.student.user.username
                
                if student_email: # Safety check
                    send_mail(
                        f"Truelog Update: Week {report.week_number} Rejected",
                        f"Hello {student_name},\n\nYour Week {report.week_number} attachment report has been rejected by your field supervisor. Please review their feedback and resubmit.\n\nLog in to the Truelog dashboard to make the necessary changes.",
                        settings.DEFAULT_FROM_EMAIL,
                        [student_email],
                        fail_silently=False,
                    )
            except Exception as e:
                print(f"Email failed to send: {e}")
            
            messages.error(request, f"Week {report.week_number} report for {report.student.user.username} rejected.")
            
        return redirect('logbook:supervisor_dashboard')

    # For GET request: Fetch daily logs to display to the supervisor
    daily_logs = report.daily_logs.all().order_by('date')

    context = {
        'report': report,
        'daily_logs': daily_logs,
    }
    return render(request, 'logbook/review_report.html', context)

@login_required(login_url='accounts:login')
def university_dashboard(request):
    # Security: Kick out anyone who isn't a University Supervisor
    if request.user.role != getattr(request.user.__class__.Role, 'UNI_SUPERVISOR', 'UNI_SUPERVISOR'):
        return redirect('logbook:student_dashboard')
    
    # 1. Unassigned Students: Students who need a field supervisor assigned 
    unassigned_students = StudentProfile.objects.filter(
        field_supervisor__isnull=True
    ).select_related('user').order_by('-user__date_joined')
    
    # 2. Assigned students: the bird's eye view of active attachments 
    assigned_students = StudentProfile.objects.filter(
        field_supervisor__isnull=False
    ).select_related('user', 'field_supervisor', 'field_supervisor__user').order_by('user__first_name')
    
    context = {
        'unassigned_students': unassigned_students,
        'assigned_students': assigned_students,
    }
    return render(request, 'logbook/university_dashboard.html', context)

@login_required(login_url='accounts:login')
def assign_supervisor(request, student_id):
    # Security: Kick out anyone who isn't a University Supervisor
    if request.user.role != getattr(request.user.__class__.Role, 'UNI_SUPERVISOR', 'UNI_SUPERVISOR'):
        return redirect('logbook:student_dashboard')

    student = get_object_or_404(StudentProfile, id=student_id)
    
    # Fetch all registered field supervisors
    supervisors = FieldSupervisorProfile.objects.all().select_related('user').order_by('company_name')

    if request.method == 'POST':
        supervisor_id = request.POST.get('supervisor_id')
        if supervisor_id:
            supervisor = get_object_or_404(FieldSupervisorProfile, id=supervisor_id)
            student.field_supervisor = supervisor
            student.save()
            messages.success(request, f"Successfully assigned {supervisor.user.get_full_name() or supervisor.user.username} to {student.user.get_full_name() or student.user.username}.")
            return redirect('logbook:university_dashboard')

    return render(request, 'logbook/assign_supervisor.html', {
        'student': student, 
        'supervisors': supervisors
    })
    
@login_required(login_url='accounts:login')
def university_student_progress(request, student_id):
    # security: only uni supervisors can access this 
    if request.user.role != getattr(request.user.__class__.Role, 'UNI_SUPERVISOR', 'UNI_SUPERVISOR'):
        return redirect('logbook:student_dashboard')
    
    student = get_object_or_404(StudentProfile, id=student_id)
    
    # fetch all reports ordered by week 
    reports = WeeklyReport.objects.filter(student=student).order_by('week_number')
    
    # calculate total approved hours 
    approved_reports = reports.filter(status=WeeklyReport.Status.APPROVED)
    total_approved_hours = LogEntry.objects.filter(
        weekly_report__in=approved_reports
    ).aggregate(Sum('hours_worked'))['hours_worked__sum'] or 0.0
    
    context = {
        'student': student,
        'reports': reports,  # <-- Make sure this is just 'reports'
        'total_approved_hours': total_approved_hours,
    }
    return render(request, 'logbook/uni_student_progress.html', context)

@login_required(login_url='accounts:login')
def student_view_report(request, report_id):
    if not hasattr(request.user, 'student_profile'):
        return redirect('home')
    
    # Ensure only the student who owns the report can view it
    report = get_object_or_404(WeeklyReport, id=report_id, student__user=request.user)
    
    # Fetch all daily logs attached to this report
    daily_logs = report.daily_logs.all().order_by('date')
    
    # Mark all unread notifications for this user as read
    unread_notes = request.user.notifications.filter(is_read=False)
    if unread_notes.exists():
        unread_notes.update(is_read=True)

    context = {
        'report': report,
        'daily_logs': daily_logs,
    }
    return render(request, 'logbook/student_view_report.html', context)

@login_required(login_url='accounts:login')
def export_report_pdf(request, report_id):
    if not hasattr(request.user, 'student_profile'):
        return redirect('home')
    # Fetch the specific report 
    report = get_object_or_404(WeeklyReport, id=report_id)
    
    # Fetch the daily logs attached to this report 
    logs = LogEntry.objects.filter(weekly_report=report).order_by('date')
    
    template_path = 'logbook/pdf_template.html'
    context = {
        'report': report,
        'logs': logs,
        'student': request.user,
    }
    
    # Create the HTTP response with pdf headers 
    response = HttpResponse(content_type='application/pdf')
    # Use 'attachment;' to force download, or 'inline;' to open in browser
    response['Content-Disposition'] = f'inline; filename="Week_{report.week_number}_Logbook.pdf"'
    
    # Render HTML and convert to pdf 
    template = get_template(template_path)
    html = template.render(context)
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse(f'Error generating PDF: {pisa_status.err}')
    
    return response