from django.urls import path
from . import views

urlpatterns = [
    path('', views.journey_list, name='journey_list'),
    path('add/', views.journey_create, name='journey_create'),
    path('edit/<int:id>/', views.journey_update, name='journey_update'),
    path('delete/<int:id>/', views.journey_delete, name='journey_delete'),
]
