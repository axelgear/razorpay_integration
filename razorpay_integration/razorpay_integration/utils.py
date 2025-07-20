import frappe
from frappe.utils import get_url, flt, nowdate, get_timestamp, get_datetime, add_days
from frappe import _
from razorpay_integration.razorpay_integration.razorpay_client import get_razorpay_client
from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import save_file
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
    settings = frappe.get_single("Razorpay Settings")
    if settings.enable_zohocliq and settings.accounts_channel_id:
        post_to_zohocliq(
            message=f"New Payment Received: {payment_doc.name}, Amount: {payment_doc.amount_paid}, {'Quotation: ' + payment_doc.quotation if quotation else 'Customer: ' + payment_doc.customer}",
            channel_id=settings.accounts_channel_id
        )

def generate_payment_slip(payment_doc):
    if payment_doc.status not in ["Paid", "Partially Paid"]:
        return
    quotation = frappe.get_doc("Quotation", payment_doc.quotation) if payment_doc.quotation else None
    customer = frappe.get_doc("Customer", payment_doc.customer)
    html = frappe.render_template("razorpay_integration/templates/payment_slip.html", {
        "payment": payment_doc,
        "quotation": quotation,
        "customer": customer
    })
    pdf_data = get_pdf(html)
    file_name = f"Payment_Slip_{payment_doc.name}.pdf"
    file_doc = save_file(file_name, pdf_data, "Razorpay Payment", payment_doc.name, is_private=1)
    payment_doc.db_set("payment_slip", file_doc.file_url)
    frappe.msgprint(f"Payment Slip generated: {file_doc.file_url}")

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
    settings = frappe.get_single("Razorpay Settings")
    if settings.enable_zohocliq and settings.accounts_channel_id:
        post_to_zohocliq(
            message=f"QR Code generated for Quotation {quotation_name}, Virtual Account: {virtual_account_id}, URL: {short_url}",
            channel_id=settings.accounts_channel_id
        )

def create_virtual_account(customer_name, description=None, amount=None, receiver_types="bank_account", close_by=None):
    customer = frappe.get_doc("Customer", customer_name)
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
            "virtual_account_id": va_response["id"],
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
        settings = frappe.get_single("Razorpay Settings")
        if settings.enable_zohocliq and settings.accounts_channel_id:
            post_to_zohocliq(
                message=f"Virtual Account Created: {va_response['id']} for Customer {customer_name}, Description: {va_data['description']}",
                channel_id=settings.accounts_channel_id
            )
        return va_response["id"]
    except Exception as e:
        frappe.throw(f"Failed to create virtual account: {str(e)}")

