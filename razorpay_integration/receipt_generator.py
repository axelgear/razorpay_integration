import frappe
from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import save_file

def generate_payment_slip(payment_doc):
    if payment_doc.status not in ["Paid", "Partially Paid"]:
        return
    quotation = frappe.get_doc("Quotation", payment_doc.quotation)
    customer = frappe.get_doc("Customer", quotation.customer)
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