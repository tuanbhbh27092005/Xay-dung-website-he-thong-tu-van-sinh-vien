from django.db import models
from accounts.models import CustomUser


class Department(models.Model):
    name = models.CharField(max_length=100, verbose_name="Tên khoa/đơn vị")
    description = models.TextField(blank=True, verbose_name="Mô tả")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Khoa/Đơn vị"
        verbose_name_plural = "Khoa/Đơn vị"


class Major(models.Model):
    name = models.CharField(max_length=100, verbose_name="Tên ngành")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name="Khoa/Đơn vị")
    description = models.TextField(blank=True, verbose_name="Mô tả")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Ngành học"
        verbose_name_plural = "Ngành học"


class QuestionCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Tên loại câu hỏi")
    description = models.TextField(blank=True, verbose_name="Mô tả")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Loại câu hỏi"
        verbose_name_plural = "Loại câu hỏi"


class Question(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Chưa trả lời'),
        ('answered', 'Đã trả lời'),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="Người đặt câu hỏi")
    title = models.CharField(max_length=200, verbose_name="Tiêu đề")
    content = models.TextField(verbose_name="Nội dung")
    major = models.ForeignKey(Major, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Ngành học liên quan")
    category = models.ForeignKey(QuestionCategory, on_delete=models.SET_NULL, null=True, verbose_name="Loại câu hỏi")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Trạng thái")

    # ← FIELD MỚI: phân biệt câu hỏi công khai (mọi người thấy) hay riêng tư (chỉ owner + tư vấn viên thấy)
    is_public = models.BooleanField(
        default=True,
        verbose_name="Công khai",
        help_text="Câu hỏi công khai hiển thị trên trang chủ và chatbot trả lời cho mọi user. "
                  "Riêng tư chỉ owner và tư vấn viên thấy."
    )

    # ← FIELD MỚI: Cho phép đặt câu hỏi ẩn danh
    is_anonymous = models.BooleanField(
        default=False,
        verbose_name="Đặt câu hỏi ẩn danh",
        help_text="Ẩn danh tính với người dùng khác và trên các trang công khai."
    )

    # ─── Counter cho trang chủ "câu hỏi được quan tâm nhất" ───
    views_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Lượt xem",
        help_text="Tăng tự động mỗi lần truy cập trang chi tiết câu hỏi (loại trừ tác giả)."
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")

    def __str__(self):
        return self.title

    def can_view(self, user):
        """User được xem câu hỏi này không?"""
        if self.is_public:
            return True
        # Riêng tư: chỉ owner + tư vấn viên (any) được xem
        if not user.is_authenticated:
            return False
        if self.user_id == user.id:
            return True
        return hasattr(user, 'advisorprofile') and user.advisorprofile is not None

    def get_author_display(self, viewer=None):
        """
        Trả về tên hiển thị của người đặt câu hỏi tuỳ theo quyền của viewer.
        (Tuần 1: Phạm Hoàng Thái Tuấn tối ưu bảo mật danh tính câu hỏi ẩn danh).
        """
        if not self.is_anonymous:
            return self.user.get_full_name() or self.user.username
        # Nếu là câu hỏi ẩn danh:
        if viewer and viewer.is_authenticated:
            if viewer.id == self.user_id:
                return "Bạn (Ẩn danh)"
            if hasattr(viewer, 'advisorprofile') and viewer.advisorprofile is not None:
                real_name = self.user.get_full_name() or self.user.username
                student_id = f" - MSSV: {self.user.student_id}" if self.user.student_id else ""
                return f"{real_name}{student_id} [Ẩn danh]"
        return "Sinh viên ẩn danh"

    @property
    def public_author_display(self):
        """Tên hiển thị mặc định cho giao diện công khai."""
        return self.get_author_display()

    class Meta:
        verbose_name = "Câu hỏi"
        verbose_name_plural = "Câu hỏi"
        ordering = ['-created_at']


class QuestionFeedback(models.Model):
    RATING_CHOICES = (
        (1, '1 sao - Rất không hài lòng'),
        (2, '2 sao - Không hài lòng'),
        (3, '3 sao - Bình thường'),
        (4, '4 sao - Hài lòng'),
        (5, '5 sao - Rất hài lòng'),
    )

    question = models.OneToOneField(
        Question,
        on_delete=models.CASCADE,
        related_name='feedback',
        verbose_name="Câu hỏi"
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name="Người đánh giá"
    )
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        verbose_name="Điểm đánh giá (sao)"
    )
    comment = models.TextField(
        blank=True,
        default='',
        verbose_name="Nhận xét / Góp ý"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày đánh giá")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")

    def __str__(self):
        return f"Đánh giá {self.rating}★ cho: {self.question.title[:30]}"

    class Meta:
        verbose_name = "Đánh giá câu trả lời"
        verbose_name_plural = "Đánh giá câu trả lời"
        ordering = ['-created_at']


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers', verbose_name="Câu hỏi")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="Người trả lời")
    content = models.TextField(verbose_name="Nội dung")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")

    def __str__(self):
        return f"Trả lời cho {self.question.title}"

    class Meta:
        verbose_name = "Câu trả lời"
        verbose_name_plural = "Câu trả lời"
        ordering = ['created_at']
