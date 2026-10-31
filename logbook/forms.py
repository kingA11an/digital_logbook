from django import forms
from .models import LogEntry, WeeklyReport

class LogEntryForm(forms.ModelForm):
    class Meta:
        model = LogEntry
        # Removed 'day_of_week' - the backend will handle it automatically
        fields = ['date', 'activity_description', 'hours_worked']
        
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-darkbg text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-500'
            }),
            'activity_description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full px-4 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-darkbg text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-500',
                'placeholder': 'Describe the tasks you completed today...'
            }),
            'hours_worked': forms.NumberInput(attrs={
                'step': '0.5',
                'min': '0.5',
                'max': '10',
                'class': 'w-full px-4 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-darkbg text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-500'
            }),
        }

class EditLogEntryForm(forms.ModelForm):
    class Meta:
        model = LogEntry
        fields = ['activity_description', 'hours_worked'] # Date is strictly locked out
        
        widgets = {
            'activity_description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full px-4 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-darkbg text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-500',
            }),
            'hours_worked': forms.NumberInput(attrs={
                'step': '0.5',
                'min': '0.5',
                'max': '10',
                'class': 'w-full px-4 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-darkbg text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-500'
            }),
        }

class SubmitWeeklyReportForm(forms.ModelForm):
    class Meta:
        model = WeeklyReport
        fields = ['summary']
        
        widgets = {
            'summary': forms.Textarea(attrs={
                'rows': 6,
                'class': 'w-full px-4 py-3 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-darkbg text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-500',
                'placeholder': 'Summarize your key learnings, challenges faced, and overall progress this week...'
            }),
        }