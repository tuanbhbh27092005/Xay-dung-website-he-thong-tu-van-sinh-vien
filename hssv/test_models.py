import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuvansinhvien.settings')
django.setup()

from google import genai
from django.conf import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

models_to_test = [
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite"
]

success = []
for m in models_to_test:
    try:
        ans = client.models.generate_content(model=m, contents="Hello")
        success.append(m)
        print(f"OK: {m}")
    except Exception as e:
        print(f"ERR {m}: {e}")

with open('model_success.txt', 'w') as f:
    f.write(", ".join(success))
