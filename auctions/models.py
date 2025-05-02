#auctions/models.py


from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from users.models import User


class Lot(models.Model):
    CATEGORY_CHOICES = [
        ('Транспорт', 'Транспорт'),
        ('Картины', 'Картины'),
        ('Недвижимость', 'Недвижимость'),
        ('Украшения', 'Украшения'),
        ('Книги', 'Книги'),
        ('Электроника', 'Электроника'),
        ('Антиквариат', 'Антиквариат'),
        ('Одежда', 'Одежда'),
        ('Спортивные товары', 'Спортивные товары'),
        ('Музыкальные инструменты', 'Музыкальные инструменты'),
        ('Коллекционные предметы', 'Коллекционные предметы'),
        ('Мебель', 'Мебель'),
    ]

    CONDITION_CHOICES = [
        ('new', 'Новое'),
        ('used', 'Б/У'),
        ('not_specified', 'Не указано'),
        ('damaged', 'Повреждено'),
        ('refurbished', 'Восстановлено'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    initial_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    main_image = models.ImageField(upload_to='lots/main/', null=True, blank=True)
    additional_image_1 = models.ImageField(upload_to='lots/additional/', null=True, blank=True)
    additional_image_2 = models.ImageField(upload_to='lots/additional/', null=True, blank=True)
    additional_image_3 = models.ImageField(upload_to='lots/additional/', null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lots')
    created_at = models.DateTimeField(auto_now_add=True)
    auction_end = models.DateTimeField()
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, default='Транспорт')
    is_active = models.BooleanField(default=True)

    # Новые поля
    condition = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        default='not_specified',
        verbose_name='Состояние'
    )
    tags = models.CharField(
        max_length=200,
        blank=True,
        help_text='Введите теги через запятую (например: антиквариат, винтаж, редкий)',
        verbose_name='Теги'
    )
    location_country = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Страна'
    )
    location_city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Город'
    )

    def is_auction_ended(self):
        return timezone.now() > self.auction_end

    def has_bids(self):
        return self.bids.exists()

    def __str__(self):
        return self.title

class Bid(models.Model):
    lot = models.ForeignKey(Lot, on_delete=models.CASCADE, related_name='bids')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bids')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-amount']

    def __str__(self):
        return f"{self.user.username} - {self.amount} on {self.lot.title}"

class Comment(models.Model):
    lot = models.ForeignKey(Lot, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.lot.title}"