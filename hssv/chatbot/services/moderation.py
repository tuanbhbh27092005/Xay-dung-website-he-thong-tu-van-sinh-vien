"""
Service kiểm duyệt ngôn từ cho nội dung do sinh viên gửi
(chat bot input + bình luận tin tức).

Cơ chế đơn giản dựa trên word list tiếng Việt + tiếng Anh phổ biến.
Có chuẩn hóa: bỏ dấu, lowercase, bỏ khoảng trắng / dấu câu giữa các chữ cái
để phát hiện các biến thể né lọc (vd "đ.ụ", "đụ.").
"""
import re
import unicodedata
from typing import List, Tuple


# ============================================================
# WORD LIST
# ============================================================
# Lưu ý: danh sách bao gồm các từ thô tục/xúc phạm phổ biến.
# Khi mở rộng, thêm các biến thể không dấu vào BAD_WORDS_NORMALIZED bên dưới.
_BAD_WORDS_RAW = [
    # Tiếng Việt
    'địt', 'đụ', 'đéo', 'đếch', 'đm', 'đmm', 'dmm', 'đcm', 'dcm', 'đcmm',
    'cmm', 'cl', 'cc', 'lồn', 'lon', 'cặc', 'cak', 'buồi', 'buoi',
    'chó', 'cho má', 'chó má', 'óc chó', 'óc lợn', 'súc vật', 'súc sinh',
    'thằng chó', 'con chó', 'đồ chó', 'mày chết', 'tao giết',
    'thằng ngu', 'con ngu', 'đồ ngu', 'ngu vl', 'ngu vc', 'ngu vcl',
    'vl', 'vcl', 'vlon', 'vailon', 'vailol', 'vailoz',
    'mẹ mày', 'mẹ kiếp', 'mả mẹ', 'tổ sư', 'tổ cha', 'tổ tiên mày',
    'đĩ', 'đĩ mẹ', 'đĩ chó', 'đĩ ngựa', 'điếm',
    'dái', 'cu to', 'thủ dâm',
    # Tiếng Anh thông dụng
    'fuck', 'fucking', 'shit', 'bitch', 'asshole', 'bastard', 'dick',
    'pussy', 'cunt', 'motherfucker', 'wtf', 'stfu',
]


def _normalize(text: str) -> str:
    """
    Chuẩn hóa text để so sánh:
    - Lowercase
    - Bỏ khoảng trắng và dấu câu giữa các ký tự (để bắt 'đ.ụ' = 'đụ')
    - KHÔNG bỏ dấu tiếng Việt để tránh false positive (vd: 'các' -> 'cac', 'cho' -> 'cho')
    """
    if not text:
        return ''
    s = text.lower()
    
    # Bỏ ký tự không phải chữ/số/khoảng trắng (để bắt biến thể như "đ.ụ", "d_m_m")
    # Giữ lại các ký tự Unicode tiếng Việt (thuộc nhóm \w)
    s = re.sub(r'[^\w\s]', '', s)
    
    # Multi-space → single space
    s = re.sub(r'\s+', ' ', s).strip()
    return s


# Tiền tính các phiên bản normalized của word list để so sánh nhanh
_BAD_WORDS_NORMALIZED = set()
_BAD_PHRASES_NORMALIZED = set()  # cho phrase có space
for w in _BAD_WORDS_RAW:
    n = _normalize(w)
    if not n:
        continue
    if ' ' in n:
        _BAD_PHRASES_NORMALIZED.add(n)
    else:
        _BAD_WORDS_NORMALIZED.add(n)


def find_profanity(text: str) -> List[str]:
    """
    Trả về danh sách từ thô tục tìm thấy trong text (đã match dạng normalized).
    Empty list nếu sạch.

    Logic:
    - Phrase nhiều từ: substring match trên cả chuỗi.
    - Single word: chỉ exact-token match (tránh false positive như "cho hỏi" → "chó").
      Riêng từ DÀI (>= 5 ký tự) mới cho substring match để bắt biến thể dính liền
      như "fuckyou" → match "fuck". Từ ngắn (vd "chó", "cl", "cc", "vl") chỉ match khi
      đứng tách riêng.
    """
    if not text:
        return []

    normalized = _normalize(text)
    matched = []

    # 1) Substring match cho phrase nhiều từ
    for phrase in _BAD_PHRASES_NORMALIZED:
        if phrase in normalized:
            matched.append(phrase)

    # 2) Token-level match cho single word
    tokens = normalized.split(' ')
    token_set = set(tokens)
    for bad in _BAD_WORDS_NORMALIZED:
        if bad in token_set:
            matched.append(bad)
            continue
        # Substring match CHỈ áp dụng cho từ đủ dài (>=5) để tránh false positive
        # cho từ ngắn như "cho" (chó), "cl", "cc", "vl"...
        if len(bad) >= 5:
            for tok in tokens:
                if bad in tok:
                    matched.append(bad)
                    break

    # Dedupe nhưng giữ thứ tự xuất hiện đầu
    seen = set()
    result = []
    for m in matched:
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


def is_clean(text: str) -> bool:
    """True nếu text không chứa từ thô tục."""
    return not find_profanity(text)


def check(text: str) -> Tuple[bool, List[str]]:
    """
    Tiện ích combined: trả (is_clean, matched_words).
    """
    matched = find_profanity(text)
    return (not matched, matched)
