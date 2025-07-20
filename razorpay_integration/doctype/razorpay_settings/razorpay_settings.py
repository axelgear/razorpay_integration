from frappe.model.document import Document
import frappe

class RazorpaySettings(Document):
    def validate(self):
        if self.enabled:
            if self.use_sandbox:
                if not self.sandbox_api_key or not self.sandbox_api_secret:
                    frappe.throw("Sandbox API Key and Secret are mandatory when Sandbox Mode is enabled.")
            else:
                if not self.api_key or not self.api_secret:
                    frappe.throw("API Key and Secret are mandatory for production mode.")
            if not self.webhook_secret:
                frappe.throw("Webhook Secret is mandatory for Razorpay integration.")