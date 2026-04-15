from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('add-transaction/', views.add_transaction, name='add_transaction'),
    path('edit-transaction/<int:pk>/', views.edit_transaction, name='edit_transaction'),
    path('delete-transaction/<int:pk>/', views.delete_transaction, name='delete_transaction'),
    path('history/', views.history, name='history'),
    path('profile/', views.profile, name='profile'),
    # Loan / Debt Tracker
    path('loans/', views.loan_list, name='loan_list'),
    path('add-loan/', views.add_loan, name='add_loan'),
    path('pay-loan/<int:pk>/', views.make_payment, name='make_payment'),
    path('delete-loan/<int:pk>/', views.delete_loan, name='delete_loan'),
]
