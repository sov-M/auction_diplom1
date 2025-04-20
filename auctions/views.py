#auctions/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from .models import Lot, Bid, Comment
from .forms import LotForm, BidForm, CommentForm
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q


class HomeView(View):
    def get(self, request):
        latest_lots = Lot.objects.filter(is_active=True).order_by('-created_at')[:7]
        other_lots = Lot.objects.filter(is_active=True).order_by('-created_at')[7:]
        return render(request, 'auctions/home.html', {
            'latest_lots': latest_lots,
            'other_lots': other_lots,
        })


class LotDetailView(View):
    def get(self, request, pk):
        lot = get_object_or_404(Lot, pk=pk)
        bid_form = BidForm(lot=lot) if request.user.is_authenticated else None
        comment_form = CommentForm() if request.user.is_authenticated else None
        return render(request, 'auctions/lot_detail.html', {
            'lot': lot,
            'bid_form': bid_form,
            'comment_form': comment_form,
        })

    def post(self, request, pk):
        lot = get_object_or_404(Lot, pk=pk)
        if not request.user.is_authenticated:
            messages.error(request, "Авторизуйтесь, чтобы сделать ставку или оставить комментарий.")
            return redirect('login')

        if 'bid' in request.POST:
            bid_form = BidForm(request.POST, lot=lot)
            if bid_form.is_valid():
                if lot.is_auction_ended():
                    messages.error(request, "Аукцион завершен.")
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
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.user = request.user
                comment.lot = lot
                comment.save()
                messages.success(request, "Комментарий добавлен.")
                return redirect('lot_detail', pk=lot.pk)

        return render(request, 'auctions/lot_detail.html', {
            'lot': lot,
            'bid_form': BidForm(lot=lot),
            'comment_form': CommentForm(),
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
        active_lots = participated_lots.filter(is_active=True)
        return render(request, 'auctions/participation_history.html', {
            'active_lots': active_lots,
            'participated_lots': participated_lots,
        })


class WinHistoryView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        won_lots = Lot.objects.filter(bids__user=user, is_active=False).filter(bids__amount__in=Lot.objects.filter(is_active=False).values('current_price')).distinct()
        top_five_lots = Lot.objects.filter(bids__user=user).filter(bids__in=Bid.objects.order_by('-amount')[:5]).distinct()
        return render(request, 'auctions/win_history.html', {
            'won_lots': won_lots,
            'top_five_lots': top_five_lots,
        })


class UserLotsView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        active_lots = Lot.objects.filter(created_by=user, is_active=True)
        finished_lots = Lot.objects.filter(created_by=user, is_active=False)
        recent_bidders = {}
        for lot in finished_lots:
            recent_bidders[lot.pk] = lot.bids.order_by('-created_at').select_related('user')[:5]
        return render(request, 'auctions/user_lots.html', {
            'active_lots': active_lots,
            'finished_lots': finished_lots,
            'recent_bidders': recent_bidders,
        })