from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, StudentProfile, FieldSupervisorProfile, UniversitySupervisorProfile

# We use Django's built-in UserAdmin to safely handle password hashing in the admin panel
admin.site.register(User, UserAdmin)

# Register the profile models so we can view and edit them
admin.site.register(StudentProfile)
admin.site.register(FieldSupervisorProfile)
admin.site.register(UniversitySupervisorProfile)