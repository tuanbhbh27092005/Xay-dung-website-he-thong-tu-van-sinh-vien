from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_staff')
    list_filter = ('user_type', 'is_staff', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ('Thông tin bổ sung', {'fields': ('user_type', 'student_id', 'graduation_year', 'phone_number', 'grade')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Thông tin bổ sung', {'fields': ('user_type', 'student_id', 'graduation_year', 'phone_number', 'grade')}),
    )
    search_fields = ('username', 'email', 'first_name', 'last_name', 'student_id')

admin.site.register(CustomUser, CustomUserAdmin)
