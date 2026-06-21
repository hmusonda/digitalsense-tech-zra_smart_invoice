import frappe
from frappe.model.document import Document


class ZRASubmissionLog(Document):
    pass


def create_log(reference_doctype, reference_name, submission_type, status, payload=None, response=None, error=None, rcpt_no=None):
    """Helper to create a ZRA Submission Log entry."""
    import json
    log = frappe.new_doc("ZRA Submission Log")
    log.reference_doctype = reference_doctype
    log.reference_name = reference_name
    log.submission_type = submission_type
    log.status = status
    log.submitted_at = frappe.utils.now_datetime()
    if payload:
        log.request_payload = json.dumps(payload, indent=2, default=str)
    if response:
        log.response_data = json.dumps(response, indent=2, default=str)
    if error:
        log.error_message = str(error)
    if rcpt_no:
        log.zra_receipt_number = rcpt_no
    log.insert(ignore_permissions=True)
    return log.name
