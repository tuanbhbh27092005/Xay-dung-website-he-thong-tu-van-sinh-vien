from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0002_question_is_public'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='views_count',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Tăng tự động mỗi lần truy cập trang chi tiết câu hỏi (loại trừ tác giả).',
                verbose_name='Lượt xem',
            ),
        ),
    ]
