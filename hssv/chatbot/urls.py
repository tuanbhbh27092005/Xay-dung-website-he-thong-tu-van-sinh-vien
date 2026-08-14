from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('', views.chat_page, name='chat'),
    path('api/send/', views.send_message, name='send_message'),
    path('api/reset/', views.reset_session, name='reset_session'),
    path('api/filters/', views.filter_options, name='filter_options'),
    path('history/', views.chat_history_list, name='history'),
    path('history/<int:session_id>/', views.chat_history_detail, name='history_detail'),
    path('history/<int:session_id>/delete/', views.chat_history_delete, name='history_delete'),
]
