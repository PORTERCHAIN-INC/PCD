# OSRM GTA ±150 km graph (not committed).

Same PBF as Valhalla: `../valhalla/data/gta-150km.osm.pbf`.

```
bash infrastructure/docker/scripts/prepare-osrm-gta.sh
docker compose --profile routing up -d osrm
```

Host: `http://127.0.0.1:5000` (`OSRM_HOST`).
