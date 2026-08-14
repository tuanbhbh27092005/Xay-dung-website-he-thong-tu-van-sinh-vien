"""
Management command: tạo dữ liệu mẫu cho chatbot demo.

Tạo ~26 câu hỏi-đáp thực tế về học vụ rải đều trong 6 tháng gần đây
để chatbot có đủ "kiến thức" và biểu đồ thống kê có dữ liệu đẹp.

Sử dụng:
    python manage.py seed_demo_data

Lệnh này AN TOÀN với data hiện có:
- Department, Major, QuestionCategory: dùng get_or_create
- Question: chỉ tạo nếu chưa có Q nào cùng title
- Answer: chỉ tạo nếu Question chưa có answer
"""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from questions.models import Department, Major, Question, Answer, QuestionCategory
from admin_panel.models import AdvisorProfile

User = get_user_model()


# ============================================================
# DỮ LIỆU MẪU
# ============================================================

DEPARTMENTS = [
    ('Công Nghệ Thông Tin', 'Khoa đào tạo các nhóm ngành về máy tính và phần mềm'),
    ('Kinh Tế & Quản Trị', 'Khoa đào tạo các nhóm ngành kinh tế'),
]

MAJORS = [
    ('Kỹ thuật phần mềm', 'Công Nghệ Thông Tin'),
    ('An toàn thông tin', 'Công Nghệ Thông Tin'),
    ('Khoa học dữ liệu', 'Công Nghệ Thông Tin'),
    ('Quản trị kinh doanh', 'Kinh Tế & Quản Trị'),
    ('Marketing số', 'Kinh Tế & Quản Trị'),
]

CATEGORIES = [
    ('Hỗ trợ', 'Câu hỏi cần hỗ trợ chung'),
    ('Học vụ', 'Câu hỏi liên quan tới học phần, đăng ký, lịch học'),
    ('Tài chính', 'Câu hỏi về học phí, học bổng'),
    ('Sinh hoạt', 'Câu hỏi về ký túc xá, sinh hoạt sinh viên'),
]

