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
        # Получаем только активные лоты (где is_active=True)
        active_lots = Lot.objects.filter(is_active=True).order_by('-created_at')
        # Разделяем на последние 3 и остальные
        latest_lots = active_lots[:3]
        other_lots = active_lots[3:]

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
                        'time_until': lot.auction_end.isoformat() if not lot.is_auction_ended() else '',
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
                        'time_until': lot.auction_end.isoformat() if not lot.is_auction_ended() else ''
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
        unique_bidders = lot.bids.values('user__username').annotate(max_amount=Max('amount')).order_by('-max_amount')[:3]

        # Формируем строку местоположения
        location = "Не указано"
        if lot.location_country or lot.location_city:
            location = lot.location_country
            if lot.location_country and lot.location_city:
                location += ", " + lot.location_city
            elif lot.location_city:
                location = lot.location_city

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
            'location': location,
            'bid_form': bid_form,
            'comment_form': comment_form,
            'is_author': is_author,
            'unique_bidders': unique_bidders,
        })

    def post(self, request, pk):
        lot = get_object_or_404(Lot, pk=pk)
        is_author = request.user.is_authenticated and lot.created_by == request.user

        if not request.user.is_authenticated:
            messages.error(request, "Авторизуйтесь, чтобы сделать ставку или оставить комментарий.")
            return redirect('login')
        
        if 'cancel_lot' in request.POST and is_author:
            if lot.has_bids():
                messages.error(request, "Нельзя отменить лот, на который уже сделаны ставки.")
            else:
                lot.delete()  # Удаляем лот
                messages.success(request, "Лот успешно отменен.")
            return redirect('user_lots')

        if is_author and 'bid' in request.POST:
            messages.error(request, "Вы не можете делать ставки на свой лот.")
            return redirect('lot_detail', pk=lot.pk)

        if lot.is_auction_ended():
            messages.error(request, "Аукцион завершён, действия больше не доступны.")
            return redirect('lot_detail', pk=pk)

        if 'bid' in request.POST:
            if is_author:
                messages.error(request, "Вы не можете делать ставки на свой лот.")
                return redirect('lot_detail', pk=pk)
            bid_form = BidForm(request.POST, lot=lot)
            if bid_form.is_valid():
                bid = bid_form.save(commit=False)
                bid.user = request.user
                bid.lot = lot
                bid.save()
                lot.current_price = bid.amount
                lot.save()
                messages.success(request, "Ваша ставка успешно принята.")
            else:
                messages.error(request, "Ошибка в ставке. Проверьте введённую сумму.")
            return redirect('lot_detail', pk=pk)

        if 'comment' in request.POST:
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.user = request.user
                comment.lot = lot
                comment.save()
                messages.success(request, "Комментарий успешно добавлен.")
            else:
                messages.error(request, "Ошибка в комментарии. Проверьте введённые данные.")
            return redirect('lot_detail', pk=pk)

        return redirect('lot_detail', pk=pk)

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

class EditLotView(LoginRequiredMixin, View):
    def get(self, request, pk):
        lot = get_object_or_404(Lot, pk=pk, created_by=request.user)
        if lot.has_bids():
            messages.error(request, "Нельзя редактировать лот, на который уже сделаны ставки.")
            return redirect('lot_detail', pk=lot.pk)
        form = LotForm(instance=lot)
        return render(request, 'auctions/edit_lot.html', {'form': form, 'lot': lot})

    def post(self, request, pk):
        lot = get_object_or_404(Lot, pk=pk, created_by=request.user)
        if lot.has_bids():
            messages.error(request, "Нельзя редактировать лот, на который уже сделаны ставки.")
            return redirect('lot_detail', pk=lot.pk)
        form = LotForm(request.POST, request.FILES, instance=lot)
        if form.is_valid():
            form.save()
            messages.success(request, "Лот успешно отредактирован.")
            return redirect('lot_detail', pk=lot.pk)
        return render(request, 'auctions/edit_lot.html', {'form': form, 'lot': lot})

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