from django.contrib import admin
from .models import AdvisorProfile

@admin.register(AdvisorProfile)
class AdvisorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'role')
    list_filter = ('role', 'department')
    search_fields = ('user__username', 'user__email')
