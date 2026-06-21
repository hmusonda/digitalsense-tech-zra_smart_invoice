import frappe

from zra_smart_invoice.zra_smart_invoice.api import digitax
from zra_smart_invoice.zra_smart_invoice.doctype.zra_submission_log.zra_submission_log import create_log
from zra_smart_invoice.zra_smart_invoice.utils import is_zra_enabled


def on_submit(doc, method=None):
    if not is_zra_enabled():
        return

    settings = digitax.get_settings()
    if not settings.auto_sync_stock or not settings.is_initialized:
        return

    # Only sync material issue, receipt, and transfer movements
    relevant_types = {"Material Issue", "Material Receipt", "Material Transfer", "Manufacture"}
    if doc.stock_entry_type not in relevant_types:
        return

    try:
        result = digitax.submit_stock_movement(doc, settings)
        create_log("Stock Entry", doc.name, "Stock Movement", "Success", response=result)
    except Exception as e:
        create_log("Stock Entry", doc.name, "Stock Movement", "Failed", error=str(e))
        frappe.log_error(f"ZRA stock sync failed for {doc.name}: {e}", "ZRA Stock Sync")
