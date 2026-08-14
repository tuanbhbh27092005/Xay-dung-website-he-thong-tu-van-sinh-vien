from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta, datetime
import calendar
from questions.models import Question, Answer, Department, Major, QuestionCategory
from questions.forms import QuestionForm, AnswerForm
from accounts.models import CustomUser
from .models import AdvisorProfile
from .forms import DepartmentForm, MajorForm, CategoryForm, AdminAnswerForm, AdvisorProfileForm

# SLA: câu hỏi pending quá X giờ → highlight đỏ ở manage_questions
OVERDUE_HOURS = 12

def is_advisor(user):
    """Kiểm tra xem người dùng có phải là tư vấn viên hay không"""
    try:
        advisor = AdvisorProfile.objects.get(user=user)
        return True
    except AdvisorProfile.DoesNotExist:
        return False

@login_required
def admin_dashboard(request):
    # Kiểm tra quyền quản trị
    if not is_advisor(request.user):
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    try:
        advisor = AdvisorProfile.objects.get(user=request.user)
    except AdvisorProfile.DoesNotExist:
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')

    # ─── Build base queryset theo phân quyền ───
    if advisor.role == 'admin':
        base_qs = Question.objects.all()
    elif advisor.department:
        base_qs = Question.objects.filter(major__department=advisor.department)
    else:
        # advisor không gắn department → không thấy gì
        base_qs = Question.objects.none()

    total_questions = base_qs.count()
    pending_questions = base_qs.filter(status='pending').count()
    answered_questions = base_qs.filter(status='answered').count()

    # ─── Đếm câu pending ĐÃ QUÁ HẠN (>48h chưa trả lời) ───
    overdue_threshold = timezone.now() - timedelta(hours=OVERDUE_HOURS)
    overdue_count = base_qs.filter(
        status='pending', created_at__lt=overdue_threshold,
    ).count()

    # ─── Thống kê theo tháng (12 tháng gần nhất, sort cũ→mới) ───
    # Format: list of {'label': 'T1/2026', 'total': 12, 'answered': 8}
    # Mỗi item là 1 cột trên bar chart ở dashboard.
    # Dùng range filter thay cho __year/__month để tránh lỗi CONVERT_TZ
    # trên MySQL khi bảng timezone_name trống.
    now = timezone.localtime(timezone.now())
    monthly_stats = []
    # Lùi 11 tháng → có đủ 12 điểm tính cả tháng hiện tại
    for i in range(11, -1, -1):
        # Tính ngày đầu tháng cách hiện tại i tháng
        year = now.year
        month = now.month - i
        while month <= 0:
            month += 12
            year -= 1
        # Tạo khoảng thời gian đầu/cuối tháng có timezone-aware
        last_day = calendar.monthrange(year, month)[1]
        start_dt = timezone.make_aware(datetime(year, month, 1, 0, 0, 0))
        end_dt   = timezone.make_aware(datetime(year, month, last_day, 23, 59, 59, 999999))
        month_qs = base_qs.filter(created_at__range=(start_dt, end_dt))
        monthly_stats.append({
            'label': f'T{month:02d}/{year}',
            'year': year,
            'month': month,
            'total':    month_qs.count(),
            'answered': month_qs.filter(status='answered').count(),
            'pending':  month_qs.filter(status='pending').count(),
        })

    return render(request, 'admin_panel/dashboard.html', {
        'total_questions': total_questions,
        'pending_questions': pending_questions,
        'answered_questions': answered_questions,
        'overdue_count': overdue_count,
        'overdue_hours': OVERDUE_HOURS,
        'monthly_stats': monthly_stats,
        'advisor': advisor,
    })

