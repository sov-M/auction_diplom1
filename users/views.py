from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.utils.http import urlsafe_base64_decode
from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.tokens import default_token_generator as token_generator
from users.forms import UserCreationForm, AuthenticationForm
from users.utils import send_email_for_verify
from django.contrib import messages
from auctions.models import Lot, Bid, Comment  # Импорт моделей из auctions
from django.db.models import Sum, Count, Max
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView, PasswordChangeView, PasswordChangeDoneView


User = get_user_model()


class MyLoginView(LoginView):
    form_class = AuthenticationForm
    template_name = 'users/registration/login.html'  # Указываем правильный путь к шаблону



class EmailVerify(View):
    def get(self, request, uidb64, token):
        user = self.get_user(uidb64)
        if user is not None and token_generator.check_token(user, token):
            user.email_verify = True
            user.save()
            login(request, user)
            return redirect('home')
        return redirect('invalid_verify')

    @staticmethod
    def get_user(uidb64):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist, ValidationError):
            user = None
        return user


class Register(View):
    template_name = 'users/registration/register.html'

    def get(self, request):
        context = {
            'form': UserCreationForm()
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password1')
            user = authenticate(email=email, password=password)
            send_email_for_verify(request, user)
            return redirect('confirm_email')
        context = {
            'form': form
        }
        return render(request, self.template_name, context)


class ProfileView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        # Статистика
        total_lots = Lot.objects.filter(created_by=user).count()
        active_lots = Lot.objects.filter(created_by=user, is_active=True, auction_end__gt=timezone.now()).count()
        finished_lots = Lot.objects.filter(created_by=user, auction_end__lte=timezone.now()).count()
        total_bids = Bid.objects.filter(user=user).count()
        won_lots = Lot.objects.filter(
            bids__user=user,
            auction_end__lt=timezone.now(),
            current_price__in=Bid.objects.filter(user=user).values('amount')
        ).distinct().count()
        total_spent = Bid.objects.filter(
            user=user,
            lot__auction_end__lt=timezone.now(),
            amount__in=Lot.objects.filter(bids__user=user).values('current_price')
        ).aggregate(total=Sum('amount'))['total'] or 0
        total_comments = Comment.objects.filter(user=user).count()
        participated_lots = Lot.objects.filter(bids__user=user).distinct().count()

        return render(request, 'users/profile.html', {
            'user': user,
            'stats': {
                'total_lots': total_lots,
                'active_lots': active_lots,
                'finished_lots': finished_lots,
                'total_bids': total_bids,
                'won_lots': won_lots,
                'total_spent': total_spent,
                'total_comments': total_comments,
                'participated_lots': participated_lots,
            }
        })

    def post(self, request):
        user = request.user
        if 'update_bio' in request.POST:
            bio = request.POST.get('bio')
            user.bio = bio
            user.save()
            messages.success(request, "Профиль обновлен.")
        return redirect('profile')


class ParticipationHistoryView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        participated_lots = Lot.objects.filter(bids__user=user).distinct()
        active_lots = participated_lots.filter(auction_end__gt=timezone.now())

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'active_lots': [
                    {
                        'id': lot.id,
                        'title': lot.title,
                        'current_price': float(lot.current_price) if lot.current_price else None,
                    } for lot in active_lots
                ],
                'participated_lots': [
                    {
                        'id': lot.id,
                        'title': lot.title,
                        'is_active': lot.is_active,
                    } for lot in participated_lots
                ]
            })

        return render(request, 'users/participation_history.html', {
            'active_lots': active_lots,
            'participated_lots': participated_lots,
        })


