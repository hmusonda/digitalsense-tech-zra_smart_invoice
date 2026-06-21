// ZRA Smart Invoice — Sales Invoice form extensions

frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		if (!frm.doc.docstatus === 1) return;

		// Show ZRA status indicator in the form toolbar
		if (frm.doc.zra_submission_status) {
			const colour = {
				Submitted: "green",
				Failed: "red",
				Pending: "orange",
				"Not Required": "grey",
			}[frm.doc.zra_submission_status] || "grey";

			frm.page.set_indicator(
				`ZRA: ${frm.doc.zra_submission_status}`,
				colour
			);
		}

		// Manual retry button for failed submissions
		if (frm.doc.docstatus === 1 && frm.doc.zra_submission_status === "Failed") {
			frm.add_custom_button(__("Retry ZRA Submission"), () => {
				frappe.confirm(
					__("Retry submitting this invoice to ZRA?"),
					() => {
						frappe.call({
							method: "zra_smart_invoice.zra_smart_invoice.api.whitelisted.retry_invoice",
							args: { invoice_name: frm.doc.name },
							freeze: true,
							freeze_message: __("Submitting to ZRA..."),
							callback(r) {
								if (!r.exc) {
									frappe.show_alert({ message: __("ZRA submission successful"), indicator: "green" });
									frm.reload_doc();
								}
							},
						});
					}
				);
			}, __("ZRA"));
		}

		// Manual submit button for invoices not yet sent
		if (frm.doc.docstatus === 1 && !frm.doc.zra_receipt_number) {
			frm.add_custom_button(__("Submit to ZRA"), () => {
				frappe.call({
					method: "zra_smart_invoice.zra_smart_invoice.api.whitelisted.submit_invoice",
					args: { invoice_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Submitting to ZRA..."),
					callback(r) {
						if (!r.exc) {
							frappe.show_alert({ message: __("ZRA submission successful"), indicator: "green" });
							frm.reload_doc();
						}
					},
				});
			}, __("ZRA"));
		}
	},
});
