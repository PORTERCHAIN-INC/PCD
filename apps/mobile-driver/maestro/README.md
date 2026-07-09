# Maestro smoke — Driver app

Dev-layer mobile smoke for §2.1.10 (login + track).

## Run

```bash
pnpm --filter @porterchain/mobile-driver start
maestro test apps/mobile-driver/maestro/login-and-track.yaml
```

Structure validation: `pnpm validate:mobile-smoke`
