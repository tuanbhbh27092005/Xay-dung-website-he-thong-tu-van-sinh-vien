"""
Management command: seed 8 tin tức HCMUTE đa dạng chủ đề.

Cách dùng:
    python manage.py seed_news                # tạo 8 tin (skip nếu đã tồn tại)
    python manage.py seed_news --reset        # xóa tin cũ rồi seed lại

Nội dung: gốc, do tác giả viết, paraphrase từ chủ đề trường HCMUTE,
KHÔNG sao chép từ hcmute.edu.vn. Có thể chỉnh sửa tự do.
"""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from news.models import News
from accounts.models import CustomUser
from questions.models import Department


# ─────────────────────────────────────────────────────────────────────────────
# Dataset: 8 tin tức HCMUTE — đa dạng chủ đề, độ dài, ngày đăng giả lập
# Mỗi tin có ảnh thumbnail từ Unsplash (free, không bản quyền) hợp ngữ cảnh
# ─────────────────────────────────────────────────────────────────────────────

NEWS_DATA = [
    # ─── 1. TUYỂN SINH (featured) ─────────────────────────────────────────
    {
        'title': 'HCMUTE công bố phương thức tuyển sinh năm 2026: thêm xét tuyển kết hợp',
        'category': 'admission',
        'is_featured': True,
        'days_ago': 2,
        'thumbnail_url': 'https://images.unsplash.com/photo-1523580494863-6f3031224c94?w=1200&q=80',
        'summary': (
            'Bên cạnh phương thức truyền thống, năm nay HCMUTE bổ sung phương thức '
            'xét tuyển kết hợp giữa kết quả thi THPT và chứng chỉ ngoại ngữ quốc tế.'
        ),
        'content': (
            'Trường Đại học Sư phạm Kỹ thuật Thành phố Hồ Chí Minh vừa công bố phương án '
            'tuyển sinh chính thức cho năm 2026. Theo đó, ngoài việc duy trì các phương '
            'thức xét tuyển truyền thống đã áp dụng nhiều năm qua, nhà trường mở thêm '
            'phương thức kết hợp dành cho thí sinh có kết quả thi tốt nghiệp THPT đạt '
            'ngưỡng đảm bảo chất lượng đầu vào và sở hữu chứng chỉ ngoại ngữ quốc tế hợp lệ.\n\n'
            'Cụ thể, các phương thức tuyển sinh năm nay gồm:\n\n'
            '1. Xét tuyển dựa trên kết quả thi tốt nghiệp THPT (chiếm phần lớn chỉ tiêu).\n'
            '2. Xét học bạ THPT đối với một số ngành.\n'
            '3. Tuyển thẳng và ưu tiên xét tuyển theo quy chế của Bộ Giáo dục và Đào tạo.\n'
            '4. Phương thức kết hợp mới: điểm thi THPT + chứng chỉ IELTS, TOEFL iBT, '
            'TOEIC 4 kỹ năng hoặc tương đương.\n\n'
            'Đối với phương thức kết hợp, ngưỡng chứng chỉ ngoại ngữ tối thiểu được công bố '
            'kèm theo cho từng nhóm ngành. Các ngành thuộc khối Công nghệ Thông tin, '
            'Cơ - Điện tử, Kỹ thuật Điều khiển và Tự động hóa dự kiến yêu cầu mức cao hơn '
            'so với mặt bằng chung.\n\n'
            'Nhà trường cũng cho biết tổng chỉ tiêu năm 2026 không thay đổi nhiều so với '
            'năm trước, tuy nhiên phân bổ giữa các chương trình đại trà, chất lượng cao '
            'và liên kết quốc tế sẽ được điều chỉnh theo nhu cầu thực tế của từng khoa. '
            'Thí sinh được khuyến nghị theo dõi thông báo chi tiết trên cổng thông tin '
            'tuyển sinh của trường để cập nhật mã ngành và mã tổ hợp xét tuyển.\n\n'
            'Lệ phí xét tuyển và lịch nộp hồ sơ sẽ được công bố sau khi Bộ Giáo dục '
            'và Đào tạo ban hành lịch thi tốt nghiệp THPT chính thức.'
        ),
    },

    # ─── 2. SỰ KIỆN ───────────────────────────────────────────────────────
    {
        'title': 'Ngày hội việc làm HCMUTE 2026: hơn 80 doanh nghiệp tham dự',
        'category': 'event',
        'is_featured': True,
        'days_ago': 5,
        'thumbnail_url': 'https://images.unsplash.com/photo-1556761175-5973dc0f32e7?w=1200&q=80',
        'summary': (
            'Hơn 80 doanh nghiệp trong và ngoài nước sẽ tham gia ngày hội việc làm '
            'năm nay, mang đến hơn 2.500 vị trí thực tập và tuyển dụng cho sinh viên.'
        ),
        'content': (
            'Trung tâm Quan hệ Doanh nghiệp và Hỗ trợ Sinh viên thông báo Ngày hội '
            'Việc làm HCMUTE 2026 sẽ được tổ chức tại sân chính cơ sở 1 (số 1 Võ Văn '
            'Ngân, Thủ Đức) trong hai ngày liên tiếp.\n\n'
            'Sự kiện năm nay quy tụ hơn 80 doanh nghiệp đến từ nhiều lĩnh vực: sản xuất '
            'cơ khí, điện - điện tử, công nghệ thông tin, ô tô, dệt may, thực phẩm, '
            'logistics. Trong số đó có sự tham gia của các tập đoàn lớn đã hợp tác lâu '
            'năm với nhà trường như Bosch Việt Nam, Samsung Electronics, ABB, Schneider '
            'Electric, Intel Products, FPT Software, cùng nhiều công ty khởi nghiệp '
            'công nghệ trong nước.\n\n'
            'Theo ban tổ chức, tổng số vị trí được công bố tại ngày hội năm nay vượt '
            '2.500, bao gồm cả vị trí thực tập có lương dành cho sinh viên năm 3-4 và '
            'vị trí kỹ sư chính thức cho sinh viên năm cuối, cựu sinh viên.\n\n'
            'Ngoài khu vực gian hàng tuyển dụng, chương trình còn có chuỗi hoạt động '
            'song song:\n\n'
            '- Hội thảo định hướng nghề nghiệp do các kỹ sư cao cấp chia sẻ kinh nghiệm.\n'
            '- Workshop viết CV và phỏng vấn xin việc bằng tiếng Anh.\n'
            '- Khu vực phỏng vấn nhanh: sinh viên có thể xin việc ngay tại chỗ.\n'
            '- Triển lãm sản phẩm nghiên cứu của sinh viên các khoa.\n\n'
            'Sinh viên muốn tham gia vui lòng đăng ký trên Portal Sinh viên trước ngày '
            'diễn ra ít nhất 3 ngày để nhận lịch phỏng vấn cá nhân hóa. Sinh viên năm '
            'cuối được khuyến khích chuẩn bị sẵn CV (tiếng Việt và tiếng Anh) cùng '
            'portfolio đồ án để tăng cơ hội ghi điểm với nhà tuyển dụng.'
        ),
    },

    # ─── 3. TIN KHOA CNTT ─────────────────────────────────────────────────
    {
        'title': 'Khoa Công nghệ Thông tin ra mắt phòng Lab AI mới với 60 GPU',
        'category': 'department',
        'department_name': 'Công nghệ Thông tin',
        'days_ago': 9,
        'thumbnail_url': 'https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&q=80',
        'summary': (
            'Phòng Lab AI mới được trang bị 60 GPU NVIDIA hỗ trợ sinh viên và giảng viên '
            'thực hành học máy, học sâu và xử lý ngôn ngữ tự nhiên.'
        ),
        'content': (
            'Khoa Công nghệ Thông tin vừa khánh thành phòng thí nghiệm Trí tuệ Nhân tạo '
            '(AI Lab) tại tầng 5 tòa nhà Trung tâm. Phòng được trang bị 60 GPU NVIDIA '
            'thế hệ mới, hệ thống lưu trữ chia sẻ NAS dung lượng lớn và đường truyền '
            'mạng nội bộ tốc độ cao đáp ứng các tác vụ huấn luyện mô hình quy mô vừa.\n\n'
            'Mục tiêu của phòng Lab là phục vụ ba nhóm hoạt động chính:\n\n'
            'Thứ nhất, đảm bảo điều kiện thực hành cho các môn học liên quan đến học '
            'máy, học sâu, thị giác máy tính và xử lý ngôn ngữ tự nhiên trong chương '
            'trình đào tạo bậc đại học và sau đại học.\n\n'
            'Thứ hai, hỗ trợ sinh viên thực hiện đồ án tốt nghiệp và đề tài nghiên cứu '
            'khoa học có sử dụng tài nguyên tính toán lớn — vốn trước đây phải dựa vào '
            'dịch vụ đám mây thương mại với chi phí không nhỏ.\n\n'
            'Thứ ba, phục vụ các đề tài nghiên cứu cấp khoa, cấp trường và các dự án '
            'hợp tác với doanh nghiệp trong lĩnh vực AI ứng dụng.\n\n'
            'Sinh viên có nhu cầu đăng ký sử dụng GPU cho đồ án tốt nghiệp có thể nộp '
            'đề xuất qua giảng viên hướng dẫn. Khoa sẽ ưu tiên xét duyệt cho các đề tài '
            'có tính ứng dụng thực tế và bám sát định hướng nghiên cứu của khoa.\n\n'
            'Đây là một trong những bước đầu tư hạ tầng quan trọng của khoa nhằm bắt '
            'kịp xu hướng phát triển của ngành AI vốn đòi hỏi tài nguyên tính toán '
            'ngày càng lớn.'
        ),
    },

    # ─── 4. HỌC BỔNG ──────────────────────────────────────────────────────
    {
        'title': 'Mở đợt xét học bổng khuyến khích học tập học kỳ 1 năm học 2025-2026',
        'category': 'school',
        'days_ago': 12,
        'thumbnail_url': 'https://images.unsplash.com/photo-1607013251379-e6eecfffe234?w=1200&q=80',
        'summary': (
            'Phòng Công tác Sinh viên thông báo nhận hồ sơ xét học bổng khuyến khích '
            'học tập (KKHT) học kỳ 1. Hạn cuối: cuối tháng này.'
        ),
        'content': (
            'Phòng Công tác Sinh viên thông báo lịch xét học bổng khuyến khích học tập '
            'cho sinh viên hệ chính quy đợt học kỳ 1 năm học 2025-2026.\n\n'
            'Đối tượng được xét bao gồm sinh viên đại học chính quy thuộc các năm học '
            'có đăng ký học phần trong học kỳ xét, đáp ứng các điều kiện về điểm trung '
            'bình học tập và điểm rèn luyện theo quy định hiện hành của trường.\n\n'
            'Thứ tự ưu tiên xét theo điểm trung bình tích lũy giảm dần và điểm rèn luyện. '
            'Mức học bổng được phân loại thành ba mức: xuất sắc, giỏi và khá. Số suất '
            'cho mỗi mức được phân bổ theo tỷ lệ sinh viên của từng khoa và từng khóa.\n\n'
            'Quy trình nộp hồ sơ:\n\n'
            '- Bước 1: Sinh viên đăng nhập cổng thông tin sinh viên, kiểm tra điểm trung '
            'bình học kỳ và điểm rèn luyện đã được công bố chính thức.\n'
            '- Bước 2: Tải mẫu đơn đăng ký từ trang Phòng Công tác Sinh viên, điền '
            'thông tin và in ra ký xác nhận.\n'
            '- Bước 3: Nộp đơn cho cố vấn học tập của lớp để được xác nhận.\n'
            '- Bước 4: Cố vấn tổng hợp và gửi về văn phòng khoa, sau đó khoa tổng hợp '
            'gửi về Phòng Công tác Sinh viên trước hạn quy định.\n\n'
            'Lưu ý: hồ sơ thiếu chữ ký cố vấn hoặc nộp sau hạn sẽ không được xem xét. '
            'Các trường hợp tranh chấp về điểm cần được giải quyết ở khoa trước khi nộp '
            'đơn xét học bổng.'
        ),
    },

    # ─── 5. HOẠT ĐỘNG SINH VIÊN ──────────────────────────────────────────
    {
        'title': 'Đội tuyển HCMUTE giành giải Ba quốc gia Olympic Tin học sinh viên',
        'category': 'class',
        'days_ago': 15,
        'thumbnail_url': 'https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=1200&q=80',
        'summary': (
            'Đội tuyển 4 sinh viên của trường vừa giành giải Ba toàn quốc tại kỳ thi '
            'Olympic Tin học Sinh viên năm nay, vượt qua hơn 200 đội tham dự.'
        ),
        'content': (
            'Đội tuyển sinh viên trường vừa khép lại hành trình tại vòng chung kết '
            'Olympic Tin học Sinh viên toàn quốc năm nay với thành tích đáng ghi nhận: '
            'giải Ba ở bảng Chuyên tin và một giải Khuyến khích ở bảng Siêu cúp.\n\n'
            'Thành tích này đặc biệt có ý nghĩa khi đội tuyển của trường thi đấu giữa '
            'hơn 200 đội đến từ các trường đại học trên cả nước, trong đó nhiều trường '
            'có truyền thống đào tạo công nghệ thông tin lâu đời.\n\n'
            'Bốn thành viên đội tuyển đến từ khoa Công nghệ Thông tin, đều là sinh viên '
            'năm 2 và năm 3, đã trải qua quá trình huấn luyện liên tục trong sáu tháng '
            'với sự dẫn dắt của các giảng viên giàu kinh nghiệm và sự hỗ trợ từ cộng '
            'đồng cựu sinh viên.\n\n'
            'Ban huấn luyện chia sẻ rằng điểm mạnh của đội năm nay nằm ở khả năng làm '
            'việc nhóm và phân chia bài tập hợp lý dưới áp lực thời gian. Các bạn cũng '
            'tích lũy được nhiều kinh nghiệm thi đấu thực chiến qua các giải online '
            'của Codeforces và HackerRank.\n\n'
            'Trường dự kiến sẽ tổ chức buổi giao lưu giữa đội tuyển và sinh viên các '
            'khóa nhỏ hơn để truyền cảm hứng và giới thiệu phương pháp luyện tập. Đây '
            'cũng là một trong những hoạt động khơi dậy phong trào học thuật và thi đấu '
            'lập trình trong sinh viên.'
        ),
    },

    # ─── 6. TIN TRƯỜNG (HỢP TÁC QUỐC TẾ) ──────────────────────────────────
    {
        'title': 'HCMUTE ký kết hợp tác trao đổi sinh viên với 3 đại học Hàn Quốc',
        'category': 'school',
        'days_ago': 19,
        'thumbnail_url': 'https://images.unsplash.com/photo-1607237138185-eedd9c632b0b?w=1200&q=80',
        'summary': (
            'Sinh viên HCMUTE sẽ có cơ hội học tập một học kỳ tại các đại học '
            'KAIST, Hanyang và Pusan với học phí được miễn giảm thông qua chương trình '
            'trao đổi mới.'
        ),
        'content': (
            'Đại diện ban giám hiệu nhà trường vừa hoàn tất việc ký kết bản ghi nhớ '
            'hợp tác trao đổi sinh viên với ba đại học của Hàn Quốc trong khuôn khổ '
            'chuyến công tác làm việc tại Seoul và Busan.\n\n'
            'Chương trình cho phép sinh viên HCMUTE đăng ký học một học kỳ tại các '
            'trường đối tác Hàn Quốc với một số ưu đãi: miễn học phí thông qua chương '
            'trình trao đổi sinh viên (cả hai bên không thu học phí của sinh viên đối '
            'tác); hỗ trợ ký túc xá với mức giá ưu đãi; được công nhận tín chỉ khi '
            'quay về trường tiếp tục học.\n\n'
            'Điều kiện đăng ký bao gồm:\n\n'
            '- Sinh viên đang học năm 2 hoặc năm 3 hệ chính quy.\n'
            '- Điểm trung bình tích lũy đạt mức tối thiểu do chương trình quy định.\n'
            '- Có chứng chỉ ngoại ngữ (tiếng Anh hoặc tiếng Hàn) hợp lệ.\n'
            '- Sức khỏe đảm bảo và có khả năng tự túc các chi phí sinh hoạt khác '
            '(ngoài học phí và ký túc xá).\n\n'
            'Số suất mỗi đợt giới hạn theo từng đại học đối tác. Phòng Hợp tác Quốc tế '
            'sẽ thông báo lịch nhận hồ sơ chi tiết và tổ chức các buổi định hướng '
            'cho sinh viên quan tâm.\n\n'
            'Trong những năm gần đây, hoạt động hợp tác quốc tế là một trong những '
            'hướng phát triển trọng tâm của trường, nhằm tăng cường năng lực ngoại ngữ '
            'và mở rộng tầm nhìn nghề nghiệp cho sinh viên.'
        ),
    },

    # ─── 7. TIN LỚP / SINH VIÊN (CLB) ─────────────────────────────────────
    {
        'title': 'CLB Khởi nghiệp HCMUTE tuyển thành viên khóa mới',
        'category': 'class',
        'days_ago': 23,
        'thumbnail_url': 'https://images.unsplash.com/photo-1556761175-b413da4baf72?w=1200&q=80',
        'summary': (
            'CLB Khởi nghiệp tuyển thành viên khóa mới với chương trình đào tạo '
            'thực chiến từ hình thành ý tưởng đến gọi vốn.'
        ),
        'content': (
            'CLB Khởi nghiệp Sinh viên HCMUTE thông báo mở đơn tuyển thành viên khóa '
            'mới dành cho sinh viên tất cả các khoa quan tâm đến lĩnh vực startup và '
            'khởi nghiệp đổi mới sáng tạo.\n\n'
            'Khác với các CLB chuyên môn truyền thống, CLB Khởi nghiệp tập trung vào '
            'rèn luyện tư duy kinh doanh và khả năng thực thi ý tưởng. Chương trình '
            'huấn luyện kéo dài một học kỳ với các nội dung sau:\n\n'
            '- Kỹ năng phát hiện vấn đề và xác định khách hàng tiềm năng.\n'
            '- Phương pháp Lean Startup và xây dựng MVP (Minimum Viable Product).\n'
            '- Lập kế hoạch tài chính cơ bản và tính toán dòng tiền.\n'
            '- Kỹ năng thuyết trình và pitching trước nhà đầu tư.\n'
            '- Cơ hội tham gia các cuộc thi khởi nghiệp cấp quốc gia.\n\n'
            'Điểm hấp dẫn của khóa này là sự xuất hiện của các mentor là cựu sinh viên '
            'đã thành công với startup riêng cùng đại diện một số quỹ đầu tư mạo hiểm '
            'tại Việt Nam. Các bạn được làm việc theo nhóm 3-5 người trên một dự án '
            'thật xuyên suốt khóa học, sản phẩm cuối khóa được trình bày trong sự kiện '
            'Demo Day có sự tham dự của doanh nghiệp.\n\n'
            'CLB không yêu cầu thành viên mới đã có ý tưởng khởi nghiệp - các bạn sẽ '
            'được hỗ trợ tìm và phát triển ý tưởng trong quá trình tham gia. Quan '
            'trọng nhất là tinh thần ham học hỏi và khả năng cam kết tham dự đầy đủ '
            'các buổi sinh hoạt định kỳ.'
        ),
    },

    # ─── 8. TIN TRƯỜNG (HỌC PHÍ) ──────────────────────────────────────────
    {
        'title': 'Thông báo điều chỉnh thời hạn đóng học phí học kỳ 1 năm học 2025-2026',
        'category': 'school',
        'days_ago': 28,
        'thumbnail_url': 'https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1200&q=80',
        'summary': (
            'Phòng Kế hoạch Tài chính thông báo điều chỉnh hạn đóng học phí học kỳ 1, '
            'gia hạn thêm 7 ngày để hỗ trợ sinh viên gặp khó khăn.'
        ),
        'content': (
            'Phòng Kế hoạch Tài chính thông báo về việc điều chỉnh thời hạn đóng học '
            'phí học kỳ 1 năm học 2025-2026 nhằm tạo điều kiện cho sinh viên gặp khó '
            'khăn về tài chính có thêm thời gian thu xếp.\n\n'
            'Theo thông báo mới nhất, thời hạn cuối cùng đóng học phí được gia hạn '
            'thêm 7 ngày so với lịch ban đầu. Sau thời điểm này, hệ thống sẽ tự động '
            'áp dụng các biện pháp xử lý theo quy định, bao gồm tạm khóa tài khoản '
            'sinh viên và không cho phép đăng ký môn học cho học kỳ tiếp theo.\n\n'
            'Hình thức thanh toán hợp lệ:\n\n'
            '1. Chuyển khoản qua tài khoản ngân hàng của trường (thông tin tài khoản '
            'đã được công bố trên cổng thông tin sinh viên, lưu ý ghi rõ mã số sinh '
            'viên trong nội dung chuyển khoản để hệ thống tự động đối soát).\n'
            '2. Đóng tại quầy thu của Phòng Kế hoạch Tài chính trong giờ hành chính.\n'
            '3. Đóng qua các ứng dụng ví điện tử hỗ trợ thanh toán học phí (chi tiết '
            'xem trên cổng thông tin sinh viên).\n\n'
            'Sinh viên thuộc diện được hỗ trợ học phí (gia đình chính sách, hộ nghèo, '
            'cận nghèo) cần liên hệ Phòng Công tác Sinh viên trước hạn để được hướng '
            'dẫn thủ tục riêng. Các trường hợp gặp khó khăn đặc biệt có thể nộp đơn '
            'xin gia hạn cá nhân kèm minh chứng để được xem xét.\n\n'
            'Sau khi đóng, sinh viên nên kiểm tra lại trạng thái trên cổng thông tin '
            'trong vòng 1-2 ngày làm việc. Nếu hệ thống chưa cập nhật, vui lòng liên '
            'hệ trực tiếp Phòng Kế hoạch Tài chính kèm chứng từ chuyển khoản để được '
            'hỗ trợ.'
        ),
    },
]


