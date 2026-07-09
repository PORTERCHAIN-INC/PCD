# Design copy — ban list & preferred vocabulary

**Type:** CANONICAL  
**Checklist:** §6.1.2 · §6.1.3 · §1.1.2  
**Last verified:** 2026-07-08

---

## Ban list (never use in product/marketing UI)

| Term / phrase                       | Why                                                | Use instead                                           |
| ----------------------------------- | -------------------------------------------------- | ----------------------------------------------------- |
| logistics company (self-desc)       | Positions Porterchain as a courier operator        | logistics technology platform, orchestration platform |
| courier app                         | Consumer gig-economy framing                       | B2B delivery platform, driver platform                |
| gig / side hustle / flexible hours  | Undermines enterprise B2B demo                     | professional driver network, contracted routes        |
| we deliver for you (platform voice) | Implies Porterchain is the carrier                 | we orchestrate delivery for your business             |
| Uber for X                          | Investor cliché                                    | structured B2B logistics orchestration                |
| best courier / cheapest courier     | Commodity comparison                               | predictable SLAs, live visibility, integrations       |
| ad-hoc courier (without context)    | OK when describing customer pain, not our identity | ad-hoc couriers (problem) → Porterchain (solution)    |

**Legal pages:** `legal-en.json` may retain “commercial logistics company” where legally required for contracts and privacy — do not change without counsel.

---

## Preferred vocabulary

| Concept          | Preferred term                                                  |
| ---------------- | --------------------------------------------------------------- |
| Product category | Logistics technology · orchestration platform · Dispatch OS     |
| Customer         | Merchant · business · shipper · operations leader               |
| Driver surface   | Driver platform · professional driver network                   |
| Core value       | Live visibility · merchant integrations · structured operations |
| vs legacy        | Outgrew ad-hoc couriers · spreadsheet dispatch                  |
| Geography        | Greater Toronto Area (GTA) · Ontario (when scoped)              |

---

## File owners

| Surface          | Files                                |
| ---------------- | ------------------------------------ |
| Corporate site   | `website/messages/corporate-en.json` |
| Business landing | `website/messages/business-en.json`  |
| Consumer retail  | `website/messages/en.json`           |
| Portals          | `apps/*/src` copy + i18n as added    |

---

## Review gate

Before marking §6.1 copy items done in a PR:

1. Run the automated gate (blocks CI — §6.1.2 · DES-G2):

```bash
pnpm validate:design-copy
```

2. Hero/metadata use platform vocabulary, not operator self-description.
3. Driver portal: earnings/statements OK; avoid gig-economy framing.

Context-sensitive carve-outs (rejected-misconception FAQ, employee careers copy)
are enumerated as reviewed exceptions in `scripts/verify_design_copy.py`. Add new
exceptions there with a one-line rationale rather than weakening the patterns.

Manual spot-check for TSX copy not yet in i18n JSON:

```bash
rg -i 'logistics company|gig economy|side hustle|courier app' apps/*/src
```
