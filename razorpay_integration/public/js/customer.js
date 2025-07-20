frappe.ui.form.on('Customer', {
    refresh: function (frm) {
        frm.add_custom_button(__('Create Virtual Account'), function () {
            frappe.prompt([
                {
                    fieldname: 'description',
                    fieldtype: 'Data',
                    label: 'Description'
                },
                {
                    fieldname: 'amount',
                    fieldtype: 'Currency',
                    label: 'Expected Amount'
                },
                {
                    fieldname: 'receiver_types',
                    fieldtype: 'Select',
                    label: 'Receiver Type',
                    options: ['bank_account', 'qr_code', 'tpv'],
                    default: 'bank_account'
                },
                {
                    fieldname: 'close_by',
                    fieldtype: 'Date',
                    label: 'Close By'
                }
            ], function (values) {
                if (values.close_by && values.close_by < frappe.datetime.nowdate()) {
                    frappe.msgprint('Close By date must be in the future.');
                    return;
                }
                frappe.call({
                    method: 'razorpay_integration.razorpay_integration.utils.create_virtual_account',
                    args: {
                        customer_name: frm.doc.name,
                        description: values.description,
                        amount: values.amount,
                        receiver_types: values.receiver_types,
                        close_by: values.close_by
                    },
                    callback: function (r) {
                        if (r.message) {
                            frappe.msgprint('Virtual Account Created Successfully: ' + r.message);
                            frm.reload_doc();
                        }
                    }
                });
            }, __('Create Virtual Account'), __('Create'));
        });
    }
});