# Mỗi entry: title, content, major, category, answer, days_ago
SEED_QA = [
    # === HỌC PHÍ ===
    {
        'title': 'Hạn nộp học phí học kỳ 1 khi nào?',
        'content': 'Em muốn hỏi hạn cuối nộp học phí học kỳ 1 năm học là ngày nào ạ? Nộp trễ có bị phạt gì không?',
        'major': 'Kỹ thuật phần mềm', 'category': 'Tài chính', 'days_ago': 175,
        'answer': 'Chào em, hạn nộp học phí học kỳ 1 thường là 30 ngày kể từ khi sinh viên hoàn thành đăng ký môn học. Nếu trễ hạn, em sẽ bị khóa tài khoản học vụ (không xem điểm, không đăng ký kỳ sau) cho tới khi đóng đủ. Em vào trang sinhvien.edu mục "Học phí" để xem hạn cụ thể của tài khoản em.',
    },
    {
        'title': 'Đóng học phí qua ngân hàng thế nào?',
        'content': 'Em ở xa không lên trường được, em đóng học phí qua chuyển khoản ngân hàng được không? Chuyển vào tài khoản nào ạ?',
        'major': 'Kỹ thuật phần mềm', 'category': 'Tài chính', 'days_ago': 168,
        'answer': 'Em chuyển khoản qua tài khoản trường tại Ngân hàng BIDV chi nhánh trường, số tài khoản chính thức được công bố trên website trường. Khi chuyển khoản, em ghi nội dung: "MSSV - Họ tên - HP HK[X]". Sau khi chuyển, hệ thống tự động cập nhật trong 1-2 ngày làm việc.',
    },
    {
        'title': 'Học phí năm 2024-2025 có tăng không?',
        'content': 'Em nghe các bạn nói học phí năm 2024-2025 sẽ tăng, có đúng không ạ?',
        'major': 'Quản trị kinh doanh', 'category': 'Tài chính', 'days_ago': 155,
        'answer': 'Theo thông báo chính thức, học phí năm học 2024-2025 tăng khoảng 5-7% so với năm trước, áp dụng cho khóa nhập học từ 2024 trở đi. Sinh viên các khóa cũ giữ nguyên mức học phí đã cam kết khi nhập học. Chi tiết em xem tại Phòng Tài chính-Kế toán hoặc website trường.',
    },

    # === ĐĂNG KÝ MÔN ===
    {
        'title': 'Cách đăng ký môn học kỳ tới',
        'content': 'Em là sinh viên năm 1, em chưa biết đăng ký môn học kỳ tới như thế nào, có giới hạn số tín chỉ không?',
        'major': 'Kỹ thuật phần mềm', 'category': 'Học vụ', 'days_ago': 148,
        'answer': 'Em đăng nhập trang đăng ký môn (dangky.edu) bằng tài khoản sinh viên. Mỗi học kỳ chính em đăng ký tối thiểu 14 tín chỉ, tối đa 25 tín chỉ. Học kỳ hè tối đa 12 tín chỉ. Lịch mở đăng ký được thông báo qua email và trang sinh viên trước 2 tuần. Em nhớ xem chương trình đào tạo của ngành để chọn đúng môn theo lộ trình.',
    },
    {
        'title': 'Đăng ký môn vượt số tín chỉ tối đa',
        'content': 'Em muốn đăng ký 27 tín chỉ trong 1 học kỳ để học vượt, có được không ạ?',
        'major': 'An toàn thông tin', 'category': 'Học vụ', 'days_ago': 140,
        'answer': 'Sinh viên có điểm trung bình tích lũy từ 3.2/4.0 trở lên được phép đăng ký vượt tới 30 tín chỉ/học kỳ. Em làm đơn gửi Phòng Đào tạo có chữ ký cố vấn học tập. Lưu ý đăng ký vượt sẽ tăng học phí tương ứng và rủi ro về chất lượng học tập, em cân nhắc kỹ.',
    },
    {
        'title': 'Trượt môn tiên quyết có học môn sau không?',
        'content': 'Em vừa trượt môn Lập trình hướng đối tượng. Em có được học các môn chuyên ngành tiếp theo không hay phải học lại trước?',
        'major': 'Kỹ thuật phần mềm', 'category': 'Học vụ', 'days_ago': 130,
        'answer': 'Nếu môn em trượt là tiên quyết của các môn chuyên ngành sau, em BẮT BUỘC phải học lại và đạt môn tiên quyết trước khi đăng ký môn tiếp theo. Hệ thống tự khóa không cho em đăng ký nếu chưa đạt môn tiên quyết. Em có thể đăng ký học cải thiện vào học kỳ hè để theo kịp lộ trình.',
    },

    # === RÚT MÔN ===
    {
        'title': 'Rút học phần xử lý bao lâu?',
        'content': 'Sau khi đăng ký học phần muốn rút thì khoảng bao lâu sẽ được xử lý ạ?',
        'major': 'Kỹ thuật phần mềm', 'category': 'Học vụ', 'days_ago': 120,
        'answer': 'Sinh viên rút môn online qua trang đăng ký trong 2 tuần đầu của học kỳ - kết quả cập nhật ngay sau khi xác nhận. Sau 2 tuần đầu nhưng còn trong 6 tuần đầu, em phải làm đơn nộp Phòng Đào tạo, thời gian xử lý 3-5 ngày làm việc. Sau tuần thứ 6 không được rút môn, em phải học hoặc bỏ và bị điểm F.',
    },

    # === THỰC TẬP ===
    {
        'title': 'Thực tập tốt nghiệp tự liên hệ công ty được không?',
        'content': 'Em đã tìm được công ty IT muốn thực tập, em tự đi thực tập có được tính tín chỉ không hay phải đăng ký qua trường?',
        'major': 'Kỹ thuật phần mềm', 'category': 'Học vụ', 'days_ago': 110,
        'answer': 'Em được phép tự liên hệ công ty thực tập, miễn là công ty có pháp nhân và lĩnh vực phù hợp với ngành học. Em làm đơn xin thực tập kèm thông tin công ty và người hướng dẫn nộp Khoa, sau khi được duyệt em sẽ có giấy giới thiệu chính thức. Cuối kỳ thực tập, em nộp báo cáo và phiếu đánh giá có chữ ký của công ty.',
    },
    {
        'title': 'Thời gian thực tập tốt nghiệp bao lâu?',
        'content': 'Cho em hỏi đợt thực tập tốt nghiệp kéo dài bao lâu? Có thể vừa thực tập vừa học môn khác không?',
        'major': 'Khoa học dữ liệu', 'category': 'Học vụ', 'days_ago': 100,
        'answer': 'Thực tập tốt nghiệp kéo dài 8-12 tuần (tương đương 4-6 tín chỉ tùy ngành). Em vẫn có thể đăng ký 1-2 môn lý thuyết khác trong thời gian thực tập, miễn là không trùng lịch họp doanh nghiệp. Tuy nhiên đa số sinh viên dồn hết môn vào kỳ trước để kỳ thực tập tập trung 100%.',
    },

    # === KHÓA LUẬN ===
    {
        'title': 'Điều kiện làm khóa luận tốt nghiệp',
        'content': 'Em phải đạt yêu cầu gì để được làm khóa luận tốt nghiệp thay vì học môn thay thế?',
        'major': 'An toàn thông tin', 'category': 'Học vụ', 'days_ago': 92,
        'answer': 'Em được làm khóa luận nếu: (1) đã hoàn thành tối thiểu 110 tín chỉ trong chương trình, (2) điểm trung bình tích lũy từ 2.5/4.0 trở lên, (3) không nợ môn tiên quyết của khóa luận. Sinh viên không đủ điều kiện sẽ học 2 môn thay thế (6 tín chỉ) thay cho khóa luận.',
    },
    {
        'title': 'Tìm giảng viên hướng dẫn khóa luận',
        'content': 'Em muốn làm khóa luận về AI nhưng không biết giảng viên nào hướng dẫn lĩnh vực đó. Làm sao tìm được ạ?',
        'major': 'Khoa học dữ liệu', 'category': 'Học vụ', 'days_ago': 85,
        'answer': 'Em vào website Khoa CNTT mục "Đội ngũ giảng viên" để xem CV và lĩnh vực nghiên cứu của từng thầy cô. Sau khi xác định 2-3 giảng viên phù hợp, em chủ động email liên hệ trình bày ý tưởng đề tài. Mỗi giảng viên hướng dẫn tối đa 5-8 sinh viên/đợt nên em nên liên hệ sớm trước khi đăng ký chính thức.',
    },

    # === HỌC BỔNG ===
    {
        'title': 'Tiêu chí xét học bổng khuyến khích học tập',
        'content': 'Em muốn xin học bổng khuyến khích học tập, điều kiện cụ thể là gì?',
        'major': 'Quản trị kinh doanh', 'category': 'Tài chính', 'days_ago': 78,
        'answer': 'Học bổng khuyến khích học tập xét mỗi học kỳ với các tiêu chí: (1) điểm trung bình học kỳ từ 3.2/4.0 trở lên, (2) điểm rèn luyện từ 80/100 trở lên, (3) không bị kỷ luật. Mức học bổng chia 3 loại: Khá (60% học phí), Giỏi (80%), Xuất sắc (100%). Trường tự động xét, danh sách công bố vào tháng 2 và tháng 8 hàng năm.',
    },
    {
        'title': 'Học bổng cho sinh viên có hoàn cảnh khó khăn',
        'content': 'Gia đình em khó khăn, có học bổng nào dành cho diện này không ạ?',
        'major': 'Marketing số', 'category': 'Tài chính', 'days_ago': 70,
        'answer': 'Trường có Quỹ học bổng vượt khó dành cho sinh viên có hoàn cảnh khó khăn. Em chuẩn bị: đơn xin học bổng theo mẫu, xác nhận hộ nghèo/cận nghèo của địa phương, bảng điểm học kỳ gần nhất. Hồ sơ nộp Phòng Công tác sinh viên trước ngày 30/9 hàng năm. Mức hỗ trợ từ 5-15 triệu/năm tùy hoàn cảnh và kết quả học tập.',
    },

    # === CẢNH BÁO HỌC VỤ ===
    {
        'title': 'Bị cảnh báo học vụ phải làm sao?',
        'content': 'Em vừa nhận thông báo cảnh báo học vụ vì điểm trung bình kỳ trước thấp. Có ảnh hưởng gì không?',
        'major': 'Kỹ thuật phần mềm', 'category': 'Học vụ', 'days_ago': 62,
        'answer': 'Cảnh báo học vụ là tín hiệu nhắc nhở khi điểm TB học kỳ < 1.0 hoặc TB tích lũy < 1.5. Em không bị buộc thôi học ngay, nhưng phải cải thiện ở học kỳ tiếp theo. Bị cảnh báo 3 học kỳ liên tiếp sẽ bị buộc thôi học. Em nên gặp cố vấn học tập để được tư vấn lộ trình học cải thiện và đăng ký môn phù hợp với năng lực.',
    },

    # === BẢO LƯU ===
    {
        'title': 'Bảo lưu kết quả học tập 1 năm',
        'content': 'Em có việc gia đình muốn nghỉ học 1 năm rồi quay lại học tiếp, làm sao để bảo lưu kết quả?',
        'major': 'Kỹ thuật phần mềm', 'category': 'Học vụ', 'days_ago': 55,
        'answer': 'Em được phép bảo lưu kết quả tối đa 2 học kỳ liên tục (1 năm). Hồ sơ gồm: đơn xin bảo lưu có lý do chính đáng (hoàn cảnh gia đình, sức khỏe...), giấy tờ chứng minh, bảng điểm các kỳ đã học. Nộp Phòng Đào tạo ít nhất 30 ngày trước học kỳ muốn bảo lưu. Khi quay lại, em làm đơn xin học tiếp và đóng học phí học kỳ mới.',
    },

    # === CHUYỂN NGÀNH ===
    {
        'title': 'Chuyển từ Kinh tế sang CNTT được không?',
        'content': 'Em đang học năm 1 ngành Quản trị kinh doanh nhưng cảm thấy thích CNTT hơn. Có thể chuyển ngành không ạ?',
        'major': 'Quản trị kinh doanh', 'category': 'Học vụ', 'days_ago': 48,
        'answer': 'Em được phép xin chuyển ngành sau khi hoàn thành học kỳ 1 với điểm TB từ 2.5/4.0 trở lên. Hồ sơ: đơn xin chuyển ngành, bảng điểm, lý do chuyển. Ngành mới phải còn chỉ tiêu và em có thể phải học bổ sung các môn cơ sở của ngành đó. Lưu ý ngành CNTT điểm chuẩn đầu vào cao hơn nên có thể em phải đáp ứng thêm điều kiện cụ thể của Khoa CNTT.',
    },

    # === MIỄN MÔN ===
    {
        'title': 'Bệnh tim có miễn môn thể chất không?',
        'content': 'Em bị bệnh tim bẩm sinh nên không đủ sức khỏe để học thể chất. Em có thể lấy giấy khám bệnh để xin miễn 2 môn thể chất không? Quy trình em nên làm thế nào?',
        'major': 'Marketing số', 'category': 'Hỗ trợ', 'days_ago': 42,
        'answer': 'Chào em! Em hoàn toàn được miễn môn thể chất nếu có lý do sức khỏe. Em chuẩn bị: (1) đơn xin miễn môn theo mẫu, (2) giấy chứng nhận của bệnh viện cấp tỉnh trở lên ghi rõ tình trạng và khuyến cáo không nên hoạt động thể lực, (3) bản sao thẻ sinh viên. Hồ sơ nộp Phòng Công tác sinh viên hoặc Trạm Y tế trường. Sau khi được duyệt, 2 môn thể chất sẽ được công nhận đạt mà không cần học và thi.',
    },
    {
        'title': 'Có IELTS có miễn môn tiếng Anh không?',
        'content': 'Em có chứng chỉ IELTS 6.5, có được miễn các môn tiếng Anh trong chương trình không?',
        'major': 'An toàn thông tin', 'category': 'Học vụ', 'days_ago': 38,
        'answer': 'Có em. Trường công nhận quy đổi miễn môn tiếng Anh cho các chứng chỉ quốc tế còn hạn (trong 2 năm): IELTS từ 5.5 → miễn TA1+TA2; từ 6.5 → miễn toàn bộ TA cơ sở (4 môn); TOEIC từ 600 trở lên có quy đổi tương tự. Em nộp bản sao công chứng chứng chỉ + đơn xin quy đổi tại Phòng Đào tạo. Việc miễn không tính vào điểm TB.',
    },

    # === KÝ TÚC XÁ ===
    {
        'title': 'Thủ tục xin ở ký túc xá',
        'content': 'Em là tân sinh viên, muốn ở ký túc xá để tiện đi học. Em phải làm gì để xin được phòng?',
        'major': 'Kỹ thuật phần mềm', 'category': 'Sinh hoạt', 'days_ago': 32,
        'answer': 'Em đăng ký ký túc xá online qua trang ktx.edu trong tuần đầu nhập học. Ưu tiên xét theo: (1) sinh viên ngoại tỉnh xa, (2) hoàn cảnh khó khăn, (3) khóa mới nhất. Sau khi đăng ký em đến Ban Quản lý KTX nộp: bản sao CCCD, ảnh 3x4, đơn đăng ký, đặt cọc 1 tháng phí phòng. Phí KTX khoảng 250-500k/tháng tùy phòng 4-8 người.',
    },
    {
        'title': 'Có thể chuyển phòng KTX không?',
        'content': 'Em đang ở phòng 8 người, muốn chuyển sang phòng 4 người yên tĩnh hơn để học tập, có được không?',
        'major': 'Khoa học dữ liệu', 'category': 'Sinh hoạt', 'days_ago': 28,
        'answer': 'Em viết đơn xin chuyển phòng nộp Ban Quản lý KTX, ghi rõ lý do và phòng muốn chuyển. Việc chuyển phụ thuộc vào: phòng đích còn chỗ trống, em đã đóng đầy đủ phí phòng cũ, không vi phạm nội quy KTX. Phí phòng 4 người cao hơn phòng 8 người, em chuẩn bị thêm khoảng 200k/tháng. Thường xử lý trong 5-7 ngày.',
    },

    # === LỊCH THI ===
    {
        'title': 'Xem lịch thi cuối kỳ ở đâu?',
        'content': 'Em muốn xem lịch thi cuối kỳ để sắp xếp thời gian ôn tập, xem ở đâu ạ?',
        'major': 'Kỹ thuật phần mềm', 'category': 'Học vụ', 'days_ago': 22,
        'answer': 'Lịch thi cuối kỳ công bố trên trang sinhvien.edu mục "Lịch thi" trước kỳ thi 2-3 tuần. Em đăng nhập tài khoản sinh viên để xem lịch theo từng môn đã đăng ký, kèm phòng thi và ca thi. Lưu ý kiểm tra trùng ca thi - nếu có em báo Phòng Khảo thí trong tuần đầu công bố để được sắp xếp lại.',
    },
    {
        'title': 'Vắng thi do bệnh có thi lại không?',
        'content': 'Em bị sốt cao đúng ngày thi cuối kỳ, không đi thi được. Em có được thi bù không?',
        'major': 'An toàn thông tin', 'category': 'Học vụ', 'days_ago': 18,
        'answer': 'Em được thi bù nếu vắng thi có lý do chính đáng. Trong vòng 5 ngày kể từ ngày thi, em làm đơn xin thi bù kèm: giấy chứng nhận của bệnh viện (nếu bệnh) hoặc giấy tờ chứng minh, đơn theo mẫu, bảng điểm môn đó. Nộp Phòng Khảo thí. Sau khi được duyệt, em sẽ thi vào lịch thi bù tổ chức 2-3 tuần sau kỳ thi chính. Vắng thi không lý do chính đáng = điểm 0 và phải học lại.',
    },

    # === BẰNG TỐT NGHIỆP ===
    {
        'title': 'Sau khi tốt nghiệp bao lâu nhận bằng?',
        'content': 'Em vừa hoàn thành khóa luận, sau bao lâu sẽ nhận được bằng tốt nghiệp ạ?',
        'major': 'Kỹ thuật phần mềm', 'category': 'Học vụ', 'days_ago': 14,
        'answer': 'Sau khi Hội đồng tốt nghiệp xét duyệt (thường tháng 7 và tháng 1 hàng năm), em nhận giấy chứng nhận tốt nghiệp tạm thời trong 1-2 tuần. Bằng chính thức được cấp sau 2-3 tháng do quy trình in và phê duyệt từ Bộ GD-ĐT. Trường tổ chức lễ tốt nghiệp khoảng tháng 9-10 mỗi năm, em sẽ nhận bằng trực tiếp tại lễ. Nếu không tham dự lễ, em có thể nhận bằng tại Phòng Đào tạo sau đó.',
    },

    # === HỌC CẢI THIỆN ===
    {
        'title': 'Đăng ký học cải thiện có giới hạn?',
        'content': 'Em muốn học lại 2 môn để cải thiện điểm, có giới hạn số môn được học cải thiện không?',
        'major': 'Marketing số', 'category': 'Học vụ', 'days_ago': 9,
        'answer': 'Em được học cải thiện không giới hạn số môn (miễn còn trong thời gian đào tạo tối đa 6 năm). Tuy nhiên mỗi học kỳ tổng số tín chỉ (kể cả học cải thiện) không vượt quá 25. Điểm cao nhất giữa các lần học sẽ được tính vào điểm TB tích lũy. Học cải thiện đóng học phí như môn mới. Lưu ý: chỉ được học cải thiện nếu môn đó đạt từ D trở lên (không học lại điểm F).',
    },

    # === XÁC NHẬN SINH VIÊN ===
    {
        'title': 'Xin giấy xác nhận sinh viên ở đâu?',
        'content': 'Em cần giấy xác nhận sinh viên để làm thủ tục vay vốn ngân hàng, em xin ở đâu?',
        'major': 'Quản trị kinh doanh', 'category': 'Hỗ trợ', 'days_ago': 5,
        'answer': 'Em đăng ký xin giấy xác nhận online tại trang sinhvien.edu mục "Dịch vụ một cửa" - chọn loại xác nhận (vay vốn, học bổng, làm thủ tục dân sự...). Phí 5,000đ/giấy. Sau 1-2 ngày làm việc em đến Phòng Công tác sinh viên nhận. Nếu cần gấp, em có thể yêu cầu xử lý nhanh trong ngày với phí 20,000đ.',
    },

    # === NGHỈ HỌC LÂU ===
    {
        'title': 'Không học gần 1 năm có bị đình chỉ không?',
        'content': 'Em hoàn thành hết các chỉ tiêu để tốt nghiệp nhưng còn nợ lại 2 môn thể chất. Em đã làm việc gần 1 năm và không học tại trường nữa thì có bị cảnh cáo hay đình chỉ không?',
        'major': 'Marketing số', 'category': 'Học vụ', 'days_ago': 3,
        'answer': 'Em vẫn còn quyền học tiếp trong thời gian đào tạo tối đa của khóa (thường 6 năm cho hệ chính quy 4 năm). Em không bị đình chỉ vì không đăng ký môn nào, chỉ bị treo trạng thái "tạm nghỉ học". Em chỉ cần đăng ký lại 2 môn thể chất còn nợ vào học kỳ phù hợp (kỳ chính hoặc kỳ hè) là tiếp tục. Trường hợp em có vấn đề sức khỏe không học được thể chất, em có thể xin miễn theo quy trình tại Phòng CTSV.',
    },
]


