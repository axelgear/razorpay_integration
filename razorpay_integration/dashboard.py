from frappe import _

def get_data():
    return {
        "fieldname": "name",
        "transactions": [
            {
                "label": _("Razorpay Payments"),
                "items": ["Razorpay Payment"]
            },
            {
                "label": _("Virtual Accounts"),
                "items": ["Razorpay Virtual Account"]
            },
            {
                "label": _("Settlements"),
                "items": ["Razorpay Settlement"]
            }
        ]
    }