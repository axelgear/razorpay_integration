# Razorpay Integration for ERPNext

A custom ERPNext app that integrates Razorpay's payment gateway and Smart Collect features, including virtual accounts, payment links, QR codes, partial payments, refunds, settlements, and payment verifications. It connects with Quotations, Sales Orders, Customers, Projects, and Payment Entries, with advanced features like auto-expiring links, receipt generation, QR codes for Quotations, multiple payment tracking, settlement management, payment verification, manual virtual account creation, payment link regeneration, and notifications via email and ZohoCliq.

## Features
- **Virtual Accounts**: Create manually via a button on the Customer page or automatically for QR codes; support bank accounts, QR codes, or TPV; add/delete allowed payers; close accounts; fetch payments; process normal/instant refunds.
- **Customer UUID**: Automatically generate a unique UUID for each customer (`custom_razorpay_customer_id`) for Razorpay virtual accounts.
- **QR Codes**: Generate QR codes for Quotations via the "Create Payment Link" button, attached as images and included in printable PDF format.
- **Payment Links**: Create or regenerate manually via a button on the Quotation page (normal or advanced options); support UPI links, custom checkout labels, prefilled fields, payment methods, and thematic changes.
- **Multiple Payments Tracking**: Track multiple payments for a single payment link via the `Razorpay Payment Transactions` child table and a dedicated report.
- **Settlements**: Fetch all settlements, fetch specific settlements, perform settlement reconciliation, create on-demand settlements, and fetch on-demand settlements via `Razorpay Settlement` doctype.
- **Refunds**: Process normal or instant refunds, fetch refund details, and update refund notes via `Razorpay Payment` doctype.
- **Partial Payments**: Supported for non-UPI payment links; tracked in `Razorpay Payment` and its transactions table.
- **Payment Verification**: Verify payments, subscription payments, and payment link payments using `verify_payment_signature`, `verify_subscription_payment_signature`, and `verify_payment_link_signature`.
- **Quotation Revision**: Automatically update payment links on quotation revision with new quotation number, amount, and extended expiry.
- **Auto-creation**: Payment Entries and payment slips generated on payment confirmation.
- **Sandbox Mode**: Toggle between sandbox and production modes with a checkbox in `Razorpay Settings`. Use separate `Sandbox API Key` and `Sandbox API Secret` for testing, and `Production API Key` and `Production API Secret` for live mode.
- **Auto-expiring Links**: Based on Quotation validity or custom expiry, extended on revision.
- **Dashboard**: View and sync unpaid payments, virtual accounts, settlements, and payment link transactions.
- **Notifications**: Email to accounts; ZohoCliq messages for payment links, payments, QR codes, refunds, settlements, tasks, sales orders, verification failures, and virtual account creation.
- **Connections**: Payments, Virtual Accounts, and Settlements link to Projects, Sales Orders, Quotations, and Customers.
- **Quotation Versioning**: Advance amounts carried forward on revision.

