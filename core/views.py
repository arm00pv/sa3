"""
SaaS Spend Optimizer — API Views
REST endpoints for dashboard, transactions, and subscriptions.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict

from django.db.models import Sum, Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response

from .models import Organization, BankAccount, Transaction, SaaSVendor, Subscription
from .serializers import (
    OrganizationSerializer, BankAccountSerializer, TransactionSerializer,
    SaaSVendorSerializer, SubscriptionSerializer,
)
from .yodlee_service import YodleeService
from .parser import parse_transactions, identify_vendor
from .workspace import reconcile_with_workspace
from .tasks import send_alert_for_new_subscription


class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer


class BankAccountViewSet(viewsets.ModelViewSet):
    queryset = BankAccount.objects.all()
    serializer_class = BankAccountSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        org_id = self.request.query_params.get('organization')
        if org_id:
            qs = qs.filter(organization_id=org_id)
        return qs


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        account_id = self.request.query_params.get('account')
        if account_id:
            qs = qs.filter(bank_account_id=account_id)
        is_saas = self.request.query_params.get('is_saas')
        if is_saas is not None:
            qs = qs.filter(is_saas=is_saas.lower() == 'true')
        return qs


class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        org_id = self.request.query_params.get('organization')
        if org_id:
            qs = qs.filter(organization_id=org_id)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class SaaSVendorViewSet(viewsets.ModelViewSet):
    queryset = SaaSVendor.objects.all()
    serializer_class = SaaSVendorSerializer


@api_view(['GET'])
def dashboard_summary(request):
    """Main dashboard aggregate endpoint."""
    org_id = request.query_params.get('organization')

    if org_id:
        subs = Subscription.objects.filter(organization_id=org_id)
    else:
        subs = Subscription.objects.all()

    active = subs.filter(status='active')
    flagged = subs.filter(status__in=['flagged', 'duplicate', 'orphaned'])

    total_monthly = active.aggregate(total=Sum('monthly_cost'))['total'] or Decimal('0')
    waste = flagged.aggregate(total=Sum('estimated_annual_waste'))['total'] or Decimal('0')

    # Monthly trend from transactions
    monthly_trend = []
    if org_id:
        txns = Transaction.objects.filter(
            bank_account__organization_id=org_id, is_saas=True
        ).values('transaction_date__year', 'transaction_date__month').annotate(
            total=Sum('amount')
        ).order_by('transaction_date__year', 'transaction_date__month')

        for entry in txns:
            month_str = f"{entry['transaction_date__year']}-{entry['transaction_date__month']:02d}"
            monthly_trend.append({"month": month_str, "spend": float(entry['total'])})

    # Category breakdown
    cat_data = subs.filter(vendor__isnull=False).values('vendor__category').annotate(
        total=Sum('monthly_cost'), count=Count('id')
    ).order_by('-total')

    category_breakdown = [
        {"category": c['vendor__category'] or 'other', "total": float(c['total']), "count": c['count']}
        for c in cat_data
    ]

    # Top spenders
    top_spenders = SubscriptionSerializer(
        active.order_by('-monthly_cost')[:10], many=True
    ).data

    # Upcoming renewals (next 30 days)
    today = datetime.now().date()
    upcoming = subs.filter(
        next_renewal__gte=today,
        next_renewal__lte=today + timedelta(days=30)
    ).order_by('next_renewal')

    return Response({
        "total_monthly_spend": float(total_monthly),
        "total_annual_spend": float(total_monthly * 12),
        "estimated_waste": float(waste),
        "active_subscriptions": active.count(),
        "flagged_subscriptions": subs.filter(status='flagged').count(),
        "duplicate_subscriptions": subs.filter(status='duplicate').count(),
        "orphaned_subscriptions": subs.filter(status='orphaned').count(),
        "top_spenders": top_spenders,
        "monthly_trend": monthly_trend,
        "upcoming_renewals": SubscriptionSerializer(upcoming, many=True).data,
        "category_breakdown": category_breakdown,
    })


@api_view(['POST'])
def ingest_transactions(request):
    """
    Ingest transactions from Yodlee (or mock data).
    Creates/updates Organization, BankAccount, Transaction, and Subscription records.
    """
    org_name = request.data.get('organization_name', 'Demo Company')
    use_mock = request.data.get('use_mock', True)

    # Get or create org
    org, created = Organization.objects.get_or_create(
        name=org_name,
        defaults={'domain': f"{org_name.lower().replace(' ', '')}.com"}
    )

    # Fetch transactions
    svc = YodleeService()
    svc.authenticate()

    if use_mock:
        accounts = svc._mock_accounts()
        raw_txns = svc._mock_transactions()
    else:
        accounts = svc.get_accounts()
        raw_txns = svc.get_transactions()

    # Create bank accounts
    for acct in accounts:
        BankAccount.objects.get_or_create(
            organization=org,
            yodlee_account_id=str(acct.get('id', '')),
            defaults={
                'account_name': acct.get('accountName', 'Unknown'),
                'account_type': acct.get('accountType', 'checking').lower().replace('_', ''),
                'institution_name': acct.get('providerName', ''),
                'last_synced': datetime.now(),
            }
        )

    bank_account = org.bank_accounts.first()
    if not bank_account:
        return Response({"error": "No bank account created"}, status=400)

    # Parse and categorize
    parsed = parse_transactions(raw_txns)

    # Store raw transactions
    tx_count = 0
    for raw_tx in raw_txns:
        desc = raw_tx.get("description", {})
        raw_desc = desc.get("original", "") if isinstance(desc, dict) else str(desc)
        amount_data = raw_tx.get("amount", {})
        amount = float(amount_data.get("amount", 0)) if isinstance(amount_data, dict) else float(amount_data or 0)
        date_str = raw_tx.get("date", datetime.now().strftime("%Y-%m-%d"))

        vendor = identify_vendor(raw_desc)
        Transaction.objects.get_or_create(
            bank_account=bank_account,
            raw_description=raw_desc,
            transaction_date=date_str,
            defaults={
                'amount': abs(amount),
                'is_saas': vendor is not None,
                'is_recurring': raw_tx.get("isRecurring", False),
                'category': vendor["category"] if vendor else 'uncategorized',
            }
        )
        tx_count += 1

    # Create subscriptions from parsed results
    sub_count = 0
    for sub_data in parsed["subscriptions"] + parsed["duplicates"]:
        vendor_obj, _ = SaaSVendor.objects.get_or_create(
            name=sub_data["vendor"],
            defaults={
                'category': sub_data["category"],
                'aliases': sub_data.get("unique_descriptions", []),
            }
        )

        sub, sub_created = Subscription.objects.update_or_create(
            organization=org,
            vendor=vendor_obj,
            defaults={
                'matched_description': sub_data["vendor"],
                'monthly_cost': sub_data["monthly_cost"],
                'first_seen': sub_data.get("first_seen", datetime.now().strftime("%Y-%m-%d")),
                'last_seen': sub_data.get("last_seen", datetime.now().strftime("%Y-%m-%d")),
                'status': sub_data["status"],
                'flag_reason': sub_data.get("flag_reason", ""),
                'transaction_count': sub_data["charge_count"],
                'estimated_annual_waste': sub_data["monthly_cost"] * 12 if sub_data["status"] != "active" else 0,
            }
        )
        if sub_created:
            send_alert_for_new_subscription.delay(str(sub.id))
        sub_count += 1

    return Response({
        "status": "success",
        "organization": org.name,
        "organization_id": str(org.id),
        "transactions_ingested": tx_count,
        "subscriptions_created": sub_count,
        "summary": parsed["summary"],
    })


@api_view(['POST'])
def reconcile_workspace(request):
    """
    Mock endpoint to sync active employees from Google Workspace
    and reconcile against SaaS licenses.
    """
    org_id = request.data.get('organization')
    if not org_id and request.user.is_authenticated and request.user.organization:
        org_id = request.user.organization.id
        
    if not org_id:
        # Fallback to first org for demo
        org = Organization.objects.first()
        if not org:
            return Response({"error": "No organization found"}, status=400)
        org_id = str(org.id)
        
    result = reconcile_with_workspace(org_id)
    return Response(result)

@api_view(['GET'])
def health(request):
    """Health check endpoint."""
    return Response({"status": "ok", "service": "saas-optimizer", "version": "1.0.0"})
