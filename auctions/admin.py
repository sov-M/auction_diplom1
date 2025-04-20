#auctions/admin.py

from django.contrib import admin
from .models import Lot, Bid, Comment


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_by', 'created_at', 'auction_end', 'is_active']
    list_filter = ['is_active', 'category']
    search_fields = ['title', 'description']


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ['lot', 'user', 'amount', 'created_at']
    list_filter = ['lot']
    search_fields = ['user__username']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['lot', 'user', 'created_at']
    search_fields = ['content']