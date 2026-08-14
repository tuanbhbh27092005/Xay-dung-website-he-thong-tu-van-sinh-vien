import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuvansinhvien.settings')
django.setup()

from accounts.models import CustomUser
from admin_panel.models import AdvisorProfile
from questions.models import Department

def create_advisor(username=None):
    # Nếu không có username, tạo tài khoản admin mặc định
    if not username:
        username = 'admin'
    
    # Kiểm tra xem tài khoản có tồn tại không
    try:
        user = CustomUser.objects.get(username=username)
        print(f"Đã tìm thấy tài khoản: {user.username}")
    except CustomUser.DoesNotExist:
        if username == 'admin':
            # Tạo tài khoản admin nếu chưa có
            user = CustomUser.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123',
                first_name='Admin',
                last_name='System',
                user_type='student'  # Loại người dùng mặc định
            )
            print(f"Đã tạo tài khoản admin: {user.username}")
        else:
            print(f"Không tìm thấy tài khoản với username: {username}")
            return
    
    # Kiểm tra xem đã có hồ sơ tư vấn viên cho user chưa
    try:
        advisor = AdvisorProfile.objects.get(user=user)
        print(f"Đã tìm thấy hồ sơ tư vấn viên cho {user.username}: {advisor.get_role_display()}")
    except AdvisorProfile.DoesNotExist:
        # Tạo một khoa mặc định nếu chưa có khoa nào
        if Department.objects.count() == 0:
            department = Department.objects.create(
                name='Khoa Công nghệ thông tin',
                description='Khoa Công nghệ thông tin'
            )
            print(f"Đã tạo khoa mặc định: {department.name}")
        else:
            department = Department.objects.first()
        
        # Tạo hồ sơ tư vấn viên cho user
        advisor = AdvisorProfile.objects.create(
            user=user,
            department=department,
            role='admin'  # Vai trò admin
        )
        print(f"Đã tạo hồ sơ tư vấn viên cho {user.username} với vai trò {advisor.get_role_display()}")
    
    print("Hoàn tất! Bây giờ bạn có thể đăng nhập với tài khoản:")
    print(f"Username: {user.username}")
    if username == 'admin' and user.date_joined.date() == django.utils.timezone.now().date():
        print("Password: admin123 (nếu vừa được tạo)")

if __name__ == "__main__":
    # Nếu có tham số dòng lệnh, sử dụng nó làm username
    if len(sys.argv) > 1:
        create_advisor(sys.argv[1])
    else:
        create_advisor() 