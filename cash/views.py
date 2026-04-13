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
    
    # Filtering Logic (Basic for now)
    month = request.GET.get('month', datetime.now().month)
    transactions_month = transactions.filter(date__month=month)

    total_income = transactions_month.filter(transaction_type='INCOME').aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    total_expense = transactions_month.filter(transaction_type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    
    # Dynamic Salary Budget
    # Check for INCOME transactions in SALARY category for this month
    monthly_salary_income = transactions_month.filter(transaction_type='INCOME', category='SALARY').aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    
    # Budget to use for progress bars: Salary if added, else fallback to Profile default
    effective_budget = monthly_salary_income if monthly_salary_income > 0 else profile.monthly_salary

    # Today's Calculations
    now = datetime.now()
    today = now.date()
    today_income = transactions.filter(date=today, transaction_type='INCOME').aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    today_expense = transactions.filter(date=today, transaction_type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    
    # Safe Daily Limit Calculation
    _, num_days = calendar.monthrange(now.year, int(month))
    remaining_days = num_days - now.day + 1 if int(month) == now.month else num_days
    if remaining_days < 1: remaining_days = 1
    
    remaining_budget = effective_budget - total_expense
    safe_daily_limit = max(0, remaining_budget / Decimal(remaining_days))

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
        'transactions': transactions[:8],
        'total_income': total_income,
        'total_expense': total_expense,
        'today_income': today_income,
        'today_expense': today_expense,
        'current_balance': profile.balance,
        'health_score': round(health_score, 1),
        'budget_usage': round(budget_usage, 1),
        'effective_budget': effective_budget,
        'safe_daily_limit': round(safe_daily_limit, 2),
        'categories_data': categories_data,
        'user': user
    }
    return render(request, 'cash/dashboard.html', context)

@login_required
def history(request):
    user = request.user
    from django.db.models.functions import ExtractMonth, ExtractYear
    
    # Raw grouping
    logs = user.transactions.annotate(
        m=ExtractMonth('date'),
        y=ExtractYear('date')
    ).values('y', 'm').annotate(
        inc=Sum('amount', filter=Q(transaction_type='INCOME')),
        exp=Sum('amount', filter=Q(transaction_type='EXPENSE')),
        sal=Sum('amount', filter=Q(transaction_type='INCOME', category='SALARY'))
    ).order_by('-y', '-m')

    # Add calculated fields
    history_data = []
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

    context = {
        'history_data': history_data,
        'now': datetime.now()
    }
    return render(request, 'cash/history.html', context)

@login_required
def add_transaction(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        amount = request.POST.get('amount')
        t_type = request.POST.get('transaction_type')
        category = request.POST.get('category')
        description = request.POST.get('description')
        location = request.POST.get('location')

        transaction = Transaction.objects.create(
            user=request.user,
            title=title,
            amount=amount,
            transaction_type=t_type,
            category=category,
            description=description,
            location=location
        )

        # Update Profile Balance
        profile = request.user.profile
        amount_val = Decimal(amount)
        if t_type == 'INCOME':
            profile.balance += amount_val
        else:
            profile.balance -= amount_val
        profile.save()

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
