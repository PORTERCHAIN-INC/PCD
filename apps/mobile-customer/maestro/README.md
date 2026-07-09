# Maestro smoke — Customer app

Dev-layer mobile smoke for §2.1.10 (login + track).

## Prerequisites

- [Maestro CLI](https://maestro.mobile.dev/) installed
- Expo dev build or simulator with `com.porterchain.customer` installed

## Run

```bash
pnpm --filter @porterchain/mobile-customer start
# separate terminal, with simulator running:
maestro test apps/mobile-customer/maestro/login-and-track.yaml
```

Structure validation (no simulator):

```bash
pnpm validate:mobile-smoke
```
