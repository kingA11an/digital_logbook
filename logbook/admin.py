from django.contrib import admin
from .models import WeeklyReport, LogEntry

class LogEntryInline(admin.TabularInline):
    model = LogEntry
    extra = 1 # Shows one blank extra row for adding new entries quickly

class WeeklyReportAdmin(admin.ModelAdmin):
    list_display = ('week_number', 'student', 'start_date', 'status')
    list_filter = ('status', 'week_number')
    search_fields = ('student__user__username', 'student__registration_number')
    inlines = [LogEntryInline]

admin.site.register(WeeklyReport, WeeklyReportAdmin)
admin.site.register(LogEntry)