def regenerate_payment_link(quotation_name, advanced_options=None):
    quotation = frappe.get_doc("Quotation", quotation_name)
    customer = frappe.get_doc("Customer", quotation.customer)
    payment_doc = frappe.get_all("Razorpay Payment", filters={"quotation": quotation_name, "status": ["!=", "Cancelled"]}, limit=1)
    if payment_doc:
        payment_doc = frappe.get_doc("Razorpay Payment", payment_doc[0].name)
    else:
        payment_doc = frappe.get_doc({
            "doctype": "Razorpay Payment",
            "quotation": quotation_name,
            "customer": customer.name,
            "amount": quotation.grand_total,
            "status": "Created"
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
        "accept_partial": advanced_options.get("accept_partial", payment_doc.accept_partial) if advanced_options else payment_doc.accept_partial,
        "first_min_partial_amount": int(advanced_options.get("first_min_partial_amount", payment_doc.first_min_partial_amount) * 100) if advanced_options and advanced_options.get("accept_partial") else 0,
        "expire_by": int(frappe.utils.get_timestamp(advanced_options.get("expire_by") or quotation.valid_till or add_days(nowdate(), 30))),
        "reference_id": advanced_options.get("reference_id") or payment_doc.name if advanced_options else payment_doc.name,
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
        payment_doc.expire_by = advanced_options.get("expire_by") or quotation.valid_till or add_days(nowdate(), 30)
        payment_doc.notify_sms = payment_data["notify"]["sms"]
        payment_doc.notify_email = payment_data["notify"]["email"]
        payment_doc.reminder_enable = payment_data["reminder_enable"]
        payment_doc.upi_link = payment_data["upi_link"]
        payment_doc.description = payment_data["description"]
        payment_doc.options = payment_data.get("options")
        payment_doc.reference_id = payment_data["reference_id"]
        payment_doc.status = "Created"
        payment_doc.save()
        payment_doc.notify_accounts()
        frappe.msgprint(f"Payment Link Regenerated: {payment_link['short_url']}")
        settings = frappe.get_single("Razorpay Settings")
        if settings.enable_zohocliq and settings.accounts_channel_id:
            post_to_zohocliq(
                message=f"Payment Link Regenerated: {payment_link['id']} for Quotation {quotation_name}, Amount: {quotation.grand_total}, Link: {payment_link['short_url']}",
                channel_id=settings.accounts_channel_id
            )
        return payment_link["id"]
    except Exception as e:
        frappe.throw(f"Failed to regenerate payment link: {str(e)}")

def handle_payment_callback(razorpay_payment_id, razorpay_order_id, razorpay_signature):
    settings = frappe.get_single("Razorpay Settings")
    client, sandbox_mode = get_razorpay_client()
    params_dict = {
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_order_id": razorpay_order_id,
        "razorpay_signature": razorpay_signature
    }
    try:
        client.utility.verify_payment_signature(params_dict)
        payment_doc = frappe.get_all("Razorpay Payment", filters={"order_id": razorpay_order_id}, limit=1)
        if payment_doc:
            payment_doc = frappe.get_doc("Razorpay Payment", payment_doc[0].name)
            payment = client.payment.fetch(razorpay_payment_id)
            existing_transaction = next((t for t in payment_doc.transactions if t.payment_id == razorpay_payment_id), None)
            if not existing_transaction:
                payment_doc.append("transactions", {
                    "payment_id": razorpay_payment_id,
                    "amount_paid": payment["amount"] / 100,
                    "status": "Captured" if payment["status"] == "captured" else "Failed",
                    "created_at": get_datetime(payment["created_at"])
                })
                total_paid = sum(t.amount_paid for t in payment_doc.transactions if t.status == "Captured")
                payment_doc.amount_paid = total_paid
                payment_doc.status = "Partially Paid" if payment_doc.accept_partial and total_paid < payment_doc.amount else "Paid"
                payment_doc.payment_id = razorpay_payment_id
                payment_doc.save()
                create_payment_entry(payment_doc)
                generate_payment_slip(payment_doc)
                payment_doc.notify_accounts()
                if payment_doc.quotation:
                    quotation = frappe.get_doc("Quotation", payment_doc.quotation)
                    quotation.db_set("custom_payment_status", payment_doc.status)
                    remaining = payment_doc.amount - total_paid
                    post_to_zohocliq(
                        message=f"Payment Verified for Payment Link {payment_doc.payment_link_id}: Payment ID {razorpay_payment_id}, Amount: {payment['amount'] / 100}, Total Paid: {total_paid}, Remaining: {remaining}, Quotation: {payment_doc.quotation}",
                        channel_id=settings.accounts_channel_id
                    )
                frappe.msgprint(f"Payment {razorpay_payment_id} verified and processed successfully. Total Paid: {total_paid}")
        else:
            frappe.log_error(f"No Razorpay Payment found for order_id: {razorpay_order_id}")
    except Exception as e:
        frappe.log_error(f"Payment verification failed: {str(e)}")
        if settings.enable_zohocliq and settings.accounts_channel_id:
            post_to_zohocliq(
                message=f"Payment Verification Failed for Payment ID {razorpay_payment_id}: {str(e)}",
                channel_id=settings.accounts_channel_id
            )
        frappe.throw(f"Payment verification failed: {str(e)}")

def handle_subscription_payment_callback(razorpay_payment_id, razorpay_subscription_id, razorpay_signature):
    settings = frappe.get_single("Razorpay Settings")
    client, sandbox_mode = get_razorpay_client()
    params_dict = {
        "razorpay_subscription_id": razorpay_subscription_id,
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_signature": razorpay_signature
    }
    try:
        client.utility.verify_subscription_payment_signature(params_dict)
        payment_doc = frappe.get_all("Razorpay Payment", filters={"subscription_id": razorpay_subscription_id}, limit=1)
        if payment_doc:
            payment_doc = frappe.get_doc("Razorpay Payment", payment_doc[0].name)
            payment = client.payment.fetch(razorpay_payment_id)
            existing_transaction = next((t for t in payment_doc.transactions if t.payment_id == razorpay_payment_id), None)
            if not existing_transaction:
                payment_doc.append("transactions", {
                    "payment_id": razorpay_payment_id,
                    "subscription_id": razorpay_subscription_id,
                    "amount_paid": payment["amount"] / 100,
                    "status": "Captured" if payment["status"] == "captured" else "Failed",
                    "created_at": get_datetime(payment["created_at"])
                })
                total_paid = sum(t.amount_paid for t in payment_doc.transactions if t.status == "Captured")
                payment_doc.amount_paid = total_paid
                payment_doc.status = "Partially Paid" if payment_doc.accept_partial and total_paid < payment_doc.amount else "Paid"
                payment_doc.payment_id = razorpay_payment_id
                payment_doc.save()
                create_payment_entry(payment_doc)
                generate_payment_slip(payment_doc)
                payment_doc.notify_accounts()
                if payment_doc.quotation:
                    quotation = frappe.get_doc("Quotation", payment_doc.quotation)
                    quotation.db_set("custom_payment_status", payment_doc.status)
                    remaining = payment_doc.amount - total_paid
                    post_to_zohocliq(
                        message=f"Subscription Payment Verified for Subscription {razorpay_subscription_id}: Payment ID {razorpay_payment_id}, Amount: {payment['amount'] / 100}, Total Paid: {total_paid}, Remaining: {remaining}, Quotation: {payment_doc.quotation}",
                        channel_id=settings.accounts_channel_id
                    )
                frappe.msgprint(f"Subscription Payment {razorpay_payment_id} verified and processed successfully. Total Paid: {total_paid}")
        else:
            frappe.log_error(f"No Razorpay Payment found for subscription_id: {razorpay_subscription_id}")
    except Exception as e:
        frappe.log_error(f"Subscription payment verification failed: {str(e)}")
        if settings.enable_zohocliq and settings.accounts_channel_id:
            post_to_zohocliq(
                message=f"Subscription Payment Verification Failed for Payment ID {razorpay_payment_id}: {str(e)}",
                channel_id=settings.accounts_channel_id
            )
        frappe.throw(f"Subscription payment verification failed: {str(e)}")

def handle_payment_link_callback(payment_link_id, payment_link_reference_id, payment_link_status, razorpay_payment_id, razorpay_signature):
    settings = frappe.get_single("Razorpay Settings")
    client, sandbox_mode = get_razorpay_client()
    params_dict = {
        "payment_link_id": payment_link_id,
        "payment_link_reference_id": payment_link_reference_id,
        "payment_link_status": payment_link_status,
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_signature": razorpay_signature
    }
    try:
        client.utility.verify_payment_link_signature(params_dict)
        payment_doc = frappe.get_all("Razorpay Payment", filters={"payment_link_id": payment_link_id}, limit=1)
        if payment_doc:
            payment_doc = frappe.get_doc("Razorpay Payment", payment_doc[0].name)
            payment = client.payment.fetch(razorpay_payment_id)
            existing_transaction = next((t for t in payment_doc.transactions if t.payment_id == razorpay_payment_id), None)
            if not existing_transaction:
                payment_doc.append("transactions", {
                    "payment_id": razorpay_payment_id,
                    "payment_link_id": payment_link_id,
                    "payment_link_reference_id": payment_link_reference_id,
                    "amount_paid": payment["amount"] / 100,
                    "status": "Captured" if payment["status"] == "captured" else "Failed",
                    "created_at": get_datetime(payment["created_at"])
                })
                total_paid = sum(t.amount_paid for t in payment_doc.transactions if t.status == "Captured")
                payment_doc.amount_paid = total_paid
                payment_doc.status = "Partially Paid" if payment_doc.accept_partial and total_paid < payment_doc.amount else "Paid"
                payment_doc.payment_id = razorpay_payment_id
                payment_doc.payment_link_status = payment_link_status
                payment_doc.save()
                create_payment_entry(payment_doc)
                generate_payment_slip(payment_doc)
                payment_doc.notify_accounts()
                if payment_doc.quotation:
                    quotation = frappe.get_doc("Quotation", payment_doc.quotation)
                    quotation.db_set("custom_payment_status", payment_doc.status)
                    remaining = payment_doc.amount - total_paid
                    post_to_zohocliq(
                        message=f"Payment Link Payment Verified for Payment Link {payment_link_id}: Payment ID {razorpay_payment_id}, Amount: {payment['amount'] / 100}, Total Paid: {total_paid}, Remaining: {remaining}, Quotation: {payment_doc.quotation}, Status: {payment_link_status}",
                        channel_id=settings.accounts_channel_id
                    )
                frappe.msgprint(f"Payment Link Payment {razorpay_payment_id} verified and processed successfully. Total Paid: {total_paid}")
        else:
            frappe.log_error(f"No Razorpay Payment found for payment_link_id: {payment_link_id}")
    except Exception as e:
        frappe.log_error(f"Payment link verification failed: {str(e)}")
        if settings.enable_zohocliq and settings.accounts_channel_id:
            post_to_zohocliq(
                message=f"Payment Link Verification Failed for Payment ID {razorpay_payment_id}: {str(e)}",
                channel_id=settings.accounts_channel_id
            )
        frappe.throw(f"Payment link verification failed: {str(e)}")

def handle_virtual_account_payment(data):
    va_id = data.get("payload", {}).get("virtual_account", {}).get("entity", {}).get("id")
    payment_id = data.get("payload", {}).get("payment", {}).get("entity", {}).get("id")
    amount = data.get("payload", {}).get("payment", {}).get("entity", {}).get("amount") / 100
    order_id = data.get("payload", {}).get("payment", {}).get("entity", {}).get("order_id")
    signature = data.get("razorpay_signature")
    if not va_id or not payment_id or not order_id or not signature:
        frappe.log_error("Invalid virtual account payment webhook data")
        return
    client, sandbox_mode = get_razorpay_client()
    params_dict = {
        "razorpay_payment_id": payment_id,
        "razorpay_order_id": order_id,
        "razorpay_signature": signature
    }
    try:
        client.utility.verify_payment_signature(params_dict)
        va_doc = frappe.get_all("Razorpay Virtual Account", filters={"virtual_account_id": va_id}, limit=1)
        if va_doc:
            va_doc = frappe.get_doc("Razorpay Virtual Account", va_doc[0].name)
            payment_doc = frappe.get_doc({
                "doctype": "Razorpay Payment",
                "customer": va_doc.customer,
                "quotation": va_doc.quotation,
                "project": va_doc.project,
                "sales_order": va_doc.sales_order,
                "amount": amount,
                "amount_paid": amount,
                "payment_id": payment_id,
                "order_id": order_id,
                "status": "Paid",
                "created_at": frappe.utils.now_datetime()
            })
            payment_doc.insert()
            payment_doc.submit()
            create_payment_entry(payment_doc)
            generate_payment_slip(payment_doc)
            frappe.msgprint(f"Virtual Account Payment {payment_id} verified and processed successfully.")
            settings = frappe.get_single("Razorpay Settings")
            if settings.enable_zohocliq and settings.accounts_channel_id:
                post_to_zohocliq(
                    message=f"Virtual Account Payment Verified: {payment_id}, Amount: {amount}, Customer: {va_doc.customer}, Quotation: {va_doc.quotation or 'None'}",
                    channel_id=settings.accounts_channel_id
                )
        else:
            frappe.log_error(f"No Razorpay Virtual Account found for virtual_account_id: {va_id}")
    except Exception as e:
        frappe.log_error(f"Virtual account payment verification failed: {str(e)}")
        settings = frappe.get_single("Razorpay Settings")
        if settings.enable_zohocliq and settings.accounts_channel_id:
            post_to_zohocliq(
                message=f"Virtual Account Payment Verification Failed for Payment ID {payment_id}: {str(e)}",
                channel_id=settings.accounts_channel_id
            )
        frappe.throw(f"Virtual account payment verification failed: {str(e)}")

def process_refund(payment_name, transaction_idx=None, amount=None, speed="normal", receipt=None):
    payment = frappe.get_doc("Razorpay Payment", payment_name)
    if payment.status not in ["Paid", "Partially Paid"]:
        frappe.throw("Cannot refund a non-paid payment.")
    client, sandbox_mode = get_razorpay_client()
    if transaction_idx is not None:
        transaction = payment.transactions[transaction_idx]
        payment_id = transaction.payment_id
        amount = amount or transaction.amount_paid
    else:
        payment_id = payment.payment_id
        amount = amount or payment.amount_paid
    try:
        refund_data = {
            "amount": int(amount * 100),
            "speed": speed,
            "notes": {"reason": f"Refund for {'Quotation ' + payment.quotation if payment.quotation else 'Customer ' + payment.customer}"},
            "receipt": receipt or f"Refund_{payment.name}"
        }
        refund = client.payment.refund(payment_id, refund_data)
        if transaction_idx is not None:
            transaction.refund_id = refund["id"]
            transaction.status = "Refunded"
        payment.status = "Refunded" if payment.amount_paid <= amount else "Partially Paid"
        payment.amount_paid -= amount
        if payment.quotation:
            quotation = frappe.get_doc("Quotation", payment.quotation)
            quotation.db_set("custom_payment_status", payment.status)
            quotation.db_set("custom_advance_amount", flt(quotation.custom_advance_amount) - amount)
        payment.save()
        frappe.msgprint(f"Refund processed successfully: {refund['id']}")
        settings = frappe.get_single("Razorpay Settings")
        if settings.enable_zohocliq and settings.accounts_channel_id:
            post_to_zohocliq(
                message=f"Refund Processed: {refund['id']}, Amount: {amount}, {'Quotation: ' + payment.quotation if payment.quotation else 'Customer: ' + payment.customer}",
                channel_id=settings.accounts_channel_id
            )
    except Exception as e:
        frappe.throw(f"Refund failed: {str(e)}")

def fetch_refunds(payment_name, from_date=None, to_date=None, count=10, skip=0):
    payment = frappe.get_doc("Razorpay Payment", payment_name)
    client, sandbox_mode = get_razorpay_client()
    options = {"count": count, "skip": skip}
    if from_date:
        options["from"] = int(get_timestamp(from_date))
    if to_date:
        options["to"] = int(get_timestamp(to_date))
    try:
        refunds = client.payment.fetch_multiple_refund(payment.payment_id, options)
        return refunds.get("items", [])
    except Exception as e:
        frappe.throw(f"Failed to fetch refunds: {str(e)}")

def fetch_refund(payment_name, refund_id):
    payment = frappe.get_doc("Razorpay Payment", payment_name)
    client, sandbox_mode = get_razorpay_client()
    try:
        refund = client.payment.fetch_refund_id(payment.payment_id, refund_id)
        return refund
    except Exception as e:
        frappe.throw(f"Failed to fetch refund {refund_id}: {str(e)}")

def update_refund(payment_name, refund_id, notes):
    payment = frappe.get_doc("Razorpay Payment", payment_name)
    client, sandbox_mode = get_razorpay_client()
    try:
        refund = client.refund.edit(refund_id, {"notes": notes})
        for transaction in payment.transactions:
            if transaction.refund_id == refund_id:
                transaction.notes = notes
                break
        payment.save()
        frappe.msgprint(f"Refund {refund_id} updated successfully.")
        return refund
    except Exception as e:
        frappe.throw(f"Failed to update refund {refund_id}: {str(e)}")

def fetch_all_settlements(from_date=None, to_date=None, count=10, skip=0):
    client, sandbox_mode = get_razorpay_client()
    options = {"count": count, "skip": skip}
    if from_date:
        options["from"] = int(get_timestamp(from_date))
    if to_date:
        options["to"] = int(get_timestamp(to_date))
    try:
        settlements = client.settlement.all(options)
        for settlement in settlements.get("items", []):
            existing = frappe.db.exists("Razorpay Settlement", {"settlement_id": settlement["id"]})
            if not existing:
                doc = frappe.get_doc({
                    "doctype": "Razorpay Settlement",
                    "settlement_id": settlement["id"],
                    "amount": settlement["amount"] / 100,
                    "status": settlement["status"],
                    "fees": settlement["fees"] / 100,
                    "tax": settlement["tax"] / 100,
                    "utr": settlement["utr"],
                    "created_at": get_datetime(settlement["created_at"]),
                    "settlement_type": "Regular"
                })
                doc.insert()
                frappe.msgprint(f"Settlement {settlement['id']} fetched and saved.")
        settings = frappe.get_single("Razorpay Settings")
        if settings.enable_zohocliq and settings.accounts_channel_id:
            post_to_zohocliq(
                message=f"Fetched {len(settlements.get('items', []))} settlements.",
                channel_id=settings.accounts_channel_id
            )
        return settlements.get("items", [])
    except Exception as e:
        frappe.throw(f"Failed to fetch settlements: {str(e)}")

def fetch_settlement(settlement_id):
    client, sandbox_mode = get_razorpay_client()
    try:
        settlement = client.settlement.fetch(settlement_id)
        existing = frappe.db.exists("Razorpay Settlement", {"settlement_id": settlement["id"]})
        if not existing:
            doc = frappe.get_doc({
                "doctype": "Razorpay Settlement",
                "settlement_id": settlement["id"],
                "amount": settlement["amount"] / 100,
                "status": settlement["status"],
                "fees": settlement["fees"] / 100,
                "tax": settlement["tax"] / 100,
                "utr": settlement["utr"],
                "created_at": get_datetime(settlement["created_at"]),
                "settlement_type": "Regular"
            })
            doc.insert()
            frappe.msgprint(f"Settlement {settlement_id} fetched and saved.")
        settings = frappe.get_single("Razorpay Settings")
        if settings.enable_zohocliq and settings.accounts_channel_id:
            post_to_zohocliq(
                message=f"Settlement {settlement_id} fetched: Amount: {settlement['amount'] / 100}, Status: {settlement['status']}",
                channel_id=settings.accounts_channel_id
            )
        return settlement
    except Exception as e:
        frappe.throw(f"Failed to fetch settlement {settlement_id}: {str(e)}")

def settlement_recon(year, month, day=None, count=10, skip=0):
    client, sandbox_mode = get_razorpay_client()
    options = {"year": year, "month": month, "count": count, "skip": skip}
    if day:
        options["day"] = day
    try:
        recon = client.settlement.report(options)
        for item in recon.get("items", []):
            settlement_doc = frappe.get_all("Razorpay Settlement", filters={"settlement_id": item["settlement_id"]}, limit=1)
            if settlement_doc:
                settlement_doc = frappe.get_doc("Razorpay Settlement", settlement_doc[0].name)
                existing = next((t for t in settlement_doc.transactions if t.entity_id == item["entity_id"]), None)
                if not existing:
                    settlement_doc.append("transactions", {
                        "entity_id": item["entity_id"],
                        "type": item["type"],
                        "debit": item["debit"] / 100,
                        "credit": item["credit"] / 100,
                        "amount": item["amount"] / 100,
                        "currency": item["currency"],
                        "fee": item["fee"] / 100,
                        "tax": item["tax"] / 100,
                        "on_hold": item["on_hold"],
                        "settled": item["settled"],
                        "created_at": get_datetime(item["created_at"]),
                        "settled_at": get_datetime(item["settled_at"]) if item["settled_at"] else None,
                        "settlement_id": item["settlement_id"],
                        "settlement_utr": item["settlement_utr"],
                        "payment_id": item["payment_id"],
                        "order_id": item["order_id"],
                        "method": item["method"],
                        "card_network": item["card_network"],
                        "card_issuer": item["card_issuer"],
                        "card_type": item["card_type"],
                        "dispute_id": item["dispute_id"]
                    })
                    settlement_doc.save()
                    # Link to Razorpay Payment Transactions
                    if item["type"] == "payment" and item["payment_id"]:
                        payment = frappe.get_all("Razorpay Payment", filters={"payment_id": item["payment_id"]}, limit=1)
                        if payment:
                            payment_doc = frappe.get_doc("Razorpay Payment", payment[0].name)
                            for t in payment_doc.transactions:
                                if t.payment_id == item["payment_id"]:
                                    t.settlement_id = item["settlement_id"]
                            payment_doc.save()
                    elif item["type"] == "refund" and item["payment_id"]:
                        payment = frappe.get_all("Razorpay Payment", filters={"payment_id": item["payment_id"]}, limit=1)
                        if payment:
                            payment_doc = frappe.get_doc("Razorpay Payment", payment[0].name)
                            for t in payment_doc.transactions:
                                if t.payment_id == item["payment_id"] and t.refund_id == item["entity_id"]:
                                    t.settlement_id = item["settlement_id"]
                            payment_doc.save()
        settings = frappe.get_single("Razorpay Settings")
        if settings.enable_zohocliq and settings.accounts_channel_id:
            post_to_zohocliq(
                message=f"Settlement reconciliation completed for {year}-{month}{'-' + str(day) if day else ''}: {len(recon.get('items', []))} transactions processed.",
                channel_id=settings.accounts_channel_id
            )
        return recon.get("items", [])
    except Exception as e:
        frappe.throw(f"Settlement reconciliation failed: {str(e)}")

def create_ondemand_settlement(amount, settle_full_balance=False, description=None, notes=None):
    client, sandbox_mode = get_razorpay_client()
    data = {
        "amount": int(amount * 100),
        "settle_full_balance": settle_full_balance,
        "description": description or "On-demand settlement",
        "notes": notes or {}
    }
    try:
        settlement = client.settlement.create_ondemand_settlement(data)
        doc = frappe.get_doc({
            "doctype": "Razorpay Settlement",
            "settlement_id": settlement["id"],
            "amount": settlement["amount_requested"] / 100,
            "amount_settled": settlement["amount_settled"] / 100,
            "amount_pending": settlement["amount_pending"] / 100,
            "amount_reversed": settlement["amount_reversed"] / 100,
            "fees": settlement["fees"] / 100,
            "tax": settlement["tax"] / 100,
            "status": settlement["status"],
            "description": settlement["description"],
            "notes": settlement["notes"],
            "created_at": get_datetime(settlement["created_at"]),
            "settlement_type": "On-Demand"
        })
        doc.insert()
        frappe.msgprint(f"On-demand settlement {settlement['id']} created successfully.")
        settings = frappe.get_single("Razorpay Settings")
        if settings.enable_zohocliq and settings.accounts_channel_id:
            post_to_zohocliq(
                message=f"On-demand settlement {settlement['id']} created: Amount: {settlement['amount_requested'] / 100}, Status: {settlement['status']}",
                channel_id=settings.accounts_channel_id
            )
        return settlement
    except Exception as e:
        frappe.throw(f"Failed to create on-demand settlement: {str(e)}")

def fetch_all_ondemand_settlements(from_date=None, to_date=None, count=10, skip=0):
    client, sandbox_mode = get_razorpay_client()
    options = {"count": count, "skip": skip}
    if from_date:
        options["from"] = int(get_timestamp(from_date))
    if to_date:
        options["to"] = int(get_timestamp(to_date))
    try:
        settlements = client.settlement.fetch_all_ondemand_settlement(options)
        for settlement in settlements.get("items", []):
            existing = frappe.db.exists("Razorpay Settlement", {"settlement_id": settlement["id"]})
            if not existing:
                doc = frappe.get_doc({
                    "doctype": "Razorpay Settlement",
                    "settlement_id": settlement["id"],
                    "amount": settlement["amount_requested"] / 100,
                    "amount_settled": settlement["amount_settled"] / 100,
                    "amount_pending": settlement["amount_pending"] / 100,
                    "amount_reversed": settlement["amount_reversed"] / 100,
                    "fees": settlement["fees"] / 100,
                    "tax": settlement["tax"] / 100,
                    "status": settlement["status"],
                    "description": settlement["description"],
                    "notes": settlement["notes"],
                    "created_at": get_datetime(settlement["created_at"]),
                    "settlement_type": "On-Demand"
                })
                doc.insert()
                frappe.msgprint(f"On-demand settlement {settlement['id']} fetched and saved.")
        settings = frappe.get_single("Razorpay Settings")
        if settings.enable_zohocliq and settings.accounts_channel_id:
            post_to_zohocliq(
                message=f"Fetched {len(settlements.get('items', []))} on-demand settlements.",
                channel_id=settings.accounts_channel_id
            )
        return settlements.get("items", [])
    except Exception as e:
        frappe.throw(f"Failed to fetch on-demand settlements: {str(e)}")

def fetch_ondemand_settlement(settlement_id):
    client, sandbox_mode = get_razorpay_client()
    try:
        settlement = client.settlement.fetch_ondemand_settlement_id(settlement_id)
        existing = frappe.db.exists("Razorpay Settlement", {"settlement_id": settlement["id"]})
        if not existing:
            doc = frappe.get_doc({
                "doctype": "Razorpay Settlement",
                "settlement_id": settlement["id"],
                "amount": settlement["amount_requested"] / 100,
                "amount_settled": settlement["amount_settled"] / 100,
                "amount_pending": settlement["amount_pending"] / 100,
                "amount_reversed": settlement["amount_reversed"] / 100,
                "fees": settlement["fees"] / 100,
                "tax": settlement["tax"] / 100,
                "status": settlement["status"],
                "description": settlement["description"],
                "notes": settlement["notes"],
                "created_at": get_datetime(settlement["created_at"]),
                "settlement_type": "On-Demand"
            })
            doc.insert()
            frappe.msgprint(f"On-demand settlement {settlement_id} fetched and saved.")
        settings = frappe.get_single("Razorpay Settings")
        if settings.enable_zohocliq and settings.accounts_channel_id:
            post_to_zohocliq(
                message=f"On-demand settlement {settlement_id} fetched: Amount: {settlement['amount_requested'] / 100}, Status: {settlement['status']}",
                channel_id=settings.accounts_channel_id
            )
        return settlement
    except Exception as e:
        frappe.throw(f"Failed to fetch on-demand settlement {settlement_id}: {str(e)}")

def generate_customer_uuid(doc, method):
    if not doc.custom_razorpay_customer_id:
        doc.custom_razorpay_customer_id = str(uuid.uuid4())
        doc.save(ignore_permissions=True)
        frappe.db.commit()

def create_payment_link(quotation_name, amount=None, accept_partial=False, first_min_partial_amount=0, expire_by=None, upi_link=False, description=None, notify_sms=True, notify_email=True, reminder_enable=True, options=None, reference_id=None, generate_qr_code=False):
    quotation = frappe.get_doc("Quotation", quotation_name)
    amount = amount or quotation.grand_total
    customer = frappe.get_doc("Customer", quotation.customer)
    if generate_qr_code:
        va_doc = frappe.get_doc({
            "doctype": "Razorpay Virtual Account",
            "customer": customer.name,
            "customer_razorpay_id": customer.custom_razorpay_customer_id,
            "quotation": quotation_name,
            "project": quotation.project,
            "sales_order": quotation.get("custom_sales_order"),
            "description": description or f"QR Code Payment for Quotation {quotation_name}",
            "receiver_types": "qr_code",
            "amount_expected": amount,
            "close_by": expire_by or quotation.valid_till
        })
        va_doc.insert()
        va_doc.submit()
        for receiver in va_doc.receivers:
            if receiver.get("entity") == "qr_code":
                generate_qr_code(va_doc.virtual_account_id, receiver.get("short_url"), quotation_name)
        return va_doc.virtual_account_id
    else:
        payment = frappe.get_doc({
            "doctype": "Razorpay Payment",
            "quotation": quotation_name,
            "customer": quotation.customer,
            "amount": amount,
            "accept_partial": accept_partial,
            "first_min_partial_amount": first_min_partial_amount,
            "expire_by": expire_by or quotation.valid_till,
            "project": quotation.project,
            "sales_order": quotation.get("custom_sales_order"),
            "status": "Created",
            "upi_link": upi_link,
            "description": description,
            "notify_sms": notify_sms,
            "notify_email": notify_email,
            "reminder_enable": reminder_enable,
            "options": options,
            "reference_id": reference_id
        })
        payment.insert()
        payment.submit()
        return payment.payment_link

def update_payment_link_on_revision(new_quotation, previous_quotation):
    payment_doc = frappe.get_all("Razorpay Payment", filters={"quotation": previous_quotation.name, "status": ["!=", "Cancelled"]}, limit=1)
    if payment_doc:
        payment_doc = frappe.get_doc("Razorpay Payment", payment_doc[0].name)
        advanced_options = {
            "description": f"Payment for Quotation {new_quotation.name}",
            "accept_partial": payment_doc.accept_partial,
            "first_min_partial_amount": payment_doc.first_min_partial_amount,
            "expire_by": new_quotation.valid_till or add_days(nowdate(), 30),
            "notify_sms": payment_doc.notify_sms,
            "notify_email": payment_doc.notify_email,
            "reminder_enable": payment_doc.reminder_enable,
            "upi_link": payment_doc.upi_link,
            "reference_id": payment_doc.reference_id or payment_doc.name,
            "options": payment_doc.options
        }
        payment_doc.quotation = new_quotation.name
        payment_doc.amount = new_quotation.grand_total
        payment_doc.save()
        regenerate_payment_link(new_quotation.name, advanced_options)
        frappe.msgprint(f"Payment Link updated for revised Quotation {new_quotation.name}")