from django import forms
from .models import News, Comment


class NewsForm(forms.ModelForm):
    class Meta:
        model = News
        fields = [
            'title', 'category', 'department',
            'thumbnail_image', 'thumbnail_url',
            'summary', 'content', 'is_published',
        ]
        widgets = {
            'content': forms.Textarea(attrs={'rows': 12, 'id': 'id_content_hidden'}),
            'summary': forms.Textarea(attrs={'rows': 2}),
        }
        labels = {
            'title': 'Tiêu đề',
            'category': 'Phân loại',
            'department': 'Khoa/Đơn vị',
            'thumbnail_image': 'Ảnh đại diện (upload)',
            'thumbnail_url': 'URL ảnh đại diện (dự phòng)',
            'summary': 'Tóm tắt',
            'content': 'Nội dung',
            'is_published': 'Công bố ngay',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].widget.attrs.update({'placeholder': 'Tiêu đề rõ ràng, súc tích'})
        self.fields['thumbnail_url'].widget.attrs.update({
            'placeholder': 'https://images.unsplash.com/...'
        })
        self.fields['summary'].widget.attrs.update({
            'placeholder': '1-2 câu tóm tắt. Để trống sẽ tự lấy từ nội dung.'
        })
        self.fields['content'].widget.attrs.update({
            'placeholder': 'Nội dung chi tiết. Có thể chèn ảnh trực tiếp.'
        })


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Viết bình luận của bạn...',
            }),
        }
        labels = {'content': ''}
