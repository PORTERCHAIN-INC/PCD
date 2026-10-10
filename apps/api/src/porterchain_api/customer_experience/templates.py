"""Central, transactional-only recipient templates (merged into notification_engine.templates).

CASL: these are transactional/relationship messages about a delivery already in
progress for the recipient (CASL s.6(6)); they carry no promotional content and
always identify the sender. Keep it that way when editing copy.
"""

from __future__ import annotations

CASL_FOOTER = (
    "Service message about a delivery to you from {merchant_name}, delivered by PorterChain. "
    "No marketing. Questions? {help_line}"
)

CX_TEMPLATES: dict[str, dict[str, str]] = {
    "cx_out_for_delivery": {
        "subject": "Your {merchant_name} delivery is out for delivery",
        "body": (
            "Your delivery {tracking_number} from {merchant_name} is out for delivery.{window_line}\n"
            "Track: {public_track_url}{manage_line}\n\n" + CASL_FOOTER
        ),
    },
    "cx_next_stop": {
        "subject": "{stops_line} — your {merchant_name} delivery",
        "body": (
            "{stops_line} Your driver is heading to you with delivery {tracking_number}.\n"
            "Track: {public_track_url}{instructions_line}\n\n" + CASL_FOOTER
        ),
    },
    "cx_eta_20": {
        "subject": "Your driver is about {eta_minutes} minutes away",
        "body": (
            "Your {merchant_name} delivery {tracking_number} is about {eta_minutes} minutes away.{id_line}\n"
            "Track: {public_track_url}\n\n" + CASL_FOOTER
        ),
    },
    "cx_delivered": {
        "subject": "Delivered: {merchant_name} {tracking_number}",
        "body": (
            "Your delivery {tracking_number} from {merchant_name} was delivered.\n"
            "Proof of delivery: {pod_url}\n\n" + CASL_FOOTER
        ),
    },
    "cx_attempted": {
        "subject": "We missed you — delivery {tracking_number}",
        "body": (
            "We tried to deliver {tracking_number} from {merchant_name} but could not complete it.\n"
            "{attempt_line}\nTrack: {public_track_url}\n\n" + CASL_FOOTER
        ),
    },
    "cx_rescheduled": {
        "subject": "New delivery time set for {tracking_number}",
        "body": (
            "Your delivery {tracking_number} from {merchant_name} is now booked for {window_label}.\n"
            "Track: {public_track_url}\n\n" + CASL_FOOTER
        ),
    },
    "cx_schedule_request": {
        "subject": "Choose a delivery time for {tracking_number}",
        "body": (
            "{merchant_name} needs you to choose a delivery window before we dispatch {tracking_number}.\n"
            "Pick a time: {manage_url}\n\n" + CASL_FOOTER
        ),
    },
}

CX_TEMPLATE_META: dict[str, dict[str, str]] = {key: {"category": "tracking"} for key in CX_TEMPLATES}

#: Every placeholder a CX template may use (context builder fills them all).
CX_PLACEHOLDERS: tuple[str, ...] = (
    "merchant_name",
    "tracking_number",
    "public_track_url",
    "manage_url",
    "pod_url",
    "window_line",
    "manage_line",
    "stops_line",
    "instructions_line",
    "eta_minutes",
    "id_line",
    "attempt_line",
    "help_line",
    "window_label",
)
