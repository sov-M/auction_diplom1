#auctions/urls.py

from django.urls import path
from .views import (
    HomeView, LotDetailView, CreateLotView, ProfileView,
    ParticipationHistoryView, WinHistoryView, UserLotsView, EditLotView
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('lot/<int:pk>/', LotDetailView.as_view(), name='lot_detail'),
    path('create_lot/', CreateLotView.as_view(), name='create_lot'),
    path('edit_lot/<int:pk>/', EditLotView.as_view(), name='edit_lot'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('participation_history/', ParticipationHistoryView.as_view(), name='participation_history'),
    path('win_history/', WinHistoryView.as_view(), name='win_history'),
    path('user_lots/', UserLotsView.as_view(), name='user_lots'),
]