from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from .models import Lot, Bid, Comment, AutoBid
from .forms import LotForm, BidForm, CommentForm, AutoBidForm
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q, Max, Count
from datetime import timedelta
from django.http import JsonResponse
from django.db import transaction


def process_auto_bids(lot):
    """Обрабатывает автоматические ставки до достижения лимита, постепенно повышая на bid_step."""
    while True:
        auto_bids = lot.auto_bids.filter(max_amount__gt=lot.current_price or 0).order_by('-max_amount', 'created_at')
        current_price = lot.current_price or lot.initial_price
        bid_made = False

        current_leader = lot.bids.order_by('-amount').first()
        current_leader_id = current_leader.user.id if current_leader else None

        for auto_bid in auto_bids:
            if current_leader_id == auto_bid.user.id:
                continue
            if auto_bid.max_amount > current_price:
                new_amount = min(current_price + lot.bid_step, auto_bid.max_amount)
                if new_amount > current_price:
                    with transaction.atomic():
                        Bid.objects.create(
                            lot=lot,
                            user=auto_bid.user,
                            amount=new_amount,
                            is_auto=True
                        )
                        lot.current_price = new_amount
                        lot.save()
                        current_price = new_amount
                        bid_made = True
                        print(f"Auto bid placed: {auto_bid.user.username} - {new_amount}")

                        time_to_end = lot.auction_end - timezone.now()
                        last_bid = lot.bids.order_by('-created_at').first()
                        if last_bid and time_to_end <= timedelta(minutes=5):
                            lot.auction_end = last_bid.created_at + timedelta(minutes=5)
                            lot.save()
                            print(f"Auction extended to: {lot.auction_end}")

        if not bid_made:
            break


