frappe.ui.form.on('Customer', {
    refresh: function(frm) {
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__('Create Virtual Account'), function() {
                frappe.call({
                    method: 'razorpay_integration.razorpay_integration.utils.create_virtual_account',
                    args: {
                        customer: frm.docname
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.msgprint(__('Virtual Account Created'));
                            frm.reload_doc();
                        }
                    }
                });
            }, __('Razorpay'));
        }
    }
});