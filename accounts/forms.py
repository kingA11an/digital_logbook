from django import forms
from django.contrib.auth import get_user_model
from .models import StudentProfile

User = get_user_model()

class StudentRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Create a strong password'}))
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm your password'}), label="Confirm Password")
    
    # Profile specific fields 
    registration_number = forms.CharField(max_length=50)
    course = forms.CharField(max_length=150)
    attachment_start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    attachment_end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']
        
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Passwords do not match.")
            
        return cleaned_data 