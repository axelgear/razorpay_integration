app_name = "razorpay_integration"
app_title = "Razorpay Integration"
app_publisher = "Your Name"
app_description = "Razorpay Integration for ERPNext"
app_icon = "octicon octicon-credit-card"
app_color = "blue"
app_email = "your.email@example.com"
app_license = "MIT"

webhooks = {
    "payment_link.paid": "razorpay_integration.razorpay_integration.utils.handle_payment_link_callback",
    "subscription.charged": "razorpay_integration.razorpay_integration.utils.handle_subscription_payment_callback",
    "virtual_account.credited": "razorpay_integration.razorpay_integration.utils.handle_virtual_account_payment"
}

app_include_js = [
    "/assets/razorpay_integration/js/quotation.bundle.js",
    "/assets/razorpay_integration/js/customer.bundle.js"
]

doc_events = {
    "Quotation": {
        "after_insert": "razorpay_integration.razorpay_integration.utils.handle_quotation_version",
        "on_update": "razorpay_integration.razorpay_integration.utils.handle_quotation_revision"
    },
    "Project": {
        "after_insert": "razorpay_integration.razorpay_integration.zohocliq.create_project_thread"
    },
    "Task": {
        "after_insert": "razorpay_integration.razorpay_integration.utils.notify_task_assignment"
    },
    "Sales Order": {
        "after_insert": "razorpay_integration.razorpay_integration.utils.notify_sales_order_creation"
    },
    "Customer": {
        "after_insert": "razorpay_integration.razorpay_integration.utils.generate_customer_uuid",
        "on_update": "razorpay_integration.razorpay_integration.utils.generate_customer_uuid"
    }
}

print_format = {
    "Quotation": {
        "Standard QR Code Format": "razorpay_integration/templates/quotation_print.html"
    }
}

reports = {
    "Payment Link Transactions": {
        "report_name": "Payment Link Transactions",
        "doctype": "Razorpay Payment",
        "module": "Razorpay Integration"
    }
}

def handle_quotation_version(doc, method):
    if doc.__islocal or not doc.__previous_doc:
        return
    previous = doc.__previous_doc
    doc.custom_advance_amount = previous.get("custom_advance_amount", 0)

def handle_quotation_revision(doc, method):
    if doc.__islocal or not doc.__previous_doc:
        return
    previous = doc.__previous_doc
    payment_doc = frappe.get_all("Razorpay Payment", filters={"quotation": previous.name, "status": ["!=", "Cancelled"]}, limit=1)
    if payment_doc:
        frappe.get_doc("Razorpay Payment", payment_doc[0].name).update_payment_link_on_revision(doc, previous)

def notify_task_assignment(doc, method):
    settings = frappe.get_single("Razorpay Integration Settings")
    if settings.zohocliq_enabled and settings.zohocliq_webhook_url:
        post_to_zohocliq(
            message=f"New Task Assigned: {doc.subject}, Project: {doc.project or 'None'}",
            webhook_url=settings.zohocliq_webhook_url
        )

def notify_sales_order_creation(doc, method):
    settings = frappe.get_single("Razorpay Integration Settings")
    if settings.zohocliq_enabled and settings.zohocliq_webhook_url:
        post_to_zohocliq(
            message=f"New Sales Order Created: {doc.name}, Customer: {doc.customer}, Amount: {doc.grand_total}",
            webhook_url=settings.zohocliq_webhook_url
        )