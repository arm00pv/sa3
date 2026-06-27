from celery import shared_task
from django.core.mail import send_mail
from .models import Organization, Subscription

@shared_task
def sync_bank_feeds():
    """
    Simulated nightly background task that fetches new transactions 
    from Plaid/Yodlee for all active organizations.
    """
    orgs = Organization.objects.all()
    for org in orgs:
        # In a real scenario, loop through org.bank_accounts and fetch from provider API
        print(f"Syncing daily bank feeds for organization: {org.name}")

    return f"Synced {orgs.count()} organizations"

@shared_task
def send_alert_for_new_subscription(subscription_id):
    """
    Sends an email or Slack alert when a new subscription is detected.
    """
    try:
        sub = Subscription.objects.get(id=subscription_id)
        
        subject = f"Alert: New SaaS Subscription Detected ({sub.vendor.name if sub.vendor else sub.matched_description})"
        message = f"A new subscription has been detected for {sub.organization.name}.\n" \
                  f"Service: {sub.matched_description}\n" \
                  f"Monthly Cost: ${sub.monthly_cost}\n\n" \
                  f"Please review the SpendShield dashboard."
                  
        send_mail(
            subject,
            message,
            'alerts@spendshield.ai',
            ['cfo@' + (sub.organization.domain or 'example.com')],
            fail_silently=False,
        )
        return True
    except Subscription.DoesNotExist:
        return False
