import frappe
from frappe.utils import get_url, flt, nowdate, get_timestamp, get_datetime, add_days
from frappe import _
from razorpay_integration.razorpay_integration.razorpay_client import get_razorpay_client
from razorpay_integration.razorpay_integration.receipt_generator import generate_payment_slip
from razorpay_integration.razorpay_integration.zohocliq import post_to_zohocliq
import uuid
import qrcode
from io import BytesIO
from PIL import Image

def create_payment_entry(payment_doc):
    if payment_doc.status not in ["Paid", "Partially Paid"]:
        return
    quotation = frappe.get_doc("Quotation", payment_doc.quotation) if payment_doc.quotation else None
    customer = frappe.get_doc("Customer", payment_doc.customer)
    payment_entry = frappe.get_doc({
        "doctype": "Payment Entry",
        "payment_type": "Receive",
        "party_type": "Customer",
        "party": customer.name,
        "posting_date": nowdate(),
        "paid_amount": payment_doc.amount_paid,
        "received_amount": payment_doc.amount_paid,
        "reference_doctype": "Quotation" if quotation else "Customer",
        "reference_name": quotation.name if quotation else customer.name,
        "remarks": f"Razorpay Payment {payment_doc.payment_id or payment_doc.name} for {'Quotation ' + payment_doc.quotation if quotation else 'Customer ' + payment_doc.customer}",
        "company": quotation.company if quotation else frappe.defaults.get_user_default("company"),
        "mode_of_payment": "Razorpay"
    })
    payment_entry.insert(ignore_permissions=True)
    payment_entry.submit()
    frappe.msgprint(f"Payment Entry created: {payment_entry.name}")
    if quotation:
        quotation.db_set("custom_advance_amount", flt(quotation.custom_advance_amount) + payment_doc.amount_paid)
        quotation.db_set("custom_payment_status", payment_doc.status)
    settings = frappe.get_single("Razorpay Integration Settings")
    if settings.zohocliq_enabled and settings.zohocliq_webhook_url:
        post_to_zohocliq(
            message=f"New Payment Received: {payment_doc.name}, Amount: {payment_doc.amount_paid}, {'Quotation: ' + payment_doc.quotation if quotation else 'Customer: ' + payment_doc.customer}",
            webhook_url=settings.zohocliq_webhook_url
        )

