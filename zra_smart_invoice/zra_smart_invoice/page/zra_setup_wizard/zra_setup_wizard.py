import frappe


def get_context(context):
    context.settings = frappe.get_single("ZRA Settings")
