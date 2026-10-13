from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    # Giao diện phía Sinh viên / Public
    path('', views.advisor_booking_list, name='advisor_list'),
    path('book/<int:advisor_id>/', views.book_advisor_slot, name='book_slot'),
    path('my-appointments/', views.student_appointment_list, name='student_appointments'),
    path('cancel/<int:appointment_id>/', views.cancel_appointment, name='cancel_appointment'),

    # Giao diện phía Cố vấn học tập (Advisor Panel)
    path('manage/', views.advisor_manage_appointments, name='manage_appointments'),
    path('manage/<int:appointment_id>/update/', views.advisor_update_appointment, name='update_appointment'),
    path('manage/schedules/', views.advisor_schedule_settings, name='schedule_settings'),
    path('manage/schedules/<int:schedule_id>/delete/', views.delete_advisor_schedule, name='delete_schedule'),
]
