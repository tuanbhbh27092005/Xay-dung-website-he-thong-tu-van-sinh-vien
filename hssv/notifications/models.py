from django.db import models
from django.conf import settings


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="Người nhận",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications_sent',
        verbose_name="Người tạo hành động",
    )
    verb = models.CharField(max_length=255, verbose_name="Nội dung thông báo")
    target_url = models.CharField(max_length=255, blank=True, default='', verbose_name="Đường dẫn đích")
    is_read = models.BooleanField(default=False, verbose_name="Đã đọc")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian tạo")

    class Meta:
        verbose_name = "Thông báo"
        verbose_name_plural = "Thông báo"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f"Thông báo tới {self.recipient.username}: {self.verb[:40]}"

    @classmethod
    def notify(cls, recipient, verb, actor=None, target_url=''):
        """Tạo thông báo mới nhanh chóng."""
        if not recipient:
            return None
        # Không tự gửi thông báo cho chính mình
        if actor and recipient.id == actor.id:
            return None
        return cls.objects.create(
            recipient=recipient,
            actor=actor,
            verb=verb,
            target_url=target_url,
        )
