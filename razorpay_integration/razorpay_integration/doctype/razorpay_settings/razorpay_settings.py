from frappe.model.document import Document
import frappe

class RazorpayIntegrationSettings(Document):
    def validate(self):
        if self.enabled:
            if not self.api_key or not self.api_secret:
                frappe.throw("API Key and API Secret are mandatory when Razorpay Integration is enabled.")
            if not self.webhook_secret:
                frappe.throw("Webhook Secret is mandatory for payment verification.")
            if self.zohocliq_enabled and not self.zohocliq_webhook_url:
                frappe.throw("ZohoCliq Webhook URL is mandatory when ZohoCliq Notifications are enabled.")
            if self.default_expiry_days <= 0:
                frappe.throw("Default Expiry Days must be greater than zero.")
            if not self.virtual_account_prefix:
                frappe.throw("Virtual Account Prefix is mandatory.")