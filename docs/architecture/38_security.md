# 38 · Security: threat model, rate limits, testing (free tooling)

## Threat model (STRIDE, short)

| Asset / entry                            | Threat                                          | Control                                                                                                            | Week             |
| ---------------------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ---------------- |
| Public API on the droplet                | credential stuffing, scraping, DoS              | Keycloak brute-force lockout; Caddy rate limits; Cloudflare free WAF/proxy; fail2ban                               | 5–6              |
| Merchant API keys                        | key leakage, abuse                              | hashed keys, scopes, per-key limits, rotation UI                                                                   | 6                |
| Webhooks in (Shopify, Stripe, ZeptoMail) | spoofing, replay                                | HMAC verify (`shopify_hmac`), timestamp window, idempotent `*_webhook_events`                                      | 1 (A05/A30 area) |
| Admin on Ubuntu                          | exposure of the home network                    | admin only through Tailscale/WireGuard (free) or Cloudflare Tunnel + Keycloak staff realm + passkey; no open ports | 2                |
| Agents / LLM                             | prompt injection from chats/emails, tool misuse | fixed tool sets, verifier, six-case approval tokens, no secrets in prompts, WhatsApp text treated as data          | 9                |
| POD media                                | tampering                                       | hash + signed timestamp (doc 26 D-items)                                                                           | 2                |
| Database                                 | SQL injection, over-broad access                | ORM-only, SpiceDB authz, least-privilege DB roles per host                                                         | 1–4              |
| Supply chain                             | malicious packages                              | lockfiles, osv-scanner, Dependabot/Renovate (free)                                                                 | 1                |

## Rate limits (start values)

- Public quote: 30/min per IP.
- Login (Keycloak): 5 failures then progressive lockout.
- Merchant API: 600/min per key.
- Public forms (inquiries, newsletter): 5/min per IP plus a Turnstile captcha (free).
- Driver GPS: 1 per 3 s per driver.
- Webhooks in: 120/min per source.

A limit returns 429 with `Retry-After`. Limits are set in Caddy (edge) and the API (per key).

## Testing

- **PR:** Semgrep CE, bandit, gitleaks, osv-scanner.
- **Nightly:** OWASP ZAP baseline against the staging droplet.
- **Week 12:** ZAP full scan, nuclei (free templates) and a manual OWASP ASVS L2 checklist for auth, session, access and input. Optionally invite a free community review (e.g. a university security club) before the pilot. A paid pen test is out under L26.
- Trivy scans container images in CI.

Done check: no high findings open at week 14.
