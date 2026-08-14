from django.contrib import admin
from .models import Department, Major, QuestionCategory, Question, Answer

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Major)
class MajorAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'description')
    list_filter = ('department',)
    search_fields = ('name',)

@admin.register(QuestionCategory)
class QuestionCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'major', 'category', 'status', 'created_at')
    list_filter = ('status', 'major', 'category', 'created_at')
    search_fields = ('title', 'content', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [AnswerInline]

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content', 'user__username', 'question__title')
    readonly_fields = ('created_at', 'updated_at')
