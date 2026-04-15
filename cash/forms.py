from django import forms
from django.contrib.auth.models import User
from .models import Profile, Transaction, Loan

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_pic', 'monthly_salary']

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['title', 'amount', 'transaction_type', 'category', 'wallet', 'location', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['wallet'].queryset = user.wallets.all()


class LoanForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ['person_name', 'phone', 'amount', 'loan_type', 'description', 'due_date']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }


class LoanPaymentForm(forms.Form):
    payment_amount = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=0.01,
        widget=forms.NumberInput(attrs={'placeholder': 'Enter payment amount'})
    )
