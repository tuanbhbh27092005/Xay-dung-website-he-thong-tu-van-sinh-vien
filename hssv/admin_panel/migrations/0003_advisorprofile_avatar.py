from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0002_advisorprofile_academic_title_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='advisorprofile',
            name='avatar',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='advisors/',
                verbose_name='Ảnh đại diện',
                help_text='Ảnh JPEG/PNG, hình vuông sẽ đẹp nhất. Tối đa ~3 MB.',
            ),
        ),
    ]
