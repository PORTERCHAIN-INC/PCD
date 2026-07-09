# Design review rubric (§6 · DES-G1)

**Type:** CANONICAL  
**Checklist:** DES-G1  
**Last verified:** 2026-07-09

## Scope

External designer scores **homepage** + **merchant portal** against this rubric. Target: **≥8/10** average.

| Criterion          | Weight | Pass (8+)                                      |
| ------------------ | ------ | ---------------------------------------------- |
| Visual hierarchy   | 20%    | Hero → CTA → proof clear in 5s                 |
| Brand consistency  | 15%    | Matches `@porterchain/ui` tokens               |
| Trust signals      | 15%    | No ban-list words; case study linked           |
| Merchant task flow | 25%    | Book → track → billing without dead ends       |
| Accessibility      | 15%    | Focus rings, contrast, `validate:booking-a11y` |
| Mobile responsive  | 10%    | Admin tablet + merchant breakpoints            |

## Process

1. Designer receives staging URLs (localhost or staging)
2. Score each criterion 1–10
3. File issues in GitHub with `design-review` label
4. Re-review after fixes

## Dev substitutes (until external review)

- `pnpm validate:design` — copy ban-list + i18n + tracking maps
- `pnpm validate:portal-ux` — empty states + skeletons

**Status:** Rubric ready — external designer session not scheduled.
