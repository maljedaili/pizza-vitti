from datetime import datetime, timedelta

from allauth.account.forms import SignupForm
from django import forms
from django.conf import settings
from django.utils import timezone

from .hours import collection_slots, is_valid_service_time
from .models import Reservation


class CustomerSignupForm(SignupForm):
    first_name = forms.CharField(
        label='Prénom',
        max_length=150,
        widget=forms.TextInput(attrs={'autocomplete': 'given-name'}),
    )
    last_name = forms.CharField(
        label='Nom',
        max_length=150,
        widget=forms.TextInput(attrs={'autocomplete': 'family-name'}),
    )

    field_order = ['first_name', 'last_name', 'email', 'password1', 'password2']

    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data['first_name'].strip()
        user.last_name = self.cleaned_data['last_name'].strip()
        user.save(update_fields=['first_name', 'last_name'])
        return user


class CheckoutForm(forms.Form):
    name = forms.CharField(label='Nom', max_length=160)
    email = forms.EmailField(label='E-mail')
    phone = forms.CharField(label='Téléphone', max_length=40)
    collection_slot = forms.ChoiceField(label='Date et heure de retrait')
    notes = forms.CharField(
        label='Instructions ou allergie à signaler',
        required=False,
        widget=forms.Textarea,
        help_text="Le restaurant ne peut pas garantir l'absence totale de traces d'allergènes.",
    )
    promo_code = forms.CharField(label='Code promotionnel', max_length=40, required=False)
    payment_method = forms.ChoiceField(label='Mode de paiement')
    accepted_terms = forms.BooleanField(
        label='J’accepte les conditions générales de commande et la politique de confidentialité.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({
            'autocomplete': 'name',
            'autocapitalize': 'words',
        })
        self.fields['email'].widget.attrs.update({
            'autocomplete': 'email',
            'inputmode': 'email',
        })
        self.fields['phone'].widget.attrs.update({
            'autocomplete': 'tel',
            'inputmode': 'tel',
        })
        self.fields['notes'].widget.attrs.update({'rows': 3})
        self.fields['promo_code'].widget.attrs.update({
            'autocomplete': 'off',
            'autocapitalize': 'characters',
        })
        today = timezone.localdate()
        choices = []
        for offset in range(14):
            day = today + timedelta(days=offset)
            for slot in collection_slots(day):
                value = f'{day.isoformat()}|{slot:%H:%M}'
                label = f'{day:%d/%m/%Y} à {slot:%H:%M}'
                choices.append((value, label))
        self.has_available_slots = bool(choices)
        self.fields['collection_slot'].choices = choices
        if not self.has_available_slots:
            self.fields['collection_slot'].choices = [('', '—')]
            self.fields['collection_slot'].widget.attrs['disabled'] = True
        payment_choices = [('cash', 'Paiement au retrait')]
        if settings.STRIPE_SECRET_KEY:
            payment_choices.insert(0, ('stripe', 'Carte bancaire sécurisée'))
        self.fields['payment_method'].choices = payment_choices

    def clean_collection_slot(self):
        value = self.cleaned_data['collection_slot']
        try:
            day_text, time_text = value.split('|', 1)
            day = datetime.strptime(day_text, '%Y-%m-%d').date()
            at_time = datetime.strptime(time_text, '%H:%M').time()
        except (TypeError, ValueError):
            raise forms.ValidationError('Créneau de retrait invalide.')
        if at_time not in collection_slots(day):
            raise forms.ValidationError('Ce créneau de retrait n’est plus disponible.')
        return day, at_time


class ReservationForm(forms.ModelForm):
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'tabindex': '-1', 'autocomplete': 'off'}),
    )

    class Meta:
        model = Reservation
        fields = ('name', 'email', 'phone', 'guests', 'date', 'time', 'message')
        labels = {
            'name': 'Nom',
            'email': 'E-mail',
            'phone': 'Téléphone',
            'guests': 'Nombre de personnes',
            'date': 'Date',
            'time': 'Heure',
            'message': 'Message (facultatif)',
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean_website(self):
        value = self.cleaned_data.get('website', '')
        if value:
            raise forms.ValidationError('Soumission invalide.')
        return value

    def clean(self):
        cleaned = super().clean()
        day = cleaned.get('date')
        at_time = cleaned.get('time')
        if not day or not at_time:
            return cleaned
        now = timezone.localtime()
        requested = timezone.make_aware(datetime.combine(day, at_time))
        if requested <= now:
            raise forms.ValidationError('Choisissez une date et une heure à venir.')
        if not is_valid_service_time(day, at_time):
            raise forms.ValidationError('Cette heure est en dehors des horaires d’ouverture.')
        return cleaned
