from django.urls import path
from .views import (
    HomeView, LotDetailView, CreateLotView, EditLotView
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('lot/<int:pk>/', LotDetailView.as_view(), name='lot_detail'),
    path('create_lot/', CreateLotView.as_view(), name='create_lot'),
    path('edit_lot/<int:pk>/', EditLotView.as_view(), name='edit_lot'),
]