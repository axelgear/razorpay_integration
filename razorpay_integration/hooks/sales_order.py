def after_insert(doc, method):
    from razorpay_integration.zohocliq import post_to_zohocliq
    settings = frappe.get_single("Razorpay Integration Settings")
    if settings.zohocliq_enabled and settings.zohocliq_webhook_url:
        post_to_zohocliq(
            message=f"New Sales Order Created: {doc.name}\nCustomer: {doc.customer}",
            webhook_url=settings.zohocliq_webhook_url
        )