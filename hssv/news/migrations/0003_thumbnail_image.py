from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0002_newslike'),
    ]

    operations = [
        migrations.AddField(
            model_name='news',
            name='thumbnail_image',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='news/thumbnails/',
                verbose_name='Ảnh đại diện (upload)',
                help_text='Upload file ảnh từ máy tính. Ưu tiên dùng cái này thay vì URL.',
            ),
        ),
        migrations.AlterField(
            model_name='news',
            name='thumbnail_url',
            field=models.URLField(
                blank=True,
                max_length=500,
                verbose_name='URL ảnh đại diện (dự phòng)',
                help_text='Chỉ dùng khi không upload được file: paste URL ảnh từ internet.',
            ),
        ),
    ]
