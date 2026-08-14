from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0004_contentreport'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chatsession',
            name='state',
            field=models.CharField(
                choices=[
                    ('initial', 'Chưa bắt đầu'),
                    ('chatting', 'Đang trò chuyện'),
                    ('collecting_dept', 'Đang chọn khoa'),
                    ('collecting_major', 'Đang chọn ngành'),
                    ('collecting_category', 'Đang chọn loại câu hỏi'),
                    ('showing_results', 'Đã hiển thị kết quả'),
                    ('escalation_form', 'Đang xác nhận chuyển tư vấn viên'),
                    ('completed', 'Hoàn tất'),
                ],
                default='initial',
                max_length=30,
                verbose_name='Trạng thái',
            ),
        ),
    ]
