from .models import Notification

def global_notifications(request):
    if request.user.is_authenticated:
        unread = request.user.notifications.filter(is_read=False)[:5] 
        count = request.user.notifications.filter(is_read=False).count()
        return {
            'unread_notifications': unread,
            'unread_count':count,
        }
    return {}