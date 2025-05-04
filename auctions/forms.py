from django import forms
from .models import Lot, Comment, Bid, AutoBid
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


class BidForm(forms.ModelForm):
    class Meta:
        model = Bid
        fields = ['amount']

    def __init__(self, *args, **kwargs):
        self.lot = kwargs.pop('lot', None)
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if not self.lot:
            raise forms.ValidationError("Лот не указан.")
        min_amount = self.lot.initial_price
        if self.lot.current_price:
            min_amount = self.lot.current_price + self.lot.bid_step
        else:
            min_amount = self.lot.initial_price + self.lot.bid_step
        if amount < min_amount:
            raise forms.ValidationError(
                f"Ставка должна быть не менее {min_amount} (текущая цена + шаг {self.lot.bid_step})."
            )
        return amount


class AutoBidForm(forms.ModelForm):
    class Meta:
        model = AutoBid
        fields = ['max_amount']

    def __init__(self, *args, **kwargs):
        self.lot = kwargs.pop('lot', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_max_amount(self):
        max_amount = self.cleaned_data['max_amount']
        if not self.lot:
            raise forms.ValidationError("Лот не указан.")
        min_amount = self.lot.initial_price
        if self.lot.current_price:
            min_amount = self.lot.current_price + self.lot.bid_step
        else:
            min_amount = self.lot.initial_price + self.lot.bid_step
        if max_amount < min_amount:
            raise forms.ValidationError(
                f"Максимальная ставка должна быть не менее {min_amount} (текущая цена + шаг {self.lot.bid_step})."
            )
        return max_amount


class CommentForm(forms.ModelForm):
    parent = forms.IntegerField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Comment
        fields = ['content', 'parent']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3}),
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