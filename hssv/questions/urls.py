from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('ask/', views.ask_question, name='ask_question'),
    path('my-questions/', views.my_questions, name='my_questions'),
    path('question/<int:pk>/', views.question_detail, name='question_detail'),
    path('search/', views.search_questions, name='search_questions'),
    path('cau-hoi-thuong-gap/', views.popular_questions, name='popular_questions'),
    path('category/<int:category_id>/', views.category_questions, name='category_questions'),
    path('major/<int:major_id>/', views.major_questions, name='major_questions'),
    path('advisors/', views.advisor_list, name='advisor_list'),
] 