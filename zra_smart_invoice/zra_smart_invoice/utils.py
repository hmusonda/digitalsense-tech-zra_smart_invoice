"""
Utility functions for ZRA Smart Invoice.
"""

import io
import os

import frappe


def is_zra_enabled() -> bool:
    """Check whether ZRA integration is configured for this site."""
    try:
        tpin = frappe.db.get_single_value("ZRA Settings", "tpin")
        return bool(tpin)
    except Exception:
        return False


def generate_qr_code(invoice_name: str, rcpt_no: str, internal_data: str = "") -> str | None:
    """
    Generate a QR code image for the ZRA receipt and attach it to the invoice.
    Returns the file URL or None on failure.
    """
    try:
        import qrcode

        qr_content = internal_data or rcpt_no
        qr = qrcode.QRCode(version=1, box_size=6, border=2)
        qr.add_data(qr_content)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        filename = f"zra_qr_{invoice_name.replace('/', '-')}.png"

        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": filename,
            "attached_to_doctype": "Sales Invoice",
            "attached_to_name": invoice_name,
            "content": buffer.read(),
            "decode": False,
            "is_private": 0,
        })
        file_doc.save(ignore_permissions=True)
        return file_doc.file_url

    except Exception as e:
        frappe.log_error(f"QR code generation failed for {invoice_name}: {e}", "ZRA QR Code")
        return None


def retry_submission(log_name: str):
    """Manually trigger a retry for a failed submission log entry."""
    log = frappe.get_doc("ZRA Submission Log", log_name)

    if log.status not in ("Failed", "Retrying"):
        frappe.throw(f"Cannot retry a submission with status '{log.status}'")

    doc = frappe.get_doc(log.reference_doctype, log.reference_name)

    from zra_smart_invoice.zra_smart_invoice.api import digitax

    settings = digitax.get_settings()

    if log.reference_doctype == "Sales Invoice":
        if log.submission_type == "Credit Note":
            result = digitax.submit_credit_note(doc, settings)
        else:
            result = digitax.submit_sales_invoice(doc, settings)
    elif log.reference_doctype == "Purchase Invoice":
        result = digitax.submit_purchase_invoice(doc, settings)
    elif log.reference_doctype == "Stock Entry":
        result = digitax.submit_stock_movement(doc, settings)
    else:
        frappe.throw(f"No retry handler for doctype '{log.reference_doctype}'")

    frappe.db.set_value("ZRA Submission Log", log_name, {
        "status": "Success",
        "retry_count": log.retry_count + 1,
        "error_message": "",
    })
    frappe.db.commit()
    return result
