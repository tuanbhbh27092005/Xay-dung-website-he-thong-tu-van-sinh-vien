from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.urls import reverse
import unicodedata
import re


def vi_slugify(s: str) -> str:
    """Slugify hỗ trợ tiếng Việt (loại dấu rồi slugify chuẩn)."""
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    s = re.sub(r'[^\w\s-]', '', s).strip().lower()
    return re.sub(r'[-\s]+', '-', s) or 'tin-tuc'


class News(models.Model):
    CATEGORY_CHOICES = [
        ('admission', 'Tuyển sinh'),
        ('event', 'Sự kiện'),
        ('school', 'Tin trường'),
        ('department', 'Tin khoa'),
        ('class', 'Tin lớp / Sinh viên'),
    ]

    title = models.CharField(max_length=200, verbose_name="Tiêu đề")
    slug = models.SlugField(max_length=220, unique=True, blank=True,
                            verbose_name="Slug",
                            help_text="Để trống sẽ tự động sinh từ tiêu đề.")
    summary = models.CharField(
        max_length=500, blank=True, verbose_name="Tóm tắt",
        help_text="Đoạn ngắn 1-2 câu hiển thị ở danh sách. Để trống sẽ tự lấy từ nội dung."
    )
    content = models.TextField(verbose_name="Nội dung")
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES,
        default='school', verbose_name="Phân loại"
    )
    department = models.ForeignKey(
        'questions.Department',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Khoa/Đơn vị (nếu là tin khoa)"
    )
    thumbnail_image = models.ImageField(
        upload_to='news/thumbnails/',
        blank=True, null=True,
        verbose_name="Ảnh đại diện (upload)",
        help_text="Upload file ảnh từ máy tính. Ưu tiên dùng cái này thay vì URL."
    )
    thumbnail_url = models.URLField(
        max_length=500, blank=True,
        verbose_name="URL ảnh đại diện (dự phòng)",
        help_text="Chỉ dùng khi không upload được file: paste URL ảnh từ internet."
    )

    def thumbnail_src(self):
        """Trả về src cho thumbnail: ưu tiên file upload, fallback URL."""
        if self.thumbnail_image:
            try:
                return self.thumbnail_image.url
            except ValueError:
                pass
        return self.thumbnail_url or ''
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='news_articles',
        verbose_name="Tác giả"
    )
    is_published = models.BooleanField(
        default=True,
        verbose_name="Đã công bố",
        help_text="Bỏ tick để lưu nháp, không hiển thị ngoài trang công khai."
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name="Tin nổi bật",
        help_text="Bài này sẽ được pin lên đầu danh sách tin tức và đánh dấu badge 'NỔI BẬT'."
    )
    views_count = models.PositiveIntegerField(default=0, verbose_name="Lượt xem")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")

    class Meta:
        verbose_name = "Tin tức"
        verbose_name_plural = "Tin tức"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['category', '-created_at']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Auto sinh slug nếu chưa có
        if not self.slug:
            base = vi_slugify(self.title)[:200]
            slug = base
            i = 2
            while News.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug

        # Auto sinh summary nếu chưa có
        if not self.summary and self.content:
            self.summary = self.content[:280] + ('...' if len(self.content) > 280 else '')

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('news:detail', kwargs={'slug': self.slug})

    @property
    def visible_comments(self):
        return self.comments.filter(is_hidden=False)

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def reading_time_minutes(self):
        """
        Ước lượng thời gian đọc dựa trên số từ trong content.
        Tốc độ đọc trung bình tiếng Việt: ~200 từ/phút (tương đương tiếng Anh
        nhưng từ tiếng Việt ngắn hơn nên đọc nhanh hơn chút).
        Trả về tối thiểu 1 phút.
        """
        word_count = len((self.content or '').split())
        return max(1, round(word_count / 200))


class NewsLike(models.Model):
    """Thả tim cho tin tức. Mỗi user chỉ thả tim 1 lần / 1 tin (UNIQUE constraint)."""
    news = models.ForeignKey(
        News, on_delete=models.CASCADE,
        related_name='likes',
        verbose_name="Tin tức"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='news_likes',
        verbose_name="Người thả tim"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày thả tim")

    class Meta:
        verbose_name = "Lượt thả tim"
        verbose_name_plural = "Lượt thả tim"
        # Mỗi user chỉ được thả 1 tim trên 1 tin → UNIQUE composite
        unique_together = [('news', 'user')]
        indexes = [
            models.Index(fields=['news']),
        ]

    def __str__(self):
        return f"{self.user.username} ❤ {self.news.title[:30]}"


class Comment(models.Model):
    news = models.ForeignKey(
        News, on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="Tin tức"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="Người bình luận"
    )
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='replies',
        verbose_name="Bình luận gốc",
        help_text="Nếu là reply: trỏ tới comment cha. Null = comment gốc trên bài.",
    )
    content = models.TextField(verbose_name="Nội dung")
    is_hidden = models.BooleanField(
        default=False,
        verbose_name="Đã ẩn",
        help_text="Tư vấn viên có thể ẩn bình luận vi phạm."
    )
    has_sensitive = models.BooleanField(
        default=False,
        verbose_name="Có ngôn từ nhạy cảm",
        help_text="Sẽ được set tự động trong Phase D (lọc ngôn từ)."
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")

    class Meta:
        verbose_name = "Bình luận"
        verbose_name_plural = "Bình luận"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username}: {self.content[:50]}"

    @property
    def visible_replies(self):
        return self.replies.filter(is_hidden=False).select_related('user').order_by('created_at')
