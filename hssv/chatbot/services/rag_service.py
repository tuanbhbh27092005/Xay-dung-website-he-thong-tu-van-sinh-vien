"""
RAG service phiên bản 3 (Phase B):
- Hỗ trợ filtered search theo (dept_id, major_id, category_id)
- Fallback broadening: nếu strict filter không có kết quả, mở rộng dần
- Threshold thấp hơn khi có metadata filter (vì đã chắc chắn cùng chủ đề)
"""
import logging
import math
from typing import List, Optional, Tuple

from ..models import QuestionEmbedding, NewsEmbedding
from . import gemini_client

logger = logging.getLogger(__name__)

# Threshold cho similarity:
# - Strict (chỉ tìm theo similarity, không filter): 0.55
# - Filtered (đã có dept/major/category): 0.40 (relaxed vì đã narrow scope)
SIMILARITY_THRESHOLD_STRICT = 0.55
SIMILARITY_THRESHOLD_FILTERED = 0.40
SIMILARITY_THRESHOLD_NEWS = 0.45  # news ngắn hơn Q&A, threshold lỏng hơn chút
TOP_K = 3
TOP_K_NEWS = 2  # ít news hơn để tránh ngợp UI


def cosine_similarity(a: list, b: list) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def search_qa(
    query: str,
    dept_id: Optional[int] = None,
    major_id: Optional[int] = None,
    category_id: Optional[int] = None,
    top_k: int = TOP_K,
) -> List[Tuple]:
    """
    Tìm top-K Q&A tương đồng nhất với query, có thể filter theo metadata.

    Pipeline broadening: nếu strict filter không có đủ kết quả, lần lượt drop:
        1. (dept, major, category) - strict nhất
        2. (dept, major, _) - drop category
        3. (dept, _, _) - drop major
        4. (_, _, _) - không filter

    Trả về: list [(Question, similarity_score), ...] đã sort desc.
    """
    try:
        query_vec = gemini_client.embed_query(query)
    except Exception as e:
        logger.error(f"Không embed được query: {e}")
        return []

    # Threshold tuỳ có filter hay không
    has_filter = bool(dept_id or major_id or category_id)
    threshold = SIMILARITY_THRESHOLD_FILTERED if has_filter else SIMILARITY_THRESHOLD_STRICT

    # Thử lần lượt từ strict đến lỏng
    filter_attempts = []
    if has_filter:
        filter_attempts.append({'dept_id': dept_id, 'major_id': major_id, 'category_id': category_id})
        if category_id:
            filter_attempts.append({'dept_id': dept_id, 'major_id': major_id, 'category_id': None})
        if major_id:
            filter_attempts.append({'dept_id': dept_id, 'major_id': None, 'category_id': None})
    filter_attempts.append({'dept_id': None, 'major_id': None, 'category_id': None})  # final fallback

    for attempt in filter_attempts:
        results = _search_with_filter(query_vec, threshold=threshold, top_k=top_k, **attempt)
        if results:
            return results
        # Nếu lỏng dần thì threshold cũng nên strict hơn (vì không còn filter context)
        threshold = SIMILARITY_THRESHOLD_STRICT

    return []


def _search_with_filter(
    query_vec: list,
    dept_id: Optional[int],
    major_id: Optional[int],
    category_id: Optional[int],
    threshold: float,
    top_k: int,
) -> List[Tuple]:
    """Helper: tính similarity trên QuestionEmbedding queryset đã filter."""
    qs = QuestionEmbedding.objects.select_related(
        'question', 'question__major', 'question__major__department', 'question__category',
    ).filter(
        question__status='answered',
        question__is_public=True,
    )

    if dept_id and not major_id:
        qs = qs.filter(question__major__department_id=dept_id)
    if major_id:
        qs = qs.filter(question__major_id=major_id)
    if category_id:
        qs = qs.filter(question__category_id=category_id)

    scored = []
    for qe in qs:
        sim = cosine_similarity(query_vec, qe.embedding)
        if sim >= threshold:
            scored.append((qe.question, sim))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


