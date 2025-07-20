from frappe.model.document import Document

class RazorpaySettlementTransactions(Document):
    def validate(self):
        if not self.entity_id:
            frappe.throw("Entity ID is mandatory.")