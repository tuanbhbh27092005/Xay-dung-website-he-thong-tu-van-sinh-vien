"""
File này thay thế hoàn toàn accounts/views.py hiện tại.
Chỉ thay đổi: profile_view giờ truyền danh sách câu hỏi của user vào context.
Các view khác giữ nguyên.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import CustomUserCreationForm, CustomAuthenticationForm


def _safe_next(request, fallback='home'):
    """
    Lấy URL `?next=` từ request POST/GET, validate để tránh open redirect.
    Trả về fallback nếu next rỗng hoặc trỏ ra ngoài domain.
    """
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return fallback


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Đăng ký thành công!')
            # Sau khi đăng ký xong, nếu có `?next=` (vd. user định vào /chatbot/
            # mà chưa có account → bấm Đăng ký) thì auto chuyển tới đó.
            return redirect(_safe_next(request))
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {
        'form': form,
        'next': request.GET.get('next', ''),
    })


def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Chào mừng trở lại, {user.get_full_name() or user.username}!')
            # Tôn trọng `?next=`: cho phép Django tự động đưa user về trang
            # họ đang muốn vào (vd. /chatbot/) sau khi đăng nhập thành công.
            return redirect(_safe_next(request))
    else:
        form = CustomAuthenticationForm()
    return render(request, 'accounts/login.html', {
        'form': form,
        'next': request.GET.get('next', ''),
    })


def logout_view(request):
    logout(request)
    messages.success(request, 'Đăng xuất thành công!')
    return redirect('home')


@login_required
def profile_view(request):
    """
    Hồ sơ cá nhân CHỈ dành cho user thường (sinh viên / phụ huynh / cựu sv / hs phổ thông).
    Advisor / Admin không có "hồ sơ cá nhân" → tự redirect sang admin dashboard
    (thông tin của họ đã hiển thị ở admin panel với học hàm/chức vụ).
    """
    # Nếu user là advisor hoặc admin → không cần trang hồ sơ cá nhân
    if hasattr(request.user, 'advisorprofile') and request.user.advisorprofile is not None:
        return redirect('admin_dashboard')

    # User thường → load câu hỏi của họ để hiển thị trong profile
    from questions.models import Question  # import bên trong để tránh circular import
    user_questions = Question.objects.filter(
        user=request.user
    ).select_related('major', 'category').order_by('-created_at')

    # Chia thành 2 nhóm cho UI dễ thấy
    pending_questions = user_questions.filter(status='pending')
    answered_questions = user_questions.filter(status='answered')

    return render(request, 'accounts/profile.html', {
        'user_questions': user_questions,
        'pending_questions': pending_questions,
        'answered_questions': answered_questions,
        'total_questions': user_questions.count(),
        'total_pending': pending_questions.count(),
        'total_answered': answered_questions.count(),
    })
