"""
Whitelisted API methods callable from the browser / JS.
"""

import frappe
from frappe import _

from zra_smart_invoice.zra_smart_invoice.api import digitax
from zra_smart_invoice.zra_smart_invoice.events.sales_invoice import _handle_success
from zra_smart_invoice.zra_smart_invoice.utils import retry_submission


@frappe.whitelist()
def submit_invoice(invoice_name: str):
    """Manually submit a Sales Invoice to ZRA from the form toolbar button."""
    doc = frappe.get_doc("Sales Invoice", invoice_name)
    if doc.docstatus != 1:
        frappe.throw(_("Only submitted invoices can be sent to ZRA."))

    settings = digitax.get_settings()
    result = digitax.submit_sales_invoice(doc, settings)
    _handle_success(doc, result)
    return result


@frappe.whitelist()
def retry_invoice(invoice_name: str):
    """Retry a failed ZRA submission for a Sales Invoice."""
    log = frappe.get_all(
        "ZRA Submission Log",
        filters={
            "reference_doctype": "Sales Invoice",
            "reference_name": invoice_name,
            "status": "Failed",
            "submission_type": "Sales Invoice",
        },
        fields=["name"],
        order_by="submitted_at desc",
        limit=1,
    )
    if not log:
        frappe.throw(_("No failed ZRA submission log found for {0}").format(invoice_name))
    return retry_submission(log[0].name)


@frappe.whitelist()
def initialize_device():
    """Run device initialization — called from Setup Wizard page."""
    settings = digitax.get_settings()
    result = digitax.initialize_device(settings)
    return result


@frappe.whitelist()
def test_connection():
    """Test reachability of the DigiTax API. Called from Setup Wizard step 1."""
    import requests
    settings = digitax.get_settings()
    url = f"{settings.get_api_url()}/health"
    headers = settings.get_headers()
    timeout = int(settings.digitax_timeout or 10)
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return {"ok": True, "status": r.status_code}
    except Exception as e:
        frappe.throw(str(e))


@frappe.whitelist()
def get_zra_status():
    """Return a summary of ZRA submission health for the dashboard."""
    total = frappe.db.count("ZRA Submission Log")
    success = frappe.db.count("ZRA Submission Log", {"status": "Success"})
    failed = frappe.db.count("ZRA Submission Log", {"status": "Failed"})
    pending = frappe.db.count("ZRA Submission Log", {"status": ["in", ["Pending", "Retrying"]]})

    return {
        "total": total,
        "success": success,
        "failed": failed,
        "pending": pending,
        "is_initialized": frappe.db.get_single_value("ZRA Settings", "is_initialized"),
        "environment": frappe.db.get_single_value("ZRA Settings", "environment"),
    }
