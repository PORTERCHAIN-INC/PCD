# Porterchain — Dependency Report

**Document version:** 1.0  
**Date:** June 29, 2026  
**Scope:** `/Users/ravi/Documents/GitHub/PCD` repository audit

---

## Executive summary

| Metric | Value |
|--------|-------|
| Projects in repo | **1** (`website/`) |
| Package manager | npm (lockfile v3) |
| Total dependencies | 595 (161 prod + 374 dev + optional) |
| Direct dependencies | 22 (13 prod + 9 dev) |
| Security vulnerabilities | **4 moderate**, 0 high/critical |
| Duplicate packages (cross-project) | N/A — single project |
| Outdated (major) | 0 direct — all current |
| Auth/payment/DB SDKs | **None installed** |
| Test frameworks | **None installed** |
| Lint/format tooling | ESLint only — no Prettier/Husky |

> Platform dependencies (Clerk, Stripe, FastAPI, Expo, Fleetbase) exist in **external repositories** documented in `CONNECTIONS.md` and `details.md` but are not auditable in this workspace.

---

## Direct dependencies — website

Source: `website/package.json` + `website/package-lock.json`

### Production

| Package | Declared | Resolved | Purpose |
|---------|----------|----------|---------|
| `next` | 16.2.9 | 16.2.9 | Framework |
| `react` | 19.2.4 | 19.2.4 | UI runtime |
| `react-dom` | 19.2.4 | 19.2.4 | DOM renderer |
| `next-intl` | ^4.13.0 | 4.13.0 | i18n (en/fr) |
| `@vis.gl/react-google-maps` | ^1.8.3 | 1.8.3 | Google Maps |
| `framer-motion` | ^12.42.0 | 12.42.0 | Animations |
| `date-fns` | ^4.4.0 | 4.4.0 | Date utilities |
| `react-day-picker` | ^10.0.1 | 10.0.1 | Schedule picker |
| `gray-matter` | ^4.0.3 | 4.0.3 | Blog frontmatter |
| `react-markdown` | ^10.1.0 | 10.1.0 | Blog rendering |
| `remark-gfm` | ^4.0.1 | 4.0.1 | GitHub-flavored markdown |
| `reading-time` | ^1.5.0 | 1.5.0 | Blog read time |
| `lucide-react` | ^1.21.0 | 1.21.0 | Icons |

### Development

| Package | Declared | Resolved | Purpose |
|---------|----------|----------|---------|
| `typescript` | ^5 | 5.9.3 | Type checking |
| `tailwindcss` | ^4 | 4.3.1 | Styling |
| `@tailwindcss/postcss` | ^4 | 4.3.1 | PostCSS plugin |
| `eslint` | ^9 | 9.39.4 | Linting |
| `eslint-config-next` | 16.2.9 | 16.2.9 | Next.js ESLint rules |
| `@types/node` | ^20 | 20.19.43 | Node types |
| `@types/react` | ^19 | 19.2.17 | React types |
| `@types/react-dom` | ^19 | 19.2.3 | React DOM types |
| `@types/google.maps` | ^3.65.2 | 3.65.2 | Maps types |

---

## Unused packages

Analysis based on import graph in `website/src/`:

| Package | Status | Notes |
|---------|--------|-------|
| All 13 production deps | **Used** | Each has active imports |
| All 9 dev deps | **Used** | Build/lint/type tooling |

No obviously unused direct dependencies detected.

### Potentially redundant (evaluate)

| Item | Detail | Recommendation |
|------|--------|----------------|
| `gray-matter` | Only used for blog MD parsing | Keep; or migrate to `contentlayer` / `@next/mdx` |
| `reading-time` | Single use in blog lib | Keep — small footprint |

---

## Duplicate packages (within website)

Normal npm deduplication artifacts:

| Package | Version A | Version B | Context |
|---------|-----------|-----------|---------|
| `postcss` | 8.5.15 | 8.4.31 | Top-level vs bundled in `next` |
| `js-yaml` | (via gray-matter) | — | Transitive only |

**Cross-project duplicates:** N/A — monorepo not established.

### Expected duplicates when monorepo is created

| Package | Risk | Mitigation |
|---------|------|------------|
| `react` / `react-dom` | Version mismatch across apps | pnpm overrides in root `package.json` |
| `typescript` | Multiple versions | Single version in `packages/config` |
| `@types/react` | Mismatch with RN types | Separate type roots per app |
| `eslint` | Config drift | `@porterchain/config/eslint` |

---

## Outdated packages

### Direct dependencies

All direct dependencies resolve to current versions within declared ranges. No major outdated direct packages.

### Transitive concerns

| Package | Issue | Fix |
|---------|-------|-----|
| `js-yaml` (via `gray-matter`) | Moderate CVE — quadratic DoS | Upgrade `gray-matter` to 2.0.1 or replace |
| `postcss` (via `next`) | Moderate CVE — XSS in stringify | Wait for Next.js patch or override |

---

## Security vulnerabilities

`npm audit` results (June 2026):

| Package | Severity | CVE / Advisory | Via | Fix |
|---------|----------|----------------|-----|-----|
| `js-yaml` | Moderate | GHSA-h67p-54hq-rp68 | `gray-matter` | Upgrade gray-matter |
| `gray-matter` | Moderate | js-yaml transitive | direct | → 2.0.1 |
| `postcss` | Moderate | GHSA-qx2v-qp2m-jg93 | `next` | Next.js upstream |
| `next` | Moderate | postcss transitive | direct | Monitor Next releases |

