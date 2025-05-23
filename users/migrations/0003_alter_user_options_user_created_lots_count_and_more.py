# Generated by Django 5.1.6 on 2025-05-04 19:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_user_email_verify_alter_user_email'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'verbose_name': 'Пользователь', 'verbose_name_plural': 'Пользователи'},
        ),
        migrations.AddField(
            model_name='user',
            name='created_lots_count',
            field=models.PositiveIntegerField(default=0, verbose_name='Создано лотов'),
        ),
        migrations.AddField(
            model_name='user',
            name='top_three_lots_count',
            field=models.PositiveIntegerField(default=0, verbose_name='Лотов в топ-3'),
        ),
        migrations.AddField(
            model_name='user',
            name='won_lots_count',
            field=models.PositiveIntegerField(default=0, verbose_name='Выиграно лотов'),
        ),
    ]