@login_required
def manage_questions(request):
    if not is_advisor(request.user):
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    try:
        advisor = AdvisorProfile.objects.get(user=request.user)
    except AdvisorProfile.DoesNotExist:
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    # Lọc câu hỏi theo quyền
    if advisor.role == 'admin':
        base_qs = Question.objects.all()
    else:
        base_qs = Question.objects.filter(major__department=advisor.department)

    # Lọc theo từ khóa tìm kiếm nếu có
    search_query = request.GET.get('search', '').strip()
    if search_query:
        base_qs = base_qs.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )

    now = timezone.now()
    overdue_threshold = now - timedelta(hours=OVERDUE_HOURS)

    # Đếm cho tab badge (trước khi filter visibility/status)
    counts = {
        'all': base_qs.count(),
        'public': base_qs.filter(is_public=True).count(),
        'private': base_qs.filter(is_public=False).count(),
        'overdue': base_qs.filter(status='pending', created_at__lt=overdue_threshold).count(),
    }

    questions = base_qs.order_by('-created_at')

    # ─── Filter theo visibility: 'public' / 'private' / 'overdue' / '' (all) ───
    visibility = request.GET.get('visibility', '')
    if visibility == 'public':
        questions = questions.filter(is_public=True)
    elif visibility == 'private':
        questions = questions.filter(is_public=False)
    elif visibility == 'overdue':
        questions = questions.filter(status='pending', created_at__lt=overdue_threshold)

    # Lọc theo trạng thái nếu có
    status = request.GET.get('status')
    if status:
        questions = questions.filter(status=status)

    questions = questions.select_related('user', 'category', 'major')

    # ─── Annotate is_overdue / overdue_days cho template ───
    # Câu hỏi pending mà created_at cách hiện tại > OVERDUE_HOURS giờ → coi là quá hạn
    # → template tô đỏ row + hiển thị badge "QUÁ HẠN N ngày".
    questions_list = list(questions)
    for q in questions_list:
        if q.status == 'pending' and q.created_at < overdue_threshold:
            q.is_overdue = True
            q.overdue_hours = int((now - q.created_at).total_seconds() // 3600)
            q.overdue_days = q.overdue_hours // 24
        else:
            q.is_overdue = False
            q.overdue_hours = 0
            q.overdue_days = 0

    return render(request, 'admin_panel/manage_questions.html', {
        'questions': questions_list,
        'status': status,
        'visibility': visibility,
        'search_query': search_query,
        'counts': counts,
        'overdue_hours_threshold': OVERDUE_HOURS,
    })

@login_required
def answer_question(request, pk):
    if not is_advisor(request.user):
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    try:
        advisor = AdvisorProfile.objects.get(user=request.user)
    except AdvisorProfile.DoesNotExist:
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    question = get_object_or_404(Question, pk=pk)
    
    # Kiểm tra quyền trả lời
    if advisor.role != 'admin' and (not question.major or question.major.department != advisor.department):
        messages.error(request, 'Bạn không có quyền trả lời câu hỏi này.')
        return redirect('manage_questions')
    
    if request.method == 'POST':
        form = AdminAnswerForm(request.POST)
        if form.is_valid():
            answer = form.save(commit=False)
            answer.question = question
            answer.user = request.user
            answer.save()
            
            # Cập nhật trạng thái câu hỏi
            question.status = 'answered'
            question.save()
            
            messages.success(request, 'Câu trả lời của bạn đã được gửi thành công!')
            return redirect('manage_questions')
    else:
        form = AdminAnswerForm()
    
    # Lấy các câu trả lời hiện có
    answers = question.answers.all().order_by('created_at')
    
    return render(request, 'admin_panel/answer_question.html', {
        'question': question,
        'answers': answers,
        'form': form
    })

@login_required
def manage_departments(request):
    if not is_advisor(request.user):
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    try:
        advisor = AdvisorProfile.objects.get(user=request.user)
        if advisor.role != 'admin':
            messages.error(request, 'Bạn không có quyền quản lý danh mục.')
            return redirect('admin_dashboard')
    except AdvisorProfile.DoesNotExist:
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    departments = Department.objects.all()
    
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thêm khoa/đơn vị thành công!')
            return redirect('manage_departments')
    else:
        form = DepartmentForm()
    
    return render(request, 'admin_panel/manage_departments.html', {
        'departments': departments,
        'form': form
    })

@login_required
def edit_department(request, pk):
    if not is_advisor(request.user):
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    try:
        advisor = AdvisorProfile.objects.get(user=request.user)
        if advisor.role != 'admin':
            messages.error(request, 'Bạn không có quyền quản lý danh mục.')
            return redirect('admin_dashboard')
    except AdvisorProfile.DoesNotExist:
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    department = get_object_or_404(Department, pk=pk)
    
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật khoa/đơn vị thành công!')
            return redirect('manage_departments')
    else:
        form = DepartmentForm(instance=department)
    
    return render(request, 'admin_panel/edit_department.html', {
        'form': form,
        'department': department
    })

@login_required
def manage_majors(request):
    if not is_advisor(request.user):
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    try:
        advisor = AdvisorProfile.objects.get(user=request.user)
        if advisor.role != 'admin':
            messages.error(request, 'Bạn không có quyền quản lý danh mục.')
            return redirect('admin_dashboard')
    except AdvisorProfile.DoesNotExist:
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    majors = Major.objects.all()
    
    if request.method == 'POST':
        form = MajorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thêm ngành học thành công!')
            return redirect('manage_majors')
    else:
        form = MajorForm()
    
    return render(request, 'admin_panel/manage_majors.html', {
        'majors': majors,
        'form': form
    })

@login_required
def edit_major(request, pk):
    if not is_advisor(request.user):
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    try:
        advisor = AdvisorProfile.objects.get(user=request.user)
        if advisor.role != 'admin':
            messages.error(request, 'Bạn không có quyền quản lý danh mục.')
            return redirect('admin_dashboard')
    except AdvisorProfile.DoesNotExist:
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    major = get_object_or_404(Major, pk=pk)
    
    if request.method == 'POST':
        form = MajorForm(request.POST, instance=major)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật ngành học thành công!')
            return redirect('manage_majors')
    else:
        form = MajorForm(instance=major)
    
    return render(request, 'admin_panel/edit_major.html', {
        'form': form,
        'major': major
    })

@login_required
def manage_categories(request):
    if not is_advisor(request.user):
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    try:
        advisor = AdvisorProfile.objects.get(user=request.user)
        if advisor.role != 'admin':
            messages.error(request, 'Bạn không có quyền quản lý danh mục.')
            return redirect('admin_dashboard')
    except AdvisorProfile.DoesNotExist:
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    categories = QuestionCategory.objects.all()
    
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thêm loại câu hỏi thành công!')
            return redirect('manage_categories')
    else:
        form = CategoryForm()
    
    return render(request, 'admin_panel/manage_categories.html', {
        'categories': categories,
        'form': form
    })

@login_required
def edit_category(request, pk):
    if not is_advisor(request.user):
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    try:
        advisor = AdvisorProfile.objects.get(user=request.user)
        if advisor.role != 'admin':
            messages.error(request, 'Bạn không có quyền quản lý danh mục.')
            return redirect('admin_dashboard')
    except AdvisorProfile.DoesNotExist:
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    category = get_object_or_404(QuestionCategory, pk=pk)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật loại câu hỏi thành công!')
            return redirect('manage_categories')
    else:
        form = CategoryForm(instance=category)
    
    return render(request, 'admin_panel/edit_category.html', {
        'form': form,
        'category': category
    })

@login_required
def manage_advisors(request):
    if not is_advisor(request.user):
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    try:
        advisor = AdvisorProfile.objects.get(user=request.user)
        if advisor.role != 'admin':
            messages.error(request, 'Bạn không có quyền quản lý tư vấn viên.')
            return redirect('admin_dashboard')
    except AdvisorProfile.DoesNotExist:
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    advisors = AdvisorProfile.objects.all()

    if request.method == 'POST':
        form = AdvisorProfileForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thêm tư vấn viên thành công!')
            return redirect('manage_advisors')
    else:
        form = AdvisorProfileForm()

    return render(request, 'admin_panel/manage_advisors.html', {
        'advisors': advisors,
        'form': form
    })


@login_required
def advisor_handbook(request):
    """
    Sổ tay ban tư vấn — danh sách tư vấn viên có: STT, họ tên, SĐT, email, avatar.
    Mặc định nhóm theo khoa. Có filter chọn khoa cụ thể từ querystring `?dept=<id>`.
    """
    if not is_advisor(request.user):
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')

    try:
        viewer = AdvisorProfile.objects.get(user=request.user)
    except AdvisorProfile.DoesNotExist:
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')

    # Lấy danh sách khoa cho filter dropdown
    departments = Department.objects.order_by('name')

    # Filter theo khoa (dept_id) hoặc mặc định lấy hết
    # CHỈ hiện role='advisor' (ban tư vấn thật) — không hiện admin hệ thống.
    dept_id = request.GET.get('dept', '').strip()
    selected_dept = None
    advisors_qs = (
        AdvisorProfile.objects
        .filter(role='advisor')
        .select_related('user', 'department')
        .order_by('department__name', 'user__last_name', 'user__first_name', 'user__username')
    )

    if dept_id:
        try:
            selected_dept = Department.objects.get(id=int(dept_id))
            advisors_qs = advisors_qs.filter(department=selected_dept)
        except (ValueError, Department.DoesNotExist):
            selected_dept = None

    # Group theo khoa: [{'department': Dept|None, 'advisors': [AdvisorProfile, ...]}]
    grouped = []
    current_group = None
    for adv in advisors_qs:
        dept_key = adv.department_id if adv.department else 0
        if current_group is None or current_group['key'] != dept_key:
            current_group = {
                'key': dept_key,
                'department': adv.department,
                'advisors': [],
            }
            grouped.append(current_group)
        current_group['advisors'].append(adv)

    return render(request, 'admin_panel/advisor_handbook.html', {
        'grouped': grouped,
        'departments': departments,
        'selected_dept': selected_dept,
        'total': advisors_qs.count(),
    })


@login_required
def delete_department(request, pk):
    """Xóa khoa/đơn vị"""
    department = get_object_or_404(Department, pk=pk)
    
    # Kiểm tra xem người dùng có phải là admin không
    try:
        advisor = AdvisorProfile.objects.get(user=request.user)
        if advisor.role != 'admin':
            messages.error(request, 'Bạn không có quyền xóa khoa/đơn vị.')
            return redirect('manage_departments')
    except AdvisorProfile.DoesNotExist:
        messages.error(request, 'Bạn không có quyền xóa khoa/đơn vị.')
        return redirect('manage_departments')
    
    # Kiểm tra xem khoa/đơn vị có ngành học hoặc tư vấn viên không
    major_count = Major.objects.filter(department=department).count()
    advisor_count = AdvisorProfile.objects.filter(department=department).count()
    
    if major_count > 0 or advisor_count > 0:
        messages.error(request, f'Không thể xóa khoa/đơn vị "{department.name}" vì có {major_count} ngành học và {advisor_count} tư vấn viên liên quan.')
        return redirect('manage_departments')
    
    # Xóa khoa/đơn vị
    department_name = department.name
    department.delete()
    messages.success(request, f'Đã xóa khoa/đơn vị "{department_name}" thành công.')
    
    return redirect('manage_departments')

@login_required
def delete_major(request, pk):
    """Xóa ngành học"""
    major = get_object_or_404(Major, pk=pk)
    
    # Kiểm tra xem người dùng có phải là admin không
    try:
        advisor = AdvisorProfile.objects.get(user=request.user)
        if advisor.role != 'admin':
            messages.error(request, 'Bạn không có quyền xóa ngành học.')
            return redirect('manage_majors')
    except AdvisorProfile.DoesNotExist:
        messages.error(request, 'Bạn không có quyền xóa ngành học.')
        return redirect('manage_majors')
    
    # Kiểm tra xem ngành học có câu hỏi không
    question_count = Question.objects.filter(major=major).count()
    
    if question_count > 0:
        messages.error(request, f'Không thể xóa ngành học "{major.name}" vì có {question_count} câu hỏi liên quan.')
        return redirect('manage_majors')
    
    # Xóa ngành học
    major_name = major.name
    major.delete()
    messages.success(request, f'Đã xóa ngành học "{major_name}" thành công.')
    
    return redirect('manage_majors')

@login_required
def delete_category(request, pk):
    """Xóa loại câu hỏi"""
    category = get_object_or_404(QuestionCategory, pk=pk)
    
    # Kiểm tra xem người dùng có phải là admin không
    try:
        advisor = AdvisorProfile.objects.get(user=request.user)
        if advisor.role != 'admin':
            messages.error(request, 'Bạn không có quyền xóa loại câu hỏi.')
            return redirect('manage_categories')
    except AdvisorProfile.DoesNotExist:
        messages.error(request, 'Bạn không có quyền xóa loại câu hỏi.')
        return redirect('manage_categories')
    
    # Kiểm tra xem loại câu hỏi có câu hỏi không
    question_count = Question.objects.filter(category=category).count()
    
    if question_count > 0:
        messages.error(request, f'Không thể xóa loại câu hỏi "{category.name}" vì có {question_count} câu hỏi liên quan.')
        return redirect('manage_categories')
    
    # Xóa loại câu hỏi
    category_name = category.name
    category.delete()
    messages.success(request, f'Đã xóa loại câu hỏi "{category_name}" thành công.')
    
    return redirect('manage_categories')

@login_required
def delete_advisor(request, pk):
    """Xóa tư vấn viên"""
    advisor = get_object_or_404(AdvisorProfile, pk=pk)
    
    # Kiểm tra xem người dùng có phải là admin không
    try:
        user_advisor = AdvisorProfile.objects.get(user=request.user)
        if user_advisor.role != 'admin':
            messages.error(request, 'Bạn không có quyền xóa tư vấn viên.')
            return redirect('manage_advisors')
    except AdvisorProfile.DoesNotExist:
        messages.error(request, 'Bạn không có quyền xóa tư vấn viên.')
        return redirect('manage_advisors')
    
    # Không cho phép xóa chính mình
    if advisor.user == request.user:
        messages.error(request, 'Bạn không thể xóa chính mình.')
        return redirect('manage_advisors')
    
    # Xóa tư vấn viên
    advisor_name = advisor.user.get_full_name() or advisor.user.username
    advisor.delete()
    messages.success(request, f'Đã xóa tư vấn viên "{advisor_name}" thành công.')
    
    return redirect('manage_advisors')

@login_required
def edit_advisor(request, pk):
    """Chỉnh sửa thông tin tư vấn viên"""
    if not is_advisor(request.user):
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    try:
        user_advisor = AdvisorProfile.objects.get(user=request.user)
        if user_advisor.role != 'admin':
            messages.error(request, 'Bạn không có quyền chỉnh sửa tư vấn viên.')
            return redirect('manage_advisors')
    except AdvisorProfile.DoesNotExist:
        messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
        return redirect('home')
    
    advisor = get_object_or_404(AdvisorProfile, pk=pk)

    if request.method == 'POST':
        form = AdvisorProfileForm(request.POST, request.FILES, instance=advisor)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã cập nhật thông tin tư vấn viên thành công.')
            return redirect('manage_advisors')
    else:
        form = AdvisorProfileForm(instance=advisor)

    return render(request, 'admin_panel/edit_advisor.html', {
        'form': form,
        'advisor': advisor
    })

@login_required
def edit_question(request, pk):
    """Chỉnh sửa câu hỏi"""
    question = get_object_or_404(Question, pk=pk)
    
    # Kiểm tra xem người dùng có phải là tư vấn viên không
    if not is_advisor(request.user):
        messages.error(request, 'Bạn không có quyền chỉnh sửa câu hỏi.')
        return redirect('question_detail', pk=pk)
    
    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã cập nhật câu hỏi "{question.title}" thành công.')
            return redirect('manage_questions')
    else:
        form = QuestionForm(instance=question)
    
    return render(request, 'admin_panel/edit_question.html', {
        'form': form,
        'question': question
    })

@login_required
def delete_question(request, pk):
    """Xóa câu hỏi"""
    question = get_object_or_404(Question, pk=pk)

    # Kiểm tra xem người dùng có phải là tư vấn viên không
    if not is_advisor(request.user):
        messages.error(request, 'Bạn không có quyền xóa câu hỏi.')
        return redirect('question_detail', pk=pk)

    # Xóa câu hỏi
    question_title = question.title
    question.delete()
    messages.success(request, f'Đã xóa câu hỏi "{question_title}" thành công.')

    return redirect('manage_questions')


# ============================================================
# CONTENT MODERATION QUEUE
# ============================================================
@login_required
def moderation_queue(request):
    """
    Danh sách báo cáo nội dung vi phạm cho tư vấn viên xử lý.
    Gom cả tin nhắn chatbot + bình luận tin tức.
    """
    if not is_advisor(request.user):
        messages.error(request, 'Bạn không có quyền truy cập.')
        return redirect('home')

    from chatbot.models import ContentReport
    status_filter = request.GET.get('status', 'pending')
    source_filter = request.GET.get('source', '')

    qs = ContentReport.objects.select_related(
        'chat_message__session', 'comment__news', 'content_user', 'reviewed_by',
    )
    if status_filter:
        qs = qs.filter(status=status_filter)
    if source_filter:
        qs = qs.filter(source=source_filter)

    qs = qs.order_by('-created_at')

    # Count cho tabs
    counts = {
        'pending': ContentReport.objects.filter(status='pending').count(),
        'all': ContentReport.objects.count(),
    }

    return render(request, 'admin_panel/moderation_queue.html', {
        'reports': qs[:100],  # limit hiển thị
        'status_filter': status_filter,
        'source_filter': source_filter,
        'counts': counts,
        'STATUS_CHOICES': ContentReport.STATUS_CHOICES,
        'SOURCE_CHOICES': ContentReport.SOURCE_CHOICES,
    })


@login_required
def moderation_action(request, report_id):
    """
    Xử lý 1 báo cáo: approve (không vi phạm) / hidden (ẩn nội dung) / warned (cảnh báo user).
    """
    if not is_advisor(request.user):
        messages.error(request, 'Bạn không có quyền.')
        return redirect('home')

    from chatbot.models import ContentReport

    report = get_object_or_404(ContentReport, pk=report_id)
    action = request.POST.get('action', '').strip()
    note = request.POST.get('note', '').strip()

    if action not in {'approved', 'hidden', 'warned'}:
        messages.error(request, 'Hành động không hợp lệ.')
        return redirect('moderation_queue')

    # Thực thi hậu quả
    if action == 'approved':
        # Khôi phục nội dung (nếu comment đang hidden vì sensitive → unhide)
        if report.source == 'comment' and report.comment:
            if report.comment.has_sensitive and report.comment.is_hidden:
                report.comment.is_hidden = False
                report.comment.save(update_fields=['is_hidden'])
    elif action == 'hidden':
        if report.source == 'comment' and report.comment:
            report.comment.is_hidden = True
            report.comment.save(update_fields=['is_hidden'])

    # Update report
    report.status = action
    report.reviewed_by = request.user
    report.reviewed_at = timezone.now()
    if note:
        report.admin_note = note
    report.save()

    messages.success(request, f'Đã xử lý báo cáo #{report.id}.')
    return redirect('moderation_queue')
