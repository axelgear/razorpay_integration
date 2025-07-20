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

Set up Razorpay webhooks in the Razorpay Dashboard:
https://your-site.com/api/method/razorpay_integration.razorpay_integration.utils.handle_payment_callback for payment_link.paid.
https://your-site.com/api/method/razorpay_integration.razorpay_integration.utils.handle_virtual_account_payment for virtual_account.credited.


Configure a ZohoCliq bot with an incoming webhook URL and obtain channel IDs.


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


Custom Fields for Customer:
Label: Razorpay Customer ID
Fieldname: custom_razorpay_customer_id
Fieldtype: Data
Read Only: 1
Select Quotation doctype and add:
Label: QR Code
Fieldname: custom_qr_code
Fieldtype: Attach
Read Only: 1




