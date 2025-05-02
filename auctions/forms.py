#auctions/forms.py

from django import forms
from .models import Lot, Comment, Bid
from django.utils import timezone


class LotForm(forms.ModelForm):
    class Meta:
        model = Lot
        fields = [
            'title', 'description', 'initial_price', 'main_image',
            'additional_image_1', 'additional_image_2', 'additional_image_3',
            'auction_end', 'category', 'condition', 'tags', 'location_country', 'location_city'
        ]
        widgets = {
            'auction_end': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 5}),
            'category': forms.Select(),
            'condition': forms.Select(),
            'tags': forms.TextInput(attrs={'placeholder': 'Введите теги через запятую (например: антиквариат, винтаж)'}),
            'location_country': forms.TextInput(attrs={'placeholder': 'Введите страну'}),
            'location_city': forms.TextInput(attrs={'placeholder': 'Введите город'}),
        }

    def clean_auction_end(self):
        auction_end = self.cleaned_data['auction_end']
        if auction_end <= timezone.now():
            raise forms.ValidationError("Дата окончания аукциона должна быть в будущем.")
        return auction_end

class BidForm(forms.ModelForm):
    class Meta:
        model = Bid
        fields = ['amount']

    def __init__(self, *args, **kwargs):
        self.lot = kwargs.pop('lot', None)
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if self.lot:
            if amount <= self.lot.initial_price:
                raise forms.ValidationError("Ставка должна быть выше начальной цены.")
            if self.lot.current_price and amount <= self.lot.current_price:
                raise forms.ValidationError("Ставка должна быть выше текущей.")
        return amount

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3}),
        }