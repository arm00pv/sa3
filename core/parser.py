"""
SaaS Spend Optimizer — Transaction Parser
Identifies SaaS vendors from messy bank statement strings using pattern matching.
"""
import re
import sys
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict


def _log(level: str, msg: str) -> None:
    sys.stderr.write(f"[PARSER] [{level}] {msg}\n")


# ─── Known SaaS Vendor Patterns ──────────────────────────────────
# Maps regex patterns to canonical vendor names and categories
VENDOR_PATTERNS: List[Tuple[re.Pattern, str, str]] = [
    (re.compile(r'GITHUB', re.I), 'GitHub', 'development'),
    (re.compile(r'SLACK\s*(TECH|INC)?', re.I), 'Slack', 'communication'),
    (re.compile(r'SLACKTECH', re.I), 'Slack', 'communication'),
    (re.compile(r'ATLASSIAN', re.I), 'Atlassian', 'development'),
    (re.compile(r'JIRA', re.I), 'Atlassian', 'development'),
    (re.compile(r'AWS|AMAZON\s*WEB', re.I), 'AWS', 'cloud'),
    (re.compile(r'GOOGLE\s*\*?\s*(WORKSPACE|GSUITE|CLOUD)', re.I), 'Google Workspace', 'productivity'),
    (re.compile(r'ADOBE', re.I), 'Adobe', 'design'),
    (re.compile(r'ZOOM\.?US', re.I), 'Zoom', 'communication'),
    (re.compile(r'NOTION', re.I), 'Notion', 'productivity'),
    (re.compile(r'DROPBOX', re.I), 'Dropbox', 'productivity'),
    (re.compile(r'HUBSPOT', re.I), 'HubSpot', 'marketing'),
    (re.compile(r'INTERCOM', re.I), 'Intercom', 'communication'),
    (re.compile(r'DATADOG', re.I), 'Datadog', 'development'),
    (re.compile(r'VERCEL', re.I), 'Vercel', 'development'),
    (re.compile(r'HEROKU', re.I), 'Heroku', 'cloud'),
    (re.compile(r'FIGMA', re.I), 'Figma', 'design'),
    (re.compile(r'MIRO\.COM', re.I), 'Miro', 'productivity'),
    (re.compile(r'CANVA', re.I), 'Canva', 'design'),
    (re.compile(r'SEMRUSH', re.I), 'SEMrush', 'marketing'),
    (re.compile(r'MIXPANEL', re.I), 'Mixpanel', 'analytics'),
    (re.compile(r'1PASSWORD|AGILEBITS', re.I), '1Password', 'security'),
    (re.compile(r'LINEAR\s*INC', re.I), 'Linear', 'development'),
    (re.compile(r'SENTRY\.?IO', re.I), 'Sentry', 'development'),
    (re.compile(r'MSFT\*?AZURE|MICROSOFT\*?AZURE', re.I), 'Azure', 'cloud'),
    (re.compile(r'MICROSOFT\*?M365|MSFT\*?M365|MICROSOFT\*?OFFICE', re.I), 'Microsoft 365', 'productivity'),
    (re.compile(r'SALESFORCE', re.I), 'Salesforce', 'marketing'),
    (re.compile(r'TWILIO', re.I), 'Twilio', 'communication'),
    (re.compile(r'SENDGRID', re.I), 'SendGrid', 'communication'),
    (re.compile(r'STRIPE', re.I), 'Stripe', 'finance'),
    (re.compile(r'SHOPIFY', re.I), 'Shopify', 'other'),
    (re.compile(r'QUICKBOOKS|INTUIT', re.I), 'QuickBooks', 'finance'),
    (re.compile(r'MONDAY\.COM', re.I), 'Monday.com', 'productivity'),
    (re.compile(r'ASANA', re.I), 'Asana', 'productivity'),
    (re.compile(r'TRELLO', re.I), 'Trello', 'productivity'),
    (re.compile(r'PAGERDUTY', re.I), 'PagerDuty', 'development'),
    (re.compile(r'CLOUDFLARE', re.I), 'Cloudflare', 'cloud'),
    (re.compile(r'OKTA', re.I), 'Okta', 'security'),
    (re.compile(r'DOCUSIGN', re.I), 'DocuSign', 'productivity'),
    (re.compile(r'GRAMMARLY', re.I), 'Grammarly', 'productivity'),
]


def identify_vendor(raw_description: str) -> Optional[Dict[str, str]]:
    """Match a messy bank string to a known SaaS vendor."""
    for pattern, vendor_name, category in VENDOR_PATTERNS:
        if pattern.search(raw_description):
            return {"name": vendor_name, "category": category}
    return None


