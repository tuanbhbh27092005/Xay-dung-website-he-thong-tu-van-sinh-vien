from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from .models import Notification


@login_required
def notification_list(request):
    """Trang xem tất cả thông báo của người dùng."""
    notifications_qs = request.user.notifications.all()
    paginator = Paginator(notifications_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'notifications/notification_list.html', {
        'page_obj': page_obj,
    })


@login_required
def mark_as_read(request, pk):
    """Đánh dấu 1 thông báo là đã đọc và chuyển hướng đến target_url."""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])

    if notification.target_url:
        return redirect(notification.target_url)
    return redirect('notifications:list')


@login_required
@require_POST
def mark_all_as_read(request):
    """Đánh dấu toàn bộ thông báo của người dùng là đã đọc (hỗ trợ AJAX)."""
    request.user.notifications.filter(is_read=False).update(is_read=True)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({'status': 'ok', 'message': 'Đã đánh dấu tất cả là đã đọc.'})
    return redirect('notifications:list')


@login_required
def unread_count_api(request):
    """API trả về số lượng thông báo chưa đọc."""
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({'unread_count': count})
