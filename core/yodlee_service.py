"""
SaaS Spend Optimizer — Yodlee Integration Service
Handles authentication, token management, and transaction fetching.
"""
import os
import sys
import time
import json
import hashlib
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


# Yodlee sandbox endpoints
YODLEE_BASE_URL = os.environ.get("YODLEE_BASE_URL", "https://sandbox.api.yodlee.com/ysl")
YODLEE_CLIENT_ID = os.environ.get("YODLEE_CLIENT_ID", "")
YODLEE_SECRET = os.environ.get("YODLEE_SECRET", "")


def _log(level: str, msg: str) -> None:
    sys.stderr.write(f"[YODLEE] [{level}] {msg}\n")


class YodleeService:
    """
    Manages Yodlee API integration.
    
    In production, this connects to the real Yodlee API.
    When YODLEE_CLIENT_ID is not set, it falls back to 
    generating realistic mock data for development.
    """

    def __init__(self, client_id: str = "", secret: str = ""):
        self.client_id = client_id or YODLEE_CLIENT_ID
        self.secret = secret or YODLEE_SECRET
        self.base_url = YODLEE_BASE_URL
        self.access_token = None
        self.token_expires = None

    @property
    def is_live(self) -> bool:
        return bool(self.client_id and self.secret)

    def authenticate(self) -> Dict[str, Any]:
        """Get an access token from Yodlee."""
        if not self.is_live:
            _log("WARN", "No Yodlee credentials. Using mock mode.")
            self.access_token = f"mock_token_{int(time.time())}"
            self.token_expires = datetime.utcnow() + timedelta(hours=1)
            return {"token": self.access_token, "mock": True}

        try:
            resp = requests.post(
                f"{self.base_url}/auth/token",
                headers={"Api-Version": "1.1", "Content-Type": "application/x-www-form-urlencoded"},
                data={"clientId": self.client_id, "secret": self.secret},
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            self.access_token = data["token"]["accessToken"]
            expires_in = data["token"].get("expiresIn", 1800)
            self.token_expires = datetime.utcnow() + timedelta(seconds=expires_in)
            _log("INFO", f"Yodlee auth success. Expires in {expires_in}s")
            return {"token": self.access_token, "mock": False}
        except Exception as e:
            _log("ERROR", f"Yodlee auth failed: {e}")
            raise

    def get_accounts(self) -> List[Dict]:
        """Fetch linked accounts."""
        if not self.is_live:
            return self._mock_accounts()

        headers = self._auth_headers()
        resp = requests.get(f"{self.base_url}/accounts", headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json().get("account", [])

    def get_transactions(self, from_date: str = None, to_date: str = None) -> List[Dict]:
        """Fetch transactions within a date range."""
        if not self.is_live:
            return self._mock_transactions()

        headers = self._auth_headers()
        params = {}
        if from_date:
            params["fromDate"] = from_date
        if to_date:
            params["toDate"] = to_date

        resp = requests.get(
            f"{self.base_url}/transactions",
            headers=headers, params=params, timeout=30
        )
        resp.raise_for_status()
        return resp.json().get("transaction", [])

    def _auth_headers(self) -> Dict[str, str]:
        if not self.access_token or (self.token_expires and datetime.utcnow() > self.token_expires):
            self.authenticate()
        return {
            "Api-Version": "1.1",
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    # ─── Mock data for development ─────────────────────────────────
    def _mock_accounts(self) -> List[Dict]:
        return [
            {"id": 10001, "accountName": "Business Checking ****4521", "accountType": "CHECKING",
             "providerName": "Chase", "balance": {"amount": 42350.00, "currency": "USD"}},
            {"id": 10002, "accountName": "Corporate Card ****8832", "accountType": "CREDIT_CARD",
             "providerName": "American Express", "balance": {"amount": -8420.50, "currency": "USD"}},
        ]

    def _mock_transactions(self) -> List[Dict]:
        """Generate realistic messy bank transaction strings."""
        import random
        from decimal import Decimal

        # These are intentionally messy — exactly what banks produce
        saas_transactions = [
            {"desc": "GITHUB INC 888-4483889 CA", "amount": 21.00, "vendor": "GitHub"},
            {"desc": "SLACK TECHNOLOGIES SF CA", "amount": 8.75, "vendor": "Slack"},
            {"desc": "ATLASSIAN PTY 0288**** AU", "amount": 150.00, "vendor": "Atlassian"},
            {"desc": "AWS EMEA aws.amazon LU", "amount": 847.32, "vendor": "AWS"},
            {"desc": "GOOGLE *WORKSPACE g.co/payhelp", "amount": 72.00, "vendor": "Google Workspace"},
            {"desc": "ADOBE CREATIVE CLOUD 800-833-6687", "amount": 54.99, "vendor": "Adobe"},
            {"desc": "ZOOM.US 888-799-9666 CA", "amount": 199.90, "vendor": "Zoom"},
            {"desc": "NOTION LABS INC SF CA", "amount": 10.00, "vendor": "Notion"},
            {"desc": "DROPBOX*BUSINESS SF CA", "amount": 75.00, "vendor": "Dropbox"},
            {"desc": "HUBSPOT INC CAMBRIDGE MA", "amount": 800.00, "vendor": "HubSpot"},
            {"desc": "INTERCOM R0YR52K0 IE", "amount": 87.00, "vendor": "Intercom"},
            {"desc": "DATADOG INC NEW YORK NY", "amount": 399.00, "vendor": "Datadog"},
            {"desc": "VERCEL INC SF CA", "amount": 20.00, "vendor": "Vercel"},
            {"desc": "HEROKU SALESFORCE.COM CA", "amount": 50.00, "vendor": "Heroku"},
            {"desc": "FIGMA INC SF CA", "amount": 45.00, "vendor": "Figma"},
            {"desc": "MIRO.COM 2963**** NL", "amount": 16.00, "vendor": "Miro"},
            {"desc": "CANVA PTY LTD SYDNEY AU", "amount": 12.99, "vendor": "Canva"},
            {"desc": "SEMRUSH INC 800**** MA", "amount": 119.95, "vendor": "SEMrush"},
            {"desc": "MIXPANEL INC SF CA", "amount": 89.00, "vendor": "Mixpanel"},
            {"desc": "1PASSWORD AGILEBITS ON CA", "amount": 7.99, "vendor": "1Password"},
            {"desc": "LINEAR INC SF CA", "amount": 8.00, "vendor": "Linear"},
            {"desc": "SENTRY.IO SF CA", "amount": 26.00, "vendor": "Sentry"},
            # Duplicates (same vendor, different merchant strings)
            {"desc": "SLACKTECH INC SAN FRANCISCO", "amount": 8.75, "vendor": "Slack"},
            {"desc": "GOOGLE *GSUITE g.co/payhelp#", "amount": 72.00, "vendor": "Google Workspace"},
            {"desc": "MSFT*AZURE MICROSOFT.COM WA", "amount": 234.50, "vendor": "Azure"},
            {"desc": "MICROSOFT*M365 REDMOND WA", "amount": 22.00, "vendor": "Microsoft 365"},
        ]

        # Non-SaaS noise transactions
        noise = [
            {"desc": "UBER *TRIP HELP.UBER.COM", "amount": 23.45},
            {"desc": "STARBUCKS STORE #12483", "amount": 6.85},
            {"desc": "DOORDASH*CHIPOTLE SF CA", "amount": 18.72},
            {"desc": "DELTA AIR LINES ATLANTA GA", "amount": 342.00},
            {"desc": "HILTON HOTELS NEW YORK NY", "amount": 289.00},
        ]

        today = datetime.now()
        results = []

        # Generate 6 months of recurring SaaS charges
        for month_offset in range(6):
            tx_date = today - timedelta(days=30 * month_offset)
            for tx in saas_transactions:
                # Add some variation to dates (±3 days)
                jitter = random.randint(-3, 3)
                actual_date = tx_date + timedelta(days=jitter)
                results.append({
                    "id": random.randint(100000, 999999),
                    "description": {"original": tx["desc"]},
                    "amount": {"amount": tx["amount"], "currency": "USD"},
                    "date": actual_date.strftime("%Y-%m-%d"),
                    "postDate": (actual_date + timedelta(days=1)).strftime("%Y-%m-%d"),
                    "categoryType": "EXPENSE",
                    "category": "Software",
                    "isRecurring": True,
                })

            # Sprinkle noise
            for tx in noise:
                results.append({
                    "id": random.randint(100000, 999999),
                    "description": {"original": tx["desc"]},
                    "amount": {"amount": tx["amount"], "currency": "USD"},
                    "date": (tx_date + timedelta(days=random.randint(-15, 15))).strftime("%Y-%m-%d"),
                    "postDate": (tx_date + timedelta(days=random.randint(-14, 16))).strftime("%Y-%m-%d"),
                    "categoryType": "EXPENSE",
                    "category": "General",
                    "isRecurring": False,
                })

        _log("INFO", f"Generated {len(results)} mock transactions (6 months)")
        return results


if __name__ == "__main__":
    svc = YodleeService()
    result = svc.authenticate()
    print(f"Auth result: {json.dumps(result)}")
    txns = svc.get_transactions()
    print(f"Fetched {len(txns)} transactions")
    if txns:
        print(f"Sample: {json.dumps(txns[0], indent=2)}")
