import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cash_management.settings')
django.setup()

from cash.models import Profile, Wallet, Transaction
from django.contrib.auth.models import User

def setup():
    for user in User.objects.all():
        # 1. Create a default Cash wallet if not exists
        wallet, created = Wallet.objects.get_or_create(
            user=user,
            name='Main Cash',
            defaults={'wallet_type': 'CASH', 'balance': 0}
        )
        
        # 2. Update existing transactions to lead to this wallet
        Transaction.objects.filter(user=user, wallet__isnull=True).update(wallet=wallet)
        
        # 3. Recalculate wallet balance based on transactions
        income = Transaction.objects.filter(wallet=wallet, transaction_type='INCOME').aggregate(django.db.models.Sum('amount'))['amount__sum'] or 0
        expense = Transaction.objects.filter(wallet=wallet, transaction_type='EXPENSE').aggregate(django.db.models.Sum('amount'))['amount__sum'] or 0
        wallet.balance = income - expense
        wallet.save()
        
        print(f"Set up {wallet.name} for {user.username}. Balance: {wallet.balance}")

if __name__ == '__main__':
    setup()
