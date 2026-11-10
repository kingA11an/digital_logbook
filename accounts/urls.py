from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication (Using Django's built-in secure views)
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Registration & Profile (Using our custom views)
    path('register/', views.register_student, name='register'),
    path('profile/', views.user_profile, name='profile'),
    path('redirect/', views.role_redirect, name='role_redirect'),
    
    #supervisor invitation links
    path('invite-supervisor/', views.send_supervisor_invite, name='send_supervisor_invite'),
    path('register/supervisor/<uuid:token>/', views.supervisor_register, name='supervisor_register'),
]