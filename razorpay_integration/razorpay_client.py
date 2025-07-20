import frappe
import razorpay

def get_razorpay_client():
    settings = frappe.get_single("Razorpay Integration Settings")
    if not settings.enabled:
        frappe.throw("Razorpay Integration is not enabled.")
    client = razorpay.Client(auth=(settings.api_key, settings.get_password("api_secret")))
    return client, settings.sandbox_mode