class HomeView(View):
    def get(self, request):
        lots = Lot.objects.all()
        print(f"Initial lots: {lots.count()}")

        search_query = request.GET.get('search', '')
        category = request.GET.get('category', '')
        tag = request.GET.get('tag', '')
        condition = request.GET.get('condition', '')
        location = request.GET.get('location', '')
        sort_by = request.GET.get('sort_by', '')
        expiring_soon = request.GET.get('expiring_soon', '')
        active_only = request.GET.get('active_only', '')

        print(f"Filters: search={search_query}, category={category}, tag={tag}, condition={condition}, location={location}, sort_by={sort_by}, expiring_soon={expiring_soon}, active_only={active_only}")
        print(f"Categories: {Lot.CATEGORY_CHOICES}")
        print(f"Conditions: {Lot.CONDITION_CHOICES}")

        filters_applied = any([
            search_query, category, tag, condition, location, sort_by, expiring_soon, active_only
        ])

        if active_only:
            lots = lots.filter(is_active=True, auction_end__gt=timezone.now())
            print(f"After active_only filter: {lots.count()}")

        if search_query:
            lots = lots.filter(Q(title__icontains=search_query))
            print(f"After search filter: {lots.count()}")

        if category:
            lots = lots.filter(category=category)
            print(f"After category filter: {lots.count()}")

        if tag:
            lots = lots.filter(tags__icontains=tag)
            print(f"After tag filter: {lots.count()}")

        if condition:
            lots = lots.filter(condition=condition)
            print(f"After condition filter: {lots.count()}")

        if location:
            lots = lots.filter(
                Q(location_country__icontains=location) | Q(location_city__icontains=location)
            )
            print(f"After location filter: {lots.count()}")

        if expiring_soon:
            lots = lots.filter(auction_end__lte=timezone.now() + timedelta(hours=24))
            print(f"After expiring_soon filter: {lots.count()}")

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
            lots = lots.order_by('-created_at')

        if not filters_applied:
            latest_lots = lots[:3]
            other_lots = lots[3:]
            print(f"Latest lots: {latest_lots.count()}, Other lots: {other_lots.count()}")
        else:
            latest_lots = None
            other_lots = None
            print(f"Filtered lots: {lots.count()}")

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
        lot = get_object_or_404(Lot.objects.prefetch_related('bids__user', 'comments__user', 'comments__replies'), pk=pk)
        is_author = request.user.is_authenticated and lot.created_by == request.user
        bid_form = BidForm(lot=lot) if request.user.is_authenticated and not is_author else None
        auto_bid_form = AutoBidForm(lot=lot, user=request.user) if request.user.is_authenticated and not is_author else None
        comment_form = CommentForm() if request.user.is_authenticated else None
        unique_bidders = lot.bids.values('user__username').annotate(max_amount=Max('amount')).order_by('-max_amount')[:3]
        user_auto_bid = AutoBid.objects.filter(lot=lot, user=request.user).first() if request.user.is_authenticated else None
        current_bid = lot.bids.filter(user=request.user).order_by('-amount').first() if request.user.is_authenticated else None
        root_comments = lot.comments.filter(parent__isnull=True)

        if lot.is_active and lot.auction_end <= timezone.now() and not lot.has_bids():
            lot.auction_end = timezone.now() + timedelta(minutes=10)
            lot.save()
            print(f"Lot {lot.id} ({lot.title}) extended to: {lot.auction_end}")

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
                    'id': comment.id,
                    'content': comment.content,
                    'username': comment.user.username,
                    'created_at': comment.created_at.isoformat(),
                    'can_edit': comment.can_edit_or_delete() and request.user == comment.user,
                    'replies_count': comment.replies.count(),
                    'replies': [
                        {
                            'id': reply.id,
                            'content': reply.content,
                            'username': reply.user.username,
                            'created_at': reply.created_at.isoformat(),
                            'can_edit': reply.can_edit_or_delete() and request.user == reply.user,
                        }
                        for reply in comment.replies.all()
                    ]
                }
                for comment in root_comments
            ]
            return JsonResponse({
                'bidders': bidders,
                'comments': comments,
                'current_price': float(lot.current_price) if lot.current_price else None,
                'is_auction_ended': lot.is_auction_ended(),
                'auction_end': lot.auction_end.isoformat(),
                'time_until': (lot.auction_end - timezone.now()).total_seconds() if lot.is_active else 0,
            })

        return render(request, 'auctions/lot_detail.html', {
            'lot': lot,
            'location': location,
            'bid_form': bid_form,
            'auto_bid_form': auto_bid_form,
            'comment_form': comment_form,
            'is_author': is_author,
            'unique_bidders': unique_bidders,
            'user_auto_bid': user_auto_bid,
            'current_bid': current_bid,
            'root_comments': root_comments,
        })

    def post(self, request, pk):
        lot = get_object_or_404(Lot, pk=pk)
        is_author = request.user.is_authenticated and lot.created_by == request.user

        if lot.is_auction_ended():
            messages.error(request, "Аукцион уже завершён.")
            return redirect('lot_detail', pk=pk)

        if not request.user.is_authenticated:
            messages.error(request, "Авторизуйтесь, чтобы сделать ставку или оставить комментарий.")
            return redirect('login')

        if 'bid' in request.POST and not is_author:
            bid_form = BidForm(request.POST, lot=lot)
            if bid_form.is_valid():
                with transaction.atomic():
                    bid = bid_form.save(commit=False)
                    bid.lot = lot
                    bid.user = request.user
                    bid.save()
                    lot.current_price = bid.amount
                    lot.save()
                    time_to_end = lot.auction_end - timezone.now()
                    last_bid = lot.bids.order_by('-created_at').first()
                    if last_bid and time_to_end <= timedelta(minutes=5):
                        lot.auction_end = last_bid.created_at + timedelta(minutes=5)
                        lot.save()
                        print(f"Auction extended to: {lot.auction_end}")
                    process_auto_bids(lot)
                    messages.success(request, "Ставка успешно сделана.")
            else:
                messages.error(request, "Ошибка в ставке: " + str(bid_form.errors))

        elif 'auto_bid' in request.POST and not is_author:
            auto_bid_form = AutoBidForm(request.POST, lot=lot, user=request.user)
            if auto_bid_form.is_valid():
                with transaction.atomic():
                    AutoBid.objects.filter(lot=lot, user=request.user).delete()
                    auto_bid = auto_bid_form.save(commit=False)
                    auto_bid.lot = lot
                    auto_bid.user = request.user
                    auto_bid.save()
                    current_price = lot.current_price or lot.initial_price
                    current_leader = lot.bids.order_by('-amount').first()
                    if not current_leader or current_leader.user != request.user:
                        new_amount = current_price + lot.bid_step
                        if auto_bid.max_amount >= new_amount:
                            Bid.objects.create(
                                lot=lot,
                                user=request.user,
                                amount=new_amount,
                                is_auto=True
                            )
                            lot.current_price = new_amount
                            lot.save()
                            print(f"Initial auto bid placed: {request.user.username} - {new_amount}")
                            time_to_end = lot.auction_end - timezone.now()
                            last_bid = lot.bids.order_by('-created_at').first()
                            if last_bid and time_to_end <= timedelta(minutes=5):
                                lot.auction_end = last_bid.created_at + timedelta(minutes=5)
                                lot.save()
                                print(f"Auction extended to: {lot.auction_end}")
                    process_auto_bids(lot)
                    messages.success(request, "Автоматическая ставка установлена.")
            else:
                messages.error(request, "Ошибка в автоматической ставке: " + str(auto_bid_form.errors))

        elif 'remove_auto_bid' in request.POST and not is_author:
            with transaction.atomic():
                AutoBid.objects.filter(lot=lot, user=request.user).delete()
                messages.success(request, "Автоматическая ставка удалена.")
                process_auto_bids(lot)

        elif 'comment' in request.POST:
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                last_reply = Comment.objects.filter(
                    user=request.user,
                    lot=lot,
                    parent__isnull=False
                ).order_by('-created_at').first()
                if last_reply and (timezone.now() - last_reply.created_at) < timedelta(minutes=1):
                    messages.error(request, "Вы можете оставлять ответы не чаще одного раза в минуту.")
                else:
                    comment = comment_form.save(commit=False)
                    comment.lot = lot
                    comment.user = request.user
                    comment.save()
                    messages.success(request, "Комментарий добавлен.")
            else:
                messages.error(request, "Ошибка в комментарии: " + str(comment_form.errors))

        elif 'edit_comment' in request.POST:
            comment_id = request.POST.get('comment_id')
            comment = get_object_or_404(Comment, id=comment_id, user=request.user, lot=lot)
            if not comment.can_edit_or_delete():
                messages.error(request, "Время для редактирования комментария истекло.")
            else:
                content = request.POST.get('content')
                if content:
                    comment.content = content
                    comment.save()
                    messages.success(request, "Комментарий обновлён.")
                else:
                    messages.error(request, "Комментарий не может быть пустым.")
                    print(f"Edit comment failed: Empty content for comment_id={comment_id}")

        elif 'delete_comment' in request.POST:
            comment_id = request.POST.get('comment_id')
            comment = get_object_or_404(Comment, id=comment_id, user=request.user, lot=lot)
            if not comment.can_edit_or_delete():
                messages.error(request, "Время для удаления комментария истекло.")
            else:
                comment.delete()
                messages.success(request, "Комментарий удалён.")

        elif 'cancel_lot' in request.POST and is_author:
            if lot.has_bids():
                messages.error(request, "Нельзя отменить лот с активными ставками.")
            else:
                lot.delete()
                messages.success(request, "Лот успешно отменён.")
                return redirect('home')

        return redirect('lot_detail', pk=pk)


class CreateLotView(LoginRequiredMixin, View):
    def get(self, request):
        form = LotForm()
        return render(request, 'auctions/create_lot.html', {'form': form})

    def post(self, request):
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