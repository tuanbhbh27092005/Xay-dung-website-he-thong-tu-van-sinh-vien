from django.db import models
from django.conf import settings


class ChatSession(models.Model):
    """Một phiên chat của user (hoặc khách) với chatbot."""

    STATE_CHOICES = [
        ('initial', 'Chưa bắt đầu'),
        ('chatting', 'Đang trò chuyện'),
        # ─── Legacy states (V1 state machine, giữ cho migration & data cũ) ───
        ('collecting_dept', 'Đang chọn khoa'),
        ('collecting_major', 'Đang chọn ngành'),
        ('collecting_category', 'Đang chọn loại câu hỏi'),
        ('showing_results', 'Đã hiển thị kết quả'),
        ('escalation_form', 'Đang xác nhận chuyển tư vấn viên'),
        ('completed', 'Hoàn tất'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        verbose_name="Người dùng"
    )
    session_key = models.CharField(max_length=40, db_index=True, verbose_name="Session key")
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Bắt đầu")
    escalated_to_advisor = models.BooleanField(default=False, verbose_name="Đã chuyển tư vấn viên")

    # ─── State machine fields ───
    state = models.CharField(max_length=30, choices=STATE_CHOICES, default='initial', verbose_name="Trạng thái")
    initial_question = models.TextField(blank=True, verbose_name="Mô tả ban đầu")
    collected_dept_id = models.IntegerField(null=True, blank=True, verbose_name="Khoa đã chọn")
    collected_major_id = models.IntegerField(null=True, blank=True, verbose_name="Ngành đã chọn")
    collected_category_id = models.IntegerField(null=True, blank=True, verbose_name="Loại câu hỏi đã chọn")

    class Meta:
        verbose_name = "Phiên chat"
        verbose_name_plural = "Phiên chat"
        ordering = ['-started_at']

    def __str__(self):
        who = self.user.username if self.user else "Khách"
        return f"Phiên #{self.id} - {who} ({self.get_state_display()})"

    def reset(self):
        """Reset toàn bộ context, quay về initial state."""
        self.state = 'initial'
        self.initial_question = ''
        self.collected_dept_id = None
        self.collected_major_id = None
        self.collected_category_id = None
        self.save(update_fields=[
            'state', 'initial_question',
            'collected_dept_id', 'collected_major_id', 'collected_category_id',
        ])


class ChatMessage(models.Model):
    """Một tin nhắn trong phiên chat."""
    ROLE_CHOICES = [
        ('user', 'Người dùng'),
        ('bot', 'Bot'),
        ('system', 'Hệ thống'),
    ]
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="Phiên chat"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, verbose_name="Vai trò")
    content = models.TextField(verbose_name="Nội dung")
    confidence = models.FloatField(null=True, blank=True, verbose_name="Độ tin cậy")
    retrieved_question_ids = models.CharField(max_length=200, blank=True, verbose_name="ID câu hỏi tham khảo")
    needs_advisor = models.BooleanField(default=False, verbose_name="Cần tư vấn viên")

    # ─── Metadata cho interactive elements (buttons / qa_results / escalation_form) ───
    metadata = models.JSONField(
        null=True, blank=True,
        verbose_name="Metadata (interactive payload)",
        help_text="JSON chứa payload buttons/cards/form đi kèm tin nhắn này. None nếu chỉ là text."
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian")

    class Meta:
        verbose_name = "Tin nhắn chat"
        verbose_name_plural = "Tin nhắn chat"
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}"


class QuestionEmbedding(models.Model):
    """
    Vector embedding của các câu hỏi đã trả lời, dùng cho retrieval RAG.
    Chỉ index câu hỏi PUBLIC (is_public=True) để tránh leak câu riêng tư qua chatbot.
    """
    question = models.OneToOneField(
        'questions.Question',
        on_delete=models.CASCADE,
        related_name='embedding',
        verbose_name="Câu hỏi"
    )
    embedding = models.JSONField(verbose_name="Vector embedding")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lần cuối")

    class Meta:
        verbose_name = "Embedding câu hỏi"
        verbose_name_plural = "Embedding câu hỏi"

    def __str__(self):
        return f"Embedding của Q#{self.question_id}"


class ContentReport(models.Model):
    """
    Báo cáo nội dung vi phạm (do hệ thống tự phát hiện hoặc người dùng report).
    Gom cả tin nhắn chat bot + bình luận tin tức để tư vấn viên xử lý 1 chỗ.
    """
    SOURCE_CHOICES = [
        ('chat', 'Tin nhắn chatbot'),
        ('comment', 'Bình luận tin tức'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Chờ xử lý'),
        ('approved', 'Đã duyệt (không vi phạm)'),
        ('hidden', 'Đã ẩn / xoá'),
        ('warned', 'Đã cảnh báo user'),
    ]

    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES,
        verbose_name="Loại nội dung",
    )
    # Một trong 2 sẽ được set tùy `source`:
    chat_message = models.ForeignKey(
        ChatMessage, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='reports',
        verbose_name="Tin nhắn chat",
    )
    comment = models.ForeignKey(
        'news.Comment', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='reports',
        verbose_name="Bình luận",
    )

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='content_reports_made',
        verbose_name="Người báo cáo (None = hệ thống tự)",
    )
    content_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='content_reports_received',
        verbose_name="User tạo nội dung",
    )

    snapshot_text = models.TextField(
        verbose_name="Nội dung khi vi phạm",
        help_text="Lưu lại text gốc để khi user/admin xoá vẫn còn ngữ cảnh.",
    )
    matched_words = models.CharField(
        max_length=300, blank=True,
        verbose_name="Từ vi phạm phát hiện",
    )
    reason = models.CharField(
        max_length=200, blank=True, default='',
        verbose_name="Lý do (nếu user báo cáo)",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending',
        verbose_name="Trạng thái",
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='content_reports_reviewed',
        verbose_name="Người xử lý",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời điểm xử lý")
    admin_note = models.TextField(blank=True, default='', verbose_name="Ghi chú xử lý")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời điểm phát hiện")

    class Meta:
        verbose_name = "Báo cáo nội dung vi phạm"
        verbose_name_plural = "Báo cáo nội dung vi phạm"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['source', 'status']),
        ]

    def __str__(self):
        return f"Report#{self.id} [{self.get_source_display()}] - {self.get_status_display()}"


class NewsEmbedding(models.Model):
    """
    Vector embedding của các bài tin tức đã công bố, dùng cho RAG để chatbot
    có thể trả lời các câu hỏi liên quan tới tin trường / khoa / tuyển sinh.
    Chỉ index bài đã `is_published=True`.
    """
    news = models.OneToOneField(
        'news.News',
        on_delete=models.CASCADE,
        related_name='embedding',
        verbose_name="Bài tin tức"
    )
    embedding = models.JSONField(verbose_name="Vector embedding")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lần cuối")

    class Meta:
        verbose_name = "Embedding tin tức"
        verbose_name_plural = "Embedding tin tức"

    def __str__(self):
        return f"Embedding News#{self.news_id}"
