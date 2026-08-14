"""
Service tạo embedding cho các câu hỏi đã được trả lời và lưu vào DB.

PHASE B THAY ĐỔI: chỉ index câu hỏi PUBLIC (is_public=True).
Câu hỏi riêng tư không vào RAG retrieval → tránh leak data sang user khác.
"""
import logging
from typing import Optional
from django.db import transaction
from questions.models import Question
from ..models import QuestionEmbedding, NewsEmbedding
from . import gemini_client

logger = logging.getLogger(__name__)


def _build_indexable_text(question: Question) -> str:
    """Ghép title + content + answer đầu tiên thành đoạn text để embed."""
    parts = [
        f"Câu hỏi: {question.title}",
        f"Nội dung: {question.content}",
    ]
    if question.major:
        parts.append(f"Ngành: {question.major.name}")
    if question.category:
        parts.append(f"Loại: {question.category.name}")

    first_answer = question.answers.order_by('created_at').first()
    if first_answer:
        parts.append(f"Trả lời: {first_answer.content}")

    return "\n".join(parts)


@transaction.atomic
def index_question(question: Question) -> Optional[QuestionEmbedding]:
    """
    Tạo/cập nhật embedding cho 1 câu hỏi.
    Điều kiện index:
        - status == 'answered'
        - is_public == True (mới: tránh leak private Q&A)
        - có ít nhất 1 answer
    """
    if question.status != 'answered':
        QuestionEmbedding.objects.filter(question=question).delete()
        return None

    # Kiểm tra is_public (field này được thêm trong Phase A)
    if not getattr(question, 'is_public', True):
        # Riêng tư → xoá embedding nếu có
        QuestionEmbedding.objects.filter(question=question).delete()
        return None

    if not question.answers.exists():
        return None

    text = _build_indexable_text(question)
    try:
        vec = gemini_client.embed_text(text, task_type="RETRIEVAL_DOCUMENT")
    except Exception as e:
        logger.error(f"Không tạo được embedding cho Q#{question.id}: {e}")
        return None

    obj, _ = QuestionEmbedding.objects.update_or_create(
        question=question,
        defaults={'embedding': vec},
    )
    return obj


def reindex_all() -> int:
    """Tạo lại embedding cho TẤT CẢ câu hỏi đã trả lời + công khai."""
    count = 0
    questions = Question.objects.filter(
        status='answered',
        is_public=True,
    ).prefetch_related('answers')

    total = questions.count()
    logger.info(f"Bắt đầu index {total} câu hỏi public...")

    for i, q in enumerate(questions, 1):
        try:
            if index_question(q):
                count += 1
            if i % 10 == 0:
                logger.info(f"  Đã xử lý {i}/{total}")
        except Exception as e:
            logger.error(f"Lỗi khi index Q#{q.id}: {e}")

    logger.info(f"Hoàn tất: {count}/{total} câu hỏi được index")
    return count


# ============================================================
# NEWS INDEXING (RAG cho tin tức)
# ============================================================
def _build_news_indexable_text(news) -> str:
    """Ghép title + category + summary + content để embed."""
    parts = [
        f"Tiêu đề: {news.title}",
        f"Phân loại: {news.get_category_display()}",
    ]
    if news.department:
        parts.append(f"Khoa/Đơn vị: {news.department.name}")
    if news.summary:
        parts.append(f"Tóm tắt: {news.summary}")
    if news.content:
        # Cắt bớt content quá dài để giảm token cost
        content = news.content[:4000]
        parts.append(f"Nội dung: {content}")
    return "\n".join(parts)


@transaction.atomic
def index_news(news) -> Optional[NewsEmbedding]:
    """Tạo / cập nhật embedding cho 1 bài news. Chỉ index bài đã publish."""
    if not getattr(news, 'is_published', False):
        NewsEmbedding.objects.filter(news=news).delete()
        return None

    text = _build_news_indexable_text(news)
    try:
        vec = gemini_client.embed_text(text, task_type="RETRIEVAL_DOCUMENT")
    except Exception as e:
        logger.error(f"Không tạo được embedding cho News#{news.id}: {e}")
        return None

    obj, _ = NewsEmbedding.objects.update_or_create(
        news=news,
        defaults={'embedding': vec},
    )
    return obj


def reindex_all_news() -> int:
    """Tạo lại embedding cho TẤT CẢ news đã publish."""
    from news.models import News
    count = 0
    news_qs = News.objects.filter(is_published=True)
    total = news_qs.count()
    logger.info(f"Bắt đầu index {total} bài news...")

    for i, n in enumerate(news_qs, 1):
        try:
            if index_news(n):
                count += 1
            if i % 10 == 0:
                logger.info(f"  Đã xử lý {i}/{total}")
        except Exception as e:
            logger.error(f"Lỗi khi index News#{n.id}: {e}")

    logger.info(f"Hoàn tất: {count}/{total} bài news được index")
    return count
