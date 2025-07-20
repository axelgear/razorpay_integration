from frappe import _

def execute(filters=None):
    columns = [
        {
            "label": _("Payment Link ID"),
            "fieldname": "payment_link_id",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Quotation"),
            "fieldname": "quotation",
            "fieldtype": "Link",
            "options": "Quotation",
            "width": 120
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 120
        },
        {
            "label": _("Amount"),
            "fieldname": "amount",
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "label": _("Amount Paid"),
            "fieldname": "amount_paid",
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Payment ID"),
            "fieldname": "payment_id",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Created At"),
            "fieldname": "created_at",
            "fieldtype": "Datetime",
            "width": 150
        }
    ]

    data = frappe.db.get_all(
        "Razorpay Payment",
        fields=["payment_link_id", "quotation", "customer", "amount", "amount_paid", "status", "payment_id", "created_at"],
        filters=filters or {},
        order_by="created_at desc"
    )

    return columns, data