import frappe
import razorpay

def get_razorpay_client():
    settings = frappe.get_single("Razorpay Integration Settings")
    if settings.sandbox_mode:
        api_key = settings.sandbox_api_key
        api_secret = settings.sandbox_api_secret
    else:
        api_key = settings.production_api_key
        api_secret = settings.production_api_secret
    if not api_key or not api_secret:
        frappe.throw("API Key and Secret are required.")
    client = razorpay.Client(auth=(api_key, api_secret))
    return client, settings.sandbox_mode