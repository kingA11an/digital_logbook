from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        FIELD_SUPERVISOR = "FIELD_SUPERVISOR", "Field Supervisor"
        UNI_SUPERVISOR = "UNI_SUPERVISOR", "University Supervisor"
        ADMIN = "ADMIN", "University Admin"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        help_text="Primary role defining user access level."
    )

class FieldSupervisorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="field_supervisor_profile")
    company_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.company_name})"

class UniversitySupervisorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="uni_supervisor_profile")
    department = models.CharField(max_length=150)
    staff_id = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.department}"

class StudentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    registration_number = models.CharField(max_length=50, unique=True)
    course = models.CharField(max_length=150)
    field_supervisor = models.ForeignKey(
        FieldSupervisorProfile, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="assigned_students"
    )
    
    university_supervisor = models.ForeignKey(
        UniversitySupervisorProfile, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="assigned_students"
    )
    attachment_start_date = models.DateField(null=True, blank=True, help_text="The official start date of the industrial attachment.")
    attachment_end_date = models.DateField(null=True, blank=True, help_text="The official end date of the industrial attachment.")

    def __str__(self):
        return f"{self.registration_number} - {self.user.get_full_name() or self.user.username}"