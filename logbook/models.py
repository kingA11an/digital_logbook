from django.db import models

class WeeklyReport(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted for Review"
        NEEDS_REVISION = "NEEDS_REVISION", "Needs Revision"
        APPROVED = "APPROVED", "Approved"

    student = models.ForeignKey(
        'accounts.StudentProfile', 
        on_delete=models.CASCADE, 
        related_name='weekly_reports'
    )
    week_number = models.PositiveIntegerField()
    start_date = models.DateField(help_text="Monday of this week")
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.DRAFT
    )
    supervisor_comments = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('student', 'week_number')
        ordering = ['-week_number']

    def __str__(self):
        return f"Week {self.week_number} - {self.student.user.get_full_name()} ({self.get_status_display()})"

class LogEntry(models.Model):
    class Days(models.TextChoices):
        MONDAY = "MON", "Monday"
        TUESDAY = "TUE", "Tuesday"
        WEDNESDAY = "WED", "Wednesday"
        THURSDAY = "THU", "Thursday"
        FRIDAY = "FRI", "Friday"

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