from django.urls import path
from . import views

urlpatterns = [
    path('', views.statistics_dashboard, name='statistics_dashboard'),
    path('department/<int:pk>/', views.department_statistics, name='department_statistics'),
] 