"""Zero-token outbound call scripts for vendor_import Dial card."""

from __future__ import annotations

from typing import Any


def outbound_call_scripts(*, company_name: str, city: str | None = None) -> dict[str, Any]:
    """Sales-bible Field Card — capacity network, not courier SaaS."""
    where = f" in {city}" if city else " in the GTA"
    name = company_name or "your team"
    return {
        "recommended": "reception",
        "opener": (
            f"Hi — this is PorterChain. We run a transportation capacity network"
            f"{where}. I'm calling {name} about vehicle-and-driver capacity for "
            f"deliveries — not selling software. Do you have 30 seconds, or who "
            f"handles shipping / logistics?"
        ),
        "scripts": {
            "reception": [
                "Ask for shipping, logistics, or the owner.",
                "If gatekeeper: 'I only need the right person for delivery capacity — who should I ask for?'",
                "Get a name + best time to call back.",
            ],
            "decision_maker": [
                "Diagnose first: how many deliveries/week or month?",
                "Which cities / FSAs matter first?",
                "Who do you use today (courier, own fleet, 3PL)?",
                "What breaks — late pickups, no tracking, cost swings?",
                "Offer a small next step: quote, sample route, or Shopify connect — not a platform tour.",
            ],
            "voicemail": [
                f"Hi, PorterChain capacity network for {name}. We help merchants "
                f"secure reliable vehicle+driver capacity{where}. "
                f"Happy to send a short note — please call back or email hello@porterchain.com.",
            ],
            "objections": [
                "Price → 'Understood — what's the cost of a missed or late delivery for you?'",
                "We have a courier → 'Many use us as backup capacity or overflow — still useful?'",
                "Not now → 'When do you review logistics next? I'll put a reminder.'",
            ],
        },
        "discovery": [
            "Approx deliveries per month?",
            "Primary cities / service area?",
            "Current provider or own fleet?",
            "Vehicle class usually needed?",
            "Who else evaluates logistics vendors?",
        ],
        "capture_checklist": [
            "Contact name + title",
            "Direct phone / email",
            "Marketing consent if they want a follow-up email",
            "Volume + current provider",
        ],
    }
