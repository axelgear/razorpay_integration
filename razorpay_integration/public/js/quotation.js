frappe.ui.form.on('Quotation', {
    refresh: function(frm) {
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__('Create Payment Link'), function() {
                frappe.call({
                    method: 'razorpay_integration.razorpay_integration.utils.create_payment_link',
                    args: {
                        doctype: frm.doctype,
                        docname: frm.docname
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.msgprint(__('Payment Link Created'));
                            frm.reload_doc();
                        }
                    }
                });
            }, __('Create'));

            frm.add_custom_button(__('Generate QR Code'), function() {
                frappe.call({
                    method: 'razorpay_integration.razorpay_integration.utils.generate_qr_code',
                    args: {
                        doctype: frm.doctype,
                        docname: frm.docname
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.msgprint(__('QR Code Generated'));
                            frm.reload_doc();
                        }
                    }
                });
            }, __('Create'));
        }
    }
});