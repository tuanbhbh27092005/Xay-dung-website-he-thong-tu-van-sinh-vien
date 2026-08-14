"""
Management command: tạo lại embedding cho TẤT CẢ câu hỏi đã trả lời.

Sử dụng:
    python manage.py build_embeddings

Khi nào chạy:
- Lần đầu sau khi đã có sẵn dữ liệu Q&A trong DB (signal chưa kịp chạy).
- Sau khi import dữ liệu thô.
- Khi đổi model embedding hoặc cách build text.
"""
from django.core.management.base import BaseCommand
from chatbot.services.embedding_service import reindex_all


class Command(BaseCommand):
    help = "Tạo lại embedding cho tất cả câu hỏi đã trả lời."

    def handle(self, *args, **options):
        self.stdout.write("Bắt đầu tạo embedding cho các câu hỏi đã trả lời...")
        try:
            count = reindex_all()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Lỗi: {e}"))
            return
        self.stdout.write(self.style.SUCCESS(
            f"Hoàn tất! Đã index {count} câu hỏi."
        ))
