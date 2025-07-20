from frappe.model.document import Document
import frappe
from razorpay_integration.razorpay_integration.razorpay_client import get_razorpay_client
from razorpay_integration.razorpay_integration.utils import create_payment_entry, generate_payment_slip
from razorpay_integration.razorpay_integration.zohocliq import post_to_zohocliq
from frappe.utils import get_url, flt, nowdate, get_datetime

class RazorpayPayment(Document):
    def validate(self):
        if not self.quotation and not self.customer:
            frappe.throw("Either Quotation or Customer is mandatory.")
        if not self.amount or self.amount <= 0:
            frappe.throw("Amount must be greater than zero.")
        if self.quotation:
            quotation = frappe.get_doc("Quotation", self.quotation)
            if self.accept_partial and self.first_min_partial_amount > self.amount:
                frappe.throw("First Minimum Partial Amount cannot exceed total amount.")
        if self.upi_link and self.accept_partial:
            frappe.throw("UPI Payment Links do not support partial payments.")
        if self.expire_by and self.expire_by < nowdate():
            frappe.throw("Expiry date must be in the future.")

    def on_submit(self):
        if self.order_id or self.subscription_id or self.payment_link_id:  # For payment links or subscriptions
            self.create_payment_link()
        create_payment_entry(self)
        generate_payment_slip(self)
        self.notify_accounts()

    def create_payment_link(self):
        client, sandbox_mode = get_razorpay_client()
        quotation = frappe.get_doc("Quotation", self.quotation) if self.quotation else None
        customer = frappe.get_doc("Customer", self.customer)
        payment_data = {
            "amount": int(self.amount * 100),
            "currency": quotation.currency or "INR" if quotation else "INR",
            "description": self.description or f"Payment for {'Quotation ' + self.quotation if quotation else 'Customer ' + self.customer}",
            "customer": {
                "name": customer.customer_name,
                "email": customer.email_id or "default@example.com",
                "contact": customer.mobile_no or "9123456780"
            },
            "notify": {
                "sms": self.notify_sms,
                "email": self.notify_email
            },
            "notes": {
                "quotation": self.quotation or "",
                "customer": self.customer,
                "project": self.project or "",
                "sales_order": self.sales_order or "",
                **(self.notes or {})
            },
            "callback_url": get_url(f"/api/method/razorpay_integration.razorpay_integration.utils.handle_payment_link_callback"),
            "callback_method": "get",
            "accept_partial": self.accept_partial,
            "first_min_partial_amount": int(self.first_min_partial_amount * 100) if self.accept_partial else 0,
            "expire_by": int(frappe.utils.get_timestamp(self.expire_by)) if self.expire_by else 0,
            "reference_id": self.reference_id or self.name,
            "reminder_enable": self.reminder_enable,
            "upi_link": self.upi_link
        }
        if self.options:
            payment_data["options"] = self.options
        try:
            payment_link = client.payment_link.create(data=payment_data)
            self.order_id = payment_link["order_id"]
            self.payment_link = payment_link["short_url"]
            self.payment_link_id = payment_link["id"]
            self.payment_link_reference_id = payment_link["reference_id"]
            self.payment_link_status = payment_link["status"]
            self.status = "Created"
            self.save()
            frappe.msgprint(f"Payment Link Created: {payment_link['short_url']}")
            settings = frappe.get_single("Razorpay Settings")
            if settings.enable_zohocliq and settings.accounts_channel_id:
                post_to_zohocliq(
                    message=f"Payment Link Created: {self.name} for {'Quotation ' + self.quotation if self.quotation else 'Customer ' + self.customer}, Amount: {self.amount}, Link: {payment_link['short_url']}",
                    channel_id=settings.accounts_channel_id
                )
        except Exception as e:
            frappe.throw(f"Failed to create payment link: {str(e)}")

    def notify_accounts(self):
        settings = frappe.get_single("Razorpay Settings")
        if settings.accounts_email:
            frappe.sendmail(
                recipients=settings.accounts_email,
                subject=f"New Payment Link Created: {self.name}",
                message=f"Payment Link {self.payment_link} created for {'Quotation ' + self.quotation if self.quotation else 'Customer ' + self.customer} with amount {self.amount}.",
            )
        if settings.enable_zohocliq and settings.accounts_channel_id and self.payment_link:
            post_to_zohocliq(
                message=f"New Payment Link Created: {self.name} for {'Quotation ' + self.quotation if self.quotation else 'Customer ' + self.customer}, Amount: {self.amount}, Link: {self.payment_link}",
                channel_id=settings.accounts_channel_id
            )

    def update_payment_link(self):
        client, sandbox_mode = get_razorpay_client()
        update_data = {
            "reference_id": self.reference_id or self.name,
            "expire_by": int(frappe.utils.get_timestamp(self.expire_by)) if self.expire_by else 0,
            "reminder_enable": self.reminder_enable,
            "notes": self.notes or {}
        }
        try:
            client.payment_link.edit(self.payment_link_id, update_data)
            frappe.msgprint(f"Payment Link {self.payment_link_id} updated successfully.")
        except Exception as e:
            frappe.throw(f"Failed to update payment link: {str(e)}")

    def cancel_payment_link(self):
        client, sandbox_mode = get_razorpay_client()
        try:
            client.payment_link.cancel(self.payment_link_id)
            self.status = "Cancelled"
            self.payment_link_status = "cancelled"
            self.save()
            frappe.msgprint(f"Payment Link {self.payment_link_id} cancelled successfully.")
        except Exception as e:
            frappe.throw(f"Failed to cancel payment link: {str(e)}")

    def send_notification(self, medium):
        client, sandbox_mode = get_razorpay_client()
        try:
            client.payment_link.notifyBy(self.payment_link_id, medium)
            frappe.msgprint(f"Notification sent via {medium} for Payment Link {self.payment_link_id}.")
        except Exception as e:
            frappe.throw(f"Failed to send notification: {str(e)}")