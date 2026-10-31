from django.urls import path
from . import views

app_name = 'logbook'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/student/log/new/', views.create_daily_log, name='create_log'),
    
    # New endpoints for Edit and Delete
    path('dashboard/student/log/<int:log_id>/edit/', views.edit_daily_log, name='edit_log'),
    path('dashboard/student/log/<int:log_id>/delete/', views.delete_daily_log, name='delete_log'),
    path('dashboard/student/reports/', views.weekly_reports_list, name='weekly_reports_list'),
    path('dashboard/student/reports/<int:report_id>/submit/', views.submit_weekly_report, name='submit_weekly_report'),
]