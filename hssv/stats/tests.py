import calendar
from datetime import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import CustomUser
from admin_panel.models import AdvisorProfile
from questions.models import Department, Major, QuestionCategory, Question
from chatbot.services.moderation import is_clean, find_profanity, check


class StatisticsAndModerationTestCase(TestCase):
    """
    Bộ kịch bản kiểm thử tự động cho Tuần 3 (Minh chứng Test Case TC-11 đến TC-14).
    Phạm Hoàng Thái Tuấn (MSSV: 24810104) & Thân Thành Nam (MSSV: 24810090)
    """

    def setUp(self):
        self.client = Client()

        # Tạo khoa & ngành mẫu
        self.dept = Department.objects.create(name="Khoa Công nghệ Thông tin", description="Khoa CNTT HCMUTE")
        self.major = Major.objects.create(name="Công nghệ phần mềm", department=self.dept)
        self.category = QuestionCategory.objects.create(name="Quy chế đào tạo")

        # 1. Tạo tài khoản Admin
        self.admin_user = CustomUser.objects.create_user(
            username="admin_user",
            email="admin@hcmute.edu.vn",
            password="adminpassword123",
            user_type="advisor",
            is_staff=True
        )
        self.admin_profile = AdvisorProfile.objects.create(
            user=self.admin_user,
            role="admin",
            department=self.dept
        )

        # 2. Tạo tài khoản Sinh viên thông thường
        self.student_user = CustomUser.objects.create_user(
            username="student_user",
            email="student@student.hcmute.edu.vn",
            password="studentpassword123",
            user_type="student"
        )

        # 3. Tạo dữ liệu câu hỏi mẫu
        now = timezone.now()
        self.q1 = Question.objects.create(
            user=self.student_user,
            title="Hỏi về chuẩn đầu ra TOEIC",
            content="Chuẩn đầu ra tiếng Anh năm 2026 là bao nhiêu?",
            major=self.major,
            category=self.category,
            status="answered",
            is_public=True
        )
        self.q2 = Question.objects.create(
            user=self.student_user,
            title="Đăng ký môn học trễ hạn",
            content="Em bị lỡ hạn đăng ký học phần đợt 1 thì làm sao?",
            major=self.major,
            category=self.category,
            status="pending",
            is_public=True
        )

    def test_tc11_statistics_dashboard_time_filter(self):
        """
        [Test Case 11] - Kiểm thử bộ lọc thời gian trên Dashboard Thống kê
        """
        self.client.login(username="admin_user", password="adminpassword123")
        current_month = timezone.now().month
        current_year = timezone.now().year
        month_filter = f"{current_month:02d}-{current_year}"

        response = self.client.get(reverse('statistics_dashboard'), {'month_filter': month_filter})
        self.assertEqual(response.status_code, 200)
        self.assertIn('departments', response.context)
        self.assertEqual(response.context['time_filter'], 'custom')
        self.assertEqual(response.context['time_filter_label'], f"Tháng {current_month}/{current_year}")

    def test_tc12_query_optimization_aggregated_counts(self):
        """
        [Test Case 12] - Kiểm thử hiệu năng truy vấn gom nhóm CSDL
        """
        self.client.login(username="admin_user", password="adminpassword123")
        response = self.client.get(reverse('statistics_dashboard'))
        self.assertEqual(response.status_code, 200)

        # Đảm bảo số lượng câu hỏi đếm được chính xác
        total_questions = response.context['total_questions']
        self.assertEqual(total_questions, 2)
        self.assertEqual(response.context['answered_questions'], 1)
        self.assertEqual(response.context['pending_questions'], 1)

    def test_tc13_block_unauthorized_user_from_stats(self):
        """
        [Test Case 13] - Chặn sinh viên thông thường truy cập trang Thống kê Quản trị
        """
        self.client.login(username="student_user", password="studentpassword123")
        response = self.client.get(reverse('statistics_dashboard'))
        # Người dùng không phải admin bị chuyển hướng về home (HTTP 302)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('home'))

    def test_tc14_content_moderation_service(self):
        """
        [Test Case 14] - Kiểm duyệt từ khóa không phù hợp (Content Moderation)
        """
        clean_text = "Em muốn hỏi về học phí học kỳ 2 và thủ tục đăng ký tín chỉ."
        toxic_text = "Thầy cô dạy như đồ ngu dốt nát vcl."

        # Nội dung sạch được chấp nhận
        self.assertTrue(is_clean(clean_text))
        self.assertEqual(find_profanity(clean_text), [])

        # Nội dung chứa từ ngữ thô tục bị phát hiện và gắn cờ
        is_clean_status, bad_words = check(toxic_text)
        self.assertFalse(is_clean_status)
        self.assertTrue(len(bad_words) > 0)
