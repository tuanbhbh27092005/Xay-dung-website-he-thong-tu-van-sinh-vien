from django.db import models
from accounts.models import CustomUser
from questions.models import Department

# Create your models here.

class AdvisorProfile(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin hệ thống'),
        ('advisor', 'Ban tư vấn'),
    )

    # Học hàm/học vị hiển thị trước tên tư vấn viên trên UI public
    # (vd: "ThS. Nguyễn Văn A", "PGS.TS. Trần Văn B"). Để trống nếu là admin kỹ thuật.
    ACADEMIC_TITLE_CHOICES = (
        ('', 'Không hiển thị'),
        ('CN', 'Cử nhân (CN)'),
        ('KS', 'Kỹ sư (KS)'),
        ('ThS', 'Thạc sĩ (ThS)'),
        ('TS', 'Tiến sĩ (TS)'),
        ('PGS.TS', 'Phó Giáo sư - Tiến sĩ (PGS.TS)'),
        ('GS.TS', 'Giáo sư - Tiến sĩ (GS.TS)'),
    )

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, verbose_name="Người dùng")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Khoa/Đơn vị")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name="Vai trò")
    academic_title = models.CharField(
        max_length=10,
        choices=ACADEMIC_TITLE_CHOICES,
        blank=True,
        default='',
        verbose_name="Học hàm/Học vị",
        help_text="Hiển thị trước tên tư vấn viên trong các câu trả lời công khai.",
    )
    position = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name="Chức vụ",
        help_text="Vd: Trưởng khoa, Phó trưởng phòng đào tạo, Cố vấn học tập…",
    )
    avatar = models.ImageField(
        upload_to='advisors/',
        blank=True, null=True,
        verbose_name="Ảnh đại diện",
        help_text="Ảnh JPEG/PNG, hình vuông sẽ đẹp nhất. Tối đa ~3 MB.",
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    @property
    def display_name(self):
        """Tên hiển thị có học hàm: 'ThS. Nguyễn Văn A'."""
        full = self.user.get_full_name() or self.user.username
        return f"{self.academic_title}. {full}" if self.academic_title else full

    class Meta:
        verbose_name = "Hồ sơ tư vấn viên"
        verbose_name_plural = "Hồ sơ tư vấn viên"
