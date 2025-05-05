from django.urls import path, include
from django.views.generic import TemplateView
from .views import (
    MyLoginView, EmailVerify, Register,
    ProfileView, ParticipationHistoryView, WinHistoryView, UserLotsView
)

urlpatterns = [
    path('login/', MyLoginView.as_view(), name='login'),
    path('', include('django.contrib.auth.urls')),
    path(
        'invalid_verify/',
        TemplateView.as_view(template_name='users/invalid_verify.html'),
        name='invalid_verify'
    ),
    path(
        'verify_email/<uidb64>/<token>/',
        EmailVerify.as_view(),
        name='verify_email',
    ),
    path(
        'confirm_email/',
        TemplateView.as_view(template_name='users/confirm_email.html'),
        name='confirm_email'
    ),
    path('register/', Register.as_view(), name='register'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('participation_history/', ParticipationHistoryView.as_view(), name='participation_history'),
    path('win_history/', WinHistoryView.as_view(), name='win_history'),
    path('user_lots/', UserLotsView.as_view(), name='user_lots'),
]