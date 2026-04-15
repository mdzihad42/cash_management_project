from django.db import models, transaction
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    monthly_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    @property
    def total_balance(self):
        return sum(wallet.balance for wallet in self.user.wallets.all())

    def __str__(self):
        return f"{self.user.username}'s Profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class Wallet(models.Model):
    WALLET_TYPES = (
        ('CASH', 'Cash'),
        ('BANK', 'Bank Account'),
        ('MOBILE', 'Mobile Banking'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wallets')
    name = models.CharField(max_length=100)
    wallet_type = models.CharField(max_length=10, choices=WALLET_TYPES, default='CASH')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def update_balance(self):
        """Recalculate balance based on transactions."""
        income = self.transactions.filter(transaction_type='INCOME').aggregate(total=Sum('amount'))['total'] or 0
        expense = self.transactions.filter(transaction_type='EXPENSE').aggregate(total=Sum('amount'))['total'] or 0
        self.balance = income - expense
        self.save()

    def __str__(self):
        return f"{self.name} ({self.user.username})"

class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
    )
    
    CATEGORIES = (
        ('FOOD', 'Food'),
        ('TRANSPORT', 'Transport'),
        ('RENT', 'Rent'),
        ('UTILITIES', 'Utilities'),
        ('SHOPPING', 'Shopping'),
        ('SALARY', 'Salary'),
        ('INVESTMENT', 'Investment'),
        ('HEALTH', 'Health'),
        ('EDUCATION', 'Education'),
        ('ENTERTAINMENT', 'Entertainment'),
        ('OTHER', 'Other'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    category = models.CharField(max_length=20, choices=CATEGORIES, default='OTHER')
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField(auto_now_add=True)
    time = models.TimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type}: {self.amount} - {self.title}"

    class Meta:
        ordering = ['-date', '-time']

@receiver(post_save, sender=Transaction)
def update_wallet_on_save(sender, instance, **kwargs):
    if instance.wallet:
        instance.wallet.update_balance()

@receiver(post_delete, sender=Transaction)
def update_wallet_on_delete(sender, instance, **kwargs):
    if instance.wallet:
        instance.wallet.update_balance()


class Loan(models.Model):
    LOAN_TYPES = (
        ('PAONA', 'পাওনা (I Lent / Others Owe Me)'),
        ('DENA', 'দেনা (I Borrowed / I Owe Others)'),
    )
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('PARTIALLY_PAID', 'Partially Paid'),
        ('PAID', 'Paid / Settled'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loans')
    person_name = models.CharField(max_length=150, help_text="Name of the person")
    phone = models.CharField(max_length=20, blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    loan_type = models.CharField(max_length=10, choices=LOAN_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    description = models.TextField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def remaining_amount(self):
        return self.amount - self.paid_amount

    @property
    def progress_percent(self):
        if self.amount > 0:
            return min(100, (self.paid_amount / self.amount) * 100)
        return 0

    @property
    def is_overdue(self):
        from datetime import date
        if self.due_date and self.status != 'PAID':
            return date.today() > self.due_date
        return False

    def __str__(self):
        return f"{self.get_loan_type_display()} - {self.person_name}: ৳{self.amount}"

    class Meta:
        ordering = ['-created_at']
