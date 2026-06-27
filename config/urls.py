"""
SaaS Spend Optimizer — URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core import views

router = DefaultRouter()
router.register(r'organizations', views.OrganizationViewSet)
router.register(r'accounts', views.BankAccountViewSet)
router.register(r'transactions', views.TransactionViewSet)
router.register(r'subscriptions', views.SubscriptionViewSet)
router.register(r'vendors', views.SaaSVendorViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/dashboard/', views.dashboard_summary, name='dashboard-summary'),
    path('api/ingest/', views.ingest_transactions, name='ingest-transactions'),
    path('api/health/', views.health, name='health'),
]
