"""
Wrapper cho Google Gemini API.
DÙNG SDK MỚI: google-genai (không phải google-generativeai cũ đã deprecated).

Cài đặt:
    pip uninstall google-generativeai
    pip install google-genai

Lấy API key miễn phí: https://aistudio.google.com/app/apikey
"""
import os
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Model embedding: gemini-embedding-001 (mới nhất, thay thế text-embedding-004)
EMBEDDING_MODEL = "gemini-embedding-001"

# Model sinh: gemini-3.5-flash (đã test ổn định, không bị 503)
CHAT_MODEL = "gemini-3.5-flash"

_client = None


def _get_client():
    """Lazy-init client của google-genai SDK."""
    global _client
    if _client is not None:
        return _client

    try:
        from google import genai
    except ImportError as e:
        raise RuntimeError(
            "Chưa cài google-genai. Chạy: pip install google-genai"
        ) from e

    api_key = (
        getattr(settings, 'GEMINI_API_KEY', None)
        or os.environ.get('GEMINI_API_KEY')
        or os.environ.get('GOOGLE_API_KEY')
    )
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY chưa được thiết lập. "
            "Thêm vào settings.py hoặc đặt biến môi trường."
        )

    _client = genai.Client(api_key=api_key)
    return _client


def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list:
    """
    Embed một đoạn text thành vector.
    task_type (UPPERCASE bắt buộc với SDK mới):
        - RETRIEVAL_DOCUMENT: khi index Q&A
        - RETRIEVAL_QUERY: khi search
        - SEMANTIC_SIMILARITY, CLASSIFICATION, CLUSTERING, QUESTION_ANSWERING...
    """
    client = _get_client()
    from google.genai import types

    text = (text or "").strip()
    if not text:
        raise ValueError("Text rỗng, không embed được.")

    # gemini-embedding-001 giới hạn ~2048 token, cắt cho an toàn
    if len(text) > 8000:
        text = text[:8000]

    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type=task_type),
    )

    # SDK mới: result.embeddings là list các ContentEmbedding
    if not result.embeddings:
        raise RuntimeError("Gemini trả về 0 embedding")
    return list(result.embeddings[0].values)


def embed_query(text: str) -> list:
    """Shortcut: embed một câu hỏi tìm kiếm (task_type=RETRIEVAL_QUERY)."""
    return embed_text(text, task_type="RETRIEVAL_QUERY")


def generate_answer(prompt: str, temperature: float = 0.3) -> str:
    """
    Gọi Gemini sinh câu trả lời từ prompt đơn (single-turn).
    temperature thấp (0.3) để câu trả lời ổn định, ít bịa.
    """
    client = _get_client()
    from google.genai import types

    try:
        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                top_p=0.9,
                max_output_tokens=800,
            ),
        )
    except Exception as e:
        logger.error(f"Gemini API lỗi: {e}")
        fallback_models = ["gemini-3.5-flash", "gemini-flash-lite-latest", "gemini-2.5-flash"]
        for fb_model in fallback_models:
            if fb_model == CHAT_MODEL: continue
            try:
                logger.info(f"Fallback sang model {fb_model}")
                response = client.models.generate_content(
                    model=fb_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        top_p=0.9,
                        max_output_tokens=800,
                    ),
                )
                break
            except Exception:
                continue
        else:
            raise

    try:
        text = response.text
    except (AttributeError, ValueError) as e:
        logger.warning(f"Không trích được text từ Gemini response: {e}")
        return "NEED_ADVISOR"

    return text or "NEED_ADVISOR"


def chat_with_history(
    system_instruction: str,
    history: list,
    user_message: str,
    temperature: float = 0.4,
    max_output_tokens: int = 1024,
) -> str:
    """
    Gọi Gemini chat multi-turn — giống ChatGPT.

    Args:
        system_instruction: prompt hệ thống (vai trò bot, nguyên tắc, context RAG...).
        history: list các dict {'role': 'user'|'model', 'text': '...'} — lịch sử hội thoại.
        user_message: tin nhắn mới nhất của user.
        temperature: 0.4 — đủ tự nhiên nhưng vẫn nhất quán.

    Returns:
        Text trả lời của bot. Nếu lỗi, raise exception cho caller xử lý.
    """
    client = _get_client()
    from google.genai import types

    # Build contents: list các Content object, mỗi cái có role + parts
    contents = []
    for turn in history:
        role = turn.get('role')
        txt = (turn.get('text') or '').strip()
        if not txt or role not in ('user', 'model'):
            continue
        contents.append(types.Content(
            role=role,
            parts=[types.Part.from_text(text=txt)],
        ))

    # Append user message hiện tại
    user_message = (user_message or '').strip()
    if user_message:
        contents.append(types.Content(
            role='user',
            parts=[types.Part.from_text(text=user_message)],
        ))

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
        top_p=0.9,
        max_output_tokens=max_output_tokens,
    )

    try:
        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=contents,
            config=config,
        )
    except Exception as e:
        logger.error(f"Gemini chat lỗi: {e}")
        fallback_models = ["gemini-3.5-flash", "gemini-flash-lite-latest", "gemini-2.5-flash"]
        for fb_model in fallback_models:
            if fb_model == CHAT_MODEL: continue
            try:
                logger.info(f"Fallback sang model {fb_model}")
                response = client.models.generate_content(
                    model=fb_model,
                    contents=contents,
                    config=config,
                )
                break
            except Exception as fb_err:
                logger.error(f"Fallback {fb_model} cũng lỗi: {fb_err}")
                continue
        else:
            raise

    try:
        text = response.text
    except (AttributeError, ValueError) as e:
        logger.warning(f"Không trích được text từ Gemini chat response: {e}")
        return ""

    return (text or '').strip()
