import frappe
import requests
from frappe import _

def post_to_zohocliq(message, channel_id=None):
    settings = frappe.get_single("Razorpay Settings")
    if not settings.enable_zohocliq or not settings.zohocliq_webhook_url:
        return
    payload = {"text": message}
    if channel_id:
        payload["channel_id"] = channel_id
    try:
        response = requests.post(settings.zohocliq_webhook_url, json=payload)
        if response.status_code != 200:
            frappe.log_error(f"ZohoCliq notification failed: {response.text}")
    except Exception as e:
        frappe.log_error(f"ZohoCliq notification error: {str(e)}")

def create_project_thread(project):
    settings = frappe.get_single("Razorpay Settings")
    if not settings.enable_zohocliq or not settings.project_channel_id:
        return
    message = f"New Project Created: {project.name}\nDescription: {project.project_name or 'No description provided'}"
    post_to_zohocliq(message, settings.project_channel_id)