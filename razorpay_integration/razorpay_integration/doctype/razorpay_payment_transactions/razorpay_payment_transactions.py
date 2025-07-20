from frappe.model.document import Document

class RazorpayPaymentTransactions(Document):
    def validate(self):
        if not self.payment_id:
            frappe.throw("Payment ID is mandatory.")