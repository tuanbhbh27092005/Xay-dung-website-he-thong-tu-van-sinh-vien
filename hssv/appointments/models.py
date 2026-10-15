from django.db import models
from django.conf import settings
from admin_panel.models import AdvisorProfile


class AdvisorSchedule(models.Model):
    """
    Khung giờ rảnh / tiếp sinh viên định kỳ hoặc cố định của Cố vấn / Trưởng khoa.
    """
    DAY_CHOICES = (
        (0, 'Thứ Hai'),
        (1, 'Thứ Ba'),
        (2, 'Thứ Tư'),
        (3, 'Thứ Năm'),
        (4, 'Thứ Sáu'),
        (5, 'Thứ Bảy'),
        (6, 'Chủ Nhật'),
    )

    advisor = models.ForeignKey(
        AdvisorProfile,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name="Cố vấn học tập"
    )
    day_of_week = models.IntegerField(
        choices=DAY_CHOICES,
        verbose_name="Ngày trong tuần"
    )
    start_time = models.TimeField(verbose_name="Giờ bắt đầu")
    end_time = models.TimeField(verbose_name="Giờ kết thúc")
    slot_duration = models.PositiveIntegerField(
        default=30,
        verbose_name="Thời lượng mỗi ca (phút)",
        help_text="Ví dụ: 30 phút hoặc 45 phút"
    )
    is_active = models.BooleanField(default=True, verbose_name="Đang kích hoạt")
    note = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name="Ghi chú (địa điểm / link Meet cố định)"
    )

    class Meta:
        verbose_name = "Khung giờ tiếp sinh viên"
        verbose_name_plural = "Khung giờ tiếp sinh viên"
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.advisor.display_name} - {self.get_day_of_week_display()} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"


class Appointment(models.Model):
    """
    Lịch hẹn tư vấn 1-1 giữa sinh viên và Cố vấn / Ban tư vấn.
    """
    STATUS_CHOICES = (
        ('pending', 'Chờ xác nhận'),
        ('confirmed', 'Đã xác nhận'),
        ('completed', 'Đã hoàn thành'),
        ('canceled', 'Đã hủy'),
    )

    MEETING_TYPE_CHOICES = (
        ('offline', 'Trực tiếp tại văn phòng khoa'),
        ('online', 'Trực tuyến (Online Meeting)'),
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_appointments',
        verbose_name="Sinh viên"
    )
    advisor = models.ForeignKey(
        AdvisorProfile,
        on_delete=models.CASCADE,
        related_name='advisor_appointments',
        verbose_name="Cố vấn học tập"
    )
    schedule = models.ForeignKey(
        AdvisorSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Khung giờ gốc"
    )
    date = models.DateField(verbose_name="Ngày hẹn")
    start_time = models.TimeField(verbose_name="Giờ bắt đầu")
    end_time = models.TimeField(verbose_name="Giờ kết thúc")
    meeting_type = models.CharField(
        max_length=20,
        choices=MEETING_TYPE_CHOICES,
        default='offline',
        verbose_name="Hình thức tư vấn"
    )
    topic = models.CharField(
        max_length=255,
        verbose_name="Chủ đề cần tư vấn",
        help_text="Ví dụ: Tư vấn đăng ký học phần / Đổi ngành / Cảnh báo học vụ"
    )
    student_notes = models.TextField(
        blank=True,
        default='',
        verbose_name="Mô tả chi tiết vấn đề",
        help_text="Mô tả cụ thể những khúc mắc cần giải đáp để cố vấn chuẩn bị trước."
    )
    location_or_link = models.CharField(
        max_length=500,
        blank=True,
        default='',
        verbose_name="Địa điểm phòng gặp hoặc Link phòng họp trực tuyến",
        help_text="Ví dụ: Văn phòng Khoa - Phòng A1-203 hoặc phòng họp trực tuyến nội bộ"
    )
    advisor_notes = models.TextField(
        blank=True,
        default='',
        verbose_name="Ghi chú / Kết luận của Cố vấn sau buổi hẹn"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Trạng thái"
    )
    cancel_reason = models.TextField(
        blank=True,
        default='',
        verbose_name="Lý do hủy"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian đặt")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lần cuối")

    class Meta:
        verbose_name = "Lịch hẹn tư vấn 1-1"
        verbose_name_plural = "Lịch hẹn tư vấn 1-1"
        ordering = ['-date', '-start_time']
        indexes = [
            models.Index(fields=['advisor', 'date', 'status']),
            models.Index(fields=['student', '-date']),
        ]

    def __str__(self):
        return f"Lịch hẹn: {self.student.get_full_name() or self.student.username} - {self.advisor.display_name} ({self.date} {self.start_time.strftime('%H:%M')})"

    def get_status_badge(self):
        badges = {
            'pending': 'bg-warning text-dark',
            'confirmed': 'bg-primary text-white',
            'completed': 'bg-success text-white',
            'canceled': 'bg-danger text-white',
        }
        return badges.get(self.status, 'bg-secondary text-white')
