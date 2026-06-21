import frappe


def after_install():
    """Run after app is installed on a site."""
    create_custom_fields()
    frappe.db.commit()
    frappe.msgprint("ZRA Smart Invoice installed. Go to ZRA Settings to configure your credentials.")


def after_migrate():
    """Run after bench migrate."""
    create_custom_fields()
    frappe.db.commit()


def create_custom_fields():
    """
    Add ZRA-specific fields to standard ERPNext doctypes.
    These store the ZRA receipt number and QR code on submitted invoices.
    """
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields as _create

    custom_fields = {
        "Sales Invoice": [
            {
                "fieldname": "zra_section",
                "label": "ZRA Smart Invoice",
                "fieldtype": "Section Break",
                "insert_after": "against_income_account",
                "collapsible": 1,
                "collapsible_depends_on": "zra_receipt_number",
            },
            {
                "fieldname": "zra_receipt_number",
                "label": "ZRA Receipt Number",
                "fieldtype": "Data",
                "insert_after": "zra_section",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "zra_internal_data",
                "label": "ZRA Internal Data",
                "fieldtype": "Data",
                "insert_after": "zra_receipt_number",
                "read_only": 1,
                "no_copy": 1,
                "hidden": 1,
            },
            {
                "fieldname": "zra_qr_code",
                "label": "ZRA QR Code",
                "fieldtype": "Attach Image",
                "insert_after": "zra_internal_data",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "zra_submission_status",
                "label": "ZRA Submission Status",
                "fieldtype": "Select",
                "options": "\nPending\nSubmitted\nFailed\nNot Required",
                "insert_after": "zra_qr_code",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "zra_submitted_at",
                "label": "ZRA Submitted At",
                "fieldtype": "Datetime",
                "insert_after": "zra_submission_status",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "zra_col_break",
                "fieldtype": "Column Break",
                "insert_after": "zra_submitted_at",
            },
            {
                "fieldname": "zra_error_message",
                "label": "ZRA Error Message",
                "fieldtype": "Small Text",
                "insert_after": "zra_col_break",
                "read_only": 1,
                "no_copy": 1,
            },
        ],
        "Purchase Invoice": [
            {
                "fieldname": "zra_submission_status",
                "label": "ZRA Submission Status",
                "fieldtype": "Select",
                "options": "\nPending\nSubmitted\nFailed\nNot Required",
                "insert_after": "against_expense_account",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "zra_submitted_at",
                "label": "ZRA Submitted At",
                "fieldtype": "Datetime",
                "insert_after": "zra_submission_status",
                "read_only": 1,
                "no_copy": 1,
            },
        ],
        "Item": [
            {
                "fieldname": "zra_item_class_code",
                "label": "ZRA Item Classification Code",
                "fieldtype": "Data",
                "insert_after": "item_group",
                "description": "ZRA item classification code (from ZRA item code list)",
            },
            {
                "fieldname": "zra_item_synced",
                "label": "Synced to ZRA",
                "fieldtype": "Check",
                "insert_after": "zra_item_class_code",
                "read_only": 1,
                "no_copy": 1,
            },
        ],
        "Customer": [
            {
                "fieldname": "zra_customer_tpin",
                "label": "ZRA TPIN",
                "fieldtype": "Data",
                "insert_after": "tax_id",
                "description": "Customer's ZRA Taxpayer Identification Number (for B2B invoices)",
            },
            {
                "fieldname": "zra_customer_synced",
                "label": "Synced to ZRA",
                "fieldtype": "Check",
                "insert_after": "zra_customer_tpin",
                "read_only": 1,
                "no_copy": 1,
            },
        ],
    }

    _create(custom_fields, ignore_validate=True)
