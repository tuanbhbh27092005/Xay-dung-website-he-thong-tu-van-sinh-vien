from django.contrib import admin
from .models import ChatSession, ChatMessage, QuestionEmbedding, NewsEmbedding


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'started_at', 'escalated_to_advisor', 'message_count')
    list_filter = ('escalated_to_advisor', 'started_at')
    search_fields = ('user__username', 'session_key')
    readonly_fields = ('session_key', 'started_at')
    date_hierarchy = 'started_at'

    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = "Số tin nhắn"


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'session', 'role', 'short_content',
        'confidence', 'needs_advisor', 'created_at',
    )
    list_filter = ('role', 'needs_advisor', 'created_at')
    search_fields = ('content', 'session__user__username')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    def short_content(self, obj):
        return obj.content[:80] + ('...' if len(obj.content) > 80 else '')
    short_content.short_description = "Nội dung"


@admin.register(QuestionEmbedding)
class QuestionEmbeddingAdmin(admin.ModelAdmin):
    list_display = ('question', 'updated_at', 'embedding_dim')
    readonly_fields = ('embedding', 'updated_at')
    search_fields = ('question__title',)

    def embedding_dim(self, obj):
        try:
            return f"{len(obj.embedding)} chiều"
        except (TypeError, AttributeError):
            return "—"
    embedding_dim.short_description = "Kích thước vector"


@admin.register(NewsEmbedding)
class NewsEmbeddingAdmin(admin.ModelAdmin):
    list_display = ('news', 'updated_at', 'embedding_dim')
    readonly_fields = ('embedding', 'updated_at')
    search_fields = ('news__title',)

    def embedding_dim(self, obj):
        try:
            return f"{len(obj.embedding)} chiều"
        except (TypeError, AttributeError):
            return "—"
    embedding_dim.short_description = "Kích thước vector"