class WinHistoryView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        won_lots = Lot.objects.filter(
            bids__user=user,
            auction_end__lt=timezone.now(),
            current_price__in=Bid.objects.filter(user=user).values('amount')
        ).distinct()
        top_three_lots = Lot.objects.filter(bids__user=user).filter(bids__in=Bid.objects.order_by('-amount')[:3]).distinct()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'won_lots': [
                    {
                        'id': lot.id,
                        'title': lot.title,
                        'current_price': float(lot.current_price) if lot.current_price else None,
                    } for lot in won_lots
                ],
                'top_three_lots': [
                    {
                        'id': lot.id,
                        'title': lot.title,
                        'current_price': float(lot.current_price) if lot.current_price else None,
                    } for lot in top_three_lots
                ]
            })

        return render(request, 'users/win_history.html', {
            'won_lots': won_lots,
            'top_three_lots': top_three_lots,
        })


class UserLotsView(LoginRequiredMixin, View):
    def get(self, request):
        active_lots = Lot.objects.filter(created_by=request.user, auction_end__gt=timezone.now()).order_by('-created_at')
        finished_lots = Lot.objects.filter(created_by=request.user, auction_end__lte=timezone.now()).order_by('-created_at')

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            finished_lots_data = []
            for lot in finished_lots:
                unique_bidders = lot.bids.values('user__username', 'user__email').annotate(max_amount=Max('amount')).order_by('-max_amount')[:3]
                finished_lots_data.append({
                    'title': lot.title,
                    'id': lot.id,
                    'current_price': float(lot.current_price) if lot.current_price else None,
                    'unique_bidders': [
                        {
                            'username': bidder['user__username'],
                            'email': bidder['user__email'],
                            'amount': float(bidder['max_amount'])
                        }
                        for bidder in unique_bidders
                    ],
                    'views': lot.views,
                    'bids_count': lot.bids.count(),
                    'unique_bidders_count': lot.bids.values('user').distinct().count(),
                    'comments_count': lot.comments.count(),
                })

            return JsonResponse({
                'active_lots': [
                    {
                        'title': lot.title,
                        'id': lot.id,
                        'current_price': float(lot.current_price) if lot.current_price else None,
                        'views': lot.views,
                        'bids_count': lot.bids.count(),
                        'unique_bidders_count': lot.bids.values('user').distinct().count(),
                        'comments_count': lot.comments.count(),
                    } for lot in active_lots
                ],
                'finished_lots': finished_lots_data
            })

        active_lots_with_stats = []
        for lot in active_lots:
            active_lots_with_stats.append({
                'lot': lot,
                'stats': {
                    'views': lot.views,
                    'bids_count': lot.bids.count(),
                    'unique_bidders_count': lot.bids.values('user').distinct().count(),
                    'comments_count': lot.comments.count(),
                }
            })

        finished_lots_with_bidders = []
        for lot in finished_lots:
            unique_bidders = lot.bids.values('user__username', 'user__email').annotate(max_amount=Max('amount')).order_by('-max_amount')[:3]
            finished_lots_with_bidders.append({
                'lot': lot,
                'unique_bidders': unique_bidders,
                'stats': {
                    'views': lot.views,
                    'bids_count': lot.bids.count(),
                    'unique_bidders_count': lot.bids.values('user').distinct().count(),
                    'comments_count': lot.comments.count(),
                }
            })

        return render(request, 'users/user_lots.html', {
            'active_lots': active_lots_with_stats,
            'finished_lots': finished_lots_with_bidders,
        })

    def post(self, request):
        if 'cancel_lot' in request.POST:
            lot_id = request.POST.get('lot_id')
            lot = get_object_or_404(Lot, pk=lot_id, created_by=request.user)
            if lot.has_bids():
                messages.error(request, "Нельзя отменить лот, на который уже сделаны ставки.")
            else:
                lot.delete()
                messages.success(request, "Лот успешно отменен.")
        return redirect('user_lots')
    
class MyLogoutView(LogoutView):
    template_name = 'users/registration/logged_out.html'

class MyPasswordResetView(PasswordResetView):
    template_name = 'users/registration/password_reset_form.html'

class MyPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'users/registration/password_reset_done.html'

class MyPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'users/registration/password_reset_confirm.html'

class MyPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'users/registration/password_reset_complete.html'

class MyPasswordChangeView(PasswordChangeView):
    template_name = 'users/registration/password_change_form.html'

class MyPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = 'users/registration/password_change_done.html'