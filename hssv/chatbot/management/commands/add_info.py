from django.core.management.base import BaseCommand
from accounts.models import CustomUser
from questions.models import Question, Answer

class Command(BaseCommand):
    help = 'Add 2025 cutoff and 2026 admission info'

    def handle(self, *args, **options):
        user = CustomUser.objects.filter(is_superuser=True).first()
        if not user:
            user = CustomUser.objects.first()

        if not user:
            self.stdout.write("No users found.")
            return

        # --- Q1: 2025 cutoff ---
        q1_title = "Điểm chuẩn Trường Đại học Sư phạm Kỹ thuật TPHCM (HCMUTE) năm 2025"
        q1_content = "Cho mình hỏi điểm chuẩn năm 2025 của trường Đại học Sư phạm Kỹ thuật TP.HCM là bao nhiêu?"
        q1, _ = Question.objects.get_or_create(
            title=q1_title,
            defaults={
                'user': user,
                'content': q1_content,
                'status': 'answered',
                'is_public': True
            }
        )

        ans1_content = """Điểm chuẩn Trường Đại học Sư phạm Kỹ thuật TPHCM (HCMUTE) năm 2025:
- Mức điểm trúng tuyển dao động từ 21,1 đến 29,57 điểm.
- Ngành có điểm chuẩn cao nhất là Sư phạm tiếng Anh với 29,57 điểm.
- Các ngành kỹ thuật và công nghệ tiếp tục duy trì mức điểm trúng tuyển cao.
Bạn có thể xem chi tiết điểm chuẩn từng mã ngành trên trang tuyển sinh chính thức của trường: tuyensinh.hcmute.edu.vn."""

        if not q1.answers.exists():
            Answer.objects.create(question=q1, user=user, content=ans1_content)
            self.stdout.write("Added Q1 successfully.")

        # --- Q2: 2026 admission info ---
        q2_title = "Thông tin tuyển sinh Trường Đại học Công nghệ Kỹ thuật TPHCM (HCMUTE) năm 2026"
        q2_content = "Cho mình hỏi thông tin tuyển sinh năm 2026 của trường Đại học Sư phạm Kỹ thuật TP.HCM (HCMUTE) như thế nào?"
        q2, _ = Question.objects.get_or_create(
            title=q2_title,
            defaults={
                'user': user,
                'content': q2_content,
                'status': 'answered',
                'is_public': True
            }
        )

        ans2_content = """Thông tin tuyển sinh năm 2026 của Trường Đại học Công nghệ Kỹ thuật TP.HCM (HCMUTE):
1. Phương thức tuyển sinh đa dạng:
- Xét tuyển thẳng.
- Xét tuyển kết hợp (kết quả học bạ, điểm thi THPT, và kết quả thi Đánh giá năng lực của ĐHQG TP.HCM).
- Thi năng khiếu (dành cho các ngành đặc thù như Kiến trúc, Thiết kế đồ họa...). Kỳ thi năng khiếu đầu tiên đã được tổ chức vào ngày 01-02/6/2026.

2. Kênh thông tin hỗ trợ:
- Website tuyển sinh: https://tuyensinh.hcmute.edu.vn
- Hệ thống đăng ký xét tuyển: https://xettuyen.hcmute.edu.vn
- Hotline tư vấn: (028) 3722 5724.
Lưu ý: Thí sinh cần sử dụng Email cá nhân chính chủ khi đăng ký tài khoản trên hệ thống."""

        if not q2.answers.exists():
            Answer.objects.create(question=q2, user=user, content=ans2_content)
            self.stdout.write("Added Q2 successfully.")

        self.stdout.write("All done.")
