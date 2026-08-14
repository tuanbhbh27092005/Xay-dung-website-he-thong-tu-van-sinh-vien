import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0002_chatmessage_metadata_and_more'),
        ('news', '0002_newslike'),
    ]

    operations = [
        migrations.CreateModel(
            name='NewsEmbedding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('embedding', models.JSONField(verbose_name='Vector embedding')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Cập nhật lần cuối')),
                ('news', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='embedding',
                    to='news.news',
                    verbose_name='Bài tin tức'
                )),
            ],
            options={
                'verbose_name': 'Embedding tin tức',
                'verbose_name_plural': 'Embedding tin tức',
            },
        ),
    ]
