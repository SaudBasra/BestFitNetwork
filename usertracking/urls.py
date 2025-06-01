from django.urls import path
from . import views

app_name = 'usertracking'

urlpatterns = [
    path('submit/', views.submit_user_tracking, name='submit_user_tracking'),
    path('dashboard/', views.user_tracking_dashboard, name='dashboard'),
    path('toggle-status/<int:tracking_id>/', views.toggle_tracking_status, name='toggle_status'),
]