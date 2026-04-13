from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import View
from .models import Transaction, Profile
from django.db import models
from django.db.models import Sum, Q
from datetime import datetime
from decimal import Decimal
import calendar

class RegisterView(View):
    def get(self, request):
        form = UserCreationForm()
        return render(request, 'registration/register.html', {'form': form})

    def post(self, request):
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful.")
            return redirect('dashboard')
        return render(request, 'registration/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
        messages.error(request, "Invalid username or password.")
    form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    user = request.user
    profile = user.profile
    transactions = user.transactions.all()
    
    # Filtering Logic
    now = datetime.now()
    month = int(request.GET.get('month', now.month))
    year = int(request.GET.get('year', now.year))
    
    transactions_month = transactions.filter(date__month=month, date__year=year)

    total_income = transactions_month.filter(transaction_type='INCOME').aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    total_expense = transactions_month.filter(transaction_type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    
    # Dynamic Salary Budget
    # Check for INCOME transactions in SALARY category for this month
    monthly_salary_income = transactions_month.filter(transaction_type='INCOME', category='SALARY').aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    
    # Budget to use for progress bars: Salary if added, else fallback to Profile default
    effective_budget = monthly_salary_income if monthly_salary_income > 0 else profile.monthly_salary

    # Wallets & Balance
    wallets = user.wallets.all()
    current_balance = user.profile.total_balance

    # Today's Calculations
    now = datetime.now()
    today = now.date()
    today_income = transactions.filter(date=today, transaction_type='INCOME').aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    today_expense = transactions.filter(date=today, transaction_type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    
    # Safe Daily Limit Calculation
    _, num_days = calendar.monthrange(year, month)
    remaining_days = num_days - now.day + 1 if (month == now.month and year == now.year) else num_days
    if remaining_days < 1: remaining_days = 1
    
    remaining_budget = effective_budget - total_expense
    safe_daily_limit = max(0, remaining_budget / Decimal(remaining_days))
    
    # Filtered View specific data
    is_current_month = (month == now.month and year == now.year)
    
    if is_current_month:
        display_balance = current_balance
        display_spent = today_expense
        display_limit = safe_daily_limit
        balance_label = "Total Combined Balance"
        spent_label = "Today's Spent"
        limit_label = "Safe Daily Limit"
        balance_sub = "↑ Across all accounts"
        spent_sub = "Resetting at 12:00 AM"
        limit_sub = "Recommended limit"
    else:
        display_balance = total_income - total_expense # Monthly Savings
        display_spent = total_income # Month's Income
        display_limit = total_expense / Decimal(num_days) if num_days > 0 else 0
        balance_label = "Net Monthly Savings"
        spent_label = "Total Month Income"
        limit_label = "Avg. Daily Spent"
        balance_sub = "Income - Expenses"
        spent_sub = f"For {calendar.month_name[month]}"
        limit_sub = f"Across {num_days} days"

    # Financial Health Calculation
    saving_ratio = 0
    if total_income > 0:
        saving_ratio = ((total_income - total_expense) / total_income) * 100
    
    health_score = max(0, min(100, saving_ratio)) # Simple score based on savings %

    # Budget Progress
    budget_usage = 0
    if effective_budget > 0:
        budget_usage = (total_expense / effective_budget) * 100

    # Category Breakdown
    categories_data = transactions_month.filter(transaction_type='EXPENSE').values('category').annotate(total=Sum('amount')).order_by('-total')[:3]

    context = {
        'transactions': transactions_month[:8],
        'total_income': total_income,
        'total_expense': total_expense,
        'today_income': today_income,
        'today_expense': today_expense,
        'current_balance': current_balance,
        'display_balance': round(display_balance, 2),
        'display_spent': round(display_spent, 2),
        'display_limit': round(display_limit, 2),
        'balance_label': balance_label,
        'spent_label': spent_label,
        'limit_label': limit_label,
        'balance_sub': balance_sub,
        'spent_sub': spent_sub,
        'limit_sub': limit_sub,
        'is_current_month': is_current_month,
        'health_score': round(health_score, 1),
        'budget_usage': round(budget_usage, 1),
        'effective_budget': effective_budget,
        'safe_daily_limit': round(safe_daily_limit, 2),
        'categories_data': categories_data,
        'wallets': wallets,
        'user': user,
        'selected_month': month,
        'selected_year': year,
        'months_choices': [(i, calendar.month_name[i]) for i in range(1, 13)],
        'years_range': range(now.year - 2, now.year + 1),
    }
    
    # 12-Month Performance Data
    performance_labels = []
    performance_income = []
    performance_expense = []
    
    from django.db.models.functions import ExtractMonth, ExtractYear
    for i in range(5, -1, -1):
        target_month = (now.month - i - 1) % 12 + 1
        target_year = now.year if target_month <= now.month else now.year - 1
        
        m_name = calendar.month_name[target_month]
        performance_labels.append(m_name[:3])
        
        m_data = transactions.filter(date__year=target_year, date__month=target_month)
        m_inc = m_data.filter(transaction_type='INCOME').aggregate(Sum('amount'))['amount__sum'] or 0
        m_exp = m_data.filter(transaction_type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or 0
        performance_income.append(float(m_inc))
        performance_expense.append(float(m_exp))
        
    context['performance_labels'] = performance_labels
    performance_income[len(performance_income)-1] = float(total_income) # Use current pre-calculated
    performance_expense[len(performance_expense)-1] = float(total_expense)
    context['performance_income'] = performance_income
    context['performance_expense'] = performance_expense

    return render(request, 'cash/dashboard.html', context)

@login_required
def history(request):
    user = request.user
    now = datetime.now()
    
    # 1. Get Params
    view_mode = request.GET.get('view', 'monthly')
    month = int(request.GET.get('month', now.month))
    year = int(request.GET.get('year', now.year))
    query = request.GET.get('q', '')

    from django.db.models.functions import ExtractMonth, ExtractYear
    
    history_data = []
    transactions_list = []

    if view_mode == 'monthly':
        # Monthly Summary Logic
        logs = user.transactions.annotate(
            m=ExtractMonth('date'),
            y=ExtractYear('date')
        ).values('y', 'm').annotate(
            inc=Sum('amount', filter=Q(transaction_type='INCOME')),
            exp=Sum('amount', filter=Q(transaction_type='EXPENSE')),
            sal=Sum('amount', filter=Q(transaction_type='INCOME', category='SALARY'))
        ).order_by('-y', '-m')

        for log in logs:
            income = log['inc'] or Decimal(0)
            expense = log['exp'] or Decimal(0)
            salary = log['sal'] or Decimal(0)
            savings = income - expense
            rate = 0
            if income > 0:
                rate = (savings / income) * 100
            
            history_data.append({
                'date': datetime(log['y'], log['m'], 1),
                'income': income,
                'expense': expense,
                'salary': salary,
                'savings': savings,
                'rate': round(rate, 1)
            })
    else:
        # Daily Transactions Logic
        transactions_list = user.transactions.filter(date__month=month, date__year=year)
        if query:
            transactions_list = transactions_list.filter(Q(title__icontains=query) | Q(category__icontains=query))
        transactions_list = transactions_list.order_by('-date', '-time')

    context = {
        'view_mode': view_mode,
        'history_data': history_data,
        'transactions_list': transactions_list,
        'selected_month': month,
        'selected_year': year,
        'query': query,
        'months_choices': [(i, calendar.month_name[i]) for i in range(1, 13)],
        'years_range': range(now.year - 2, now.year + 1),
        'now': now
    }
    return render(request, 'cash/history.html', context)

@login_required
def add_transaction(request):
    user = request.user
    if request.method == 'POST':
        title = request.POST.get('title')
        amount = request.POST.get('amount')
        t_type = request.POST.get('transaction_type')
        category = request.POST.get('category')
        description = request.POST.get('description')
        location = request.POST.get('location')

        wallet_id = request.POST.get('wallet')
        wallet = user.wallets.get(id=wallet_id)

        transaction = Transaction.objects.create(
            user=user,
            wallet=wallet,
            title=title,
            amount=amount,
            transaction_type=t_type,
            category=category,
            description=description,
            location=location
        )

        # Update Wallet Balance
        amount_val = Decimal(amount)
        if t_type == 'INCOME':
            wallet.balance += amount_val
        else:
            wallet.balance -= amount_val
        wallet.save()

        messages.success(request, f"{t_type.capitalize()} added successfully.")
        return redirect('dashboard')
    
    return render(request, 'cash/add_transaction.html')

from .forms import UserUpdateForm, ProfileUpdateForm

@login_required
def profile(request):
    user = request.user
    profile = user.profile
    
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, "Your profile has been updated!")
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=user)
        p_form = ProfileUpdateForm(instance=profile)
    
    transactions_count = user.transactions.count()
    
    context = {
        'u_form': u_form,
        'p_form': p_form,
        'transactions_count': transactions_count,
        'joined_date': user.date_joined,
    }
    return render(request, 'cash/profile.html', context)
