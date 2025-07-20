frappe.ui.form.on('Quotation', {
    refresh: function (frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Create/Regenerate Payment Link'), function () {
                frappe.call({
                    method: 'frappe.client.get',
                    args: {
                        doctype: 'Razorpay Integration Settings',
                        name: 'Razorpay Integration Settings'
                    },
                    callback: function (r) {
                        let settings = r.message;
                        let default_expiry_date = frappe.datetime.add_days(frappe.datetime.nowdate(), settings.default_expiry_days);
                        frappe.prompt([
                            {
                                fieldname: 'regenerate_type',
                                fieldtype: 'Select',
                                label: 'Regeneration Type',
                                options: ['Normal', 'Advanced'],
                                default: 'Normal',
                                reqd: 1
                            },
                            {
                                fieldname: 'description',
                                fieldtype: 'Data',
                                label: 'Description',
                                depends_on: 'eval:doc.regenerate_type=="Advanced"'
                            },
                            {
                                fieldname: 'accept_partial',
                                fieldtype: 'Check',
                                label: 'Accept Partial Payments',
                                default: settings.allow_partial_payments,
                                depends_on: 'eval:doc.regenerate_type=="Advanced"'
                            },
                            {
                                fieldname: 'first_min_partial_amount',
                                fieldtype: 'Currency',
                                label: 'First Minimum Partial Amount',
                                depends_on: 'eval:doc.regenerate_type=="Advanced" && doc.accept_partial==1'
                            },
                            {
                                fieldname: 'expire_by',
                                fieldtype: 'Date',
                                label: 'Expiry Date',
                                default: frm.doc.valid_till || default_expiry_date,
                                depends_on: 'eval:doc.regenerate_type=="Advanced"'
                            },
                            {
                                fieldname: 'upi_link',
                                fieldtype: 'Check',
                                label: 'UPI Payment Link',
                                depends_on: 'eval:doc.regenerate_type=="Advanced"'
                            },
                            {
                                fieldname: 'notify_sms',
                                fieldtype: 'Check',
                                label: 'Notify via SMS',
                                default: 1,
                                depends_on: 'eval:doc.regenerate_type=="Advanced"'
                            },
                            {
                                fieldname: 'notify_email',
                                fieldtype: 'Check',
                                label: 'Notify via Email',
                                default: 1,
                                depends_on: 'eval:doc.regenerate_type=="Advanced"'
                            },
                            {
                                fieldname: 'reminder_enable',
                                fieldtype: 'Check',
                                label: 'Enable Reminders',
                                default: 1,
                                depends_on: 'eval:doc.regenerate_type=="Advanced"'
                            },
                            {
                                fieldname: 'reference_id',
                                fieldtype: 'Data',
                                label: 'Reference ID',
                                depends_on: 'eval:doc.regenerate_type=="Advanced"'
                            },
                            {
                                fieldname: 'options',
                                fieldtype: 'JSON',
                                label: 'Custom Options',
                                depends_on: 'eval:doc.regenerate_type=="Advanced"'
                            }
                        ], function (values) {
                            if (values.regenerate_type === 'Normal') {
                                frappe.call({
                                    method: 'razorpay_integration.razorpay_integration.utils.regenerate_payment_link',
                                    args: {
                                        quotation_name: frm.doc.name
                                    },
                                    callback: function (r) {
                                        if (r.message) {
                                            frappe.msgprint('Payment Link Created/Regenerated Successfully: ' + r.message);
                                            frm.reload_doc();
                                        }
                                    }
                                });
                            } else {
                                if (values.accept_partial && values.upi_link) {
                                    frappe.msgprint('UPI Payment Links do not support partial payments.');
                                    return;
                                }
                                if (values.accept_partial && values.first_min_partial_amount > frm.doc.grand_total) {
                                    frappe.msgprint('First Minimum Partial Amount cannot exceed Quotation Grand Total.');
                                    return;
                                }
                                if (values.expire_by && values.expire_by < frappe.datetime.nowdate()) {
                                    frappe.msgprint('Expiry Date must be in the future.');
                                    return;
                                }
                                frappe.call({
                                    method: 'razorpay_integration.razorpay_integration.utils.regenerate_payment_link',
                                    args: {
                                        quotation_name: frm.doc.name,
                                        advanced_options: {
                                            description: values.description,
                                            accept_partial: values.accept_partial,
                                            first_min_partial_amount: values.first_min_partial_amount,
                                            expire_by: values.expire_by,
                                            upi_link: values.upi_link,
                                            notify_sms: values.notify_sms,
                                            notify_email: values.notify_email,
                                            reminder_enable: values.reminder_enable,
                                            reference_id: values.reference_id,
                                            options: values.options
                                        }
                                    },
                                    callback: function (r) {
                                        if (r.message) {
                                            frappe.msgprint('Payment Link Created/Regenerated Successfully: ' + r.message);
                                            frm.reload_doc();
                                        }
                                    }
                                });
                            }
                        }, __('Create/Regenerate Payment Link'), __('Generate'));
                    }
                });
            });
        }
    }
});