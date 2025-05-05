from django.urls import path
from django.views.generic import TemplateView
from .views import (
    MyLoginView, EmailVerify, Register,
    ProfileView, ParticipationHistoryView, WinHistoryView, UserLotsView,
    MyLogoutView, MyPasswordResetView, MyPasswordResetDoneView,
    MyPasswordResetConfirmView, MyPasswordResetCompleteView,
    MyPasswordChangeView, MyPasswordChangeDoneView
)

urlpatterns = [
    path('login/', MyLoginView.as_view(), name='login'),
    path('logout/', MyLogoutView.as_view(), name='logout'),
    path('password_reset/', MyPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', MyPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', MyPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', MyPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('password_change/', MyPasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', MyPasswordChangeDoneView.as_view(), name='password_change_done'),
    path(
        'invalid_verify/',
        TemplateView.as_view(template_name='users/registration/invalid_verify.html'),
        name='invalid_verify'
    ),
    path(
        'verify_email/<uidb64>/<token>/',
        EmailVerify.as_view(),
        name='verify_email',
    ),
    path(
        'confirm_email/',
        TemplateView.as_view(template_name='users/registration/confirm_email.html'),
        name='confirm_email'
    ),
    path('register/', Register.as_view(), name='register'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('participation_history/', ParticipationHistoryView.as_view(), name='participation_history'),
    path('win_history/', WinHistoryView.as_view(), name='win_history'),
    path('user_lots/', UserLotsView.as_view(), name='user_lots'),
]