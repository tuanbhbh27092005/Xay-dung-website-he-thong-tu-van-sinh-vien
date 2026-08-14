from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'user_type', 'student_id', 'graduation_year', 'phone_number', 'grade')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['user_type'].widget = forms.RadioSelect(choices=CustomUser.USER_TYPE_CHOICES)
        
        # Thêm các label tiếng Việt
        self.fields['username'].label = "Tên đăng nhập"
        self.fields['email'].label = "Email"
        self.fields['first_name'].label = "Tên"
        self.fields['last_name'].label = "Họ"
        self.fields['password1'].label = "Mật khẩu"
        self.fields['password2'].label = "Xác nhận mật khẩu"
        self.fields['user_type'].label = "Loại người dùng"
        self.fields['student_id'].label = "Mã số sinh viên"
        self.fields['graduation_year'].label = "Niên khóa"
        self.fields['phone_number'].label = "Số điện thoại"
        self.fields['grade'].label = "Lớp"
        
    def clean(self):
        cleaned_data = super().clean()
        user_type = cleaned_data.get('user_type')
        
        # Kiểm tra các trường bắt buộc dựa trên loại người dùng
        if user_type == 'student' and not cleaned_data.get('student_id'):
            self.add_error('student_id', 'Mã số sinh viên là bắt buộc đối với sinh viên')
        elif user_type == 'alumni':
            if not cleaned_data.get('student_id'):
                self.add_error('student_id', 'Mã số sinh viên là bắt buộc đối với cựu sinh viên')
            if not cleaned_data.get('graduation_year'):
                self.add_error('graduation_year', 'Niên khóa là bắt buộc đối với cựu sinh viên')
        elif user_type == 'parent' and not cleaned_data.get('phone_number'):
            self.add_error('phone_number', 'Số điện thoại là bắt buộc đối với phụ huynh')
        elif user_type == 'high_school' and not cleaned_data.get('grade'):
            self.add_error('grade', 'Lớp là bắt buộc đối với học sinh phổ thông')
            
        return cleaned_data

class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "Tên đăng nhập"
        self.fields['password'].label = "Mật khẩu" 