**Total:** 4 moderate, 0 high, 0 critical

### Risk assessment

| Finding | Exploitability in Porterchain context |
|---------|--------------------------------------|
| js-yaml DoS | Low — blog MD parsed at build time only, not runtime user input |
| postcss XSS | Low — no user-supplied CSS processed at runtime |

### Recommended actions

1. Pin `gray-matter@2.0.1` when blog parsing is verified compatible
2. Add `npm audit --audit-level=moderate` to CI — fail on high/critical
3. Enable Dependabot on GitHub when repo is initialized

---

## Version conflicts

### Within website

| Pair | Status |
|------|--------|
| `next` 16.2.9 + `eslint-config-next` 16.2.9 | ✓ Aligned |
| `react` 19.2.4 + `@types/react` 19.2.17 | ✓ Compatible |
| `next` requires Node ≥20.9.0 + `@types/node` ^20 | ✓ Compatible |

### Cross-platform (documented, not in repo)

| Conflict | Detail | Resolution |
|----------|--------|------------|
| Node 20 vs 22 | Website: Node 20; EAS production: Node 22.14 | Document per-app `.nvmrc` |
| API port 8000 | Porterchain API + Fleetbase API same port | Separate ports (see PORT_CONFIGURATION.md) |
| Firebase docs vs driver app | `details.md` enables FCM; driver app has no push | Document as API-only |

---

## Missing dependencies (platform gap)

These should be added when respective projects enter the monorepo:

### Website

| Package | Purpose | Priority |
|---------|---------|----------|
| `@sentry/nextjs` | Error monitoring | High |
| `prettier` | Code formatting | Medium |
| `husky` + `lint-staged` | Pre-commit hooks | Medium |
| `vitest` + `@testing-library/react` | Unit tests | Medium |
| `@playwright/test` | E2E tests | Medium |
| `@supabase/supabase-js` | Booking OTP (when wired) | High |
| `@clerk/nextjs` | If portal routes merge | Low (separate app) |

### API (FastAPI — external)

| Package | Purpose |
|---------|---------|
| `fastapi`, `uvicorn` | API framework |
| `sqlalchemy`, `alembic` | ORM + migrations |
| `stripe` | Payment webhooks |
| `python-jose` / `PyJWT` | JWT verification |
| `httpx` | Fleetbase bridge calls |
| `redis` | Cache + rate limits |
| `sentry-sdk[fastapi]` | Monitoring |

### Merchant portal (external)

| Package | Purpose |
|---------|---------|
| `@clerk/nextjs` | Auth |
| `stripe` | Checkout |
| `@porterchain/api-client` | Generated API client |

### Driver app (external)

| Package | Purpose |
|---------|---------|
| `expo` ~52 | Framework |
| `react-native-maps` | Google Maps |
| `@mapbox/polyline` | Route decode |
| `expo-secure-store` | Token storage |
| `expo-location` | GPS tracking |

### Monorepo tooling (root)

| Package | Purpose |
|---------|---------|
| `turbo` | Build orchestration |
| `pnpm` | Package manager |
| `husky` | Git hooks |
| `changesets` | Version management |

---

## License audit

All website direct dependencies use permissive licenses (MIT, Apache-2.0, ISC). No GPL dependencies detected in direct tree.

**Action:** Run `license-checker --summary` in CI when monorepo is established.

---

## Bundle size notes

| Package | Impact | Notes |
|---------|--------|-------|
| `framer-motion` | Medium | Used extensively — consider lazy loading |
| `@vis.gl/react-google-maps` | Low | Loads Google script async |
| `react-markdown` + `remark-gfm` | Low | Blog pages only |
| `lucide-react` | Low | Tree-shakeable imports |

---

## Dependency governance (recommended)

### CI pipeline checks

```yaml
# .github/workflows/ci.yml — target
- run: pnpm audit --audit-level=high
- run: pnpm outdated --recursive
- run: license-checker --failOn GPL
```

### Renovate config (target)

```json
{
  "extends": ["config:base"],
  "packageRules": [
    { "matchUpdateTypes": ["patch"], "automerge": true },
    { "matchPackageNames": ["next", "react"], "matchUpdateTypes": ["major"], "enabled": false }
  ]
}
```

### Pinning policy

| Type | Policy |
|------|--------|
| Framework (Next, Expo) | Exact pin |
| Utilities (date-fns, lucide) | Caret within major |
| Security-critical (stripe, clerk) | Exact pin |
| Dev tooling | Caret |

---

## Action items

| Priority | Action |
|----------|--------|
| **P0** | Initialize git at repo root; add `.gitignore` for secrets |
| **P0** | Remove `details.md` secrets; rotate all exposed keys |
| **P1** | Add `.nvmrc`, `pnpm-workspace.yaml`, `turbo.json` |
| **P1** | Add `@sentry/nextjs` to website |
| **P2** | Upgrade `gray-matter` to address js-yaml CVE |
| **P2** | Add Prettier + Husky + lint-staged |
| **P2** | Add Vitest + Playwright |
| **P3** | Consolidate external repos; re-run this audit |

---

*Re-run `npm audit` and regenerate this report after any dependency change or monorepo consolidation.*
