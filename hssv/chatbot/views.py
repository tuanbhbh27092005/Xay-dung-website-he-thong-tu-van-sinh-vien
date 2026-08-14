import json
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required

from .models import ChatSession, ChatMessage, ContentReport
from .services.conversation import handle_turn
from .services import moderation

logger = logging.getLogger(__name__)


def _get_or_create_session(request) -> ChatSession:
    """Lấy hoặc tạo phiên chat dựa trên session_key của Django."""
    if not request.session.session_key:
        request.session.save()
    sk = request.session.session_key
    user = request.user if request.user.is_authenticated else None

    session, _ = ChatSession.objects.get_or_create(
        session_key=sk,
        defaults={'user': user},
    )
    if user and not session.user:
        session.user = user
        session.save(update_fields=['user'])
    return session


@login_required
def chat_page(request):
    """
    Trang chat đầy đủ với lịch sử.
    REQUIRE LOGIN: chatbot là tính năng cá nhân hóa (lưu lịch sử + có thể
    escalate câu hỏi tới tư vấn viên). Anonymous → redirect sang login với
    ?next=/chatbot/ để sau khi đăng nhập tự quay lại.
    """
    session = _get_or_create_session(request)

    # Nếu phiên mới (chưa có messages), gửi greeting tự động vào DB
    if not session.messages.exists():
        from .services.conversation import _greet_messages
        for content, metadata in _greet_messages():
            ChatMessage.objects.create(session=session, role='bot', content=content, metadata=metadata)

    history = session.messages.all()
    return render(request, 'chatbot/chat.html', {
        'session': session,
        'history': history,
    })


