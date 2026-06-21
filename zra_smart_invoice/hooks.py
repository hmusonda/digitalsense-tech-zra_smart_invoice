app_name = "zra_smart_invoice"
app_title = "ZRA Smart Invoice"
app_publisher = "Digital Sense"
app_description = "ZRA Smart Invoice integration for ERPNext — multi-tenant via DigiTax middleware"
app_email = "humphrey@digitalsense.tech"
app_license = "MIT"
app_version = "0.1.0"

# -------------------------------------------------------------------
# Document Events
# Hooks into ERPNext doctypes to trigger ZRA submissions automatically
# -------------------------------------------------------------------
doc_events = {
    "Sales Invoice": {
        "on_submit": "zra_smart_invoice.zra_smart_invoice.events.sales_invoice.on_submit",
        "on_cancel": "zra_smart_invoice.zra_smart_invoice.events.sales_invoice.on_cancel",
    },
    "Purchase Invoice": {
        "on_submit": "zra_smart_invoice.zra_smart_invoice.events.purchase_invoice.on_submit",
    },
    "Stock Entry": {
        "on_submit": "zra_smart_invoice.zra_smart_invoice.events.stock_entry.on_submit",
    },
    "Item": {
        "after_insert": "zra_smart_invoice.zra_smart_invoice.events.item.sync_to_zra",
        "on_update": "zra_smart_invoice.zra_smart_invoice.events.item.sync_to_zra",
    },
    "Customer": {
        "after_insert": "zra_smart_invoice.zra_smart_invoice.events.customer.sync_to_zra",
        "on_update": "zra_smart_invoice.zra_smart_invoice.events.customer.sync_to_zra",
    },
}

# -------------------------------------------------------------------
# Scheduled Tasks
# Background jobs for retry queue and periodic syncs
# -------------------------------------------------------------------
scheduler_events = {
    "cron": {
        # Retry failed ZRA submissions every 15 minutes
        "*/15 * * * *": [
            "zra_smart_invoice.zra_smart_invoice.tasks.retry_failed_submissions"
        ],
        # Daily stock sync to ZRA (midnight)
        "0 0 * * *": [
            "zra_smart_invoice.zra_smart_invoice.tasks.daily_stock_sync"
        ],
    }
}

# -------------------------------------------------------------------
# App Includes — JS loaded on all desk pages
# -------------------------------------------------------------------
app_include_js = "/assets/zra_smart_invoice/js/zra_smart_invoice.js"

# -------------------------------------------------------------------
# DocType JS overrides
# -------------------------------------------------------------------
doctype_js = {
    "Sales Invoice": "public/js/sales_invoice.js",
}

# -------------------------------------------------------------------
# Installation
# -------------------------------------------------------------------
after_install = "zra_smart_invoice.zra_smart_invoice.install.after_install"
after_migrate = "zra_smart_invoice.zra_smart_invoice.install.after_migrate"