class Command(BaseCommand):
    help = 'Seed 8 tin tức HCMUTE đa dạng chủ đề (paraphrase, không đạo từ hcmute.edu.vn)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Xóa hết news cũ rồi seed mới (cẩn thận: mất data!)'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        reset = options['reset']

        if reset:
            count = News.objects.count()
            if count:
                self.stdout.write(self.style.WARNING(f'Xóa {count} tin tức cũ...'))
                News.objects.all().delete()

        # Tìm author: ưu tiên user 'admin', fallback first superuser/staff
        author = (
            CustomUser.objects.filter(username='admin').first()
            or CustomUser.objects.filter(is_superuser=True).first()
            or CustomUser.objects.filter(is_staff=True).first()
        )
        if not author:
            self.stdout.write(self.style.ERROR(
                'Không tìm thấy user nào để gán làm tác giả. '
                'Hãy tạo superuser bằng `python manage.py createsuperuser` trước.'
            ))
            return

        self.stdout.write(f'Tác giả: {author.username}')

        now = timezone.now()
        created = 0
        skipped = 0

        for item in NEWS_DATA:
            title = item['title']

            if News.objects.filter(title=title).exists():
                skipped += 1
                self.stdout.write(self.style.NOTICE(f'  ⊘ Bỏ qua (đã tồn tại): {title[:60]}'))
                continue

            # Map department theo tên (nếu có)
            department = None
            dept_name = item.get('department_name')
            if dept_name:
                department = Department.objects.filter(name__icontains=dept_name).first()

            news = News(
                title=title,
                summary=item['summary'],
                content=item['content'],
                category=item['category'],
                department=department,
                thumbnail_url=item.get('thumbnail_url', ''),
                author=author,
                is_published=True,
                is_featured=item.get('is_featured', False),
                views_count=item.get('initial_views', 0),
            )
            news.save()  # save() sẽ auto-generate slug từ title

            # Backdate ngày đăng để feel realistic + ordering đúng
            days_ago = item.get('days_ago', 0)
            backdate = now - timedelta(days=days_ago)
            News.objects.filter(pk=news.pk).update(created_at=backdate, updated_at=backdate)

            created += 1
            badge = ' ⭐' if item.get('is_featured') else ''
            self.stdout.write(self.style.SUCCESS(
                f'  ✓ Tạo: [{item["category"]:10}]{badge} {title[:60]}'
            ))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'=== Hoàn tất: tạo mới {created}, bỏ qua {skipped} ==='
        ))
