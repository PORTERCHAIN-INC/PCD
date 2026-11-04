<#-- Porterchain branded new-device code email (EN/FR via messages). Inline styles for mail clients. -->
<html lang="${locale.language!'en'}"><body style="margin:0;padding:0;background:#f0f4f8;font-family:Calibri,'Segoe UI',Arial,sans-serif;color:#0a1628">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:32px 12px"><tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:440px;background:#ffffff;border:1px solid rgba(10,22,40,.08);border-radius:16px;padding:32px">
<tr><td style="font-size:20px;font-weight:600;letter-spacing:.04em;color:#0a1628">Porterchain</td></tr>
<tr><td style="padding-top:20px;font-size:18px;font-weight:600">${msg("pcOtpHeading")}</td></tr>
<tr><td style="padding-top:8px;font-size:14px;line-height:1.6;color:#64748b">${msg("pcOtpIntro")}</td></tr>
<tr><td align="center" style="padding:24px 0"><div style="display:inline-block;background:#f0f4f8;border-radius:12px;padding:14px 22px;font-size:30px;font-weight:700;letter-spacing:8px;font-family:'Courier New',monospace;color:#0a1628">${otp}</div></td></tr>
<tr><td style="font-size:14px;line-height:1.6;color:#64748b">${msg("pcOtpExpires", ttlMinutes)}</td></tr>
<tr><td style="padding-top:16px;font-size:13px;line-height:1.6;color:#64748b">${msg("pcOtpNotYou")}</td></tr>
</table>
<p style="font-size:12px;color:#94a3b8;margin-top:16px">Porterchain Inc.</p>
</td></tr></table></body></html>