# ============================================================
# NEWS RAG SEARCH
# ============================================================
def search_news(
    query: str,
    dept_id: Optional[int] = None,
    top_k: int = TOP_K_NEWS,
    query_vec: Optional[list] = None,
) -> List[Tuple]:
    """
    Tìm top-K bài news liên quan tới query.
    Có thể filter theo dept_id (chỉ lấy tin của khoa đó hoặc tin trường chung).
    Trả về list [(News, similarity), ...] đã sort desc.
    """
    if query_vec is None:
        try:
            query_vec = gemini_client.embed_query(query)
        except Exception as e:
            logger.error(f"Không embed được query cho news: {e}")
            return []

    qs = NewsEmbedding.objects.select_related('news', 'news__department').filter(
        news__is_published=True,
    )

    # Nếu user có chọn khoa: ưu tiên tin của khoa đó + tin chung (department=None)
    if dept_id:
        from django.db.models import Q
        qs = qs.filter(Q(news__department_id=dept_id) | Q(news__department__isnull=True))

    scored = []
    for ne in qs:
        sim = cosine_similarity(query_vec, ne.embedding)
        if sim >= SIMILARITY_THRESHOLD_NEWS:
            scored.append((ne.news, sim))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def search_qa_and_news(
    query: str,
    dept_id: Optional[int] = None,
    major_id: Optional[int] = None,
    category_id: Optional[int] = None,
    top_k_qa: int = TOP_K,
    top_k_news: int = TOP_K_NEWS,
) -> dict:
    """
    Combined search: trả về cả Q&A và news liên quan.
    Reuse query embedding cho cả 2 để tiết kiệm 1 lần gọi API.
    """
    try:
        query_vec = gemini_client.embed_query(query)
    except Exception as e:
        logger.error(f"Không embed được query: {e}")
        return {'qa': [], 'news': []}

    # Q&A search - reuse logic của search_qa nhưng truyền sẵn query_vec
    has_filter = bool(dept_id or major_id or category_id)
    threshold = SIMILARITY_THRESHOLD_FILTERED if has_filter else SIMILARITY_THRESHOLD_STRICT

    filter_attempts = []
    if has_filter:
        filter_attempts.append({'dept_id': dept_id, 'major_id': major_id, 'category_id': category_id})
        if category_id:
            filter_attempts.append({'dept_id': dept_id, 'major_id': major_id, 'category_id': None})
        if major_id:
            filter_attempts.append({'dept_id': dept_id, 'major_id': None, 'category_id': None})
    filter_attempts.append({'dept_id': None, 'major_id': None, 'category_id': None})

    qa_results = []
    cur_thres = threshold
    for attempt in filter_attempts:
        qa_results = _search_with_filter(query_vec, threshold=cur_thres, top_k=top_k_qa, **attempt)
        if qa_results:
            break
        cur_thres = SIMILARITY_THRESHOLD_STRICT

    # News search (reuse query_vec)
    news_results = search_news(query, dept_id=dept_id, top_k=top_k_news, query_vec=query_vec)

    return {'qa': qa_results, 'news': news_results}


# ============================================================
# Generation (gọi Gemini với context Q&A)
# Dùng cho phần "khái quát kết quả" sau khi đã retrieve.
# Phase B chủ yếu show Q&A trực tiếp dạng cards, không cần generation lắm.
# Giữ hàm này để fallback khi muốn tóm tắt.
# ============================================================
SUMMARIZE_PROMPT = """Bạn là trợ lý ảo của ban tư vấn sinh viên trường ĐH Sư phạm Kỹ thuật TP.HCM.

CÂU HỎI USER: {query}

CÁC Q&A LIÊN QUAN TỪ DATABASE:
{context}

Yêu cầu:
- Tóm tắt ngắn gọn (3-4 câu) câu trả lời dựa trên các Q&A trên.
- KHÔNG bịa thông tin ngoài phạm vi tham khảo.
- Nếu Q&A không đủ rõ, kết thúc bằng: "Để biết chính xác, bạn nên hỏi tư vấn viên".

Câu tóm tắt:"""


def summarize_with_context(query: str, top_qs: List[Tuple]) -> str:
    """
    Tóm tắt các Q&A đã retrieve thành 1 câu trả lời chung.
    Dùng khi muốn show câu tóm tắt "phía trên" các cards Q&A.
    """
    if not top_qs:
        return ""

    blocks = []
    for i, (q, sim) in enumerate(top_qs, 1):
        first_answer = q.answers.order_by('created_at').first()
        ans_text = first_answer.content if first_answer else "(chưa có)"
        blocks.append(
            f"--- Tham khảo {i} (sim {sim:.2f}) ---\n"
            f"Q: {q.title}\nNội dung: {q.content}\nA: {ans_text}"
        )
    context = "\n\n".join(blocks)

    try:
        summary = gemini_client.generate_answer(
            SUMMARIZE_PROMPT.format(query=query, context=context),
            temperature=0.3,
        ).strip()
        if 'NEED_ADVISOR' in summary.upper():
            return ""
        return summary
    except Exception as e:
        logger.warning(f"Gemini summarize lỗi: {e}")
        return ""
