"""Public marketing site support: instant estimate, calculator leads, hero A/B flag,
lead attribution stats and merchant signup attribution.

Lives outside the *_engine packages on purpose: it composes the booking engine's
quote preview with the collaboration engine's lead ingest without adding an
engine-to-engine import.
"""
