from frappe.model.document import Document

class RazorpaySettlement(Document):
    def validate(self):
        if not self.settlement_id:
            frappe.throw("Settlement ID is mandatory.")