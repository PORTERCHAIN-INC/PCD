"""Unit tests for D2 contract parser helpers (detail/offline expansion)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_d2_contracts.py"


def _load():
    spec = importlib.util.spec_from_file_location("verify_d2_contracts", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_pydantic_fields_include_subclass_body() -> None:
    mod = _load()
    text = """
class Parent(BaseModel):
    a: int

class Child(Parent):
    b: str
    cod_status: str | None = None
"""
    assert mod._pydantic_model_fields(text, "Child") == {"b", "cod_status"}


def test_ts_fields_simple_and_intersection() -> None:
    mod = _load()
    simple = """
export type DriverJobSummary = {
  order_id: string;
  order_number: string;
};
"""
    assert mod._ts_interface_fields(simple, "DriverJobSummary") == {"order_id", "order_number"}

    intersection = """
export type DriverJobDetail = DriverJobSummary & {
  otp_required?: boolean;
  cod_status?: string | null;
};
"""
    assert mod._ts_interface_fields(intersection, "DriverJobDetail") == {
        "otp_required",
        "cod_status",
    }


def test_driver_job_summary_parity_helper_green() -> None:
    mod = _load()
    failures = mod._check_driver_job_summary_parity()
    assert failures == [], failures
