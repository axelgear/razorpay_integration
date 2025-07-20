import frappe
import requests
from frappe import _

def post_to_zohocliq(message, webhook_url=None):
    """
    Send a message to ZohoCliq using the provided or configured webhook URL.
    """
    settings = frappe.get_single("Razorpay Integration Settings")
    if not settings.zohocliq_enabled or not settings.zohocliq_webhook_url:
        return
    webhook_url = webhook_url or settings.zohocliq_webhook_url
    payload = {"text": message}
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code != 200:
            frappe.log_error(f"ZohoCliq notification failed: {response.text}")
        else:
            frappe.log(f"ZohoCliq notification sent: {message}")
    except Exception as e:
        frappe.log_error(f"ZohoCliq notification error: {str(e)}")

def create_project_thread(project):
    """
    Send a ZohoCliq notification for a new project.
    """
    settings = frappe.get_single("Razorpay Integration Settings")
    if not settings.zohocliq_enabled or not settings.zohocliq_webhook_url:
        return
    message = f"New Project Created: {project.name}\nDescription: {project.project_name or 'No description provided'}"
    post_to_zohocliq(message, settings.zohocliq_webhook_url)