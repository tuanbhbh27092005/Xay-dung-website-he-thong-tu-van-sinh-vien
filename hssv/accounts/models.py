from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('student', 'Sinh viên'),
        ('alumni', 'Cựu sinh viên'),
        ('parent', 'Phụ huynh'),
        ('high_school', 'Học sinh phổ thông'),
    )
    
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    student_id = models.CharField(max_length=20, blank=True, null=True)
    graduation_year = models.IntegerField(blank=True, null=True)  # Cho cựu sinh viên
    phone_number = models.CharField(max_length=15, blank=True, null=True)  # Cho phụ huynh
    grade = models.CharField(max_length=10, blank=True, null=True)  # Cho học sinh phổ thông
