"""
SaaS Spend Optimizer — DRF Serializers
"""
from rest_framework import serializers
from .models import Organization, BankAccount, Transaction, SaaSVendor, Subscription


class OrganizationSerializer(serializers.ModelSerializer):
    total_monthly_spend = serializers.SerializerMethodField()
    subscription_count = serializers.SerializerMethodField()
    flagged_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'domain', 'created_at', 'updated_at',
            'total_monthly_spend', 'subscription_count', 'flagged_count',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_monthly_spend(self, obj):
        return float(obj.subscriptions.filter(status='active').aggregate(
            total=serializers.models.Sum('monthly_cost')
        )['total'] or 0)

    def get_subscription_count(self, obj):
        return obj.subscriptions.count()

    def get_flagged_count(self, obj):
        return obj.subscriptions.filter(status__in=['flagged', 'duplicate', 'orphaned']).count()


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class SaaSVendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaaSVendor
        fields = '__all__'
        read_only_fields = ['created_at']


class SubscriptionSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.name', read_only=True, default='Unknown')
    vendor_category = serializers.CharField(source='vendor.category', read_only=True, default='other')
    vendor_logo = serializers.URLField(source='vendor.logo_url', read_only=True, default='')

    class Meta:
        model = Subscription
        fields = [
            'id', 'organization', 'vendor', 'vendor_name', 'vendor_category',
            'vendor_logo', 'matched_description', 'monthly_cost', 'billing_cycle',
            'first_seen', 'last_seen', 'next_renewal', 'status', 'flag_reason',
            'estimated_annual_waste', 'transaction_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DashboardSummarySerializer(serializers.Serializer):
    """Aggregate dashboard data for the frontend."""
    total_monthly_spend = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_annual_spend = serializers.DecimalField(max_digits=12, decimal_places=2)
    estimated_waste = serializers.DecimalField(max_digits=12, decimal_places=2)
    active_subscriptions = serializers.IntegerField()
    flagged_subscriptions = serializers.IntegerField()
    duplicate_subscriptions = serializers.IntegerField()
    orphaned_subscriptions = serializers.IntegerField()
    top_spenders = SubscriptionSerializer(many=True)
    monthly_trend = serializers.ListField()
    upcoming_renewals = SubscriptionSerializer(many=True)
    category_breakdown = serializers.ListField()
