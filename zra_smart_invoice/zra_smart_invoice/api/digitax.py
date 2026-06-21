"""
DigiTax API Client
==================
Handles all HTTP communication between ERPNext and DigiTax middleware,
which in turn forwards to ZRA Smart Invoice System (SIS).

Each method maps to a ZRA VSDC API endpoint category:
  - Device Initialization
  - Item Registration
  - Customer (Branch Customer) Registration
  - Sales Invoice Submission
  - Credit Note Submission
  - Purchase Invoice Submission
  - Stock Movement Submission

ZRA VSDC API Spec v1.0.7 reference:
  https://www.zra.org.zm/wp-content/uploads/2024/08/VSDC-API-Specification-Document-v1.0.7-1.pdf
"""

import json

import frappe
import requests
from frappe import _


def get_settings():
    """Return ZRA Settings singleton for current site."""
    settings = frappe.get_single("ZRA Settings")
    if not settings.tpin:
        frappe.throw(_("ZRA Settings not configured. Please complete ZRA Setup first."))
    return settings


def _make_request(method: str, endpoint: str, payload: dict = None, settings=None) -> dict:
    """
    Core HTTP request handler.
    Raises frappe.ValidationError on non-2xx responses so callers can catch cleanly.
    """
    if not settings:
        settings = get_settings()

    url = f"{settings.get_api_url()}{endpoint}"
    headers = settings.get_headers()
    timeout = int(settings.digitax_timeout or 30)

    try:
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        frappe.throw(_("ZRA API request timed out after {0}s. Will retry.").format(timeout))
    except requests.exceptions.ConnectionError as e:
        frappe.throw(_("Cannot connect to DigiTax API: {0}").format(str(e)))
    except requests.exceptions.HTTPError as e:
        try:
            error_body = response.json()
        except Exception:
            error_body = response.text
        frappe.throw(
            _("DigiTax API error [{0}]: {1}").format(response.status_code, json.dumps(error_body))
        )


# -------------------------------------------------------------------
# Device Initialization
# Called once per site to register the VSDC with ZRA.
# -------------------------------------------------------------------

def initialize_device(settings=None) -> dict:
    """
    POST /initializer/selectInitInfo
    Registers this site's device with ZRA via DigiTax.
    Returns security keys stored in ZRA Settings.
    """
    if not settings:
        settings = get_settings()

    payload = {
        "tpin": settings.tpin,
        "bhfId": settings.branch_id,
        "dvcSrlNo": settings.device_serial_no,
    }
    result = _make_request("POST", "/vsdc/initializer/selectInitInfo", payload, settings)

    if result.get("resultCd") == "000":
        # Mark as initialized
        frappe.db.set_value("ZRA Settings", "ZRA Settings", "is_initialized", 1)
        frappe.db.commit()

    return result


# -------------------------------------------------------------------
# Item Registration
# -------------------------------------------------------------------

def register_item(item_doc, settings=None) -> dict:
    """
    POST /items/saveItem
    Registers or updates an item in ZRA Smart Invoice.
    """
    if not settings:
        settings = get_settings()

    payload = {
        "tpin": settings.tpin,
        "bhfId": settings.branch_id,
        "itemCd": item_doc.item_code,
        "itemClsCd": item_doc.zra_item_class_code or "5020230602",  # default unclassified
        "itemTyCd": "1" if item_doc.is_stock_item else "2",  # 1=product, 2=service
        "itemNm": item_doc.item_name,
        "itemStdNm": item_doc.item_name,
        "orgnNatCd": "ZM",
        "pkgUnitCd": "NT",  # Unit — map from ERPNext UOM if needed
        "qtyUnitCd": item_doc.stock_uom or "NT",
        "taxTyCd": _get_tax_type(item_doc),
        "dftPrc": float(item_doc.standard_rate or 0),
        "useYn": "Y",
        "regrNm": frappe.session.user,
        "regrId": frappe.session.user,
        "modrNm": frappe.session.user,
        "modrId": frappe.session.user,
    }
    return _make_request("POST", "/vsdc/items/saveItem", payload, settings)


# -------------------------------------------------------------------
# Customer Registration
# -------------------------------------------------------------------

