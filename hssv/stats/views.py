from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from questions.models import Question, Answer, Department, Major, QuestionCategory
from admin_panel.models import AdvisorProfile
from datetime import datetime
import calendar

def is_admin(user):
    """Kiểm tra xem người dùng có phải là admin hay không"""
    try:
        advisor = AdvisorProfile.objects.get(user=user)
        return advisor.role == 'admin'
    except AdvisorProfile.DoesNotExist:
        return False

@login_required
def statistics_dashboard(request):
    if not is_admin(request.user):
        messages.error(request, 'Bạn không có quyền truy cập trang thống kê.')
        return redirect('home')
    
    from datetime import timedelta
    
    from datetime import timedelta, datetime
    import calendar
    
    time_filter = request.GET.get('time_filter', '')
    month_filter = request.GET.get('month_filter', '')
    now = timezone.now()
    
    # Tạo filter theo thời gian
    time_q = Q()
    dept_total_filter = Q()
    dept_ans_filter = Q(major__question__status='answered')
    cat_filter = Q()
    time_filter_label = None
    
    if month_filter:
        try:
            m_str, y_str = month_filter.split('-')
            m, y = int(m_str), int(y_str)
            start_date = timezone.make_aware(datetime(y, m, 1))
            last_day = calendar.monthrange(y, m)[1]
            end_date = timezone.make_aware(datetime(y, m, last_day, 23, 59, 59, 999999))
            
            time_q = Q(created_at__range=(start_date, end_date))
            dept_total_filter = Q(major__question__created_at__range=(start_date, end_date))
            dept_ans_filter &= Q(major__question__created_at__range=(start_date, end_date))
            cat_filter = Q(question__created_at__range=(start_date, end_date))
            time_filter_label = f"Tháng {m}/{y}"
            time_filter = 'custom'
        except Exception:
            pass
    elif time_filter == '3m':
        start_date = now - timedelta(days=90)
        time_q = Q(created_at__gte=start_date)
        dept_total_filter = Q(major__question__created_at__gte=start_date)
        dept_ans_filter &= Q(major__question__created_at__gte=start_date)
        cat_filter = Q(question__created_at__gte=start_date)
    elif time_filter == '6m':
        start_date = now - timedelta(days=180)
        time_q = Q(created_at__gte=start_date)
        dept_total_filter = Q(major__question__created_at__gte=start_date)
        dept_ans_filter &= Q(major__question__created_at__gte=start_date)
        cat_filter = Q(question__created_at__gte=start_date)
    elif time_filter == '1y':
        start_date = now - timedelta(days=365)
        time_q = Q(created_at__gte=start_date)
        dept_total_filter = Q(major__question__created_at__gte=start_date)
        dept_ans_filter &= Q(major__question__created_at__gte=start_date)
        cat_filter = Q(question__created_at__gte=start_date)

    # Thống kê hiệu quả làm việc của các khoa
    departments = Department.objects.annotate(
        total_questions=Count('major__question', filter=dept_total_filter, distinct=True),
        answered_questions=Count('major__question', filter=dept_ans_filter, distinct=True)
    )
    
    # Tính tỷ lệ trả lời
    for dept in departments:
        if dept.total_questions > 0:
            dept.response_rate = (dept.answered_questions / dept.total_questions) * 100
        else:
            dept.response_rate = 0
    
    # Thống kê tổng số câu hỏi
    base_qs = Question.objects.filter(time_q)
    total_questions = base_qs.count()
    pending_questions = base_qs.filter(status='pending').count()
    answered_questions = base_qs.filter(status='answered').count()
    
    # Thống kê số lượng câu hỏi từ đầu năm
    current_year = datetime.now().year
    questions_this_year = Question.objects.filter(
        created_at__year=current_year
    ).count()
    
    # Thống kê đề tài được quan tâm nhiều nhất
    popular_categories = QuestionCategory.objects.annotate(
        question_count=Count('question', filter=cat_filter)
    ).order_by('-question_count')[:5]

    # ─── Thống kê theo tháng (12 tháng gần nhất) ───
    # Dùng range filter thay cho __year/__month để tránh lỗi CONVERT_TZ
    # trên MySQL khi bảng timezone_name trống.
    now = timezone.localtime(timezone.now())
    monthly_stats = []
    for i in range(11, -1, -1):
        year = now.year
        month = now.month - i
        while month <= 0:
            month += 12
            year -= 1
        # Tạo khoảng thời gian đầu/cuối tháng có timezone-aware
        last_day = calendar.monthrange(year, month)[1]
        start_dt = timezone.make_aware(datetime(year, month, 1, 0, 0, 0))
        end_dt   = timezone.make_aware(datetime(year, month, last_day, 23, 59, 59, 999999))
        month_qs = Question.objects.filter(created_at__range=(start_dt, end_dt))
        monthly_stats.append({
            'label':    f'T{month:02d}/{year}',
            'total':    month_qs.count(),
            'answered': month_qs.filter(status='answered').count(),
            'pending':  month_qs.filter(status='pending').count(),
        })
    
    return render(request, 'stats/dashboard.html', {
        'departments': departments,
        'total_questions': total_questions,
        'pending_questions': pending_questions,
        'answered_questions': answered_questions,
        'questions_this_year': questions_this_year,
        'popular_categories': popular_categories,
        'monthly_stats': monthly_stats,
        'time_filter': time_filter,
        'time_filter_label': time_filter_label,
    })

@login_required
def department_statistics(request, pk):
    if not is_admin(request.user):
        messages.error(request, 'Bạn không có quyền truy cập trang thống kê.')
        return redirect('home')
    
    department = Department.objects.get(pk=pk)
    
    # Thống kê câu hỏi theo ngành học
    majors = Major.objects.filter(department=department).annotate(
        total_questions=Count('question', distinct=True),
        answered_questions=Count('question', filter=Q(question__status='answered'), distinct=True)
    )
    
    # Tính tỷ lệ trả lời
    for major in majors:
        if major.total_questions > 0:
            major.response_rate = (major.answered_questions / major.total_questions) * 100
        else:
            major.response_rate = 0
    
    # Thống kê câu hỏi theo tháng
    questions_by_month = []
    current_year = datetime.now().year
    
    for month in range(1, 13):
        count = Question.objects.filter(
            major__department=department,
            created_at__year=current_year,
            created_at__month=month
        ).count()
        
        questions_by_month.append({
            'month': month,
            'count': count
        })
    
    return render(request, 'stats/department_statistics.html', {
        'department': department,
        'majors': majors,
        'questions_by_month': questions_by_month
    })
