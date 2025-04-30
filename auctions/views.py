from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from .models import Lot, Bid, Comment
from .forms import LotForm, BidForm, CommentForm
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q, Max
from datetime import timedelta


class HomeView(View):
    def get(self, request):
        all_lots = Lot.objects.all().order_by('-created_at')
        latest_lots = all_lots[:7]
        other_lots = all_lots[7:]
        return render(request, 'auctions/home.html', {
            'latest_lots': latest_lots,
            'other_lots': other_lots,
        })

class LotDetailView(View):
    def get(self, request, pk):
        lot = get_object_or_404(Lot.objects.prefetch_related('bids__user'), pk=pk)
        is_author = request.user.is_authenticated and lot.created_by == request.user
        bid_form = BidForm(lot=lot) if request.user.is_authenticated and not is_author else None
        comment_form = CommentForm() if request.user.is_authenticated else None
        # Получаем уникальных участников с их максимальными ставками
        unique_bidders = lot.bids.values('user__username').annotate(max_amount=Max('amount')).order_by('-max_amount')
        return render(request, 'auctions/lot_detail.html', {
            'lot': lot,
            'bid_form': bid_form,
            'comment_form': comment_form,
            'is_author': is_author,
            'unique_bidders': unique_bidders,
        })

    def post(self, request, pk):
        lot = get_object_or_404(Lot.objects.prefetch_related('bids__user'), pk=pk)
        is_author = request.user.is_authenticated and lot.created_by == request.user
        if not request.user.is_authenticated:
            messages.error(request, "Авторизуйтесь, чтобы сделать ставку или оставить комментарий.")
            return redirect('login')

        if is_author and 'bid' in request.POST:
            messages.error(request, "Вы не можете делать ставки на свой лот.")
            return redirect('lot_detail', pk=lot.pk)

        if 'bid' in request.POST:
            bid_form = BidForm(request.POST, lot=lot)
            if bid_form.is_valid():
                if lot.is_auction_ended():
                    messages.error(request, "Аукцион завершен.")
                    return redirect('lot_detail', pk=lot.pk)
                # Проверка, может ли пользователь сделать новую ставку
                last_bid = lot.bids.first()
                if last_bid and last_bid.user == request.user:
                    messages.error(request, "Вы не можете сделать новую ставку, пока другой пользователь не перебьёт вашу.")
                    return redirect('lot_detail', pk=lot.pk)
                bid = bid_form.save(commit=False)
                bid.user = request.user
                bid.lot = lot
                bid.save()
                lot.current_price = bid.amount
                lot.save()
                messages.success(request, "Ставка успешно сделана.")
                return redirect('lot_detail', pk=lot.pk)
        elif 'comment' in request.POST:
            if lot.is_auction_ended():
                messages.error(request, "Комментарии нельзя оставлять после завершения аукциона.")
                return redirect('lot_detail', pk=lot.pk)
            
            # Проверка времени последнего комментария
            if request.user.is_authenticated:
                last_comment = Comment.objects.filter(
                    user=request.user,
                    created_at__gte=timezone.now() - timedelta(minutes=1)
                ).order_by('-created_at').first()
                if last_comment:
                    messages.error(request, "Вы можете оставлять комментарий не чаще одного раза в минуту.")
                    return redirect('lot_detail', pk=lot.pk)

            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.user = request.user
                comment.lot = lot
                comment.save()
                messages.success(request, "Комментарий добавлен.")
                return redirect('lot_detail', pk=lot.pk)

        # Получаем уникальных участников с их максимальными ставками для отображения после POST
        unique_bidders = lot.bids.values('user__username').annotate(max_amount=Max('amount')).order_by('-max_amount')
        return render(request, 'auctions/lot_detail.html', {
            'lot': lot,
            'bid_form': BidForm(lot=lot) if not is_author else None,
            'comment_form': CommentForm(),
            'is_author': is_author,
            'unique_bidders': unique_bidders,
        })

class CreateLotView(LoginRequiredMixin, View):
    def get(self, request):
        form = LotForm()
        return render(request, 'auctions/create_lot.html', {'form': form})

    def post(self, request):
        form = LotForm(request.POST, request.FILES)
        if form.is_valid():
            lot = form.save(commit=False)
            lot.created_by = request.user
            lot.save()
            messages.success(request, "Лот успешно создан.")
            return redirect('home')
        return render(request, 'auctions/create_lot.html', {'form': form})

class ProfileView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        return render(request, 'auctions/profile.html', {'user': user})

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
        return render(request, 'auctions/participation_history.html', {
            'active_lots': active_lots,
            'participated_lots': participated_lots,
        })

class WinHistoryView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        won_lots = Lot.objects.filter(
            bids__user=user,
            auction_end__lt=timezone.now(),
            current_price__in=Lot.objects.filter(bids__user=user).values('bids__amount')
        ).distinct()
        top_three_lots = Lot.objects.filter(bids__user=user).filter(bids__in=Bid.objects.order_by('-amount')[:3]).distinct()
        return render(request, 'auctions/win_history.html', {
            'won_lots': won_lots,
            'top_three_lots': top_three_lots,
        })

class UserLotsView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        active_lots = Lot.objects.filter(created_by=user, auction_end__gt=timezone.now())
        finished_lots = Lot.objects.filter(created_by=user, auction_end__lte=timezone.now())
        recent_bidders = {}
        for lot in finished_lots:
            # Получаем уникальных пользователей
            bids = lot.bids.values('user_id').distinct()[:3]
            user_ids = [bid['user_id'] for bid in bids]
            # Получаем последнюю ставку для каждого пользователя
            recent_bidders[lot.pk] = Bid.objects.filter(
                lot=lot,
                user_id__in=user_ids
            ).order_by('user_id', '-created_at').distinct('user_id')
        return render(request, 'auctions/user_lots.html', {
            'active_lots': active_lots,
            'finished_lots': finished_lots,
            'recent_bidders': recent_bidders,
        })