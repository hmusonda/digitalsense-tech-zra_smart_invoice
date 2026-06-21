import frappe

from zra_smart_invoice.zra_smart_invoice.api import digitax
from zra_smart_invoice.zra_smart_invoice.utils import is_zra_enabled


def sync_to_zra(doc, method=None):
    if not is_zra_enabled():
        return

    settings = digitax.get_settings()
    if not settings.is_initialized:
        return

    # Only sync if the item has a ZRA classification code
    if not doc.zra_item_class_code:
        return

    try:
        digitax.register_item(doc, settings)
        frappe.db.set_value("Item", doc.name, "zra_item_synced", 1)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"ZRA item sync failed for {doc.name}: {e}", "ZRA Item Sync")
