import frappe

from zra_smart_invoice.zra_smart_invoice.api import digitax
from zra_smart_invoice.zra_smart_invoice.utils import is_zra_enabled


def sync_to_zra(doc, method=None):
    if not is_zra_enabled():
        return

    settings = digitax.get_settings()
    if not settings.is_initialized:
        return

    # Only sync customers that have a ZRA TPIN (B2B customers)
    if not doc.zra_customer_tpin:
        return

    try:
        digitax.register_customer(doc, settings)
        frappe.db.set_value("Customer", doc.name, "zra_customer_synced", 1)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"ZRA customer sync failed for {doc.name}: {e}", "ZRA Customer Sync")
