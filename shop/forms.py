from allauth.account.forms import SignupForm
from django import forms


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
