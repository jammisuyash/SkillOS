"""payments/service.py — Razorpay integration for recruiter subscriptions + cert purchases.

SETUP (free to use — Razorpay takes 2% per transaction):
  1. Sign up at https://razorpay.com (free)
  2. Get API keys from Dashboard → Settings → API Keys
  3. Set env vars:
       RAZORPAY_KEY_ID=rzp_test_xxxx
       RAZORPAY_KEY_SECRET=xxxx
  4. For production, switch to live keys

DEV MODE: If keys not set, returns mock order IDs so frontend can be tested.
"""
import os, uuid, hmac, hashlib, json, urllib.request, urllib.error, base64
from skillos.db.database import fetchone, transaction
from skillos.shared.exceptions import ValidationError
from skillos.shared.utils import utcnow_iso

KEY_ID     = os.environ.get("RAZORPAY_KEY_ID", "")
KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
_DEV       = not (KEY_ID and KEY_SECRET)

PLANS = {
    "starter":    {"amount_paise": 299900,  "contacts": 10,      "label": "Starter"},
    "growth":     {"amount_paise": 799900,  "contacts": 50,      "label": "Growth"},
    "enterprise": {"amount_paise": 2499900, "contacts": 999999,  "label": "Enterprise"},
    "cert_exam":  {"amount_paise": 49900,   "contacts": 0,       "label": "Certification Exam"},
}

def _razorpay_request(method: str, path: str, body: dict = None) -> dict:
    url  = f"https://api.razorpay.com/v1{path}"
    data = json.dumps(body or {}).encode()
    cred = base64.b64encode(f"{KEY_ID}:{KEY_SECRET}".encode()).decode()
    req  = urllib.request.Request(url, data=data, method=method,
           headers={"Authorization": f"Basic {cred}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise ValidationError(f"Razorpay error: {e.read().decode()}")

def create_order(company_id: str, user_id: str, plan: str) -> dict:
    if plan not in PLANS: raise ValidationError(f"Unknown plan: {plan}")
    p          = PLANS[plan]
    amount     = p["amount_paise"]
    order_id   = str(uuid.uuid4())

    if _DEV:
        # Dev mode — mock order so frontend works without real keys
        provider_order_id = f"order_DEV_{uuid.uuid4().hex[:16]}"
    else:
        rz = _razorpay_request("POST", "/orders", {
            "amount": amount, "currency": "INR",
            "receipt": order_id,
            "notes": {"company_id": company_id, "plan": plan},
        })
        provider_order_id = rz["id"]

    with transaction() as db:
        db.execute("""INSERT INTO payment_orders
            (id,company_id,user_id,provider_order_id,amount_paise,currency,plan)
            VALUES (?,?,?,?,?,'INR',?)""",
            (order_id, company_id, user_id, provider_order_id, amount, plan))

    return {
        "order_id":          order_id,
        "provider_order_id": provider_order_id,
        "amount_paise":      amount,
        "currency":          "INR",
        "plan":              plan,
        "key_id":            KEY_ID or "rzp_test_DEV",
        "dev_mode":          _DEV,
    }

def verify_payment(order_id: str, provider_payment_id: str, provider_signature: str) -> dict:
    """Verify Razorpay webhook signature and activate plan."""
    order = fetchone("SELECT * FROM payment_orders WHERE id=?", (order_id,))
    if not order: raise ValidationError("Order not found")
    if order["status"] == "paid": raise ValidationError("Already processed")

    if not _DEV:
        # Signature verification: HMAC-SHA256(order_id + "|" + payment_id, secret)
        body     = f"{order['provider_order_id']}|{provider_payment_id}"
        expected = hmac.new(KEY_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, provider_signature):
            raise ValidationError("Payment signature invalid")

    plan = order["plan"]
    with transaction() as db:
        db.execute("""UPDATE payment_orders SET status='paid', provider_payment_id=?, paid_at=?
                      WHERE id=?""", (provider_payment_id, utcnow_iso(), order_id))
        if order["company_id"] and plan in PLANS:
            from datetime import datetime, timedelta
            expires = (datetime.utcnow() + timedelta(days=30)).isoformat()
            limit   = PLANS[plan]["contacts"]
            db.execute("""UPDATE companies SET plan=?, plan_expires_at=?,
                          contacts_limit=?, contacts_used=0 WHERE id=?""",
                       (plan, expires, limit, order["company_id"]))

    return {"status": "paid", "plan": plan, "order_id": order_id}

def get_payment_history(company_id: str) -> list:
    from skillos.db.database import fetchall
    rows = fetchall("""SELECT id, plan, amount_paise, status, created_at, paid_at
                       FROM payment_orders WHERE company_id=? ORDER BY created_at DESC""",
                    (company_id,))
    return [dict(r) for r in rows]
