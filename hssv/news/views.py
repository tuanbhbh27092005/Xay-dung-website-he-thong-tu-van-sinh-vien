from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Count, Q, F
from django.core.paginator import Paginator

from .models import News, Comment, NewsLike
from .forms import NewsForm, CommentForm


# ============================================================
# HELPERS
# ============================================================
def _is_advisor(user):
    if not user.is_authenticated:
        return False
    return hasattr(user, 'advisorprofile') and user.advisorprofile is not None


def _require_advisor(view_func):
    """Decorator chặn user không phải tư vấn viên."""
    def wrapper(request, *args, **kwargs):
        if not _is_advisor(request.user):
            return HttpResponseForbidden(
                "Chỉ tư vấn viên hoặc quản trị viên mới có quyền truy cập trang này."
            )
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ============================================================
# PUBLIC VIEWS
# ============================================================
def news_list(request):
    """Danh sách tin tức công khai, hỗ trợ filter theo category."""
    # Ordering: tin nổi bật (is_featured=True) lên trước, sau đó theo ngày mới nhất
    qs = (
        News.objects.filter(is_published=True)
        .select_related('author', 'department')
        .order_by('-is_featured', '-created_at')
    )

    # Filter theo category
    selected_cat = request.GET.get('cat', '').strip()
    if selected_cat:
        qs = qs.filter(category=selected_cat)

    # Filter theo keyword
    keyword = request.GET.get('q', '').strip()
    if keyword:
        qs = qs.filter(Q(title__icontains=keyword) | Q(summary__icontains=keyword))

    # Pagination
    paginator = Paginator(qs, 9)  # 9 cards/trang (3x3 grid)
    page_num = request.GET.get('page', 1)
    page = paginator.get_page(page_num)

    # Hero featured: ưu tiên tin có is_featured=True, fallback bài mới nhất
    featured = (
        News.objects.filter(is_published=True, is_featured=True).order_by('-created_at').first()
        or News.objects.filter(is_published=True).order_by('-created_at').first()
    )

    return render(request, 'news/news_list.html', {
        'page': page,
        'news_list': page.object_list,
        'categories': News.CATEGORY_CHOICES,
        'selected_cat': selected_cat,
        'keyword': keyword,
        'featured': featured,
    })


def news_detail(request, slug):
    """Trang chi tiết tin + bình luận."""
    news = get_object_or_404(
        News.objects.select_related('author', 'department'),
        slug=slug, is_published=True,
    )

    # Tăng view count (bỏ qua chính tác giả)
    if not request.user.is_authenticated or request.user.id != news.author_id:
        News.objects.filter(pk=news.pk).update(views_count=F('views_count') + 1)
        news.views_count += 1  # cập nhật local instance để hiển thị

    # Comments — chỉ lấy comment gốc (parent=None), replies sẽ access qua adv.visible_replies
    from django.db.models import Prefetch
    comments = (
        news.comments
        .filter(is_hidden=False, parent__isnull=True)
        .select_related('user')
        .prefetch_related(
            Prefetch(
                'replies',
                queryset=Comment.objects.filter(is_hidden=False).select_related('user').order_by('created_at'),
                to_attr='visible_replies_list',
            )
        )
        .order_by('created_at')
    )

    # Related news (cùng category)
    related = News.objects.filter(
        is_published=True, category=news.category
    ).exclude(pk=news.pk).order_by('-created_at')[:3]

    # Trạng thái thả tim của user hiện tại (để UI tô đỏ icon đã like)
    user_liked = (
        request.user.is_authenticated
        and NewsLike.objects.filter(news=news, user=request.user).exists()
    )
    like_count = news.likes.count()

    comment_form = CommentForm()
    can_moderate = _is_advisor(request.user)

    return render(request, 'news/news_detail.html', {
        'news': news,
        'comments': comments,
        'comment_form': comment_form,
        'related': related,
        'can_moderate': can_moderate,
        'user_liked': user_liked,
        'like_count': like_count,
    })


