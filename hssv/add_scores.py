from accounts.models import CustomUser
from questions.models import Question, Answer

# Get a user (superuser or first user)
user = CustomUser.objects.filter(is_superuser=True).first()
if not user:
    user = CustomUser.objects.first()

if not user:
    print("No users found in the database. Cannot create Question.")
    exit(1)

# Create the Question
q_title = "Điểm chuẩn Đại học Sư phạm Kỹ thuật TP.HCM năm 2023 và 2024 là bao nhiêu?"
q_content = "Cho mình hỏi điểm chuẩn năm ngoái (2023) và năm nay (2024) của trường Đại học Sư phạm Kỹ thuật TP.HCM là bao nhiêu điểm? Xin cảm ơn."

question = Question.objects.create(
    user=user,
    title=q_title,
    content=q_content,
    status='answered',
    is_public=True
)

# Create the Answer
ans_content = """Dưới đây là thông tin điểm chuẩn theo phương thức xét kết quả thi tốt nghiệp THPT của Trường Đại học Sư phạm Kỹ thuật TP.HCM (HCMUTE):

- **Năm 2024:** 
  + Ngành có điểm chuẩn cao nhất: Sư phạm tiếng Anh (27,5 điểm).
  + Các ngành kỹ thuật hot: Công nghệ kỹ thuật Điều khiển và Tự động hóa (26,14 điểm), Công nghệ Thông tin - hệ đại trà (25,97 điểm).
  + Ngành có điểm chuẩn thấp nhất: Kỹ nghệ gỗ và nội thất (20,5 điểm).

- **Năm 2023 (năm ngoái):** Điểm chuẩn dao động từ 19 đến 27,25 điểm.
  + Ngành cao điểm nhất: Kinh doanh quốc tế hệ đại trà (27,25 điểm), Sư phạm tiếng Anh (27,2 điểm).
  + Ngành thấp điểm nhất: Công nghệ kỹ thuật in, Kỹ thuật gỗ và nội thất (từ 19 điểm).

*Lưu ý:* Các mức điểm trên dành cho phương thức xét điểm thi THPT. Để tra cứu điểm chuẩn của từng ngành cụ thể hoặc theo các phương thức khác (học bạ, ĐGNL...), bạn vui lòng truy cập trang tuyển sinh chính thức của trường tại: https://tuyensinh.hcmute.edu.vn"""

answer = Answer.objects.create(
    question=question,
    user=user,
    content=ans_content
)

print(f"Thành công! Đã thêm câu hỏi ID: {question.id} và câu trả lời. Hệ thống đã tự động index embedding.")
