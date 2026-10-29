# 37 · Secrets: SOPS replaces Doppler

**L26 check:** Doppler has a free Developer tier, so it isn't strictly paid today. But team features, more than 3 users, audit logs and service-account limits need paid tiers, and it's an outside vendor. Ravi's direction is SOPS, and it removes a vendor. **Decision: SOPS + age replaces Doppler.**

- Encrypted `secrets/{droplet,ubuntu,oracle,ci}.enc.yaml` in the repo. age keys: one per host plus one for Ravi (offline backup on paper/USB) plus one for CI (GitHub Actions secret).
- Deploy decrypts to a tmpfs `.env` that's read by docker compose. Never written to disk unencrypted.
- Replace `doppler.yaml`, `setup-doppler.sh`, `sync-secrets.sh` (Doppler parts), `prune-legacy-clerk-doppler.sh` and `upload-clerk-to-doppler.sh` (file 32: DELETE). Keep `verify-secrets-alignment.sh` and re-point it at SOPS.
- Rotation: all keys rotated at the Keycloak cutover (week 5) and every 90 days after. Stripe, ZeptoMail, Shopify and Apple keys have their rotation recorded in `docs/SECRETS_MAP.md`.
- gitleaks in pre-commit and the PR gate.

Weeks: 1 (SOPS in place, Doppler read-only), 2 (Doppler off), 5 (rotate).
