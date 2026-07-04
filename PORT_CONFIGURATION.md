# Porterchain — Local Port Configuration

**Document version:** 1.1  
**Date:** June 29, 2026

Single reference for **local development** ports. Production uses domain names (no local ports).

---

## Quick start (local)

| URL                        | Start command                                  |
| -------------------------- | ---------------------------------------------- |
| http://localhost:3000      | `pnpm dev:website`                             |
| http://localhost:3001      | `pnpm dev:merchant`                            |
| http://localhost:3002      | `pnpm dev:admin`                               |
| http://localhost:3003      | `pnpm dev:driver`                              |
| http://localhost:8001      | `pnpm dev:api`                                 |
| http://localhost:8001/docs | API Swagger (with API running)                 |
| http://localhost:4200      | Fleetbase console (`pnpm docker:fleetbase:up`) |
| http://localhost:8000      | Fleetbase API (with Fleetbase stack)           |

Check which ports are in use: `pnpm ports`

---

## Port allocation (local)

| Port      | Service                  | Protocol | Start / notes                                               |
| --------- | ------------------------ | -------- | ----------------------------------------------------------- |
| **3000**  | Public website           | HTTP     | `pnpm dev:website`                                          |
| **3001**  | Merchant portal          | HTTP     | `pnpm dev:merchant`                                         |
| **3002**  | Admin platform           | HTTP     | `pnpm dev:admin`                                            |
| **3003**  | Driver web portal        | HTTP     | `pnpm dev:driver` — invite links (`DRIVER_PORTAL_BASE_URL`) |
| **4200**  | Fleetbase console        | HTTP     | Docker / `apps/fleetbase` — dispatch UI                     |
| **8000**  | Fleetbase API            | HTTP     | Docker / `apps/fleetbase` — **not** Porterchain API         |
| **8001**  | Porterchain API          | HTTP     | `pnpm dev:api` — all frontends call this                    |
| **8002**  | Valhalla routing         | HTTP     | `pnpm docker:up:routing`                                    |
| **8080**  | Nginx dev proxy          | HTTP     | Docker `proxy` profile (optional)                           |
| **1025**  | Mailhog SMTP             | TCP      | `pnpm docker:up` — outbound mail capture                    |
| **8025**  | Mailhog web UI           | HTTP     | http://localhost:8025                                       |
| **3306**  | MySQL (Fleetbase)        | TCP      | `pnpm docker:up` — `127.0.0.1` only                         |
| **5432**  | PostgreSQL (Porterchain) | TCP      | `pnpm docker:up` — `127.0.0.1` only                         |
| **6379**  | Redis                    | TCP      | `pnpm docker:up` — `127.0.0.1` only                         |
| **38000** | Fleetbase SocketCluster  | WS       | Fleetbase real-time (with Fleetbase stack)                  |

**Worker** (`pnpm dev:worker`) has no HTTP port — it consumes Redis/events only.

---

## Porterchain vs Fleetbase on 8000

| Service             | Local port | Env var               | Default in code         |
| ------------------- | ---------- | --------------------- | ----------------------- |
| **Porterchain API** | **8001**   | `PORTERCHAIN_API_URL` | `http://localhost:8001` |
| **Fleetbase API**   | **8000**   | `FLEETBASE_API_URL`   | `http://localhost:8000` |

Do **not** point frontends or the mobile app at `:8000` unless you intentionally proxy Porterchain through Fleetbase. All Next.js apps and `EXPO_PUBLIC_API_URL` use **`:8001`** locally.

---

## Env files ↔ ports

Copy templates from [`env/`](./env/README.md):

| App           | Env file                          | Key URL vars                                                                                          |
| ------------- | --------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Website       | `website/.env.local`              | `NEXT_PUBLIC_SITE_URL=http://localhost:3000`, `NEXT_PUBLIC_PORTERCHAIN_API_URL=http://localhost:8001` |
| Merchant      | `apps/merchant-portal/.env.local` | `NEXT_PUBLIC_SITE_URL=http://localhost:3001`, `NEXT_PUBLIC_PORTERCHAIN_API_URL=http://localhost:8001` |
| Admin         | `apps/admin/.env.local`           | `NEXT_PUBLIC_SITE_URL=http://localhost:3002`, `NEXT_PUBLIC_PORTERCHAIN_API_URL=http://localhost:8001` |
| Driver portal | `apps/driver-portal/.env.local`   | `NEXT_PUBLIC_PORTERCHAIN_API_URL=http://localhost:8001`                                               |
| API           | `apps/api/.env`                   | `PORTERCHAIN_API_URL=http://localhost:8001`, `FLEETBASE_API_URL=http://localhost:8000`                |
| Mobile driver | `apps/mobile-driver/.env`         | `EXPO_PUBLIC_API_URL=http://localhost:8001`                                                           |

API CORS (default) allows origins `3000`–`3003`: set `CORS_ORIGINS` in `apps/api/.env` if you change any frontend port.

---

## Mobile / emulator networking

Porterchain API is on **8001** locally.

| Context                  | `EXPO_PUBLIC_API_URL`                              |
| ------------------------ | -------------------------------------------------- |
| iOS Simulator            | `http://localhost:8001` or `http://127.0.0.1:8001` |
| Android Emulator         | `http://10.0.2.2:8001`                             |
| Physical device (LAN)    | `http://<YOUR_LAN_IP>:8001`                        |
| Production               | `https://api.porterchain.com`                      |

---

## Docker: internal vs host

| Service       | Inside Docker   | From host machine       |
| ------------- | --------------- | ----------------------- |
| MySQL         | `database:3306` | `127.0.0.1:3306`        |
| PostgreSQL    | `postgres:5432` | `127.0.0.1:5432`        |
| Redis         | `cache:6379`    | `127.0.0.1:6379`        |
| Valhalla      | `valhalla:8002` | `http://localhost:8002` |
| Fleetbase API | `api:8000`      | `http://localhost:8000` |

---

## Production URLs (subdomains — no local ports)

| Service         | URL                              | Local port (dev) |
| --------------- | -------------------------------- | ---------------- |
| Website         | `https://porterchain.com`        | 3000             |
| Merchant portal | `https://merchant.porterchain.com` | 3001           |
| Admin platform  | `https://admin.porterchain.com`  | 3002             |
| Driver portal   | `https://driver.porterchain.com` | 3003             |
| Customer portal | `https://customer.porterchain.com` | 3004           |
| Porterchain API | `https://api.porterchain.com`    | 8001             |

See [`env/production.env.example`](env/production.env.example) for the full production env template.

---

## Port reservation registry

| Range     | Reserved for                  |
| --------- | ----------------------------- |
| 3000–3009 | Porterchain Next.js frontends |
| 4200–4299 | Fleetbase / console UIs       |
| 8000–8019 | HTTP APIs and routing engines |
| 3306      | MySQL                         |
| 5432      | PostgreSQL                    |
| 6379      | Redis                         |

Register new services here before assigning a port.

---

_See also: [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md), [env/README.md](./env/README.md)_
