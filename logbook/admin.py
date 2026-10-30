from django.contrib import admin
from .models import WeeklyReport, LogEntry

@admin.register(WeeklyReport)
class WeeklyReportAdmin(admin.ModelAdmin):
    list_display = ('week_number', 'student', 'start_date', 'status')
    list_filter = ('status', 'week_number')
    search_fields = ('student__user__username',)

@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('date', 'day_of_week', 'weekly_report', 'hours_worked')
    list_filter = ('day_of_week', 'weekly_report__week_number')