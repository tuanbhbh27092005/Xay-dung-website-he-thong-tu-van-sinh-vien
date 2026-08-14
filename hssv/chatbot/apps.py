from django.apps import AppConfig


class ChatbotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chatbot'
    verbose_name = "Chatbot tư vấn"

    def ready(self):
        # Đăng ký signal khi Answer được tạo/cập nhật để tự động re-index embedding
        from . import signals  # noqa: F401
