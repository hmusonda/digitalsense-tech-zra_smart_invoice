import frappe
from frappe import _

from zra_smart_invoice.zra_smart_invoice.api import digitax
from zra_smart_invoice.zra_smart_invoice.doctype.zra_submission_log.zra_submission_log import create_log
from zra_smart_invoice.zra_smart_invoice.utils import is_zra_enabled


def on_submit(doc, method=None):
    if not is_zra_enabled():
        return

    settings = digitax.get_settings()
    if not settings.auto_submit_purchase_invoice or not settings.is_initialized:
        return

    try:
        result = digitax.submit_purchase_invoice(doc, settings)
        create_log("Purchase Invoice", doc.name, "Purchase Invoice", "Success", response=result)
        frappe.db.set_value("Purchase Invoice", doc.name, {
            "zra_submission_status": "Submitted",
            "zra_submitted_at": frappe.utils.now_datetime(),
        })
        frappe.db.commit()

    except Exception as e:
        create_log("Purchase Invoice", doc.name, "Purchase Invoice", "Failed", error=str(e))
        frappe.db.set_value("Purchase Invoice", doc.name, "zra_submission_status", "Failed")
        frappe.db.commit()
        frappe.log_error(f"ZRA purchase invoice failed for {doc.name}: {e}", "ZRA Purchase Invoice")
