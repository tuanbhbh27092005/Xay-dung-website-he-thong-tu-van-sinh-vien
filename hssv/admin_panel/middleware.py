from django.shortcuts import redirect
from django.urls import resolve, reverse
from django.contrib import messages

class AdminPanelMiddleware:
    """
    Middleware để kiểm tra quyền truy cập vào trang admin panel.
    Chỉ cho phép người dùng có vai trò tư vấn viên truy cập.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Kiểm tra xem URL hiện tại có thuộc về admin panel không
        url_name = resolve(request.path_info).url_name
        
        # Danh sách các URL thuộc về admin panel
        admin_urls = [
            'admin_dashboard', 'manage_questions', 'answer_question',
            'manage_departments', 'edit_department', 'delete_department',
            'manage_majors', 'edit_major', 'delete_major',
            'manage_categories', 'edit_category', 'delete_category',
            'manage_advisors', 'edit_advisor', 'delete_advisor', 'advisor_handbook',
            'statistics_dashboard', 'department_statistics', 'admin_redirect'
        ]
        
        # Nếu URL thuộc về admin panel
        if url_name in admin_urls:
            # Kiểm tra xem người dùng đã đăng nhập chưa
            if not request.user.is_authenticated:
                messages.error(request, 'Bạn cần đăng nhập để truy cập trang quản trị.')
                return redirect(f"{reverse('login')}?next={request.path}")
            
            # Kiểm tra xem người dùng có vai trò tư vấn viên không
            try:
                advisor = request.user.advisorprofile
            except:
                messages.error(request, 'Bạn không có quyền truy cập trang quản trị.')
                return redirect('home')
        
        response = self.get_response(request)
        return response 