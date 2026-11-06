# Address search and maps (free first, Google as backup)

- **Maps:** MapLibre with self-hosted Protomaps tiles at tiles.porterchain.com (GTA + 150 km).
- **Address search:** our own Photon index (GTA + 150 km, built on the home build server,
  monthly) behind `/v1/geo/autocomplete` and `/v1/geo/place`, with Nominatim if Photon is down.
- **Google Places (New) is a capped server-side backup for addresses.** Photon always goes
  first; Google is queried only when Photon is not confident, so usage should stay within
  Google's free monthly allowance. UI clients keep calling `/v1/geo` only — no browser Places
  widget, no Distance Matrix, no Maps JS SDK for search.

## Google backup details

- Server-side only (`apps/api/src/porterchain_api/geo_google.py`), Places API (New)
  Autocomplete + Place Details.
- Key: `GOOGLE_MAPS_SERVER_API_KEY` from droplet SOPS (`secrets/droplet.enc.yaml`),
  IP-restricted to the droplet, APIs limited to Places (New) (+ Geocoding if already enabled).
  Never shipped to browsers or apps. Do **not** enable Google Cloud billing without an
  explicit go-ahead — free tier only.
- Switch: `GEO_GOOGLE_FALLBACK` (compose default `1`); set `0` to turn the backup off.
- Daily cap: `GEO_GOOGLE_DAILY_CAP` (default 300 billable calls/day; autocomplete and details
  both count). Fails closed: no Redis counter → no Google call.
- Usage: Redis `pc:geo:google:calls:YYYYMMDD`, shown in admin → Settings → Integrations
  (`maps.places_fallback`).

## Enable on the droplet (after merge)

1. Ensure `GOOGLE_MAPS_SERVER_API_KEY` is present in SOPS (see open secrets PR for Google keys)
   and sync secrets to the api runtime env.
2. Set `GEO_GOOGLE_FALLBACK=true` (or `1`) and optionally `GEO_GOOGLE_DAILY_CAP=300` on the
   api service, then recreate/restart **api only** (no full stack redeploy required for the
   flag once the image with `geo_google.py` is live).
3. Smoke: type an address Photon misses in a portal address field; response `source` should be
   `photon+google` and suggestions should include Google hits. Confident Photon hits must stay
   `source: photon` with no Google call.

## When results count as confident (no Google call)

- An address point whose house number **and** street match what was typed.
- A named place or postal-code hit.
- Street-only hits are never confident; the typed house number is kept only when all matching
  segments are one stretch of road (within 1.5 km).
