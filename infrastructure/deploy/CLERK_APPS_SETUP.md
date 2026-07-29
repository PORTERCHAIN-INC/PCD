# Clerk apps setup (superseded)

**Type:** POINTER  
**Last verified:** 2026-07-29

This doc described the legacy **4 separate Clerk applications** (one per portal) setup flow. PorterChain now runs a **unified Platform Clerk app** (`CLERK_MODE=unified`) only; the 4-app / 12-key layout (`CLERK_MODE=enterprise`) is **retired** (`pnpm clerk:sync` exits if requested).

- **Primary setup + secrets:** [docs/runbooks/clerk-consolidation.md](../../docs/runbooks/clerk-consolidation.md)
- **Production cutover:** [docs/runbooks/clerk-cutover-phase10.md](../../docs/runbooks/clerk-cutover-phase10.md)
- **Secret names (unified + portal slot aliases):** [docs/SECRETS_MAP.md](../../docs/SECRETS_MAP.md)
- **Doppler/GitHub matrix:** [docs/architecture/clerk-doppler-secret-matrix.md](../../docs/architecture/clerk-doppler-secret-matrix.md)

Portal slot names (`CLERK_{CUSTOMER,MERCHANT,ADMIN,DRIVER}_*`) remain for compose dual-read — see `clerk-consolidation.md` §3. Step-by-step multi-app Dashboard instructions previously here are archived in git history.
