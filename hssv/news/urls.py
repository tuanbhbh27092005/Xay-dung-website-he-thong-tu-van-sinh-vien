from django.urls import path
from . import views

app_name = 'news'

urlpatterns = [
    # Public
    path('', views.news_list, name='list'),

    # Manage (cho tư vấn viên + admin) - đặt TRƯỚC <slug:slug> để route đúng
    path('manage/', views.manage_list, name='manage_list'),
    path('manage/new/', views.manage_create, name='manage_create'),
    path('manage/<int:news_id>/edit/', views.manage_edit, name='manage_edit'),
    path('manage/<int:news_id>/delete/', views.manage_delete, name='manage_delete'),
    path('manage/upload-image/', views.upload_inline_image, name='upload_inline_image'),
    path('manage/comment/<int:comment_id>/hide/', views.hide_comment, name='hide_comment'),

    # Detail (catch-all slug, đặt cuối)
    path('<slug:slug>/', views.news_detail, name='detail'),
    path('<slug:slug>/comment/', views.add_comment, name='add_comment'),
    path('<slug:slug>/like/', views.toggle_like, name='toggle_like'),
]
