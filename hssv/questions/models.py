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

    class Meta:
        verbose_name = "Câu hỏi"
        verbose_name_plural = "Câu hỏi"
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
