from django import forms
from .models import LogEntry

class LogEntryForm(forms.ModelForm):
    class Meta:
        model = LogEntry
        # We only ask the user for these 4 fields. 
        # The 'weekly_report' will be assigned automatically by our view behind the scenes.
        fields = ['date', 'day_of_week', 'activity_description', 'hours_worked']
        
        # We attach Tailwind CSS classes directly to the form inputs here
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-darkbg text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-500'
            }),
            'day_of_week': forms.Select(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-darkbg text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-500'
            }),
            'activity_description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-darkbg text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-500',
                'placeholder': 'Describe the tasks you completed today...'
            }),
            'hours_worked': forms.NumberInput(attrs={
                'step': '0.5',
                'min' : '0.5',
                'max' : '10',
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-darkbg text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-500'
            }),
        }