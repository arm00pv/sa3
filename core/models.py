"""
SaaS Spend Optimizer — Core Models
Tracks organizations, bank accounts, raw transactions, and identified subscriptions.
"""
import uuid
from django.db import models


class Organization(models.Model):
    """A company using the SaaS optimizer."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Yodlee integration
    yodlee_user_id = models.CharField(max_length=255, blank=True, null=True)
    yodlee_access_token = models.TextField(blank=True, null=True)
    yodlee_token_expires = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class BankAccount(models.Model):
    """A linked financial account from Yodlee."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='bank_accounts')
    account_name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=50, choices=[
        ('checking', 'Checking'),
        ('savings', 'Savings'),
        ('credit_card', 'Credit Card'),
        ('business', 'Business'),
    ])
    institution_name = models.CharField(max_length=255, blank=True)
    yodlee_account_id = models.CharField(max_length=255, blank=True, null=True)
    last_synced = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.account_name} ({self.institution_name})"


class Transaction(models.Model):
    """A raw bank transaction. The merchant string is messy on purpose—
    that's what the parsing engine cleans up."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='transactions')
    raw_description = models.TextField(help_text="Original messy merchant string from bank feed")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    transaction_date = models.DateField()
    posted_date = models.DateField(blank=True, null=True)
    category = models.CharField(max_length=100, blank=True)
    is_recurring = models.BooleanField(default=False)
    is_saas = models.BooleanField(default=False)
    yodlee_transaction_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-transaction_date']

    def __str__(self):
        return f"{self.raw_description[:50]} — ${self.amount}"


class SaaSVendor(models.Model):
    """Known SaaS vendor for matching against transaction strings."""
    name = models.CharField(max_length=255, unique=True)
    aliases = models.JSONField(default=list, help_text="Alternative merchant strings that map to this vendor")
    category = models.CharField(max_length=100, choices=[
        ('productivity', 'Productivity'),
        ('communication', 'Communication'),
        ('development', 'Development'),
        ('design', 'Design'),
        ('marketing', 'Marketing'),
        ('analytics', 'Analytics'),
        ('security', 'Security'),
        ('cloud', 'Cloud Infrastructure'),
        ('finance', 'Finance'),
        ('hr', 'Human Resources'),
        ('other', 'Other'),
    ])
    website = models.URLField(blank=True)
    logo_url = models.URLField(blank=True)
    avg_monthly_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'SaaS Vendor'
        verbose_name_plural = 'SaaS Vendors'

    def __str__(self):
        return self.name


class Subscription(models.Model):
    """An identified recurring SaaS subscription tied to a vendor."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('flagged', 'Flagged'),
        ('duplicate', 'Duplicate'),
        ('orphaned', 'Orphaned'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='subscriptions')
    vendor = models.ForeignKey(SaaSVendor, on_delete=models.SET_NULL, null=True, blank=True)
    matched_description = models.CharField(max_length=255)
    monthly_cost = models.DecimalField(max_digits=10, decimal_places=2)
    billing_cycle = models.CharField(max_length=20, choices=[
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ], default='monthly')
    first_seen = models.DateField()
    last_seen = models.DateField()
    next_renewal = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    flag_reason = models.TextField(blank=True)
    estimated_annual_waste = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transaction_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-monthly_cost']

    def __str__(self):
        return f"{self.matched_description} — ${self.monthly_cost}/mo [{self.status}]"
