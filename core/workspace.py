import random
from .models import Organization

def reconcile_with_workspace(organization_id):
    """
    Mock Google Workspace / M365 Integration.
    In a real app, this would use the Google Admin SDK to pull 
    the active employee count for the domain.
    """
    try:
        org = Organization.objects.get(id=organization_id)
        
        # Simulate fetching active users from Workspace directory
        # e.g., google_admin.users().list(domain=org.domain).execute()
        # For mock purposes, we generate a realistic employee count 
        # based on their SaaS spend (roughly 1 employee per $150 in SaaS spend)
        
        total_monthly = sum(s.monthly_cost for s in org.subscriptions.filter(status='active'))
        estimated_employees = max(10, int(total_monthly / 150))
        
        # Add some random variance (-10% to +10%)
        variance = random.uniform(0.9, 1.1)
        active_employees = int(estimated_employees * variance)
        
        org.active_employees = active_employees
        org.save()
        
        # Now reconcile licenses
        for sub in org.subscriptions.filter(status='active'):
            # If we know they are paying for N licenses but only have M employees...
            if sub.licenses_paid_for > active_employees:
                sub.status = 'orphaned'
                waste_per_seat = float(sub.monthly_cost) / max(1, sub.licenses_paid_for)
                excess_seats = sub.licenses_paid_for - active_employees
                
                # Update flag logic
                sub.flag_reason = f"Paying for {sub.licenses_paid_for} seats, but only have {active_employees} active employees. {excess_seats} orphaned seats."
                sub.estimated_annual_waste = (waste_per_seat * excess_seats) * 12
                sub.save()
                
        return {"status": "success", "active_employees": active_employees}
    except Organization.DoesNotExist:
        return {"error": "Organization not found"}