def generate_qr_code(virtual_account_id, short_url, quotation_name):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(short_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    file_name = f"QR_Code_{quotation_name}.png"
    file_doc = save_file(file_name, buffer.getvalue(), "Quotation", quotation_name, is_private=1)
    frappe.db.set_value("Quotation", quotation_name, "custom_qr_code", file_doc.file_url)
    frappe.msgprint(f"QR Code generated and attached to Quotation: {file_doc.file_url}")
    settings = frappe.get_single("Razorpay Integration Settings")
    if settings.zohocliq_enabled and settings.zohocliq_webhook_url:
        post_to_zohocliq(
            message=f"QR Code generated for Quotation {quotation_name}, Virtual Account: {virtual_account_id}, URL: {short_url}",
            webhook_url=settings.zohocliq_webhook_url
        )

def create_virtual_account(customer_name, description=None, amount=None, receiver_types="bank_account", close_by=None):
    customer = frappe.get_doc("Customer", customer_name)
    settings = frappe.get_single("Razorpay Integration Settings")
    if not customer.custom_razorpay_customer_id:
        customer.custom_razorpay_customer_id = str(uuid.uuid4())
        customer.save(ignore_permissions=True)
    client, sandbox_mode = get_razorpay_client()
    va_data = {
        "receivers": {"types": [receiver_types]},
        "description": description or f"Virtual Account for Customer {customer_name}",
        "customer_id": customer.custom_razorpay_customer_id,
        "notes": {"customer_name": customer.customer_name}
    }
    if amount:
        va_data["amount"] = int(amount * 100)
    if close_by:
        va_data["close_by"] = int(frappe.utils.get_timestamp(close_by))
    try:
        va_response = client.virtual_account.create(va_data)
        va_doc = frappe.get_doc({
            "doctype": "Razorpay Virtual Account",
            "customer": customer_name,
            "customer_razorpay_id": customer.custom_razorpay_customer_id,
            "virtual_account_id": settings.virtual_account_prefix + va_response["id"],
            "description": va_data["description"],
            "amount_expected": amount if amount else 0,
            "status": va_response["status"],
            "close_by": close_by,
            "receivers": [{"entity": r["entity"], "id": r["id"], "short_url": r.get("short_url")} for r in va_response["receivers"]],
            "created_at": get_datetime(va_response["created_at"])
        })
        va_doc.insert()
        va_doc.submit()
        frappe.msgprint(f"Virtual Account {va_response['id']} created for Customer {customer_name}.")
        if settings.zohocliq_enabled and settings.zohocliq_webhook_url:
            post_to_zohocliq(
                message=f"Virtual Account Created: {va_response['id']} for Customer {customer_name}, Description: {va_data['description']}",
                webhook_url=settings.zohocliq_webhook_url
            )
        return va_response["id"]
    except Exception as e:
        frappe.throw(f"Failed to create virtual account: {str(e)}")

def regenerate_payment_link(quotation_name, advanced_options=None):
    quotation = frappe.get_doc("Quotation", quotation_name)
    customer = frappe.get_doc("Customer", quotation.customer)
    settings = frappe.get_single("Razorpay Integration Settings")
    payment_doc = frappe.get_all("Razorpay Payment", filters={"quotation": quotation_name, "status": ["!=", "Cancelled"]}, limit=1)
    if payment_doc:
        payment_doc = frappe.get_doc("Razorpay Payment", payment_doc[0].name)
    else:
        payment_doc = frappe.get_doc({
            "doctype": "Razorpay Payment",
            "quotation": quotation_name,
            "customer": customer.name,
            "amount": quotation.grand_total,
            "status": "Created",
            "accept_partial": settings.allow_partial_payments
        })
        payment_doc.insert()
    client, sandbox_mode = get_razorpay_client()
    payment_data = {
        "amount": int(quotation.grand_total * 100),
        "currency": quotation.currency or "INR",
        "description": advanced_options.get("description") or f"Payment for Quotation {quotation_name}",
        "customer": {
            "name": customer.customer_name,
            "email": customer.email_id or "default@example.com",
            "contact": customer.mobile_no or "9123456780"
        },
        "notify": {
            "sms": advanced_options.get("notify_sms", 1) if advanced_options else payment_doc.notify_sms,
            "email": advanced_options.get("notify_email", 1) if advanced_options else payment_doc.notify_email
        },
        "notes": {
            "quotation": quotation_name,
            "customer": customer.name,
            "project": quotation.project or "",
            "sales_order": quotation.get("custom_sales_order") or ""
        },
        "callback_url": get_url(f"/api/method/razorpay_integration.razorpay_integration.utils.handle_payment_link_callback"),
        "callback_method": "get",
        "accept_partial": advanced_options.get("accept_partial", settings.allow_partial_payments) if advanced_options else settings.allow_partial_payments,
        "first_min_partial_amount": int(advanced_options.get("first_min_partial_amount", payment_doc.first_min_partial_amount) * 100) if advanced_options and advanced_options.get("accept_partial") else 0,
        "expire_by": int(frappe.utils.get_timestamp(advanced_options.get("expire_by") or quotation.valid_till or add_days(nowdate(), settings.default_expiry_days))),
        "reference_id": advanced_options.get("reference_id") or payment_doc.name,
        "reminder_enable": advanced_options.get("reminder_enable", 1) if advanced_options else payment_doc.reminder_enable,
        "upi_link": advanced_options.get("upi_link", 0) if advanced_options else payment_doc.upi_link
    }
    if advanced_options and advanced_options.get("options"):
        payment_data["options"] = advanced_options["options"]
    try:
        if payment_doc.payment_link_id:
            client.payment_link.cancel(payment_doc.payment_link_id)
            frappe.msgprint(f"Existing Payment Link {payment_doc.payment_link_id} cancelled.")
        payment_link = client.payment_link.create(data=payment_data)
        payment_doc.order_id = payment_link["order_id"]
        payment_doc.payment_link = payment_link["short_url"]
        payment_doc.payment_link_id = payment_link["id"]
        payment_doc.payment_link_reference_id = payment_link["reference_id"]
        payment_doc.payment_link_status = payment_link["status"]
        payment_doc.amount = quotation.grand_total
        payment_doc.accept_partial = payment_data["accept_partial"]
        payment_doc.first_min_partial_amount = advanced_options.get("first_min_partial_amount", payment_doc.first_min_partial_amount) if advanced_options else payment_doc.first_min_partial_amount
        payment_doc.expire_by = advanced_options.get("expire_by") or quotation