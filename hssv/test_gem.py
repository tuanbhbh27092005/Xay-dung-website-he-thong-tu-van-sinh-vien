import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuvansinhvien.settings')
django.setup()

from chatbot.services.gemini_client import chat_with_history

history = [
    {'role': 'model', 'text': 'Chào bạn'},
    {'role': 'user', 'text': 'Hạn nộp học phí?'},
    {'role': 'model', 'text': '30 ngày'}
]

try:
    ans = chat_with_history('Sys prompt', history, 'Học phí')
    with open('out2.txt', 'w', encoding='utf-8') as f:
        f.write('OK: ' + ans)
except Exception as e:
    with open('out2.txt', 'w', encoding='utf-8') as f:
        f.write('ERR: ' + str(e))
