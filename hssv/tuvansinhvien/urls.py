"""
URL configuration for tuvansinhvien project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

# View để chuyển hướng từ /admin sang trang admin panel
@login_required
def admin_redirect(request):
    return redirect('admin_dashboard')

urlpatterns = [
    path('django-admin/', admin.site.urls),  # Đổi tên đường dẫn admin mặc định của Django
    path('admin/', admin_redirect, name='admin_redirect'),  # Thêm đường dẫn /admin để chuyển hướng
    path('', include('questions.urls')),
    path('accounts/', include('accounts.urls')),
    path('admin-panel/', include('admin_panel.urls')),
    path('stats/', include('stats.urls')),
    path('chatbot/', include('chatbot.urls')),
    path('news/', include('news.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
