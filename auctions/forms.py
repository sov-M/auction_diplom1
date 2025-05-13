# forms.py
from django import forms
from .models import Lot, Comment, Bid
from django.utils import timezone

class LotForm(forms.ModelForm):
    class Meta:
        model = Lot
        fields = [
            'title', 'description', 'initial_price', 'main_image',
            'additional_image_1', 'additional_image_2', 'additional_image_3',
            'auction_end', 'category', 'condition', 'tags', 'location_country',
            'location_city', 'bid_step'
        ]
        widgets = {
            'auction_end': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 5}),
            'category': forms.Select(),
            'condition': forms.Select(),
            'tags': forms.TextInput(attrs={'placeholder': 'Введите теги через запятую (например: антиквариат, винтаж)'}),
            'location_country': forms.TextInput(attrs={'placeholder': 'Введите страну'}),
            'location_city': forms.TextInput(attrs={'placeholder': 'Введите город'}),
            'bid_step': forms.NumberInput(attrs={'step': '1.00', 'min': '1.00'}),
        }

    def clean_auction_end(self):
        auction_end = self.cleaned_data['auction_end']
        if auction_end <= timezone.now():
            raise forms.ValidationError("Дата окончания аукциона должна быть в будущем.")
        return auction_end

    def clean_bid_step(self):
        bid_step = self.cleaned_data['bid_step']
        if bid_step < 1.00:
            raise forms.ValidationError("Минимальный шаг ставки должен быть не менее 1.00.")
        return bid_step

# forms.py
class BidForm(forms.ModelForm):
    class Meta:
        model = Bid
        fields = ['amount']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '100',
                'type': 'number',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.lot = kwargs.pop('lot', None)
        super().__init__(*args, **kwargs)
        if self.lot:
            current_price = self.lot.current_price or self.lot.initial_price
            min_amount = current_price + self.lot.bid_step
            self.fields['amount'].widget.attrs['placeholder'] = f'Мин. {min_amount:.2f}'

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if not self.lot:
            raise forms.ValidationError("Лот не указан.")
        current_price = self.lot.current_price or self.lot.initial_price
        min_amount = current_price + self.lot.bid_step
        max_amount = current_price + (self.lot.bid_step * 100)  # Макс. +100 шагов
        if amount < min_amount:
            raise forms.ValidationError(
                f"Ставка должна быть не менее {min_amount:.2f} (текущая цена {current_price:.2f} + шаг {self.lot.bid_step:.2f})."
            )
        if amount > max_amount:
            raise forms.ValidationError(
                f"Ставка не может превышать {max_amount:.2f}."
            )
        return amount

class CommentForm(forms.ModelForm):
    parent = forms.IntegerField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Comment
        fields = ['content', 'parent']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Ваш комментарий'
            }),
        }

    def clean_parent(self):
        parent_id = self.cleaned_data.get('parent')
        if parent_id:
            try:
                parent = Comment.objects.get(id=parent_id)
                return parent
            except Comment.DoesNotExist:
                raise forms.ValidationError("Указанный родительский комментарий не существует.")
        return None