#auctions/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from .models import Lot, Bid, Comment
from .forms import LotForm, BidForm, CommentForm
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q, Max, Count
from datetime import timedelta
from django.http import JsonResponse
import json

class HomeView(View):
    def get(self, request):
        # По умолчанию берём все лоты
        lots = Lot.objects.all()
        print(f"Initial lots: {lots.count()}")  # Отладка: общее количество лотов

        # Фильтрация
        search_query = request.GET.get('search', '')
        category = request.GET.get('category', '')
        tag = request.GET.get('tag', '')
        condition = request.GET.get('condition', '')
        location = request.GET.get('location', '')
        sort_by = request.GET.get('sort_by', '')
        expiring_soon = request.GET.get('expiring_soon', '')
        active_only = request.GET.get('active_only', '')

        # Логирование для отладки
        print(f"Filters: search={search_query}, category={category}, tag={tag}, condition={condition}, location={location}, sort_by={sort_by}, expiring_soon={expiring_soon}, active_only={active_only}")
        print(f"Categories: {Lot.CATEGORY_CHOICES}")
        print(f"Conditions: {Lot.CONDITION_CHOICES}")

        # Проверка, применены ли фильтры
        filters_applied = any([
            search_query,
            category,
            tag,
            condition,
            location,
            sort_by,
            expiring_soon,
            active_only
        ])

        # Фильтр для активных лотов
        if active_only:
            lots = lots.filter(is_active=True, auction_end__gt=timezone.now())
            print(f"After active_only filter: {lots.count()}")

        # Поиск по названию
        if search_query:
            lots = lots.filter(Q(title__icontains=search_query))
            print(f"After search filter: {lots.count()}")

        # Фильтр по категории
        if category:
            lots = lots.filter(category=category)
            print(f"After category filter: {lots.count()}")

        # Фильтр по тегу
        if tag:
            lots = lots.filter(tags__icontains=tag)
            print(f"After tag filter: {lots.count()}")

        # Фильтр по состоянию
        if condition:
            lots = lots.filter(condition=condition)
            print(f"After condition filter: {lots.count()}")

        # Фильтр по местоположению (страна или город)
        if location:
            lots = lots.filter(
                Q(location_country__icontains=location) | Q(location_city__icontains=location)
            )
            print(f"After location filter: {lots.count()}")

        # Фильтр по лотам, заканчивающимся в течение 24 часов
        if expiring_soon:
            lots = lots.filter(
                auction_end__lte=timezone.now() + timedelta(hours=24)
            )
            print(f"After expiring_soon filter: {lots.count()}")

        # Сортировка
        if sort_by == 'price_desc':
            lots = lots.order_by('-current_price', '-initial_price')
        elif sort_by == 'price_asc':
            lots = lots.order_by('current_price', 'initial_price')
        elif sort_by == 'date_desc':
            lots = lots.order_by('-created_at')
        elif sort_by == 'date_asc':
            lots = lots.order_by('created_at')
        elif sort_by == 'views_desc':
            lots = lots.order_by('-views')
        elif sort_by == 'views_asc':
            lots = lots.order_by('views')
        elif sort_by == 'bids_desc':
            lots = lots.annotate(bid_count=Count('bids')).order_by('-bid_count')
        elif sort_by == 'bids_asc':
            lots = lots.annotate(bid_count=Count('bids')).order_by('bid_count')
        else:
            lots = lots.order_by('-created_at')  # По умолчанию

        # Разделение на последние 3 и остальные, если фильтры НЕ применены
        if not filters_applied:
            latest_lots = lots[:3]
            other_lots = lots[3:]
            print(f"Latest lots: {latest_lots.count()}, Other lots: {other_lots.count()}")
        else:
            latest_lots = None  # Не используем разделение
            other_lots = None
            print(f"Filtered lots: {lots.count()}")

        # Подготовка данных для AJAX
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            if filters_applied:
                return JsonResponse({
                    'lots': [
                        {
                            'id': lot.id,
                            'title': lot.title,
                            'main_image': lot.main_image.url if lot.main_image else None,
                            'initial_price': float(lot.initial_price),
                            'current_price': float(lot.current_price) if lot.current_price else None,
                            'is_auction_ended': lot.is_auction_ended(),
                            'time_until': lot.auction_end.isoformat() if not lot.is_auction_ended() else '',
                            'views': lot.views,
                        } for lot in lots
                    ]
                })
            else:
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
                            'last_bidder': lot.bids.first().user.username if lot.bids.exists() else None,
                            'views': lot.views,
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
                            'time_until': lot.auction_end.isoformat() if not lot.is_auction_ended() else '',
                            'views': lot.views,
                        } for lot in other_lots
                    ]
                })

        # Данные для формы фильтрации
        categories = Lot.CATEGORY_CHOICES
        conditions = Lot.CONDITION_CHOICES

        return render(request, 'auctions/home.html', {
            'lots': lots if filters_applied else None,
            'latest_lots': latest_lots if not filters_applied else None,
            'other_lots': other_lots if not filters_applied else None,
            'categories': categories,
            'conditions': conditions,
            'search_query': search_query,
            'selected_category': category,
            'selected_condition': condition,
            'selected_tag': tag,
            'selected_location': location,
            'sort_by': sort_by,
            'expiring_soon': expiring_soon,
            'active_only': active_only,
            'filters_applied': filters_applied,
        })
        
class LotDetailView(View):
    def get(self, request, pk):
        lot = get_object_or_404(Lot.objects.prefetch_related('bids__user', 'comments__user'), pk=pk)
        is_author = request.user.is_authenticated and lot.created_by == request.user
        bid_form = BidForm(lot=lot) if request.user.is_authenticated and not is_author else None
        comment_form = CommentForm() if request.user.is_authenticated else None
        unique_bidders = lot.bids.values('user__username').annotate(max_amount=Max('amount')).order_by('-max_amount')[:3]

        # Увеличиваем количество просмотров
        lot.views += 1
        lot.save()

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

class CreateLotView(LoginRequiredMixin, View):
    def get(self, request):
        form = LotForm()
        return render(request, 'auctions/create_lot.html', {'form': form})

    def post(self, request):
        # Проверка на максимум 3 активных лота
        active_lots_count = Lot.objects.filter(
            created_by=request.user,
            is_active=True,
            auction_end__gt=timezone.now()
        ).count()
        if active_lots_count >= 3:
            messages.error(request, "Вы не можете иметь более 3 активных лотов одновременно.")
            return render(request, 'auctions/create_lot.html', {'form': LotForm()})

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