@login_required
@require_POST
def add_comment(request, slug):
    """
    POST endpoint thêm bình luận (hoặc reply nếu có parent_id).
    Tự động kiểm duyệt ngôn từ TRƯỚC KHI lưu:
    - Nếu sạch → lưu bình thường, hiển thị công khai.
    - Nếu phát hiện ngôn từ vi phạm → CHẶN luôn, không lưu, hiện cảnh báo cho user.

    Hỗ trợ reply lồng 1 cấp: nếu POST có `parent_id` thì comment mới sẽ là reply.
    Nếu parent đã là reply (parent.parent != None) → vẫn gắn vào parent_id đó (flatten),
    không cho lồng sâu hơn.
    """
    from chatbot.services import moderation

    news = get_object_or_404(News, slug=slug, is_published=True)
    form = CommentForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Bình luận không hợp lệ.")
        return redirect('news:detail', slug=slug)

    content = form.cleaned_data.get('content', '')

    # ─── Kiểm duyệt TRƯỚC khi lưu ───
    matched = moderation.find_profanity(content)
    if matched:
        messages.error(
            request,
            "⚠️ Bình luận của bạn chứa ngôn từ không phù hợp nên không thể gửi. "
            "Vui lòng dùng ngôn ngữ lịch sự và thử lại."
        )
        return redirect('news:detail', slug=slug)

    # ─── Reply nếu có parent_id ───
    parent = None
    parent_id = (request.POST.get('parent_id') or '').strip()
    if parent_id:
        try:
            parent = Comment.objects.get(id=int(parent_id), news=news, is_hidden=False)
            # Nếu parent đã là reply của ai khác → flatten về comment gốc của thread
            # (giữ chỉ 1 cấp lồng cho UI gọn)
            if parent.parent_id:
                parent = parent.parent
        except (ValueError, Comment.DoesNotExist):
            parent = None

    comment = form.save(commit=False)
    comment.news = news
    comment.user = request.user
    comment.parent = parent
    comment.save()
    messages.success(
        request,
        "Đã gửi phản hồi." if parent else "Bình luận của bạn đã được gửi."
    )
    # Anchor về comment vừa gửi
    return redirect(f"{news.get_absolute_url()}#comment-{comment.id}")


@login_required
@require_POST
def toggle_like(request, slug):
    """
    Toggle thả tim cho 1 tin tức. Idempotent:
    - Nếu user CHƯA thả tim → tạo NewsLike (return liked=True)
    - Nếu user ĐÃ thả tim   → xoá NewsLike (return liked=False)

    Trả về JSON cho frontend cập nhật icon + counter mà không reload.
    Đảm bảo race-safe nhờ UNIQUE(news, user) ở DB layer.
    """
    news = get_object_or_404(News, slug=slug, is_published=True)
    like, created = NewsLike.objects.get_or_create(news=news, user=request.user)
    if not created:
        # Đã thả rồi → click lần nữa = bỏ tim
        like.delete()
        liked = False
    else:
        liked = True

    return JsonResponse({
        'liked': liked,
        'like_count': news.likes.count(),
    })


@require_POST
def hide_comment(request, comment_id):
    """Tư vấn viên ẩn bình luận vi phạm."""
    if not _is_advisor(request.user):
        return HttpResponseForbidden("Chỉ tư vấn viên có quyền ẩn bình luận.")

    comment = get_object_or_404(Comment, pk=comment_id)
    comment.is_hidden = True
    comment.save(update_fields=['is_hidden'])
    messages.success(request, "Đã ẩn bình luận.")
    return redirect('news:detail', slug=comment.news.slug)


