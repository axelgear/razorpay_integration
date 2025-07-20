from frappe.model.document import Document
import frappe
from razorpay_integration.razorpay_integration.razorpay_client import get_razorpay_client
from razorpay_integration.razorpay_integration.zohocliq import post_to_zohocliq
from frappe.utils import nowdate, get_timestamp

class RazorpayVirtualAccount(Document):
    def validate(self):
        if not self.customer:
            frappe.throw("Customer is mandatory.")
        if not self.customer_razorpay_id:
            frappe.throw("Customer Razorpay ID is missing. Ensure the Customer has a valid Razorpay ID.")
        if self.project and not frappe.db.exists("Project", self.project):
            frappe.throw("Invalid Project reference.")
        if self.sales_order and not frappe.db.exists("Sales Order", self.sales_order):
            frappe.throw("Invalid Sales Order reference.")
        if self.quotation and not frappe.db.exists("Quotation", self.quotation):
            frappe.throw("Invalid Quotation reference.")
        if self.close_by and self.close_by < nowdate():
            frappe.throw("Close By date must be in the future.")

    def on_submit(self):
        self.create_virtual_account()

    def create_virtual_account(self):
        client, sandbox_mode = get_razorpay_client()
        customer = frappe.get_doc("Customer", self.customer)
        va_data = {
            "receivers": {
                "types": self.receiver_types or ["bank_account"]
            },
            "description": self.description or f"Virtual Account for {customer.customer_name}",
            "customer_id": self.customer_razorpay_id,
            "notes": {
                "customer": self.customer,
                "project": self.project or "",
                "sales_order": self.sales_order or "",
                "quotation": self.quotation or ""
            },
            "close_by": int(get_timestamp(self.close_by)) if self.close_by else None
        }
        if self.allowed_payers:
            va_data["allowed_payers"] = self.allowed_payers
        if self.amount_expected:
            va_data["amount_expected"] = int(self.amount_expected * 100)
        try:
            va = client.virtual_account.create(data=va_data)
            self.virtual_account_id = va["id"]
            self.status = va["status"]
            self.receivers = va["receivers"]
            if va.get("allowed_payers"):
                self.allowed_payers = va["allowed_payers"]
            self.save()
            frappe.msgprint(f"Virtual Account Created: {self.virtual_account_id}")
            settings = frappe.get_single("Razorpay Settings")
            if settings.enable_zohocliq and settings.accounts_channel_id:
                post_to_zohocliq(
                    message=f"New Virtual Account Created: {self.virtual_account_id} for Customer {self.customer}, Description: {self.description}",
                    channel_id=settings.accounts_channel_id
                )
        except Exception as e:
            frappe.throw(f"Failed to create virtual account: {str(e)}")

    def add_receiver(self, receiver_type, vpa_descriptor=None):
        client, sandbox_mode = get_razorpay_client()
        receiver_data = {"types": [receiver_type]}
        if receiver_type == "vpa" and vpa_descriptor:
            receiver_data["vpa"] = {"descriptor": vpa_descriptor}
        try:
            client.virtual_account.add_receiver(self.virtual_account_id, receiver_data)
            va = client.virtual_account.fetch(self.virtual_account_id)
            self.receivers = va["receivers"]
            self.save()
            frappe.msgprint(f"Receiver {receiver_type} added to Virtual Account {self.virtual_account_id}")
        except Exception as e:
            frappe.throw(f"Failed to add receiver: {str(e)}")

    def add_allowed_payer(self, payer_type, bank_account=None, vpa=None):
        client, sandbox_mode = get_razorpay_client()
        payer_data = {"type": payer_type}
        if payer_type == "bank_account" and bank_account:
            payer_data["bank_account"] = bank_account
        elif payer_type == "vpa" and vpa:
            payer_data["vpa"] = vpa
        try:
            client.virtual_account.add_allowed_payer(self.virtual_account_id, payer_data)
            va = client.virtual_account.fetch(self.virtual_account_id)
            self.allowed_payers = va["allowed_payers"]
            self.save()
            frappe.msgprint(f"Allowed Payer {payer_type} added to Virtual Account {self.virtual_account_id}")
        except Exception as e:
            frappe.throw(f"Failed to add allowed payer: {str(e)}")

    def delete_allowed_payer(self, allowed_payer_id):
        client, sandbox_mode = get_razorpay_client()
        try:
            client.virtual_account.delete_allowed_payer(self.virtual_account_id, allowed_payer_id)
            va = client.virtual_account.fetch(self.virtual_account_id)
            self.allowed_payers = va["allowed_payers"]
            self.save()
            frappe.msgprint(f"Allowed Payer {allowed_payer_id} deleted from Virtual Account {self.virtual_account_id}")
        except Exception as e:
            frappe.throw(f"Failed to delete allowed payer: {str(e)}")

    def close_virtual_account(self):
        client, sandbox_mode = get_razorpay_client()
        try:
            client.virtual_account.close(self.virtual_account_id)
            self.status = "closed"
            self.save()
            frappe.msgprint(f"Virtual Account {self.virtual_account_id} closed successfully.")
            settings = frappe.get_single("Razorpay Settings")
            if settings.enable_zohocliq and settings.accounts_channel_id:
                post_to_zohocliq(
                    message=f"Virtual Account Closed: {self.virtual_account_id}, Customer: {self.customer}",
                    channel_id=settings.accounts_channel_id
                )
        except Exception as e:
            frappe.throw(f"Failed to close virtual account: {str(e)}")