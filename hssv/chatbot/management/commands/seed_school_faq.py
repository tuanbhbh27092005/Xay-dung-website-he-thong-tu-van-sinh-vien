"""
Management command: tạo FAQ về trường HCMUTE để chatbot có kiến thức về:
- Lịch sử / giới thiệu trường
- Cơ sở vật chất, địa chỉ, liên hệ
- Tuyển sinh, học bổng, ký túc xá
- Các ngành đào tạo chính

Sử dụng:
    python manage.py seed_school_faq
    python manage.py seed_school_faq --reset-embeddings
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from questions.models import Department, Major, Question, Answer, QuestionCategory
from admin_panel.models import AdvisorProfile

User = get_user_model()


# Category mới: "Giới thiệu trường" để gom FAQ về HCMUTE
SCHOOL_FAQ_CATEGORY = ('Giới thiệu trường', 'Câu hỏi về lịch sử, ngành đào tạo, cơ sở vật chất, tuyển sinh HCMUTE')

# FAQ về trường - không gán major cụ thể (chung cho mọi sinh viên)
SCHOOL_FAQ = [
    # ─── LỊCH SỬ & GIỚI THIỆU ───
    {
        'title': 'Trường HCMUTE thành lập năm nào?',
        'content': 'Em muốn tìm hiểu về lịch sử thành lập trường Đại học Sư phạm Kỹ thuật TP.HCM (HCMUTE).',
        'answer': (
            'Trường Đại học Sư phạm Kỹ thuật TP.HCM (HCMUTE - Ho Chi Minh City University of '
            'Technology and Education) được thành lập năm 1962, tiền thân là Trường Trung học Kỹ '
            'thuật Nguyễn Trường Tộ. Năm 1991, trường chính thức trở thành Đại học Sư phạm Kỹ '
            'thuật TP.HCM. Hiện nay trường là một trong các trường đại học hàng đầu của Việt Nam '
            'về đào tạo kỹ sư và giáo viên kỹ thuật.'
        ),
    },
    {
        'title': 'HCMUTE nằm ở đâu? Địa chỉ trường?',
        'content': 'Em ở tỉnh, muốn biết địa chỉ chính xác và cách đi đến trường HCMUTE.',
        'answer': (
            'Trường HCMUTE có cơ sở chính tại số 1 Võ Văn Ngân, phường Linh Chiểu, TP. Thủ Đức, '
            'TP. Hồ Chí Minh. Trường gần ga Metro số 1 (tuyến Bến Thành - Suối Tiên), đi từ trung '
            'tâm TP.HCM mất khoảng 30-40 phút. Em có thể đi xe buýt số 8, 19, 53, 56 đến trạm '
            'gần trường, hoặc Grab/taxi tới địa chỉ trên.'
        ),
    },
    {
        'title': 'HCMUTE có bao nhiêu khoa? Đào tạo những ngành gì?',
        'content': 'Em muốn xem danh sách các khoa và ngành đào tạo của HCMUTE.',
        'answer': (
            'HCMUTE hiện có khoảng 14 khoa đào tạo các nhóm ngành: Công nghệ thông tin, Điện - '
            'Điện tử, Cơ khí Chế tạo máy, Cơ khí Động lực, Xây dựng, Công nghệ Hóa học và Thực '
            'phẩm, Công nghệ May và Thời trang, Kinh tế, Ngoại ngữ, Lý luận chính trị, In và '
            'Truyền thông, Đào tạo Chất lượng cao, Đào tạo Quốc tế. Tổng cộng có hơn 40 ngành '
            'đại học chính quy. Chi tiết em xem tại website hcmute.edu.vn.'
        ),
    },
    {
        'title': 'HCMUTE có chương trình đào tạo chất lượng cao không?',
        'content': 'Em nghe nói có chương trình chất lượng cao học bằng tiếng Anh, đúng không?',
        'answer': (
            'HCMUTE có chương trình Chất lượng cao (CLC) và chương trình liên kết quốc tế. CLC '
            'có học phần bằng tiếng Anh, sĩ số lớp nhỏ (~30 sinh viên), cơ sở vật chất tốt hơn, '
            'cấp bằng chính quy. Học phí CLC cao hơn chương trình thường khoảng 2-2.5 lần. Yêu '
            'cầu tiếng Anh đầu vào tối thiểu IELTS 5.0 hoặc TOEIC 500 (hoặc qua kỳ thi đánh giá '
            'của trường).'
        ),
    },

    # ─── TUYỂN SINH ───
    {
        'title': 'HCMUTE xét tuyển bằng phương thức nào?',
        'content': 'Em là học sinh phổ thông lớp 12, muốn biết các phương thức xét tuyển vào HCMUTE năm 2025.',
        'answer': (
            'HCMUTE thường xét tuyển bằng các phương thức chính: (1) Xét điểm thi tốt nghiệp '
            'THPT - khoảng 50-60% chỉ tiêu. (2) Xét học bạ THPT - khoảng 15-20% chỉ tiêu, dựa '
            'trên điểm trung bình 3-5 học kỳ THPT. (3) Xét điểm thi đánh giá năng lực ĐHQG '
            'TP.HCM - khoảng 10-15% chỉ tiêu. (4) Tuyển thẳng theo quy chế Bộ GD&ĐT. Mỗi năm '
            'cụ thể có thể thay đổi, em theo dõi trang tuyển sinh hcmute.edu.vn/tuyensinh.'
        ),
    },
    {
        'title': 'Điểm chuẩn HCMUTE năm trước là bao nhiêu?',
        'content': 'Em muốn xem điểm chuẩn các ngành của HCMUTE năm 2024 để định hướng học tập.',
        'answer': (
            'Điểm chuẩn HCMUTE 2024 (xét điểm thi THPT) dao động từ 22-27 điểm tùy ngành. Các '
            'ngành "hot" như Công nghệ Kỹ thuật Ô tô, Robot và Trí tuệ nhân tạo, Logistics, '
            'Công nghệ Thông tin (CLC) thường có điểm cao 25-27. Các ngành Sư phạm Kỹ thuật, '
            'Công nghệ May, In thường thấp hơn 22-23. Em xem chi tiết bảng điểm chuẩn từng '
            'ngành tại tuyensinh.hcmute.edu.vn.'
        ),
    },
    {
        'title': 'Học phí HCMUTE là bao nhiêu một học kỳ?',
        'content': 'Em muốn biết mức học phí trung bình của HCMUTE để chuẩn bị tài chính.',
        'answer': (
            'Học phí HCMUTE năm 2024-2025: chương trình đại trà khoảng 13-16 triệu/học kỳ tùy '
            'số tín chỉ đăng ký (mức ~600,000-700,000 đ/tín chỉ). Chương trình Chất lượng cao '
            'khoảng 25-32 triệu/học kỳ. Chương trình liên kết quốc tế khoảng 40-60 triệu/học '
            'kỳ. Mức cụ thể tuỳ ngành và số tín chỉ, em xem tại Phòng Tài chính-Kế toán.'
        ),
    },
    {
        'title': 'HCMUTE có học bổng cho sinh viên không?',
        'content': 'Em hoàn cảnh khó khăn, muốn hỏi HCMUTE có những học bổng nào.',
        'answer': (
            'HCMUTE có nhiều loại học bổng: (1) Học bổng khuyến khích học tập (KKHT) - dành cho '
            'sinh viên có điểm GPA cao, xét theo từng học kỳ, từ 50% đến 100% học phí. (2) Học '
            'bổng sinh viên xuất sắc đầu vào. (3) Học bổng doanh nghiệp tài trợ (FPT, Samsung, '
            'Vinfast...). (4) Học bổng hoàn cảnh khó khăn - cần nộp đơn kèm xác nhận từ địa '
            'phương. (5) Quỹ học bổng "Thắp sáng ước mơ" cho tân sinh viên. Em theo dõi thông '
            'báo của Phòng Công tác Sinh viên hoặc trang web trường.'
        ),
    },

    # ─── CƠ SỞ VẬT CHẤT ───
    {
        'title': 'HCMUTE có ký túc xá không? Đăng ký thế nào?',
        'content': 'Em ở tỉnh, muốn ở ký túc xá HCMUTE năm đầu, cách đăng ký ra sao?',
        'answer': (
            'HCMUTE có ký túc xá nội trú với khoảng 4-5 dãy nhà, sức chứa ~3000 sinh viên. KTX '
            'ưu tiên sinh viên năm 1, sinh viên ở xa, sinh viên có hoàn cảnh đặc biệt. Đăng ký '
            'online qua trang KTX của trường ngay sau khi nhập học. Chi phí khoảng 200,000-'
            '400,000 đ/tháng tùy phòng 4-8 người. Có wifi, điện nước riêng. Hồ sơ cần: đơn xin '
            'ở KTX, giấy báo nhập học, CMND/CCCD, ảnh 3x4.'
        ),
    },
    {
        'title': 'Thư viện HCMUTE mở cửa thời gian nào?',
        'content': 'Em muốn vào thư viện học bài, thư viện trường mở mấy giờ?',
        'answer': (
            'Thư viện HCMUTE (tòa nhà Thư viện - Trung tâm Thông tin Thư viện) mở cửa từ Thứ 2 '
            'đến Thứ 6: 7h30 - 21h00; Thứ 7: 8h00 - 17h00; Chủ nhật và ngày lễ đóng cửa. Có '
            'khu tự học rộng rãi, có wifi, ổ điện. Mượn sách bằng thẻ sinh viên, mỗi lần tối '
            'đa 5 cuốn trong 14 ngày. Em có thể truy cập thư viện điện tử online qua tài khoản '
            'sinh viên.'
        ),
    },
    {
        'title': 'HCMUTE có sân thể thao, phòng gym không?',
        'content': 'Em thích thể thao, muốn biết HCMUTE có những tiện ích thể thao nào.',
        'answer': (
            'HCMUTE có khu liên hợp thể thao gồm: sân bóng đá cỏ nhân tạo, sân bóng rổ, sân '
            'bóng chuyền, sân tennis, nhà thi đấu đa năng, hồ bơi (chỉ mở mùa nóng), phòng gym '
            'với máy tập đầy đủ. Sinh viên dùng miễn phí khi xuất trình thẻ sinh viên, đăng ký '
            'lịch tại bộ phận Thể chất - Quốc phòng. Có nhiều CLB thể thao tổ chức tập luyện '
            'thường xuyên.'
        ),
    },

    # ─── ĐỜI SỐNG SINH VIÊN ───
    {
        'title': 'HCMUTE có những CLB sinh viên nào?',
        'content': 'Em muốn tham gia hoạt động ngoại khóa, HCMUTE có những CLB nào nổi bật?',
        'answer': (
            'HCMUTE có rất nhiều CLB chia thành các nhóm: (1) Học thuật: CLB Lập trình, CLB '
            'Robot, CLB Tiếng Anh ESC, CLB Toán-Lý, CLB Khoa học Dữ liệu. (2) Văn hóa - Nghệ '
            'thuật: CLB Guitar, CLB Hip-hop, CLB Nhiếp ảnh, CLB Truyền thông. (3) Tình nguyện: '
            'Đội Công tác Xã hội, Mùa hè Xanh. (4) Thể thao: CLB Bóng đá, Cầu lông, Vovinam, '
            'Esport. Đầu mỗi học kỳ có Ngày hội CLB để sinh viên đăng ký, em theo dõi Đoàn '
            'trường để biết lịch.'
        ),
    },
    {
        'title': 'Sinh viên HCMUTE có cơ hội thực tập tại doanh nghiệp không?',
        'content': 'Em quan tâm cơ hội thực tập / việc làm khi học HCMUTE, trường có hỗ trợ gì không?',
        'answer': (
            'HCMUTE có Trung tâm Hợp tác Doanh nghiệp & Cựu sinh viên (CCD) hỗ trợ sinh viên '
            'kết nối thực tập và việc làm. Trường có quan hệ đối tác với hơn 200 doanh nghiệp '
            'lớn: FPT, Samsung, Bosch, Honda, Vinfast, TMA, ngân hàng VPBank, Techcombank... '
            'Hàng năm tổ chức 2-3 Ngày hội Việc làm (Job Fair) với hàng trăm gian hàng tuyển '
            'dụng. Khoảng 90% sinh viên HCMUTE có việc làm trong 6 tháng sau tốt nghiệp.'
        ),
    },

    # ─── LIÊN HỆ ───
    {
        'title': 'Số điện thoại / email liên hệ HCMUTE?',
        'content': 'Em muốn liên hệ trực tiếp với phòng tuyển sinh / phòng đào tạo HCMUTE.',
        'answer': (
            'Tổng đài trường HCMUTE: (028) 3722 1223. Email tư vấn chung: tuvan@hcmute.edu.vn. '
            'Phòng Tuyển sinh: (028) 3896 8641, email tuyensinh@hcmute.edu.vn. Phòng Đào tạo: '
            '(028) 3722 5963. Phòng Công tác Sinh viên: (028) 3722 1223 ext.8261. Website chính '
            'thức: hcmute.edu.vn. Fanpage chính: facebook.com/hcmute.edu.vn. Em chú ý chỉ tin '
            'thông tin từ các kênh chính thức để tránh bị lừa.'
        ),
    },
]


class Command(BaseCommand):
    help = "Tạo FAQ về trường HCMUTE (lịch sử, ngành, tuyển sinh...) làm knowledge base cho chatbot."

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-embeddings',
            action='store_true',
            help='Sau khi seed xong, build lại embedding cho FAQ.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("=> Đảm bảo Category 'Giới thiệu trường'...")
        cat, created = QuestionCategory.objects.get_or_create(
            name=SCHOOL_FAQ_CATEGORY[0],
            defaults={'description': SCHOOL_FAQ_CATEGORY[1]},
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"   Đã tạo category: {cat.name}"))

        # User & advisor
        self.stdout.write("=> Lấy user / advisor để gán tác giả...")
        asker = User.objects.filter(user_type='student').first()
        if not asker:
            asker = User.objects.create_user(
                username='demo_student',
                password='demo12345',
                email='demo_student@hcmute.edu.vn',
                first_name='Demo',
                last_name='Sinh viên',
                user_type='student',
                student_id='DEMO0001',
            )
            self.stdout.write(self.style.WARNING(
                "   Tạo user demo_student / demo12345"
            ))

        advisor_profile = AdvisorProfile.objects.first()
        if not advisor_profile:
            # Cần có dept để gán
            dept = Department.objects.first()
            if not dept:
                dept = Department.objects.create(
                    name='Phòng Tư vấn',
                    description='Phòng Tư vấn Tuyển sinh HCMUTE',
                )
            advisor_user = User.objects.filter(username='demo_advisor').first()
            if not advisor_user:
                advisor_user = User.objects.create_user(
                    username='demo_advisor',
                    password='demo12345',
                    email='advisor@hcmute.edu.vn',
                    first_name='Demo',
                    last_name='Tư vấn',
                    user_type='student',
                    is_staff=True,
                )
            advisor_profile = AdvisorProfile.objects.create(
                user=advisor_user,
                department=dept,
                role='advisor',
            )
        advisor = advisor_profile.user

        # Seed FAQ
        self.stdout.write(f"=> Tạo {len(SCHOOL_FAQ)} câu FAQ về trường...")
        created = skipped = 0

        for entry in SCHOOL_FAQ:
            if Question.objects.filter(title=entry['title']).exists():
                skipped += 1
                continue

            q = Question.objects.create(
                user=asker,
                title=entry['title'],
                content=entry['content'],
                major=None,  # FAQ trường không thuộc ngành cụ thể
                category=cat,
                status='answered',
                is_public=True,
            )
            Answer.objects.create(
                question=q,
                user=advisor,
                content=entry['answer'],
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"   Đã tạo: {created} FAQ | Bỏ qua (trùng title): {skipped}"
        ))

        if options['reset_embeddings']:
            self.stdout.write("=> Re-build embeddings...")
            from chatbot.services.embedding_service import reindex_all
            count = reindex_all()
            self.stdout.write(self.style.SUCCESS(f"   Đã index {count} câu hỏi (bao gồm FAQ)."))
        else:
            self.stdout.write(self.style.WARNING(
                "Lưu ý: Chạy 'python manage.py build_embeddings' để FAQ mới được index."
            ))

        self.stdout.write(self.style.SUCCESS("Hoàn tất seed FAQ trường!"))