@login_required
@require_POST
@csrf_protect
def send_message(request):
    """
    API endpoint nhận user input (text hoặc action), trả về list messages mới của bot.

    Request body:
        {"text": "...", "action": "select_dept", "value": 5}

    Response:
        {
          "messages": [
            {"id": 123, "role": "user", "content": "...", "metadata": null, "created_at": "..."},
            {"id": 124, "role": "bot", "content": "...", "metadata": {...}, "created_at": "..."}
          ],
          "session_state": "collecting_major"
        }
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Body phải là JSON hợp lệ.'}, status=400)

    text = (data.get('text') or '').strip()
    action = data.get('action')
    value = data.get('value')

    if not text and not action:
        return JsonResponse({'error': 'Cần text hoặc action.'}, status=400)
    if text and len(text) > 2000:
        return JsonResponse({'error': 'Tin nhắn quá dài (tối đa 2000 ký tự).'}, status=400)

    session = _get_or_create_session(request)
    new_messages = []

    # 1. Lưu input của user (nếu có text hoặc nếu action có nhãn rõ)
    user_label = text
    if action and not text:
        # Lưu nhãn của button làm "user message" để history dễ đọc
        action_label_map = {
            'request_escalation': '✗ Gửi câu hỏi tới tư vấn viên',
            'submit_escalation': 'Gửi câu hỏi tới tư vấn viên',
            'cancel_escalation': 'Huỷ',
            'restart': '🔄 Hội thoại mới',
            'set_filters': '🎯 Đặt phạm vi tư vấn',
        }
        user_label = action_label_map.get(action, action)

    # ─── Kiểm duyệt ngôn từ trên text user gõ ───
    profanity_matched = []
    if text:
        profanity_matched = moderation.find_profanity(text)

    if user_label:
        u_msg = ChatMessage.objects.create(
            session=session,
            role='user',
            content=user_label,
            needs_advisor=bool(profanity_matched),
        )
        new_messages.append(_serialize_msg(u_msg))

        # Nếu phát hiện ngôn từ vi phạm → tạo ContentReport + trả về cảnh báo
        if profanity_matched:
            ContentReport.objects.create(
                source='chat',
                chat_message=u_msg,
                content_user=request.user if request.user.is_authenticated else None,
                snapshot_text=user_label,
                matched_words=', '.join(profanity_matched)[:300],
                status='pending',
            )
            warn_msg = ChatMessage.objects.create(
                session=session,
                role='bot',
                content=(
                    "⚠️ Tin nhắn của bạn chứa ngôn từ không phù hợp và đã được gửi tới "
                    "ban tư vấn để xem xét. Vui lòng dùng ngôn ngữ lịch sự khi trao đổi. "
                    "Bạn có thể mô tả lại vấn đề một cách rõ ràng hơn."
                ),
            )
            new_messages.append(_serialize_msg(warn_msg))
            return JsonResponse({
                'messages': new_messages,
                'session_state': session.state,
                'moderation_flagged': True,
            })

    # 2. Chạy state machine
    try:
        outgoing = handle_turn(
            session,
            action=action,
            value=value,
            text=text,
            user=request.user if request.user.is_authenticated else None,
        )
    except Exception as e:
        logger.exception("State machine crash")
        return JsonResponse({
            'error': 'Hệ thống gặp lỗi khi xử lý.',
            'detail': str(e),
        }, status=500)

    # 3. Persist các message bot → list response
    for content, metadata in outgoing:
        bot_msg = ChatMessage.objects.create(
            session=session,
            role='bot',
            content=content,
            metadata=metadata,
        )
        new_messages.append(_serialize_msg(bot_msg))

    return JsonResponse({
        'messages': new_messages,
        'session_state': session.state,
    })


def _serialize_msg(m: ChatMessage) -> dict:
    return {
        'id': m.id,
        'role': m.role,
        'content': m.content,
        'metadata': m.metadata,
        'created_at': m.created_at.isoformat(),
    }


@login_required
@require_GET
def filter_options(request):
    """
    Trả về danh sách khoa, ngành, loại câu hỏi cho dropdown filter trên chat UI.
    Đính kèm dept/major/category đã chọn trong session hiện tại.
    """
    from questions.models import Department, Major, QuestionCategory

    session = _get_or_create_session(request)
    departments = list(Department.objects.order_by('name').values('id', 'name'))
    majors = list(
        Major.objects.select_related('department').order_by('department__name', 'name')
        .values('id', 'name', 'department_id')
    )
    categories = list(QuestionCategory.objects.order_by('name').values('id', 'name'))

    return JsonResponse({
        'departments': departments,
        'majors': majors,
        'categories': categories,
        'selected': {
            'dept_id': session.collected_dept_id,
            'major_id': session.collected_major_id,
            'category_id': session.collected_category_id,
        },
    })


@login_required
def chat_history_list(request):
    """Danh sách các phiên chat đã có của user (có phân trang 10 phiên/trang)."""
    from django.core.paginator import Paginator

    sessions = (
        ChatSession.objects
        .filter(user=request.user)
        .order_by('-started_at')
        .prefetch_related('messages')
    )

    paginator = Paginator(sessions, 10)
    page_num = request.GET.get('page', 1)
    page = paginator.get_page(page_num)

    # Đính kèm preview tin nhắn đầu (user) và số message
    items = []
    for s in page.object_list:
        first_user_msg = s.messages.filter(role='user').first()
        last_msg = s.messages.order_by('-created_at').first()
        # Preview: ưu tiên câu mô tả ban đầu, nếu rỗng thì lấy user message đầu tiên,
        # nếu vẫn không có thì lấy bot message đầu (chỉ là greeting).
        if s.initial_question:
            preview = s.initial_question
        elif first_user_msg:
            preview = first_user_msg.content
        else:
            preview = '(Phiên trống - chưa có nội dung)'

        items.append({
            'session': s,
            'preview': preview,
            'message_count': s.messages.count(),
            'last_at': last_msg.created_at if last_msg else s.started_at,
        })

    return render(request, 'chatbot/history_list.html', {
        'items': items,
        'page': page,
        'paginator': paginator,
    })


@login_required
def chat_history_detail(request, session_id):
    """Xem chi tiết một phiên chat cũ (read-only)."""
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return render(request, 'chatbot/history_detail.html', {
            'session': None,
            'chat_messages': [],
            'not_found': True,
        })

    chat_messages = session.messages.all().order_by('created_at')
    return render(request, 'chatbot/history_detail.html', {
        'session': session,
        'chat_messages': chat_messages,
        'not_found': False,
    })


@login_required
@require_POST
@csrf_protect
def chat_history_delete(request, session_id):
    """Xoá một phiên chat của chính user."""
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
        session.delete()
        return JsonResponse({'success': True})
    except ChatSession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Không tìm thấy'}, status=404)


@login_required
@require_POST
@csrf_protect
def reset_session(request):
    """Reset session về initial state. Useful khi user click 'Bắt đầu lại' từ UI."""
    session = _get_or_create_session(request)
    session.reset()
    # Xoá history luôn để UI sạch
    session.messages.all().delete()

    # Tạo greeting mới
    from .services.conversation import _greet_messages
    new_messages = []
    for content, metadata in _greet_messages():
        m = ChatMessage.objects.create(session=session, role='bot', content=content, metadata=metadata)
        new_messages.append(_serialize_msg(m))

    return JsonResponse({'messages': new_messages, 'session_state': session.state})
