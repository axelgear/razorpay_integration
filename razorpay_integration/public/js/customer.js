frappe.ui.form.on('Customer', {
    refresh: function (frm) {
        frm.add_custom_button(__('Create Virtual Account'), function () {
            frappe.prompt([
                {
                    fieldname: 'description',
                    fieldtype: 'Data',
                    label: 'Description',
                    default: `Virtual Account for Customer ${frm.doc.name}`
                },
                {
                    fieldname: 'amount',
                    fieldtype: 'Currency',
                    label: 'Amount'
                },
                {
                    fieldname: 'receiver_types',
                    fieldtype: 'Select',
                    label: 'Receiver Types',
                    options: ['bank_account', 'qr_code', 'tpv'],
                    default: 'bank_account'
                },
                {
                    fieldname: 'close_by',
                    fieldtype: 'Date',
                    label: 'Close By'
                }
            ], function (values) {
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
                            frappe.msgprint(`Virtual Account Created: ${r.message}`);
                            frm.reload_doc();
                        }
                    }
                });
            }, __('Create Virtual Account'), __('Create'));
        });
    }
});