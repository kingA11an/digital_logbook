from django import forms
from django.contrib.auth import get_user_model
from .models import StudentProfile
from django.core.exceptions import ValidationError

User = get_user_model()

class StudentRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Create a strong password'}))
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm your password'}), label="Confirm Password")
    
    # Profile specific fields 
    registration_number = forms.CharField(max_length=50)
    course = forms.CharField(max_length=150)
    attachment_start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    attachment_end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
    def clean(self):
        cleaned_data = super().clean()
        
        # 1. grab all fields needed for cross-validation 
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        start = cleaned_data.get('attachment_start_date')
        end = cleaned_data.get('attachment_end_date')
        
        # 2. Check for password mismatch 
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Passwords do not match.")
            
        # 3. Check for backward dates 
        if start and end and end < start:
            self.add_error('attachment_end_date', "The end date cannot be earlier than the start date.")
            
        # 4. If any errors were added, raise ValidationError to halt the form 
        if self.errors:
            raise forms.ValidationError("Please correct the errors below.")
        
        return cleaned_data
    
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']
        
    
    def clean_attachment_start_date(self):
        start_date = self.cleaned_data.get('attachment_start_date')
        # .weekday() returns 6 for Sunday
        if start_date and start_date.weekday() == 6:
            raise ValidationError("Attachment start dates cannot fall on a Sunday.")
        return start_date

    def clean_attachment_end_date(self):
        end_date = self.cleaned_data.get('attachment_end_date')
        if end_date and end_date.weekday() == 6:
            raise ValidationError("Attachment end dates cannot fall on a Sunday.")
        return end_date
    
class SupervisorRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=50)
    password = forms.CharField(widget=forms.PasswordInput())
    password_confirm = forms.CharField(widget=forms.PasswordInput())
        
    class Meta:
        model = User
        fields = ['first_name', 'last_name']
            
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Passwords do not match.")
            
        if self.errors:
            raise forms.ValidationError("Please correct the errors below.")
        
        return cleaned_data
    