# ============================================================
# COMMAND
# ============================================================

class Command(BaseCommand):
    help = "Tạo dữ liệu Q&A mẫu cho chatbot demo (~26 câu rải 6 tháng)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-embeddings',
            action='store_true',
            help='Xoá toàn bộ embedding hiện có và build lại sau khi seed.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # 1. Đảm bảo Departments + Majors + Categories có đủ
        self.stdout.write("=> Đảm bảo Department / Major / Category...")
        dept_map = {}
        for name, desc in DEPARTMENTS:
            d, _ = Department.objects.get_or_create(name=name, defaults={'description': desc})
            dept_map[name] = d

        major_map = {}
        for major_name, dept_name in MAJORS:
            m, _ = Major.objects.get_or_create(
                name=major_name,
                defaults={'department': dept_map[dept_name], 'description': ''},
            )
            major_map[major_name] = m

        cat_map = {}
        for cat_name, cat_desc in CATEGORIES:
            c, _ = QuestionCategory.objects.get_or_create(
                name=cat_name,
                defaults={'description': cat_desc},
            )
            cat_map[cat_name] = c

        # 2. Tìm hoặc tạo 1 user "asker" (sinh viên) và 1 advisor để làm tác giả
        self.stdout.write("=> Đảm bảo có asker và advisor...")
        asker = User.objects.filter(user_type='student').first()
        if not asker:
            asker = User.objects.create_user(
                username='demo_student',
                password='demo12345',
                email='demo_student@school.edu.vn',
                first_name='Demo',
                last_name='Sinh viên',
                user_type='student',
                student_id='DEMO0001',
            )
            self.stdout.write(self.style.WARNING(
                "  Tạo user demo_student / demo12345 (sinh viên mẫu)"
            ))

        advisor_profile = AdvisorProfile.objects.first()
        if not advisor_profile:
            advisor_user = User.objects.create_user(
                username='demo_advisor',
                password='demo12345',
                email='demo_advisor@school.edu.vn',
                first_name='Demo',
                last_name='Tư vấn',
                user_type='student',  # cần giá trị
                is_staff=True,
            )
            advisor_profile = AdvisorProfile.objects.create(
                user=advisor_user,
                department=dept_map['Công Nghệ Thông Tin'],
                role='advisor',
            )
            self.stdout.write(self.style.WARNING(
                "  Tạo user demo_advisor / demo12345 (tư vấn viên mẫu)"
            ))
        advisor = advisor_profile.user

        # 3. Tạo Q&A
        self.stdout.write(f"=> Tạo {len(SEED_QA)} Q&A mẫu...")
        now = timezone.now()
        created = skipped = 0

        for entry in SEED_QA:
            # Skip nếu đã có Q cùng title
            if Question.objects.filter(title=entry['title']).exists():
                skipped += 1
                continue

            q_time = now - timedelta(days=entry['days_ago'])
            a_time = q_time + timedelta(hours=2)  # advisor trả lời sau 2h

            q = Question.objects.create(
                user=asker,
                title=entry['title'],
                content=entry['content'],
                major=major_map[entry['major']],
                category=cat_map[entry['category']],
                status='answered',
            )
            # Đè timestamps (auto_now_add đã set now, cần update lại)
            Question.objects.filter(pk=q.pk).update(created_at=q_time, updated_at=q_time)

            a = Answer.objects.create(
                question=q,
                user=advisor,
                content=entry['answer'],
            )
            Answer.objects.filter(pk=a.pk).update(created_at=a_time, updated_at=a_time)

            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"   Đã tạo: {created} Q&A | Bỏ qua (đã tồn tại): {skipped}"
        ))

        # 4. Build embeddings (signal sẽ tự chạy khi tạo Answer ở trên,
        #    nhưng có thể fail nếu chưa có Gemini API key sẵn sàng)
        if options['reset_embeddings']:
            self.stdout.write("=> Reset & rebuild embeddings...")
            from chatbot.models import QuestionEmbedding
            from chatbot.services.embedding_service import reindex_all
            QuestionEmbedding.objects.all().delete()
            count = reindex_all()
            self.stdout.write(self.style.SUCCESS(f"   Đã index {count} câu hỏi."))
        else:
            self.stdout.write(self.style.WARNING(
                "Lưu ý: Hãy chạy 'python manage.py build_embeddings' để tạo "
                "embedding cho các câu mới (signal có thể đã chạy sẵn)."
            ))

        self.stdout.write(self.style.SUCCESS("Hoàn tất seed!"))