def register_customer(customer_doc, settings=None) -> dict:
    """
    POST /customers/saveBhfCustomer
    Registers a customer against this branch in ZRA.
    """
    if not settings:
        settings = get_settings()

    payload = {
        "tpin": settings.tpin,
        "bhfId": settings.branch_id,
        "custNo": customer_doc.name,
        "custTpin": customer_doc.zra_customer_tpin or "",
        "custNm": customer_doc.customer_name,
        "adrs": _get_customer_address(customer_doc),
        "useYn": "Y",
        "regrNm": frappe.session.user,
        "regrId": frappe.session.user,
        "modrNm": frappe.session.user,
        "modrId": frappe.session.user,
    }
    return _make_request("POST", "/vsdc/customers/saveBhfCustomer", payload, settings)


# -------------------------------------------------------------------
# Sales Invoice Submission
# -------------------------------------------------------------------

def submit_sales_invoice(invoice_doc, settings=None) -> dict:
    """
    POST /trnsSales/saveSales
    Submits a Sales Invoice to ZRA via DigiTax.
    Returns rcptNo and other ZRA receipt data.
    """
    if not settings:
        settings = get_settings()

    payload = {
        "tpin": settings.tpin,
        "bhfId": settings.branch_id,
        "orgInvcNo": None,  # null for new invoice, set for credit notes
        "cisInvcNo": invoice_doc.name,
        "custTpin": _get_customer_tpin(invoice_doc),
        "custNm": invoice_doc.customer_name,
        "salesTyCd": "N",  # N=Normal, C=Copy, T=Training
        "rcptTyCd": "S",   # S=Sales, R=Return (credit note)
        "pmtTyCd": _get_payment_type(invoice_doc),
        "salesSttsCd": "02",  # 02=Approved
        "cfmDt": frappe.utils.formatdate(invoice_doc.posting_date, "yyyyMMdd"),
        "salesDt": frappe.utils.formatdate(invoice_doc.posting_date, "yyyyMMdd"),
        "stockRlsDt": frappe.utils.formatdate(invoice_doc.posting_date, "yyyyMMdd"),
        "totItemCnt": len(invoice_doc.items),
        "taxblAmtA": 0.0,  # taxable amount by tax type A (VAT 16%)
        "taxblAmtB": 0.0,
        "taxblAmtC": 0.0,
        "taxblAmtD": 0.0,
        "taxRtA": 16.0,
        "taxRtB": 0.0,
        "taxRtC": 0.0,
        "taxRtD": 0.0,
        "taxAmtA": 0.0,
        "taxAmtB": 0.0,
        "taxAmtC": 0.0,
        "taxAmtD": 0.0,
        "totTaxblAmt": 0.0,
        "totTaxAmt": 0.0,
        "totAmt": float(invoice_doc.grand_total),
        "regrNm": frappe.session.user,
        "regrId": frappe.session.user,
        "modrNm": frappe.session.user,
        "modrId": frappe.session.user,
        "itemList": _build_item_list(invoice_doc),
    }

    # Calculate tax breakdowns
    payload = _calculate_tax_amounts(invoice_doc, payload)

    return _make_request("POST", "/vsdc/trnsSales/saveSales", payload, settings)


def submit_credit_note(invoice_doc, settings=None) -> dict:
    """
    POST /trnsSales/saveSales with rcptTyCd=R
    Submits a credit note (cancelled/returned Sales Invoice) to ZRA.
    """
    if not settings:
        settings = get_settings()

    original_rcpt_no = invoice_doc.zra_receipt_number
    if not original_rcpt_no:
        frappe.log_error(
            f"Cannot submit credit note for {invoice_doc.name}: original ZRA receipt number missing.",
            "ZRA Credit Note"
        )
        return {}

    payload = {
        "tpin": settings.tpin,
        "bhfId": settings.branch_id,
        "orgInvcNo": original_rcpt_no,
        "cisInvcNo": f"CR-{invoice_doc.name}",
        "custTpin": _get_customer_tpin(invoice_doc),
        "custNm": invoice_doc.customer_name,
        "salesTyCd": "N",
        "rcptTyCd": "R",  # R = Return/Credit Note
        "pmtTyCd": _get_payment_type(invoice_doc),
        "salesSttsCd": "02",
        "cfmDt": frappe.utils.formatdate(frappe.utils.today(), "yyyyMMdd"),
        "salesDt": frappe.utils.formatdate(frappe.utils.today(), "yyyyMMdd"),
        "totItemCnt": len(invoice_doc.items),
        "totAmt": float(invoice_doc.grand_total) * -1,
        "regrNm": frappe.session.user,
        "regrId": frappe.session.user,
        "modrNm": frappe.session.user,
        "modrId": frappe.session.user,
        "itemList": _build_item_list(invoice_doc, is_return=True),
    }

    payload = _calculate_tax_amounts(invoice_doc, payload, is_return=True)
    return _make_request("POST", "/vsdc/trnsSales/saveSales", payload, settings)


