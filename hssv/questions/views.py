from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, F
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from .models import Question, Answer, Major, QuestionCategory, Department
from .forms import QuestionForm, AnswerForm, QuestionSearchForm
from admin_panel.models import AdvisorProfile


# ============================================================
# HELPER: Filter queryset theo quyền truy cập câu hỏi riêng tư
# ============================================================
def _is_advisor(user):
    """User có phải tư vấn viên không (any role)?"""
    if not user.is_authenticated:
        return False
    return hasattr(user, 'advisorprofile') and user.advisorprofile is not None


def _filter_visible_questions(queryset, user):
    """
    Lọc queryset Question theo quyền xem:
    - Tư vấn viên (advisor) → thấy tất cả
    - User đăng nhập → thấy public + câu hỏi của chính mình (kể cả riêng tư)
    - Anonymous → chỉ thấy public
    """
    if _is_advisor(user):
        return queryset
    if user.is_authenticated:
        return queryset.filter(Q(is_public=True) | Q(user=user))
    return queryset.filter(is_public=True)


# ============================================================
# VIEWS
# ============================================================
def home(request):
    """
    Trang chủ: hiển thị các câu hỏi ĐƯỢC QUAN TÂM NHẤT (sort theo views_count).
    Lý do: từ phase này trở đi sinh viên không tự đặt câu hỏi qua form nữa
    (đã chuyển sang chatbot) → trang chủ ưu tiên những câu hỏi mà cộng đồng
    đã xem nhiều = có khả năng giải đáp được thắc mắc của người mới vào.
    """
    qs = _filter_visible_questions(Question.objects.all(), request.user)
    # Chỉ lấy câu đã được trả lời để landing page có giá trị tham khảo cao
    popular_qs = (
        qs.filter(status='answered')
          .order_by('-views_count', '-created_at')
    )

    paginator = Paginator(popular_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = QuestionCategory.objects.annotate(
        question_count=Count('question', filter=Q(question__is_public=True))
    ).order_by('-question_count')

    departments = Department.objects.all().prefetch_related('major_set')

    return render(request, 'questions/home.html', {
        'popular_questions': page_obj,
        'page_obj': page_obj,
        'page_query': '',
        'categories': categories,
        'departments': departments,
    })


@login_required
def ask_question(request):
    """
    Lưu ý: Phase B sẽ thay flow này bằng chatbot intent gathering.
    Tạm giữ form cho backward compatibility / cho admin tự tạo.
    """
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.user = request.user
            question.save()
            messages.success(request, 'Câu hỏi của bạn đã được gửi thành công!')
            return redirect('profile')  # ← redirect về profile, không còn my_questions riêng
    else:
        form = QuestionForm()
    return render(request, 'questions/ask_question.html', {'form': form})


@login_required
def my_questions(request):
    """
    Giữ view này để URL cũ không 404, redirect về profile.
    """
    return redirect('profile')


def question_detail(request, pk):
    question = get_object_or_404(Question, pk=pk)

    # Kiểm tra quyền xem nếu là câu hỏi riêng tư
    if not question.can_view(request.user):
        return HttpResponseForbidden(
            "Câu hỏi này được đánh dấu riêng tư. "
            "Chỉ người đặt câu hỏi và tư vấn viên có thể xem."
        )

    # ─── Tăng views_count (loại trừ tác giả & advisor xem để moderate) ───
    # Pattern giống news_detail: dùng F() để tránh race condition khi nhiều
    # user xem song song.
    is_author = request.user.is_authenticated and request.user.id == question.user_id
    is_advisor_user = _is_advisor(request.user)
    if not is_author and not is_advisor_user:
        Question.objects.filter(pk=question.pk).update(views_count=F('views_count') + 1)
        question.views_count += 1  # cập nhật local instance để template hiển thị đúng

    answers = question.answers.all().select_related(
        'user', 'user__advisorprofile', 'user__advisorprofile__department',
    ).order_by('created_at')

    related_questions = _filter_visible_questions(
        Question.objects.filter(
            Q(category=question.category) | Q(major=question.major)
        ).exclude(id=question.id),
        request.user,
    ).distinct().order_by('-views_count', '-created_at')[:4]

    return render(request, 'questions/question_detail.html', {
        'question': question,
        'answers': answers,
        'related_questions': related_questions,
    })


def search_questions(request):
    form = QuestionSearchForm(request.GET)
    questions = Question.objects.filter(status='answered')

    if form.is_valid():
        query = form.cleaned_data.get('query')
        category = form.cleaned_data.get('category')
        major = form.cleaned_data.get('major')

        if query:
            questions = questions.filter(
                Q(title__icontains=query) | Q(content__icontains=query)
            )
        if category:
            questions = questions.filter(category=category)
        if major:
            questions = questions.filter(major=major)

    questions = _filter_visible_questions(questions, request.user)
    questions = questions.order_by('-created_at')

    # Build query string without 'page' for pagination links
    query_params = request.GET.copy()
    query_params.pop('page', None)
    page_query = query_params.urlencode()

    paginator = Paginator(questions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'questions/search_questions.html', {
        'form': form,
        'questions': page_obj,
        'page_obj': page_obj,
        'page_query': page_query,
    })


def popular_questions(request):
    """
    Câu hỏi thường gặp: hiển thị câu hỏi đã trả lời, sort theo lượt xem giảm dần.
    """
    qs = _filter_visible_questions(
        Question.objects.filter(status='answered'),
        request.user,
    ).order_by('-views_count', '-created_at')

    return render(request, 'questions/popular_questions.html', {
        'questions': qs,
    })


def category_questions(request, category_id):
    category = get_object_or_404(QuestionCategory, id=category_id)
    qs = Question.objects.filter(category=category)
    qs = _filter_visible_questions(qs, request.user).order_by('-created_at')

    return render(request, 'questions/category_questions.html', {
        'category': category,
        'questions': qs,
    })


def major_questions(request, major_id):
    major = get_object_or_404(Major, id=major_id)
    qs = Question.objects.filter(major=major)
    qs = _filter_visible_questions(qs, request.user).order_by('-created_at')

    return render(request, 'questions/major_questions.html', {
        'major': major,
        'questions': qs,
    })


def advisor_list(request):
    """
    Sổ tay ban tư vấn — trang public hiển thị danh bạ tư vấn viên.
    CHỈ hiện role='advisor', KHÔNG hiện admin hệ thống (admin là kỹ thuật, không phải BTV).
    Bảng phẳng có cột STT, Họ tên, SĐT, Email, Ảnh, Đơn vị.
    """
    advisors_qs = (
        AdvisorProfile.objects
        .filter(role='advisor')
        .select_related('user', 'department')
        .order_by('department__name', 'user__last_name', 'user__first_name', 'user__username')
    )

    department_id = request.GET.get('department', '').strip()
    selected_dept = None
    if department_id:
        try:
            selected_dept = Department.objects.get(id=int(department_id))
            advisors_qs = advisors_qs.filter(department=selected_dept)
        except (ValueError, Department.DoesNotExist):
            selected_dept = None

    departments = Department.objects.order_by('name')

    return render(request, 'questions/advisor_list.html', {
        'advisors': list(advisors_qs),
        'departments': departments,
        'selected_dept': selected_dept,
        'total': advisors_qs.count(),
    })
