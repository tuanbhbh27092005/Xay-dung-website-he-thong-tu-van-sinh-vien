"""
Signals tự động re-index embedding khi:
- Có Answer mới được tạo
- Answer hiện có được cập nhật
- Question đổi status (qua Question.save)
"""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='questions.Answer')
def reindex_on_answer_save(sender, instance, created, **kwargs):
    """Khi có câu trả lời mới hoặc cập nhật → re-index câu hỏi tương ứng."""
    try:
        from .services.embedding_service import index_question
        index_question(instance.question)
    except Exception as e:
        # Không để signal làm crash việc save Answer
        logger.warning(
            f"Không re-index được Q#{instance.question_id} sau khi save Answer: {e}"
        )


@receiver(post_delete, sender='questions.Answer')
def reindex_on_answer_delete(sender, instance, **kwargs):
    """Khi câu trả lời bị xóa → re-index lại (hoặc xóa embedding nếu không còn answer nào)."""
    try:
        from .services.embedding_service import index_question
        # index_question tự xử lý: nếu không còn answer thì không tạo embedding
        index_question(instance.question)
    except Exception as e:
        logger.warning(f"Không re-index sau khi xóa Answer: {e}")


@receiver(post_save, sender='news.News')
def reindex_on_news_save(sender, instance, created, **kwargs):
    """Khi tin tức mới/cập nhật → re-index để chatbot có thể trả lời câu hỏi liên quan."""
    try:
        from .services.embedding_service import index_news
        index_news(instance)
    except Exception as e:
        logger.warning(
            f"Không re-index được News#{instance.id} sau khi save: {e}"
        )


@receiver(post_delete, sender='news.News')
def reindex_on_news_delete(sender, instance, **kwargs):
    """Khi xoá tin tức → xoá embedding tương ứng (CASCADE đã làm nhưng đề phòng)."""
    try:
        from .models import NewsEmbedding
        NewsEmbedding.objects.filter(news_id=instance.id).delete()
    except Exception as e:
        logger.warning(f"Không xoá NewsEmbedding sau khi xoá News#{instance.id}: {e}")
