from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('questions/', views.manage_questions, name='manage_questions'),
    path('questions/<int:pk>/answer/', views.answer_question, name='answer_question'),
    path('questions/<int:pk>/edit/', views.edit_question, name='edit_question'),
    path('questions/<int:pk>/delete/', views.delete_question, name='delete_question'),
    
    path('departments/', views.manage_departments, name='manage_departments'),
    path('departments/<int:pk>/edit/', views.edit_department, name='edit_department'),
    path('departments/<int:pk>/delete/', views.delete_department, name='delete_department'),
    
    path('majors/', views.manage_majors, name='manage_majors'),
    path('majors/<int:pk>/edit/', views.edit_major, name='edit_major'),
    path('majors/<int:pk>/delete/', views.delete_major, name='delete_major'),
    
    path('categories/', views.manage_categories, name='manage_categories'),
    path('categories/<int:pk>/edit/', views.edit_category, name='edit_category'),
    path('categories/<int:pk>/delete/', views.delete_category, name='delete_category'),
    
    path('advisors/', views.manage_advisors, name='manage_advisors'),
    path('advisors/handbook/', views.advisor_handbook, name='advisor_handbook'),
    path('advisors/<int:pk>/edit/', views.edit_advisor, name='edit_advisor'),
    path('advisors/<int:pk>/delete/', views.delete_advisor, name='delete_advisor'),

    # Content moderation
    path('moderation/', views.moderation_queue, name='moderation_queue'),
    path('moderation/<int:report_id>/action/', views.moderation_action, name='moderation_action'),
]