# -------------------------------------------------------------------
# Purchase Invoice Submission
# -------------------------------------------------------------------

def submit_purchase_invoice(invoice_doc, settings=None) -> dict:
    """
    POST /trnsPurchase/savePurchase
    Submits a Purchase Invoice to ZRA.
    """
    if not settings:
        settings = get_settings()

    payload = {
        "tpin": settings.tpin,
        "bhfId": settings.branch_id,
        "invcNo": invoice_doc.name,
        "orgInvcNo": invoice_doc.bill_no or invoice_doc.name,
        "spplrTpin": _get_supplier_tpin(invoice_doc),
        "spplrNm": invoice_doc.supplier_name,
        "spplrInvcNo": invoice_doc.bill_no or "",
        "regTyCd": "A",
        "pchsSttsCd": "02",
        "pchsDt": frappe.utils.formatdate(invoice_doc.posting_date, "yyyyMMdd"),
        "totItemCnt": len(invoice_doc.items),
        "totTaxblAmt": 0.0,
        "totTaxAmt": 0.0,
        "totAmt": float(invoice_doc.grand_total),
        "regrNm": frappe.session.user,
        "regrId": frappe.session.user,
        "modrNm": frappe.session.user,
        "modrId": frappe.session.user,
        "itemList": _build_purchase_item_list(invoice_doc),
    }
    return _make_request("POST", "/vsdc/trnsPurchase/savePurchase", payload, settings)


# -------------------------------------------------------------------
# Stock Movement
# -------------------------------------------------------------------

def submit_stock_movement(stock_entry_doc, settings=None) -> dict:
    """
    POST /stockMaster/saveStockMaster
    Notifies ZRA of stock movements.
    """
    if not settings:
        settings = get_settings()

    payload = {
        "tpin": settings.tpin,
        "bhfId": settings.branch_id,
        "sarNo": stock_entry_doc.name,
        "ocrnDt": frappe.utils.formatdate(stock_entry_doc.posting_date, "yyyyMMdd"),
        "totItemCnt": len(stock_entry_doc.items),
        "regrNm": frappe.session.user,
        "regrId": frappe.session.user,
        "modrNm": frappe.session.user,
        "modrId": frappe.session.user,
        "itemList": [
            {
                "itemSeq": idx + 1,
                "itemCd": row.item_code,
                "itemClsCd": frappe.db.get_value("Item", row.item_code, "zra_item_class_code") or "",
                "itemNm": row.item_name,
                "pkgUnitCd": "NT",
                "pkg": float(row.qty or 0),
                "qtyUnitCd": row.uom or "NT",
                "qty": float(row.qty or 0),
                "prc": float(row.basic_rate or 0),
                "splyAmt": float(row.amount or 0),
                "totDcAmt": 0.0,
                "taxTyCd": "A",
                "taxblAmt": float(row.amount or 0),
                "taxAmt": round(float(row.amount or 0) * 16 / 116, 2),
                "totAmt": float(row.amount or 0),
            }
            for idx, row in enumerate(stock_entry_doc.items)
        ],
    }
    return _make_request("POST", "/vsdc/stockMaster/saveStockMaster", payload, settings)


# -------------------------------------------------------------------
# Private Helpers
# -------------------------------------------------------------------

def _get_tax_type(item_doc) -> str:
    """Map item tax template to ZRA tax type code."""
    # A=VAT 16%, B=Tourism Levy, C=Zero-rated, D=Exempt
    # Extend this mapping based on your tax templates
    return "A"


