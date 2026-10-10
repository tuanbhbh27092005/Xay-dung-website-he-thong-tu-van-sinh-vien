from django import forms
from .models import Question, Answer, Major, QuestionCategory, QuestionFeedback


class QuestionForm(forms.ModelForm):
    # Override is_public thành RadioSelect với UI rõ ràng hơn checkbox
    is_public = forms.TypedChoiceField(
        coerce=lambda x: x == 'True',
        choices=(
            ('True', 'Công khai — Mọi người có thể xem & chatbot dùng làm tham khảo'),
            ('False', 'Riêng tư — Chỉ tôi và tư vấn viên thấy được'),
        ),
        widget=forms.RadioSelect,
        initial='True',
        label='Quyền riêng tư',
    )

    is_anonymous = forms.BooleanField(
        required=False,
        initial=False,
        label='Đặt câu hỏi ẩn danh',
        help_text='Bảo vệ danh tính: ẩn tên và thông tin của bạn trên câu hỏi công khai',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    class Meta:
        model = Question
        fields = ['title', 'content', 'major', 'category', 'is_public', 'is_anonymous']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['major'].queryset = Major.objects.all().order_by('name')
        self.fields['category'].queryset = QuestionCategory.objects.all().order_by('name')

        # Placeholders
        self.fields['title'].widget.attrs.update({'placeholder': 'Nhập tiêu đề câu hỏi'})
        self.fields['content'].widget.attrs.update({'placeholder': 'Nhập nội dung câu hỏi chi tiết'})


class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Nhập câu trả lời của bạn'}),
        }


class QuestionSearchForm(forms.Form):
    query = forms.CharField(
        label='Tìm kiếm',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Nhập từ khóa tìm kiếm'})
    )
    category = forms.ModelChoiceField(
        label='Loại câu hỏi',
        queryset=QuestionCategory.objects.all(),
        required=False,
        empty_label="Tất cả loại câu hỏi"
    )
    major = forms.ModelChoiceField(
        label='Ngành học',
        queryset=Major.objects.all(),
        required=False,
        empty_label="Tất cả ngành học"
    )


class QuestionFeedbackForm(forms.ModelForm):
    class Meta:
        model = QuestionFeedback
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=QuestionFeedback.RATING_CHOICES),
            'comment': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Nhận xét của bạn về câu trả lời này (không bắt buộc)...',
                'class': 'form-control',
            }),
        }