# ============================================================
# ADMIN VIEWS (cho tư vấn viên + admin)
# ============================================================
@login_required
@_require_advisor
def manage_list(request):
    """Danh sách tin tức để quản lý (kể cả nháp)."""
    qs = News.objects.select_related('author', 'department').order_by('-created_at')

    # Hiển thị tất cả tin tức cho cả admin và tư vấn viên
    # (Quyền edit/delete được kiểm soát trong từng view và template)

    keyword = request.GET.get('q', '').strip()
    if keyword:
        qs = qs.filter(Q(title__icontains=keyword) | Q(content__icontains=keyword))

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'news/news_admin_list.html', {
        'page': page,
        'news_items': page.object_list,
        'keyword': keyword,
    })


@login_required
@_require_advisor
def manage_create(request):
    """Tạo tin mới."""
    if request.method == 'POST':
        form = NewsForm(request.POST, request.FILES)
        if form.is_valid():
            news = form.save(commit=False)
            news.author = request.user
            # Nếu advisor không chọn department → mặc định lấy department của họ
            if not news.department and request.user.advisorprofile.department:
                news.department = request.user.advisorprofile.department
            news.save()
            messages.success(request, f"Đã tạo tin '{news.title}'.")
            return redirect('news:manage_list')
    else:
        form = NewsForm()

    return render(request, 'news/news_form.html', {
        'form': form,
        'is_create': True,
    })


@login_required
@_require_advisor
def manage_edit(request, news_id):
    """Sửa tin."""
    news = get_object_or_404(News, pk=news_id)

    # Advisor (không phải admin) chỉ sửa được tin của mình hoặc của khoa
    if request.user.advisorprofile.role != 'admin':
        if news.author_id != request.user.id and \
           news.department_id != getattr(request.user.advisorprofile.department, 'id', None):
            return HttpResponseForbidden("Bạn không có quyền sửa tin này.")

    if request.method == 'POST':
        form = NewsForm(request.POST, request.FILES, instance=news)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã cập nhật tin.")
            return redirect('news:manage_list')
    else:
        form = NewsForm(instance=news)

    return render(request, 'news/news_form.html', {
        'form': form,
        'news': news,
        'is_create': False,
    })


@login_required
@_require_advisor
@require_POST
def upload_inline_image(request):
    """
    Endpoint nhận file ảnh từ rich-text editor (Quill) → lưu vào MEDIA_ROOT/news/inline/
    → trả về URL để editor chèn vào content.

    Response: {"url": "/media/news/inline/abc.png"} hoặc {"error": "..."}
    """
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile
    import os
    import uuid

    upload = request.FILES.get('image') or request.FILES.get('file')
    if not upload:
        return JsonResponse({'error': 'Không có file ảnh trong request.'}, status=400)

    # Validate MIME type
    if not upload.content_type or not upload.content_type.startswith('image/'):
        return JsonResponse({'error': 'File phải là ảnh.'}, status=400)

    # Giới hạn size 5 MB
    MAX_SIZE = 5 * 1024 * 1024
    if upload.size > MAX_SIZE:
        return JsonResponse({'error': 'Ảnh vượt quá 5 MB.'}, status=400)

    # Lưu với tên random để tránh trùng
    ext = os.path.splitext(upload.name)[1].lower() or '.png'
    if ext not in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
        return JsonResponse({'error': 'Định dạng ảnh không hỗ trợ.'}, status=400)

    filename = f"news/inline/{uuid.uuid4().hex}{ext}"
    saved_path = default_storage.save(filename, ContentFile(upload.read()))
    url = default_storage.url(saved_path)
    return JsonResponse({'url': url, 'location': url})  # 'location' = TinyMCE format, 'url' = Quill


@login_required
@_require_advisor
@require_POST
def manage_delete(request, news_id):
    """Xoá tin."""
    news = get_object_or_404(News, pk=news_id)

    if request.user.advisorprofile.role != 'admin':
        if news.author_id != request.user.id:
            return HttpResponseForbidden("Bạn chỉ xoá được tin của chính mình.")

    title = news.title
    news.delete()
    messages.success(request, f"Đã xoá tin '{title}'.")
    return redirect('news:manage_list')
