# Generated by Django 5.1.6 on 2025-05-10 17:05

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Lot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('initial_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('current_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('main_image', models.ImageField(upload_to='lots/main/')),
                ('additional_image_1', models.ImageField(blank=True, null=True, upload_to='lots/additional/')),
                ('additional_image_2', models.ImageField(blank=True, null=True, upload_to='lots/additional/')),
                ('additional_image_3', models.ImageField(blank=True, null=True, upload_to='lots/additional/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('auction_end', models.DateTimeField()),
                ('category', models.CharField(choices=[('Транспорт', 'Транспорт'), ('Картины', 'Картины'), ('Недвижимость', 'Недвижимость'), ('Украшения', 'Украшения'), ('Книги', 'Книги'), ('Электроника', 'Электроника'), ('Антиквариат', 'Антиквариат'), ('Одежда', 'Одежда'), ('Спортивные товары', 'Спортивные товары'), ('Музыкальные инструменты', 'Музыкальные инструменты'), ('Коллекционные предметы', 'Коллекционные предметы'), ('Мебель', 'Мебель')], default='Транспорт', max_length=100)),
                ('is_active', models.BooleanField(default=True)),
                ('views', models.PositiveIntegerField(default=0, verbose_name='Просмотры')),
                ('condition', models.CharField(choices=[('not_specified', 'Не указано'), ('new', 'Новое'), ('used', 'Б/У'), ('damaged', 'Повреждено'), ('refurbished', 'Восстановлено')], default='not_specified', max_length=20, verbose_name='Состояние')),
                ('tags', models.CharField(help_text='Введите теги через запятую (например: антиквариат, винтаж, редкий)', max_length=200, verbose_name='Теги')),
                ('location_country', models.CharField(max_length=100, verbose_name='Страна')),
                ('location_city', models.CharField(blank=True, max_length=100, verbose_name='Город')),
                ('bid_step', models.DecimalField(decimal_places=2, default=100.0, max_digits=10, validators=[django.core.validators.MinValueValidator(1.0)], verbose_name='Минимальный шаг ставки')),
                ('has_been_extended', models.BooleanField(default=False, help_text='Indicates if the auction has been extended due to no bids.', verbose_name='Has been extended')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lots', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='auctions.comment')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to=settings.AUTH_USER_MODEL)),
                ('lot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='auctions.lot')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Bid',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_auto', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bids', to=settings.AUTH_USER_MODEL)),
                ('lot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bids', to='auctions.lot')),
            ],
            options={
                'ordering': ['-amount'],
            },
        ),
        migrations.CreateModel(
            name='AutoBid',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('max_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='auto_bids', to=settings.AUTH_USER_MODEL)),
                ('lot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='auto_bids', to='auctions.lot')),
            ],
            options={
                'ordering': ['-max_amount'],
                'unique_together': {('lot', 'user')},
            },
        ),
    ]
