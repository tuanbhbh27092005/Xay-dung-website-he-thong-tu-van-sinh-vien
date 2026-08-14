from django import forms
from questions.models import Department, Major, QuestionCategory, Answer
from accounts.models import CustomUser
from .models import AdvisorProfile

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class MajorForm(forms.ModelForm):
    class Meta:
        model = Major
        fields = ['name', 'department', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = QuestionCategory
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class AdminAnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Nhập câu trả lời chính thức'}),
        }
        labels = {
            'content': 'Nội dung câu trả lời',
        }

class AdvisorProfileForm(forms.ModelForm):
    class Meta:
        model = AdvisorProfile
        fields = ['user', 'department', 'role', 'academic_title', 'position', 'avatar']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Khi TẠO MỚI (không có instance.pk): chỉ hiện user chưa có hồ sơ
        # Khi SỬA (có instance.pk): giữ nguyên user hiện tại + cho phép đổi sang user khác chưa có hồ sơ
        existing_advisors = AdvisorProfile.objects.values_list('user', flat=True)
        if self.instance and self.instance.pk:
            self.fields['user'].queryset = CustomUser.objects.exclude(
                id__in=existing_advisors
            ) | CustomUser.objects.filter(id=self.instance.user_id)
        else:
            self.fields['user'].queryset = CustomUser.objects.exclude(id__in=existing_advisors)