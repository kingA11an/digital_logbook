from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from accounts.models import User, SupervisorInvitation

def csrf_failure(request, reason=""):
    return render(request, '403_csrf.html', status=403)

@staff_member_required(login_url='accounts:login')
def admin_dashboard(request):
    # 1. query the database for live metrics
    total_students = User.objects.filter(role=User.Role.STUDENT).count()

    # count both university and field supervisors
    active_supervisors = User.objects.filter(
        role__in=['UNI_SUPERVISOR', 'FIELD_SUPERVISOR']
    ).count()

    # count invites that haven't been redeemed yet
    pending_invites = SupervisorInvitation.objects.filter(is_used=False).count()

    # 5 most recently joined users for the Recent Activity card
    recent_users = User.objects.order_by('-date_joined')[:5]

    # 2. pass the variable claude's template is expecting
    context = {
        'total_students': total_students,
        'active_supervisors': active_supervisors,
        'system_errors': 0,
        'pending_invites': pending_invites,
        'recent_users': recent_users,
        'audit_logs': []
    }

    return render(request, 'admin_dashboard.html', context)
