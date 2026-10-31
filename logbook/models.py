from django.db import models
from django.utils import timezone

class WeeklyReport(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted - Pending Approval"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected - Needs Revision"

    student = models.ForeignKey('accounts.StudentProfile', on_delete=models.CASCADE, related_name='weekly_reports')
    week_number = models.PositiveIntegerField()
    start_date = models.DateField()
    
    # --- NEW FIELDS FOR SUBMISSION ---
    summary = models.TextField(blank=True, help_text="Student's summary of the week's learning and activities.")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'week_number')

    def __str__(self):
        return f"{self.student.user.username} - Week {self.week_number} ({self.get_status_display()})"
    
class LogEntry(models.Model):
    class Days(models.TextChoices):
        MONDAY = "MON", "Monday"
        TUESDAY = "TUE", "Tuesday"
        WEDNESDAY = "WED", "Wednesday"
        THURSDAY = "THU", "Thursday"
        FRIDAY = "FRI", "Friday"
        SATURDAY = "SAT", "Saturday"

    weekly_report = models.ForeignKey(
        WeeklyReport, 
        on_delete=models.CASCADE, 
        related_name='daily_logs'
    )
    date = models.DateField()
    day_of_week = models.CharField(max_length=3, choices=Days.choices)
    activity_description = models.TextField()
    hours_worked = models.DecimalField(max_digits=4, decimal_places=2, default=8.0)

    class Meta:
        ordering = ['date']
        unique_together = ('weekly_report', 'date')

    def __str__(self):
        return f"{self.get_day_of_week_display()} - {self.date}"