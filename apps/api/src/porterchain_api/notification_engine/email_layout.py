"""PorterChain branded HTML email shell — table layout for client compatibility."""

from __future__ import annotations

import html
from typing import Any

BRAND_NAME = "PorterChain"
TAGLINE = "Moving commerce on chain"
PRIMARY = "#0a1628"
ACCENT = "#2563eb"
SURFACE = "#f1f5f9"
MUTED = "#64748b"
BORDER = "#e2e8f0"
WHITE = "#ffffff"

# Outlook / Office-native Calibri first; Carlito is the open metric-compatible fallback.
FONT = "Calibri, Carlito, Candara, 'Segoe UI', Arial, sans-serif"


def _esc(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def _detail_rows(rows: list[tuple[str, str]]) -> str:
    parts: list[str] = []
    for label, value in rows:
        if not value:
            continue
        parts.append(
            f"""
            <tr>
              <td style="padding:10px 0;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:13px;color:{MUTED};width:38%;vertical-align:top;">
                {_esc(label)}
              </td>
              <td style="padding:10px 0;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:14px;color:{PRIMARY};font-weight:600;text-align:right;vertical-align:top;">
                {_esc(value)}
              </td>
            </tr>
            """
        )
    if not parts:
        return ""
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:8px 0 4px;">{"".join(parts)}</table>'


def _cta(label: str, url: str) -> str:
    if not url:
        return ""
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:28px 0 8px;">
      <tr>
        <td style="border-radius:10px;background:{ACCENT};">
          <a href="{_esc(url)}"
             style="display:inline-block;padding:14px 22px;font-family:{FONT};font-size:14px;font-weight:700;color:{WHITE};text-decoration:none;letter-spacing:0.01em;">
            {_esc(label)}
          </a>
        </td>
      </tr>
    </table>
    """


def wrap_email(
    *,
    preheader: str,
    eyebrow: str,
    headline: str,
    lead: str,
    details_html: str = "",
    cta_label: str = "",
    cta_url: str = "",
    note: str = "",
) -> str:
    """Full multipart-safe HTML document with PorterChain chrome."""
    note_html = (
        f'<p style="margin:20px 0 0;font-family:{FONT};font-size:13px;line-height:1.55;color:{MUTED};">{_esc(note)}</p>'
        if note
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="light" />
  <title>{_esc(headline)}</title>
</head>
<body style="margin:0;padding:0;background:{SURFACE};font-family:{FONT};">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">
    {_esc(preheader)}
  </div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{SURFACE};padding:32px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:{WHITE};border-radius:16px;overflow:hidden;border:1px solid {BORDER};">
          <tr>
            <td style="background:{PRIMARY};padding:28px 32px 24px;">
              <p style="margin:0;font-family:{FONT};font-size:11px;letter-spacing:0.18em;text-transform:uppercase;color:rgba(255,255,255,0.65);">
                {_esc(BRAND_NAME)}
              </p>
              <p style="margin:10px 0 0;font-family:{FONT};font-size:28px;line-height:1.15;font-weight:700;color:{WHITE};letter-spacing:-0.02em;">
                {_esc(BRAND_NAME)}
              </p>
              <p style="margin:10px 0 0;font-family:{FONT};font-size:14px;font-style:italic;color:#93c5fd;">
                {_esc(TAGLINE)}
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:32px;">
              <p style="margin:0 0 8px;font-family:{FONT};font-size:12px;letter-spacing:0.12em;text-transform:uppercase;color:{ACCENT};font-weight:700;">
                {_esc(eyebrow)}
              </p>
              <h1 style="margin:0 0 12px;font-family:{FONT};font-size:24px;line-height:1.25;font-weight:700;color:{PRIMARY};letter-spacing:-0.02em;">
                {_esc(headline)}
              </h1>
              <p style="margin:0 0 8px;font-family:{FONT};font-size:15px;line-height:1.6;color:#334155;">
                {_esc(lead)}
              </p>
              {details_html}
              {_cta(cta_label, cta_url)}
              {note_html}
            </td>
          </tr>
          <tr>
            <td style="padding:20px 32px 28px;background:{SURFACE};border-top:1px solid {BORDER};">
              <p style="margin:0;font-family:{FONT};font-size:12px;color:{MUTED};line-height:1.5;">
                <strong style="color:{PRIMARY};">{_esc(BRAND_NAME)}</strong>
                &nbsp;·&nbsp;{_esc(TAGLINE)}
              </p>
              <p style="margin:8px 0 0;font-family:{FONT};font-size:11px;color:#94a3b8;line-height:1.45;">
                Transportation capacity network for the Greater Toronto Area.
                Questions? Reply to this email or visit porterchain.com
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def build_transactional_html(
    *,
    eyebrow: str,
    headline: str,
    lead: str,
    rows: list[tuple[str, str]] | None = None,
    cta_label: str = "",
    cta_url: str = "",
    note: str = "",
    preheader: str | None = None,
) -> str:
    return wrap_email(
        preheader=preheader or lead,
        eyebrow=eyebrow,
        headline=headline,
        lead=lead,
        details_html=_detail_rows(rows or []),
        cta_label=cta_label,
        cta_url=cta_url,
        note=note,
    )
