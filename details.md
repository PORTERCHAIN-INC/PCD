# Environment configuration index

**Do not store secrets in this file.** Use local `.env` files (gitignored).

## Templates (copy → fill secrets)

| Service | Template | Local file |
|---------|----------|------------|
| Website | [env/website.env.example](env/website.env.example) | `website/.env.local` |
| Porterchain API | [env/api.env.example](env/api.env.example) | `apps/api/.env` |
| Fleetbase | [env/fleetbase.env.example](env/fleetbase.env.example) | `services/fleetbase/.env` |
| Merchant portal | [env/merchant-portal.env.example](env/merchant-portal.env.example) | `apps/merchant-portal/.env.local` |
| Driver app | [env/mobile-driver.env.example](env/mobile-driver.env.example) | `apps/mobile-driver/.env` |
| Docker Compose | [env/compose.env.example](env/compose.env.example) | `.env` (repo root) |

Quick start for this repo:

```bash
cp env/website.env.example website/.env.local
# Paste secrets into website/.env.local
```

## Documentation

- [env/README.md](env/README.md) — usage guide
- [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) — full catalog
- [PORT_CONFIGURATION.md](PORT_CONFIGURATION.md) — ports

## Local ports

| Port | Service |
|------|---------|
| 3000 | Website |
| 3001 | Merchant portal |
| 3003 | Driver invite web portal |
| 4200 | Fleetbase console |
| 8000 | Fleetbase API |
| 8001 | Porterchain API (recommended) |
| 8002 | Valhalla |

## Security

If this file previously contained live API keys or passwords, **rotate those credentials** — treat them as exposed.
