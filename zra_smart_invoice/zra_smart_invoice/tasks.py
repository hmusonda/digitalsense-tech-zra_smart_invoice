"""
Scheduled background tasks.
Registered in hooks.py under scheduler_events.
"""

import frappe


def retry_failed_submissions():
    """
    Runs every 15 minutes.
    Picks up Failed submission logs and retries them, up to 5 attempts.
    """
    from zra_smart_invoice.zra_smart_invoice.utils import retry_submission

    failed_logs = frappe.get_all(
        "ZRA Submission Log",
        filters={"status": ["in", ["Failed", "Retrying"]], "retry_count": ["<", 5]},
        fields=["name", "retry_count"],
        order_by="submitted_at asc",
        limit=20,
    )

    for log in failed_logs:
        try:
            frappe.db.set_value("ZRA Submission Log", log.name, "status", "Retrying")
            frappe.db.commit()
            retry_submission(log.name)
        except Exception as e:
            frappe.db.set_value("ZRA Submission Log", log.name, {
                "status": "Failed",
                "retry_count": log.retry_count + 1,
                "error_message": str(e),
            })
            frappe.db.commit()

            if log.retry_count + 1 >= 5:
                _alert_persistent_failure(log.name)


def daily_stock_sync():
    """
    Runs at midnight daily.
    Syncs any stock entries that failed or were missed during the day.
    """
    failed = frappe.get_all(
        "ZRA Submission Log",
        filters={
            "submission_type": "Stock Movement",
            "status": "Failed",
            "retry_count": ["<", 5],
        },
        fields=["name"],
        limit=50,
    )

    from zra_smart_invoice.zra_smart_invoice.utils import retry_submission
    for log in failed:
        try:
            retry_submission(log.name)
        except Exception as e:
            frappe.log_error(f"Daily stock sync retry failed for {log.name}: {e}", "ZRA Stock Sync")


def _alert_persistent_failure(log_name: str):
    """Notify System Manager of a submission that has exceeded max retries."""
    frappe.sendmail(
        recipients=frappe.get_all("User", filters={"role_profile_name": "System Manager"}, pluck="email"),
        subject=f"[ZRA] Persistent submission failure: {log_name}",
        message=(
            f"ZRA Submission Log <b>{log_name}</b> has failed 5 times and will not be retried automatically.<br>"
            f"Please review and retry manually from the ZRA Submission Log list."
        ),
    )
