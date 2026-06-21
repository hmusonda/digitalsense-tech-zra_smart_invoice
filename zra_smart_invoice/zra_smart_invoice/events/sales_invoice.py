"""
Sales Invoice event handlers.
Fires on submit (new invoice → ZRA) and on cancel (credit note → ZRA).
"""

import frappe
from frappe import _

from zra_smart_invoice.zra_smart_invoice.api import digitax
from zra_smart_invoice.zra_smart_invoice.doctype.zra_submission_log.zra_submission_log import create_log
from zra_smart_invoice.zra_smart_invoice.utils import generate_qr_code, is_zra_enabled


def on_submit(doc, method=None):
    if not is_zra_enabled():
        return

    settings = digitax.get_settings()
    if not settings.auto_submit_sales_invoice:
        return

    if not settings.is_initialized:
        frappe.msgprint(
            _("ZRA device not initialized. Invoice saved but NOT submitted to ZRA. "
              "Complete ZRA Setup Wizard to enable automatic submission."),
            indicator="orange",
            alert=True,
        )
        return

    try:
        result = digitax.submit_sales_invoice(doc, settings)
        _handle_success(doc, result)

    except Exception as e:
        create_log("Sales Invoice", doc.name, "Sales Invoice", "Failed", error=str(e))
        frappe.db.set_value("Sales Invoice", doc.name, {
            "zra_submission_status": "Failed",
            "zra_error_message": str(e),
        })
        frappe.db.commit()

        if not settings.submit_on_error:
            frappe.throw(
                _("ZRA submission failed: {0}<br><br>"
                  "The invoice has NOT been submitted. Fix the error and resubmit, "
                  "or enable 'Allow submission on ZRA error' in ZRA Settings.").format(str(e))
            )
        else:
            frappe.msgprint(
                _("Invoice submitted but ZRA submission failed: {0}. "
                  "It will be retried automatically.").format(str(e)),
                indicator="orange",
                alert=True,
            )


def on_cancel(doc, method=None):
    if not is_zra_enabled():
        return

    settings = digitax.get_settings()
    if not settings.is_initialized:
        return

    if not doc.zra_receipt_number:
        # Invoice was never submitted to ZRA — nothing to cancel
        return

    try:
        result = digitax.submit_credit_note(doc, settings)
        rcpt_no = result.get("data", {}).get("rcptNo") or result.get("rcptNo")
        create_log("Sales Invoice", doc.name, "Credit Note", "Success",
                   response=result, rcpt_no=rcpt_no)

    except Exception as e:
        create_log("Sales Invoice", doc.name, "Credit Note", "Failed", error=str(e))
        frappe.log_error(
            f"ZRA credit note failed for {doc.name}: {e}", "ZRA Credit Note"
        )


def _handle_success(doc, result):
    """Store ZRA receipt data back on the invoice and log."""
    data = result.get("data", {}) or result
    rcpt_no = data.get("rcptNo") or data.get("receipt_number")
    internal_data = data.get("intrlData") or data.get("internal_data") or ""

    qr_path = None
    if rcpt_no:
        qr_path = generate_qr_code(doc.name, rcpt_no, internal_data)

    frappe.db.set_value("Sales Invoice", doc.name, {
        "zra_receipt_number": rcpt_no,
        "zra_internal_data": internal_data,
        "zra_qr_code": qr_path,
        "zra_submission_status": "Submitted",
        "zra_submitted_at": frappe.utils.now_datetime(),
        "zra_error_message": "",
    })
    frappe.db.commit()

    create_log("Sales Invoice", doc.name, "Sales Invoice", "Success",
               response=result, rcpt_no=rcpt_no)

    frappe.msgprint(
        _("✓ Invoice submitted to ZRA. Receipt No: <b>{0}</b>").format(rcpt_no),
        indicator="green",
        alert=True,
    )
