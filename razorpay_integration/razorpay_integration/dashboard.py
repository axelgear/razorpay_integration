import frappe
from frappe import _
from razorpay_integration.razorpay_integration.razorpay_client import get_razorpay_client

def get_unpaid_payments_dashboard():
    client, sandbox_mode = get_razorpay_client()
    payments = client.payment.all({"count": 100})
    data = []
    for payment in payments.get("items", []):
        existing = frappe.db.exists("Razorpay Payment Transactions", {"payment_id": payment["id"]})
        if not existing:
            data.append({
                "payment_id": payment["id"],
                "amount": payment["amount"] / 100,
                "status": payment["status"],
                "created_at": frappe.utils.get_datetime(payment["created_at"]),
                "order_id": payment["order_id"]
            })
    return {
        "columns": [
            {"label": _("Payment ID"), "fieldname": "payment_id", "fieldtype": "Data", "width": 150},
            {"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 120},
            {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
            {"label": _("Created At"), "fieldname": "created_at", "fieldtype": "Datetime", "width": 150}
        ],
        "data": data
    }

def get_virtual_accounts_dashboard():
    client, sandbox_mode = get_razorpay_client()
    virtual_accounts = client.virtual_account.all({"count": 100})
    data = []
    for va in virtual_accounts.get("items", []):
        if not frappe.db.exists("Razorpay Virtual Account", {"virtual_account_id": va["id"]}):
            data.append({
                "virtual_account_id": va["id"],
                "customer_id": va["customer_id"],
                "status": va["status"],
                "description": va["description"],
                "created_at": frappe.utils.get_datetime(va["created_at"])
            })
    return {
        "columns": [
            {"label": _("Virtual Account ID"), "fieldname": "virtual_account_id", "fieldtype": "Data", "width": 150},
            {"label": _("Customer ID"), "fieldname": "customer_id", "fieldtype": "Data", "width": 120},
            {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
            {"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 200},
            {"label": _("Created At"), "fieldname": "created_at", "fieldtype": "Datetime", "width": 150}
        ],
        "data": data
    }

def get_payment_link_transactions(payment_link_id):
    payment = frappe.get_all("Razorpay Payment", filters={"payment_link_id": payment_link_id}, limit=1)
    if not payment:
        return {
            "columns": [],
            "data": []
        }
    payment = frappe.get_doc("Razorpay Payment", payment[0].name)
    return {
        "columns": [
            {"label": _("Payment ID"), "fieldname": "payment_id", "fieldtype": "Data", "width": 150},
            {"label": _("Amount Paid"), "fieldname": "amount_paid", "fieldtype": "Currency", "width": 120},
            {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
            {"label": _("Created At"), "fieldname": "created_at", "fieldtype": "Datetime", "width": 150},
            {"label": _("Refund ID"), "fieldname": "refund_id", "fieldtype": "Data", "width": 120},
            {"label": _("Settlement ID"), "fieldname": "settlement_id", "fieldtype": "Data", "width": 120}
        ],
        "data": [
            {
                "payment_id": t.payment_id,
                "amount_paid": t.amount_paid,
                "status": t.status,
                "created_at": t.created_at,
                "refund_id": t.refund_id,
                "settlement_id": t.settlement_id
            } for t in payment.transactions
        ]
    }

def get_settlements_dashboard():
    settlements = frappe.get_all("Razorpay Settlement", fields=["settlement_id", "amount", "status", "fees", "tax", "utr", "created_at", "settlement_type"], limit=100)
    return {
        "columns": [
            {"label": _("Settlement ID"), "fieldname": "settlement_id", "fieldtype": "Data", "width": 150},
            {"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 120},
            {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
            {"label": _("Fees"), "fieldname": "fees", "fieldtype": "Currency", "width": 100},
            {"label": _("Tax"), "fieldname": "tax", "fieldtype": "Currency", "width": 100},
            {"label": _("UTR"), "fieldname": "utr", "fieldtype": "Data", "width": 150},
            {"label": _("Created At"), "fieldname": "created_at", "fieldtype": "Datetime", "width": 150},
            {"label": _("Settlement Type"), "fieldname": "settlement_type", "fieldtype": "Data", "width": 120}
        ],
        "data": settlements
    }