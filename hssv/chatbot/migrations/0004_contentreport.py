import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0003_newsembedding'),
        ('news', '0002_newslike'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ContentReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(
                    choices=[('chat', 'Tin nhắn chatbot'), ('comment', 'Bình luận tin tức')],
                    max_length=20,
                    verbose_name='Loại nội dung'
                )),
                ('snapshot_text', models.TextField(
                    help_text='Lưu lại text gốc để khi user/admin xoá vẫn còn ngữ cảnh.',
                    verbose_name='Nội dung khi vi phạm'
                )),
                ('matched_words', models.CharField(blank=True, max_length=300, verbose_name='Từ vi phạm phát hiện')),
                ('reason', models.CharField(blank=True, default='', max_length=200, verbose_name='Lý do (nếu user báo cáo)')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Chờ xử lý'),
                        ('approved', 'Đã duyệt (không vi phạm)'),
                        ('hidden', 'Đã ẩn / xoá'),
                        ('warned', 'Đã cảnh báo user'),
                    ],
                    default='pending', max_length=20, verbose_name='Trạng thái'
                )),
                ('reviewed_at', models.DateTimeField(blank=True, null=True, verbose_name='Thời điểm xử lý')),
                ('admin_note', models.TextField(blank=True, default='', verbose_name='Ghi chú xử lý')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Thời điểm phát hiện')),
                ('chat_message', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='reports', to='chatbot.chatmessage',
                    verbose_name='Tin nhắn chat'
                )),
                ('comment', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='reports', to='news.comment',
                    verbose_name='Bình luận'
                )),
                ('content_user', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='content_reports_received',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='User tạo nội dung'
                )),
                ('reporter', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='content_reports_made',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Người báo cáo (None = hệ thống tự)'
                )),
                ('reviewed_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='content_reports_reviewed',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Người xử lý'
                )),
            ],
            options={
                'verbose_name': 'Báo cáo nội dung vi phạm',
                'verbose_name_plural': 'Báo cáo nội dung vi phạm',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['status', '-created_at'], name='chatbot_con_status_b50aa0_idx'),
                    models.Index(fields=['source', 'status'], name='chatbot_con_source_b73a13_idx'),
                ],
            },
        ),
    ]