def parse_transactions(raw_transactions: List[Dict]) -> Dict:
    """
    Takes raw Yodlee-format transactions and returns:
    - identified SaaS subscriptions
    - flagged duplicates
    - monthly spend aggregation
    """
    vendor_charges = defaultdict(list)
    unmatched = []
    total_saas = 0
    total_non_saas = 0

    for tx in raw_transactions:
        desc = tx.get("description", {})
        if isinstance(desc, dict):
            raw = desc.get("original", "")
        else:
            raw = str(desc)

        amount_data = tx.get("amount", {})
        if isinstance(amount_data, dict):
            amount = float(amount_data.get("amount", 0))
        else:
            amount = float(amount_data or 0)

        date_str = tx.get("date", "")

        vendor = identify_vendor(raw)
        if vendor:
            total_saas += amount
            vendor_charges[vendor["name"]].append({
                "description": raw,
                "amount": amount,
                "date": date_str,
                "category": vendor["category"],
            })
        else:
            total_non_saas += amount
            unmatched.append({"description": raw, "amount": amount, "date": date_str})

    # Build subscription summaries
    subscriptions = []
    duplicates = []
    seen_vendors = set()

    for vendor_name, charges in vendor_charges.items():
        amounts = [c["amount"] for c in charges]
        dates = sorted([c["date"] for c in charges if c["date"]])
        avg_amount = sum(amounts) / len(amounts) if amounts else 0
        category = charges[0]["category"]

        # Detect duplicates: same vendor appearing with different amounts
        unique_amounts = set(amounts)
        descriptions = set(c["description"] for c in charges)

        sub = {
            "vendor": vendor_name,
            "category": category,
            "monthly_cost": round(avg_amount, 2),
            "charge_count": len(charges),
            "first_seen": dates[0] if dates else "",
            "last_seen": dates[-1] if dates else "",
            "unique_descriptions": list(descriptions),
            "status": "active",
        }

        # Flag if multiple distinct merchant strings point to same vendor
        if len(descriptions) > 1:
            sub["status"] = "duplicate"
            sub["flag_reason"] = f"Multiple merchant strings detected: {', '.join(descriptions)}"
            duplicates.append(sub)
        else:
            subscriptions.append(sub)

        seen_vendors.add(vendor_name)

    # Monthly trend
    monthly_spend = defaultdict(float)
    for vendor_name, charges in vendor_charges.items():
        for c in charges:
            if c["date"]:
                month_key = c["date"][:7]  # YYYY-MM
                monthly_spend[month_key] += c["amount"]

    monthly_trend = [{"month": k, "spend": round(v, 2)}
                     for k, v in sorted(monthly_spend.items())]

    # Category breakdown
    cat_spend = defaultdict(float)
    for vendor_name, charges in vendor_charges.items():
        cat = charges[0]["category"]
        cat_spend[cat] += sum(c["amount"] for c in charges)

    category_breakdown = [{"category": k, "total": round(v, 2)}
                          for k, v in sorted(cat_spend.items(), key=lambda x: -x[1])]

    result = {
        "summary": {
            "total_saas_spend": round(total_saas, 2),
            "total_non_saas_spend": round(total_non_saas, 2),
            "identified_vendors": len(seen_vendors),
            "total_subscriptions": len(subscriptions) + len(duplicates),
            "flagged_duplicates": len(duplicates),
            "estimated_monthly": round(sum(s["monthly_cost"] for s in subscriptions + duplicates), 2),
        },
        "subscriptions": subscriptions,
        "duplicates": duplicates,
        "monthly_trend": monthly_trend,
        "category_breakdown": category_breakdown,
        "unmatched_count": len(unmatched),
    }

    _log("INFO", f"Parsed {len(raw_transactions)} txns → {len(subscriptions)} subs, "
         f"{len(duplicates)} dupes, {len(unmatched)} unmatched")
    return result


if __name__ == "__main__":
    # Quick self-test with mock data
    from yodlee_service import YodleeService
    svc = YodleeService()
    svc.authenticate()
    txns = svc.get_transactions()
    result = parse_transactions(txns)
    import json
    print(json.dumps(result["summary"], indent=2))
    print(f"\nSubscriptions ({len(result['subscriptions'])}):")
    for s in result["subscriptions"][:5]:
        print(f"  {s['vendor']:20s} ${s['monthly_cost']:>8.2f}/mo  [{s['category']}]")
    print(f"\nDuplicates ({len(result['duplicates'])}):")
    for d in result["duplicates"]:
        print(f"  ⚠️ {d['vendor']:20s} ${d['monthly_cost']:>8.2f}/mo — {d['flag_reason'][:60]}")
