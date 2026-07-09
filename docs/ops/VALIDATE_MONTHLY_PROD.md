# Monthly prod validation cadence (§5 · EXE-G4)

**Type:** CANONICAL  
**Checklist:** EXE-G4  
**Last verified:** 2026-07-09

## Schedule

| When       | Action                                                                     |
| ---------- | -------------------------------------------------------------------------- |
| 1st Monday | Run prod smoke suite from ops laptop or GitHub Actions `workflow_dispatch` |
| Same week  | Archive output to `docs/ops/validate-logs/YYYY-MM.md` (redacted)           |

## Commands (prod)

```bash
pnpm validate:p0:prod          # health + Stripe + Fleetbase probe
pnpm validate:d3:prod          # portal contract smoke
pnpm validate:investor-monopoly
pnpm validate:enterprise-security
```

## Pass criteria

- All commands exit 0
- No new Critical DD items in Appendix H
- `/health/ready` fleetbase_sync.meets_slo when bridge enabled

## Dev layer

CI runs full `validate:*` on every PR — this doc covers **prod recurrence** only.
