from django.core.management.base import BaseCommand
from accounts.models import CustomUser
from questions.models import Question, Answer

class Command(BaseCommand):
    help = 'Add cutoff scores to database'

    def handle(self, *args, **options):
        user = CustomUser.objects.filter(is_superuser=True).first()
        if not user:
            user = CustomUser.objects.first()

        if not user:
            self.stdout.write(self.style.ERROR("No users found."))
            return

        q_title = "Điểm chuẩn Đại học Sư phạm Kỹ thuật TP.HCM năm 2023 và 2024 là bao nhiêu?"
        q_content = "Cho mình hỏi điểm chuẩn năm ngoái (2023) và năm nay (2024) của trường Đại học Sư phạm Kỹ thuật TP.HCM là bao nhiêu điểm? Xin cảm ơn."

        question, created = Question.objects.get_or_create(
            title=q_title,
            defaults={
                'user': user,
                'content': q_content,
                'status': 'answered',
                'is_public': True
            }
        )

        ans_content = """Dưới đây là thông tin điểm chuẩn theo phương thức xét kết quả thi tốt nghiệp THPT của Trường Đại học Sư phạm Kỹ thuật TP.HCM (HCMUTE):

- **Năm 2024:** 
  + Ngành có điểm chuẩn cao nhất: Sư phạm tiếng Anh (27,5 điểm).
  + Các ngành kỹ thuật hot: Công nghệ kỹ thuật Điều khiển và Tự động hóa (26,14 điểm), Công nghệ Thông tin - hệ đại trà (25,97 điểm).
  + Ngành có điểm chuẩn thấp nhất: Kỹ nghệ gỗ và nội thất (20,5 điểm).

- **Năm 2023 (năm ngoái):** Điểm chuẩn dao động từ 19 đến 27,25 điểm.
  + Ngành cao điểm nhất: Kinh doanh quốc tế hệ đại trà (27,25 điểm), Sư phạm tiếng Anh (27,2 điểm).
  + Ngành thấp điểm nhất: Công nghệ kỹ thuật in, Kỹ thuật gỗ và nội thất (từ 19 điểm).

*Lưu ý:* Các mức điểm trên dành cho phương thức xét điểm thi THPT. Để tra cứu điểm chuẩn của từng ngành cụ thể hoặc theo các phương thức khác (học bạ, ĐGNL...), bạn vui lòng truy cập trang tuyển sinh chính thức của trường tại: https://tuyensinh.hcmute.edu.vn"""

        if created or not question.answers.exists():
            Answer.objects.create(
                question=question,
                user=user,
                content=ans_content
            )
            self.stdout.write(self.style.SUCCESS(f"Thành công! Đã thêm câu hỏi ID: {question.id}"))
        else:
            self.stdout.write("Câu hỏi đã tồn tại.")
