from .models import Notification

def notification_context(request):
    """Context processor cung cấp thông báo cho toàn bộ templates."""
    if not request.user.is_authenticated:
        return {
            'unread_notifications_count': 0,
            'recent_notifications': [],
        }

    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    recent = Notification.objects.filter(recipient=request.user)[:6]
    return {
        'unread_notifications_count': unread_count,
        'recent_notifications': recent,
    }
