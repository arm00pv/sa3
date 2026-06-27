"""
SaaS Spend Optimizer — URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from core import views

router = DefaultRouter()
router.register(r'organizations', views.OrganizationViewSet)
router.register(r'accounts', views.BankAccountViewSet)
router.register(r'transactions', views.TransactionViewSet)
router.register(r'subscriptions', views.SubscriptionViewSet)
router.register(r'vendors', views.SaaSVendorViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/dashboard/', views.dashboard_summary, name='dashboard-summary'),
    path('api/ingest/', views.ingest_transactions, name='ingest-transactions'),
    path('api/reconcile/', views.reconcile_workspace, name='reconcile-workspace'),
    path('api/health/', views.health, name='health'),
]
