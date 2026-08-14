from django.contrib import admin
from .models import News, Comment


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'department', 'author', 'is_published', 'views_count', 'created_at')
    list_filter = ('category', 'is_published', 'department', 'created_at')
    search_fields = ('title', 'content', 'summary')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'created_at'
    readonly_fields = ('views_count', 'created_at', 'updated_at')

    fieldsets = (
        ('Nội dung', {
            'fields': ('title', 'slug', 'category', 'department', 'thumbnail_url', 'summary', 'content'),
        }),
        ('Cấu hình', {
            'fields': ('author', 'is_published'),
        }),
        ('Thống kê (tự động)', {
            'classes': ('collapse',),
            'fields': ('views_count', 'created_at', 'updated_at'),
        }),
    )


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'news', 'user', 'short_content', 'is_hidden', 'has_sensitive', 'created_at')
    list_filter = ('is_hidden', 'has_sensitive', 'created_at')
    search_fields = ('content', 'user__username', 'news__title')
    readonly_fields = ('created_at',)
    actions = ['hide_selected', 'unhide_selected']

    def short_content(self, obj):
        return obj.content[:60] + ('...' if len(obj.content) > 60 else '')
    short_content.short_description = "Nội dung"

    @admin.action(description="Ẩn các bình luận đã chọn")
    def hide_selected(self, request, queryset):
        n = queryset.update(is_hidden=True)
        self.message_user(request, f"Đã ẩn {n} bình luận.")

    @admin.action(description="Hiện lại các bình luận đã chọn")
    def unhide_selected(self, request, queryset):
        n = queryset.update(is_hidden=False)
        self.message_user(request, f"Đã hiện lại {n} bình luận.")
