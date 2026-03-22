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
    path('expenses/', views.expense_tracker, name='expense_tracker'),
    path('expenses/add/', views.expense_add, name='expense_add'),
    path('expenses/delete/<str:expense_id>/', views.expense_delete, name='expense_delete'),
]