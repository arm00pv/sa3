from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Organization, SaaSVendor, BankAccount, Subscription, Transaction

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'organization', 'is_organization_admin', 'is_staff')
    list_filter = ('is_organization_admin', 'is_staff', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ('SaaS Optimizer specific', {'fields': ('organization', 'is_organization_admin')}),
    )

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'active_employees', 'created_at')
    search_fields = ('name', 'domain')

@admin.register(SaaSVendor)
class SaaSVendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_known_duplicate_risk')
    list_filter = ('category', 'is_known_duplicate_risk')
    search_fields = ('name',)

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('organization', 'matched_description', 'vendor', 'monthly_cost', 'status', 'licenses_paid_for')
    list_filter = ('status', 'billing_cycle')
    search_fields = ('matched_description', 'organization__name')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'organization', 'amount', 'original_description', 'parsed_merchant_name')
    list_filter = ('date',)
    search_fields = ('original_description', 'parsed_merchant_name')

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('institution_name', 'account_type', 'organization', 'last_synced')
