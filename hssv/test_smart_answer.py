import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuvansinhvien.settings')
django.setup()

from chatbot.models import ChatSession, ChatMessage
from chatbot.services.conversation import _smart_answer

# Tạm session
session = ChatSession.objects.create()

ChatMessage.objects.create(session=session, role='bot', content='Chào bạn 👋 Tôi là Trợ lý AI')
ChatMessage.objects.create(session=session, role='user', content='Hạn nộp học phí học kỳ 1 khi nào?')
ChatMessage.objects.create(session=session, role='bot', content='Hạn nộp học phí học kỳ 1 thường là 30 ngày kể từ khi đăng ký môn học.')

try:
    msgs = _smart_answer(session, 'Học phí học kỳ 1')
    with open('out_smart.txt', 'w', encoding='utf-8') as f:
        f.write('OK: ' + str(msgs))
except Exception as e:
    with open('out_smart.txt', 'w', encoding='utf-8') as f:
        f.write('ERR: ' + str(e))
