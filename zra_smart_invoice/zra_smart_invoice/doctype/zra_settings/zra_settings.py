import frappe
from frappe.model.document import Document


class ZRASettings(Document):
    def validate(self):
        if self.environment == "Production" and not self.is_initialized:
            frappe.throw(
                "Cannot switch to Production environment before completing device initialization. "
                "Please run the ZRA Setup Wizard first."
            )

    def get_api_url(self):
        base = self.digitax_api_url.rstrip("/")
        return base

    def get_headers(self):
        return {
            "Authorization": f"Bearer {self.get_password('digitax_api_key')}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
