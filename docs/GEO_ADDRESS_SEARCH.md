# Address search and maps (free first, Google as backup)

- **Maps:** MapLibre with self-hosted Protomaps tiles at tiles.porterchain.com (GTA + 150 km).
- **Address search:** our own Photon index (GTA + 150 km, built on the home build server,
  monthly) behind `/v1/geo/autocomplete` and `/v1/geo/place`, with Nominatim if Photon is down.
- **Google Maps (Places) is kept as a parallel backup for addresses.** Our own free address
  search (Photon/NAR) always goes first; Google is only queried when ours finds nothing
  confident, so usage should stay within Google's free monthly allowance. This fallback ensures
  customers and merchants aren't affected if our search misses, with minimal budget impact.

## Google backup details

- Server-side only (`geo_google.py`), Places API (New) Autocomplete + Place Details.
- Key: `GOOGLE_MAPS_SERVER_API_KEY` (Doppler `pcd/prd`), IP-restricted to the droplet
  (68.183.103.49), APIs limited to Places (New) + Geocoding. Never shipped to browsers or apps.
- Switch: `GEO_GOOGLE_FALLBACK` (compose default `1`); set `0` in Doppler to turn it off.
- Daily cap: `GEO_GOOGLE_DAILY_CAP` (default 300 billable calls/day, autocomplete and details
  both count). Fails closed: no Redis counter, no Google call.
- Usage: Redis `pc:geo:google:calls:YYYYMMDD`, shown in admin → Settings → Integrations
  (`google_maps.places_fallback`).

## When results count as confident (no Google call)

- An address point whose house number **and** street match what was typed.
- A named place or postal-code hit.
- Street-only hits are never confident; the typed house number is kept only when all matching
  segments are one stretch of road (within 1.5 km).
