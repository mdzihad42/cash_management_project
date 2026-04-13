from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('add-transaction/', views.add_transaction, name='add_transaction'),
    path('profile/', views.profile, name='profile'),
]
