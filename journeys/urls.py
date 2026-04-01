from django.urls import path
from . import views

urlpatterns = [
    # Journeys
    path('', views.journey_list, name='journey_list'),
    path('create/', views.journey_create, name='journey_create'),
    path('<int:id>/', views.journey_detail, name='journey_detail'),
    path('update/<int:id>/', views.journey_update, name='journey_update'),
    path('delete/<int:id>/', views.journey_delete, name='journey_delete'),
    
    # Consultations
    path('consultations/', views.available_consultations, name='available_consultations'),
    path('consultations/book/<int:slot_id>/', views.book_consultation, name='book_consultation'),
    path('consultations/mine/', views.my_appointments, name='my_appointments'),
    path('<int:journey_id>/expenses/', views.expense_tracker, name='expense_tracker'),
    path('<int:journey_id>/expenses/delete/<str:expense_date>/', views.expense_delete, name='expense_delete'),
    path('surprise-me/', views.surprise_me, name='surprise_me'),
    path('surprise-me/save/', views.save_inspiration, name='save_inspiration'),
    path('journey/<int:id>/upload/', views.upload_media, name='upload_media'),
    path('journey/<int:id>/media/<int:media_id>/delete/', views.delete_media, name='delete_media'),
]