## Installation
1. Install the app:
   ```bash
   bench --site [your-site-name] install-app razorpay_integration

Install dependencies:pip install -r apps/razorpay_integration/requirements.txt


Run migrations:bench migrate
bench build
bench restart



Configuration

Go to Razorpay Settings in ERPNext.
Enter:
Production API Key and Production API Secret (from Razorpay Dashboard for live mode).
Sandbox API Key and Sandbox API Secret (from Razorpay Dashboard for sandbox mode).
Webhook Secret (for webhook verification).
ZohoCliq Webhook URL, Accounts Channel ID, and Project Channel ID (from ZohoCliq).
Accounts Email for notifications.


Check Use Sandbox Mode to enable sandbox testing, or uncheck for live mode.
Check Enabled to activate the integration and Enable ZohoCliq for notifications.
Set up Razorpay webhooks in the Razorpay Dashboard:
https://your-site.com/api/method/razorpay_integration.razorpay_integration.utils.handle_payment_callback for payment_link.paid.
https://your-site.com/api/method/razorpay_integration.razorpay_integration.utils.handle_virtual_account_payment for virtual_account.credited.


Configure a ZohoCliq bot with an incoming webhook URL and obtain channel IDs.



Add a custom field to Quotation:

custom_payment_status (Select: Pending, Paid, Refunded)

Custom Fields for Quotation:

custom_payment_status (Select: Pending, Partially Paid, Paid, Refunded)
custom_advance_amount (Currency, Default 0)
custom_sales_order (Link, Sales Order)
project (Link, Project, fetched from Sales Order if exists

Custom Field Setup
Go to Customize Form in ERPNext.
Select Customer doctype.
Add a new field:
Label: Razorpay Customer ID
Fieldname: custom_razorpay_customer_id
Fieldtype: Data
Read Only: 1

Custom Fields for Quotation:

custom_payment_status (Select: Pending, Partially Paid, Paid, Refunded)
custom_advance_amount (Currency, Default 0)
custom_sales_order (Link, Sales Order)
project (Link, Project, fetched from Sales Order if exists)

Displays the current state of the Payment Link. Possible values:
created
partially_paid
expired
cancelled
paid


Add Custom Fields:
Go to Customize Form in ERPNext.
Select Customer doctype and add:
Label: Razorpay Customer ID
Fieldname: custom_razorpay_customer_id
Fieldtype: Data
Read Only: 1
Select Quotation doctype and add:
Label: QR Code
Fieldname: custom_qr_code
Fieldtype: Attach
Read Only: 1



Save and run bench migrate.




Custom Field Setup

Go to Customize Form in ERPNext.
Select Customer doctype and add:
Label: Razorpay Customer ID
Fieldname: custom_razorpay_customer_id
Fieldtype: Data
Read Only: 1


Select Quotation doctype and add:
Label: QR Code
Fieldname: custom_qr_code
Fieldtype: Attach
Read Only: 1


Save and run bench migrate.

Usage

Customer UUID: Automatically generated for each Customer (custom_razorpay_customer_id).
Virtual Accounts:
Create via Razorpay Virtual Account doctype, supporting bank accounts, QR codes, or TPV.
Payments processed via virtual_account.credited webhook, creating Razorpay Payment records.


QR Codes:
Generate via "Create Payment Link" button on submitted Quotations by selecting "Generate QR Code".
QR code attached to Quotation (custom_qr_code) and included in printable PDF (Standard QR Code Format).


Payment Links:
Create via "Create Payment Link" button with advanced options (UPI, custom labels, etc.).
Enable Accept Partial Payments to allow multiple payments.


Multiple Payments Tracking:
View all payments for a payment link in the Razorpay Payment doctype’s Payment Transactions child table.
Use the Payment Link Transactions report to view transactions by payment_link_id.


Settlements:
Fetch all settlements or a specific settlement via Razorpay Settlement doctype using fetch_all_settlements or fetch_settlement.
Perform settlement reconciliation with settlement_recon, linking transactions to Razorpay Payment Transactions.
Create on-demand settlements with create_ondemand_settlement.
Fetch on-demand settlements with fetch_all_ondemand_settlements or fetch_ondemand_settlement.
View settlement details and transactions in the Razorpay Settlement doctype and dashboard.


Refunds:
Process normal or instant refunds for individual transactions via Razorpay Payment doctype.
Fetch multiple refunds, specific refunds, or all refunds via API methods.
Update refund notes as needed.


Payment Entries and Slips: Auto-generated for each payment (including partial payments).
Dashboard: View and sync unpaid payments (get_unpaid_payments_dashboard), virtual accounts (get_virtual_accounts_dashboard), settlements (get_settlements_dashboard), and payment link transactions (get_payment_link_transactions).
Notifications:
Email to accounts for payment links and payments.
ZohoCliq notifications to accounts_channel_id for payment links, payments, QR codes, refunds, settlements, and sales orders, including total paid and remaining balance for partial payments.
ZohoCliq notifications to project_channel_id for project threads and task assignments.


Quotation Versioning: Advance amounts (custom_advance_amount) carried forward during revisions.

Sandbox Testing

Use the Razorpay Sandbox URL (https://api.razorpay.com/v1/ or v2/ for specific APIs) with test API keys from the Razorpay Dashboard.
In Razorpay Settings, check Use Sandbox Mode and enter Sandbox API Key and Sandbox API Secret (obtained from Razorpay Dashboard in test mode).
Initialize the Razorpay client in razorpay_client.py with the appropriate keys based on the use_sandbox setting:import razorpay
client = razorpay.Client(auth=(settings.sandbox_api_key, settings.sandbox_api_secret))  # For sandbox mode
# OR
client = razorpay.Client(auth=(settings.api_key, settings.api_secret))  # For production mode


Test payments, refunds, and settlements using test card details, UPI handles, and QR codes from the Razorpay Dashboard.

Notes

Security: Store API keys, webhook secrets, and channel IDs in Razorpay Settings.
Testing: Use Razorpay’s sandbox mode with test keys. Test card details, UPI handles, and QR codes available in Razorpay Dashboard.
Webhooks: Ensure ERPNext site is publicly accessible. Use ngrok for local testing.
ZohoCliq: Requires bot with webhook URL and channel IDs configured.
Razorpay Limitations: QR codes require amount_expected; UPI links do not support partial payments; prefilled card details for testing only.
Dependencies: Requires razorpay, qrcode, and Pillow.
Reports: Use Payment Link Transactions report to track multiple payments for a single payment link.
Settlements: Reconciliation links payments and refunds to Razorpay Payment Transactions for tracking.