def _get_payment_type(invoice_doc) -> str:
    """Map ERPNext payment mode to ZRA pmtTyCd."""
    # 01=Cash, 02=Credit, 03=Card, 04=Mobile Money, 05=Other
    if invoice_doc.is_return:
        return "01"
    mode = (invoice_doc.payment_terms_template or "").lower()
    if "credit" in mode or invoice_doc.outstanding_amount > 0:
        return "02"
    return "01"


def _get_customer_tpin(invoice_doc) -> str:
    tpin = frappe.db.get_value("Customer", invoice_doc.customer, "zra_customer_tpin")
    return tpin or ""


def _get_supplier_tpin(invoice_doc) -> str:
    tpin = frappe.db.get_value("Supplier", invoice_doc.supplier, "tax_id")
    return tpin or ""


def _get_customer_address(customer_doc) -> str:
    addr = frappe.db.get_value(
        "Address",
        {"link_doctype": "Customer", "link_name": customer_doc.name, "is_primary_address": 1},
        "address_line1",
    )
    return addr or ""


def _build_item_list(invoice_doc, is_return=False) -> list:
    items = []
    multiplier = -1 if is_return else 1
    for idx, row in enumerate(invoice_doc.items):
        tax_type = frappe.db.get_value("Item", row.item_code, "zra_item_class_code") or "A"
        taxable_amt = float(row.net_amount or row.amount or 0)
        tax_amt = round(taxable_amt * 16 / 116, 2)
        items.append({
            "itemSeq": idx + 1,
            "itemCd": row.item_code,
            "itemClsCd": frappe.db.get_value("Item", row.item_code, "zra_item_class_code") or "",
            "itemTyCd": "1",
            "itemNm": row.item_name,
            "pkgUnitCd": "NT",
            "pkg": float(row.qty or 0) * multiplier,
            "qtyUnitCd": row.uom or "NT",
            "qty": float(row.qty or 0) * multiplier,
            "prc": float(row.rate or 0),
            "splyAmt": float(row.amount or 0) * multiplier,
            "dcRt": float(row.discount_percentage or 0),
            "dcAmt": float(row.discount_amount or 0) * multiplier,
            "isrccCd": None,
            "isrccNm": None,
            "isrcRt": 0,
            "isrcAmt": 0,
            "taxTyCd": "A",
            "taxblAmt": round(taxable_amt * multiplier, 2),
            "taxAmt": round(tax_amt * multiplier, 2),
            "totAmt": float(row.amount or 0) * multiplier,
        })
    return items


def _build_purchase_item_list(invoice_doc) -> list:
    items = []
    for idx, row in enumerate(invoice_doc.items):
        taxable_amt = float(row.net_amount or row.amount or 0)
        tax_amt = round(taxable_amt * 16 / 116, 2)
        items.append({
            "itemSeq": idx + 1,
            "itemCd": row.item_code,
            "itemClsCd": frappe.db.get_value("Item", row.item_code, "zra_item_class_code") or "",
            "itemTyCd": "1",
            "itemNm": row.item_name,
            "pkgUnitCd": "NT",
            "pkg": float(row.qty or 0),
            "qtyUnitCd": row.uom or "NT",
            "qty": float(row.qty or 0),
            "prc": float(row.rate or 0),
            "splyAmt": float(row.amount or 0),
            "dcRt": 0,
            "dcAmt": 0,
            "taxTyCd": "A",
            "taxblAmt": round(taxable_amt, 2),
            "taxAmt": round(tax_amt, 2),
            "totAmt": float(row.amount or 0),
        })
    return items


def _calculate_tax_amounts(invoice_doc, payload, is_return=False) -> dict:
    """Populate tax breakdown fields on the payload."""
    multiplier = -1 if is_return else 1
    total_taxable = 0.0
    total_tax = 0.0

    for row in invoice_doc.items:
        taxable = float(row.net_amount or row.amount or 0)
        tax = round(taxable * 16 / 116, 2)
        total_taxable += taxable
        total_tax += tax

    payload["taxblAmtA"] = round(total_taxable * multiplier, 2)
    payload["taxAmtA"] = round(total_tax * multiplier, 2)
    payload["totTaxblAmt"] = round(total_taxable * multiplier, 2)
    payload["totTaxAmt"] = round(total_tax * multiplier, 2)
    return payload
