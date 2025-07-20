from frappe.model.document import Document
import frappe

class RazorpayVirtualAccount(Document):
    def validate(self):
        if not self.customer:
            frappe.throw("Customer is mandatory.")
        if not self.virtual_account_id:
            frappe.throw("Virtual Account ID is mandatory.")