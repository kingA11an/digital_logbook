from django.urls import path
from . import views

app_name = 'logbook'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/student/log/new/', views.create_daily_log, name='create_log'),
]