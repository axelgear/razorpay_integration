import frappe
import razorpay

def get_razorpay_client():
    settings = frappe.get_single("Razorpay Settings")
    if not settings.enabled:
        frappe.throw("Razorpay Integration is not enabled.")
    
    sandbox_mode = settings.use_sandbox
    if sandbox_mode:
        if not settings.sandbox_api_key or not settings.sandbox_api_secret:
            frappe.throw("Sandbox API Key and Secret are required when Sandbox Mode is enabled.")
        client = razorpay.Client(auth=(settings.sandbox_api_key, settings.sandbox_api_secret))
    else:
        if not settings.production_api_key or not settings.production_api_secret:
            frappe.throw("Production API Key and Secret are required for production mode.")
        client = razorpay.Client(auth=(settings.production_api_key, settings.production_api_secret))
    
    return client, sandbox_mode