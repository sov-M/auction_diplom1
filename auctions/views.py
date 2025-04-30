#auctions/views.py

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
from django.http import JsonResponse
import json

class HomeView(View):
    def get(self, request):
        all_lots = Lot.objects.all().order_by('-created_at')
        latest_lots = all_lots[:3]
        other_lots = all_lots[3:]

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'latest_lots': [
                    {
                        'id': lot.id,
                        'title': lot.title,
                        'main_image': lot.main_image.url if lot.main_image else None,
                        'initial_price': float(lot.initial_price),
                        'current_price': float(lot.current_price) if lot.current_price else None,
                        'is_auction_ended': lot.is_auction_ended(),
                        'time_until': lot.auction_end.isoformat() if not lot.is_auction_ended() else '',  # Передаем ISO-строку
                        'last_bidder': lot.bids.first().user.username if lot.bids.exists() else None
                    } for lot in latest_lots
                ],
                'other_lots': [
                    {
                        'id': lot.id,
                        'title': lot.title,
                        'main_image': lot.main_image.url if lot.main_image else None,
                        'initial_price': float(lot.initial_price),
                        'current_price': float(lot.current_price) if lot.current_price else None,
                        'is_auction_ended': lot.is_auction_ended(),
                        'time_until': lot.auction_end.isoformat() if not lot.is_auction_ended() else ''  # Передаем ISO-строку
                    } for lot in other_lots
                ]
            })

        return render(request, 'auctions/home.html', {
            'latest_lots': latest_lots,
            'other_lots': other_lots,
        })

class LotDetailView(View):
    def get(self, request, pk):
        lot = get_object_or_404(Lot.objects.prefetch_related('bids__user', 'comments__user'), pk=pk)
        is_author = request.user.is_authenticated and lot.created_by == request.user
        bid_form = BidForm(lot=lot) if request.user.is_authenticated and not is_author else None
        comment_form = CommentForm() if request.user.is_authenticated else None
        unique_bidders = lot.bids.values('user__username').annotate(max_amount=Max('amount')).order_by('-max_amount')[:3]  # Ограничиваем тремя
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            bidders = [
                {'username': bidder['user__username'], 'amount': float(bidder['max_amount'])}
                for bidder in unique_bidders
            ]
            comments = [
                {
                    'content': comment.content,
                    'username': comment.user.username,
                    'created_at': comment.created_at.isoformat()
                }
                for comment in lot.comments.all()
            ]
            return JsonResponse({
                'bidders': bidders,
                'comments': comments,
                'current_price': float(lot.current_price) if lot.current_price else None,
                'is_auction_ended': lot.is_auction_ended(),
            })

        return render(request, 'auctions/lot_detail.html', {
            'lot': lot,
            'bid_form': bid_form,
            'comment_form': comment_form,
            'is_author': is_author,
            'unique_bidders': unique_bidders,
        })

    def post(self, request, pk):
        lot = get_object_or_404(Lot.objects.prefetch_related('bids__user', 'comments__user'), pk=pk)
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

        unique_bidders = lot.bids.values('user__username').annotate(max_amount=Max('amount')).order_by('-max_amount')[:4]  # Ограничиваем тремя
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

        return render(request, 'auctions/win_history.html', {
            'won_lots': won_lots,
            'top_three_lots': top_three_lots,
        })

class UserLotsView(LoginRequiredMixin, View):
    def get(self, request):
        active_lots = Lot.objects.filter(created_by=request.user, auction_end__gt=timezone.now()).order_by('-created_at')
        finished_lots = Lot.objects.filter(created_by=request.user, auction_end__lte=timezone.now()).order_by('-created_at')

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Формируем unique_bidders для каждого завершенного лота
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
                    ]
                })

            return JsonResponse({
                'active_lots': [
                    {
                        'title': lot.title,
                        'id': lot.id,
                        'current_price': float(lot.current_price) if lot.current_price else None,
                    } for lot in active_lots
                ],
                'finished_lots': finished_lots_data
            })

        # Формируем unique_bidders для начального рендеринга
        finished_lots_with_bidders = []
        for lot in finished_lots:
            unique_bidders = lot.bids.values('user__username', 'user__email').annotate(max_amount=Max('amount')).order_by('-max_amount')[:3]
            finished_lots_with_bidders.append({
                'lot': lot,
                'unique_bidders': unique_bidders
            })

        return render(request, 'auctions/user_lots.html', {
            'active_lots': active_lots,
            'finished_lots': finished_lots_with_bidders,
        })