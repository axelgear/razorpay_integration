from frappe.model.document import Document
import frappe
from razorpay_integration.razorpay_integration.razorpay_client import get_razorpay_client

class RazorpayAnalytics(Document):
    pass

def get_analytics_data():
    total_payments = frappe.db.count("Razorpay Payment")
    successful_payments = frappe.db.count("Razorpay Payment", filters={"status": ["in", ["Paid", "Partially Paid"]]})
    total_amount = frappe.db.sql("""
        SELECT SUM(amount_paid)
        FROM `tabRazorpay Payment`
        WHERE status IN ('Paid', 'Partially Paid')
    """)[0][0] or 0
    return {
        "total_payments": total_payments,
        "successful_payments": successful_payments,
        "success_rate": (successful_payments / total_payments * 100) if total_payments else 0,
        "total_amount": total_amount
    }

def sync_unpaid_payments():
    client, sandbox_mode = get_razorpay_client()
    try:
        payments = client.payment.all({"count": 100})
        for payment in payments.get("items", []):
            if not frappe.db.exists("Razorpay Payment", {"payment_id": payment["id"]}):
                quotation = frappe.db.get_value("Razorpay Payment", {"order_id": payment["order_id"]}, "quotation")
                if quotation:
                    payment_doc = frappe.get_doc({
                        "doctype": "Razorpay Payment",
                        "quotation": quotation,
                        "amount": payment["amount"] / 100,
                        "amount_paid": payment["amount"] / 100,
                        "payment_id": payment["id"],
                        "order_id": payment["order_id"],
                        "status": "Paid" if payment["status"] == "captured" else "Partially Paid",
                        "created_at": frappe.utils.get_datetime(payment["created_at"])
                    })
                    payment_doc.insert()
                    payment_doc.submit()
                    frappe.msgprint(f"Synced Razorpay Payment: {payment['id']}")
    except Exception as e:
        frappe.log_error(f"Failed to sync payments: {str(e)}")