"""Compatibility shim — Redis last-known GPS lives in platform."""

from porterchain_api.platform.last_known import *  # noqa: F403
from porterchain_api.platform.last_known import (  # noqa: F401
    LastKnown,
    accumulate_shift_mileage,
    distance_m,
    parse_recorded_at,
    read_last_known,
    read_shift_mileage_km,
    write_last_known,
)
