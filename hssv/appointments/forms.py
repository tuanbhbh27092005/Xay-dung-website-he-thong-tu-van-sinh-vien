from django import forms
from .models import AdvisorSchedule, Appointment


class AdvisorScheduleForm(forms.ModelForm):
    class Meta:
        model = AdvisorSchedule
        fields = ['day_of_week', 'start_time', 'end_time', 'slot_duration', 'note', 'is_active']
        widgets = {
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'slot_duration': forms.NumberInput(attrs={'class': 'form-control', 'min': '15', 'step': '5'}),
            'note': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Vd: Văn phòng Khoa A1-203 hoặc link Meet mặc định'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AppointmentBookingForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['meeting_type', 'topic', 'student_notes']
        widgets = {
            'meeting_type': forms.Select(attrs={'class': 'form-select'}),
            'topic': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Vd: Tư vấn kế hoạch học tập vượt/cảnh báo học vụ'}),
            'student_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Mô tả cụ thể những khó khăn, câu hỏi bạn muốn trao đổi trực tiếp...'}),
        }


class AppointmentUpdateStatusForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['status', 'location_or_link', 'advisor_notes', 'cancel_reason']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'location_or_link': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Địa điểm gặp (Văn phòng A1-203) hoặc Link Google Meet'}),
            'advisor_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ghi chú / Hướng dẫn thêm cho sinh viên hoặc kết luận sau buổi gặp'}),
            'cancel_reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lý do từ chối / hủy (nếu có)'}),
        }
