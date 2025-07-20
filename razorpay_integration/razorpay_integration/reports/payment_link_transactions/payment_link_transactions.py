from frappe import _
from razorpay_integration.razorpay_integration.dashboard import get_payment_link_transactions

def execute(filters=None):
    payment_link_id = filters.get("payment_link_id") if filters else None
    if not payment_link_id:
        return [], []
    result = get_payment_link_transactions(payment_link_id)
    return result["columns"], result["data"]