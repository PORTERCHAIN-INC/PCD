# Porterchain 5-minute demo script

**Audience:** Enterprise logistics buyer or investor  
**Duration:** 5 minutes  
**Goal:** Show orchestration platform value end-to-end without caveats.

---

## Prerequisites (dev / staging setup)

Run the local stack before the meeting:

```bash
pnpm install && pnpm db:migrate
pnpm dev                    # API :8001, website :3000, portals
pnpm validate:p0:fast       # confirms G1–G9 health
```

Use Clerk dev bypass (`Bearer dev`) for admin and merchant portals. Seed or complete one booking via the website widget so you have a live tracking number.

---

## Demo script (spoken narrative)

### Minute 0:00 — Homepage positioning

1. Open `http://localhost:3000` (or `https://porterchain.com` in prod).
2. **Say:** “Porterchain is a logistics orchestration platform — merchants book, we coordinate professional drivers, and every stakeholder gets live visibility.”
3. Scroll to the **Book delivery** widget in the hero.
4. Enter a GTA pickup and drop-off, choose vehicle class, and show the instant quote.

### Minute 1:00 — Book and pay

1. Complete checkout (Stripe test card in dev: `4242 4242 4242 4242`).
2. Land on the confirmation screen and copy the **tracking number**.
3. **Say:** “Quote, payment, and order creation are one flow — no separate courier app, no manual dispatch email.”

### Minute 1:30 — Customer track (map + ETA)

1. Open `/track/{tracking}` on the website (or customer portal `http://localhost:3002/track/{tracking}`).
2. Point to the **route map**, driver pin when in transit, and the **estimated arrival** panel.
3. **Say:** “Shippers and recipients see the same live map and ETA your ops team uses internally.”

### Minute 2:30 — Merchant portal

1. Sign in to merchant portal (`http://localhost:3003`).
2. Open **Orders** → the new shipment → **Live tracking**.
3. Show timeline, map layers (Valhalla route + OSRM ETA path), and POD gallery when delivered.
4. **Say:** “Merchants manage bulk uploads, billing, and live tracking without calling your dispatch desk.”

### Minute 3:30 — Admin operations

1. Sign in to admin (`http://localhost:3004`).
2. Open **Operations** or **Live map** — show active drivers and in-flight orders.
3. **Say:** “Your control tower assigns drivers, replays routes, and surfaces exceptions in one surface.”

### Minute 4:30 — Close

1. Return to homepage **Developers** footer link or `/developers`.
2. **Say:** “Partners integrate through documented APIs, webhooks, and scoped keys — Porterchain is the system of record, not a white-label courier.”
3. Offer pilot timeline and SLA conversation.

---

## Success criteria

| Beat                | Surface                      | Pass if                                 |
| ------------------- | ---------------------------- | --------------------------------------- |
| Quote + book        | Website widget               | Quote → checkout → tracking number      |
| Track               | Website or customer `/track` | Map + ETA visible                       |
| Merchant visibility | Merchant live tracking       | Map + timeline                          |
| Ops control         | Admin live map / operations  | Active orders visible                   |
| Platform story      | Homepage + `/developers`     | Orchestration language, API docs linked |

---

## Troubleshooting (do not read aloud)

| Issue              | Fix                                                            |
| ------------------ | -------------------------------------------------------------- |
| Map blank          | Set `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` in portal env            |
| No ETA             | Ensure pickup/drop-off have lat/lng from Places autocomplete   |
| No live driver pin | Order must be dispatched with Fleetbase bridge enabled locally |
| Auth blocked       | `CLERK_DEV_BYPASS=true` / `NEXT_PUBLIC_CLERK_DEV_BYPASS=true`  |
