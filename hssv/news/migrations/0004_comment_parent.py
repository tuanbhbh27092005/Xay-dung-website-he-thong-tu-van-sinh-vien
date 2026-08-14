from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0003_thumbnail_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='parent',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name='replies',
                to='news.comment',
                verbose_name='Bình luận gốc',
                help_text='Nếu là reply: trỏ tới comment cha. Null = comment gốc trên bài.',
            ),
        ),
    ]
