"""
Management command: tạo embedding cho TẤT CẢ tin tức đã công bố.

Sử dụng:
    python manage.py build_news_embeddings
"""
from django.core.management.base import BaseCommand
from chatbot.services.embedding_service import reindex_all_news


class Command(BaseCommand):
    help = "Tạo lại embedding cho tất cả tin tức đã công bố (để chatbot có thể search)."

    def handle(self, *args, **options):
        self.stdout.write("Bắt đầu tạo embedding cho các bài tin tức...")
        try:
            count = reindex_all_news()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Lỗi: {e}"))
            return
        self.stdout.write(self.style.SUCCESS(
            f"Hoàn tất! Đã index {count} bài tin tức."
        ))
