"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AdvancedMarker, Map, useMap, useMapsLibrary } from "@vis.gl/react-google-maps";
import { MarkerClusterer } from "@googlemaps/markerclusterer";
import type { LiveMapSnapshot, MapLayers } from "@/lib/live-map";
import { GTA_DEFAULT_CENTER, GTA_DEFAULT_ZOOM, isGoogleMapsConfigured } from "@/lib/maps";
import { VEHICLE_ICONS, driverMarkerColor, VEHICLE_STATUS_COLORS } from "./map-styles";

type MapOverlay = { setMap: (map: google.maps.Map | null) => void };

function overlaySetMap(overlay: unknown, map: google.maps.Map | null) {
  if (!overlay) return;
  (overlay as MapOverlay).setMap(map);
}

type MapMode = "roadmap" | "satellite" | "hybrid" | "terrain";
type Theme = "light";

type Props = {
  data: LiveMapSnapshot;
  layers: MapLayers;
  mapMode: MapMode;
  theme: Theme;
  heatMetric: keyof LiveMapSnapshot["heat_maps"];
  selectedId: string | null;
  onSelect: (type: string, id: string) => void;
  measureActive: boolean;
  drawMode: "none" | "rectangle" | "circle" | "polygon";
  onDrawComplete?: (
    shape: google.maps.Polygon | google.maps.Circle | google.maps.Rectangle
  ) => void;
  playbackFrames?: Array<{ lat: number; lng: number; driver_id: string }>;
  playbackIndex?: number;
};

function MapLayersController({
  layers,
  theme,
  heatMetric,
  data,
}: {
  layers: MapLayers;
  theme: Theme;
  heatMetric: keyof LiveMapSnapshot["heat_maps"];
  data: LiveMapSnapshot;
}) {
  const map = useMap();
  const heatCirclesRef = useRef<google.maps.Circle[]>([]);
  const trafficRef = useRef<google.maps.TrafficLayer | null>(null);
  const transitRef = useRef<google.maps.TransitLayer | null>(null);
  const bikeRef = useRef<google.maps.BicyclingLayer | null>(null);

  useEffect(() => {
    if (!map) return;
    map.setOptions({
      colorScheme: google.maps.ColorScheme.LIGHT,
    });
  }, [map]);

  useEffect(() => {
    if (!map) return;
    if (layers.traffic) {
      trafficRef.current = trafficRef.current ?? new google.maps.TrafficLayer();
      overlaySetMap(trafficRef.current, map);
    } else {
      overlaySetMap(trafficRef.current, null);
    }
    if (layers.traffic) {
      transitRef.current = transitRef.current ?? new google.maps.TransitLayer();
      overlaySetMap(transitRef.current, map);
    } else {
      overlaySetMap(transitRef.current, null);
    }
    if (layers.traffic) {
      bikeRef.current = bikeRef.current ?? new google.maps.BicyclingLayer();
      overlaySetMap(bikeRef.current, map);
    } else {
      overlaySetMap(bikeRef.current, null);
    }
  }, [map, layers.traffic]);

  useEffect(() => {
    if (!map) return;
    heatCirclesRef.current.forEach((c) => c.setMap(null));
    heatCirclesRef.current = [];
    if (!layers.heatMap) return;

    const pts = (data.heat_maps[heatMetric] ?? []).map((p) => new google.maps.LatLng(p.lat, p.lng));
    if (!pts.length) return;

    heatCirclesRef.current = pts.map(
      (center) =>
        new google.maps.Circle({
          map,
          center,
          radius: 420,
          fillColor: "#2563eb",
          fillOpacity: 0.18,
          strokeWeight: 0,
          clickable: false,
        })
    );

    return () => {
      heatCirclesRef.current.forEach((c) => c.setMap(null));
      heatCirclesRef.current = [];
    };
  }, [map, layers.heatMap, heatMetric, data.heat_maps]);

  return null;
}

function ClusteredMarkers({
  markers,
  layers,
  onSelect,
}: {
  markers: Array<{ id: string; type: string; lat: number; lng: number; content: React.ReactNode }>;
  layers: MapLayers;
  onSelect: (type: string, id: string) => void;
}) {
  const map = useMap();
  const clustererRef = useRef<MarkerClusterer | null>(null);
  const markersRef = useRef<google.maps.marker.AdvancedMarkerElement[]>([]);
  const useCluster = layers.cluster && markers.length > 20;

  useEffect(() => {
    if (!map || !useCluster) return;
    markersRef.current.forEach((m) => {
      m.map = null;
    });
    markersRef.current = [];
    clustererRef.current?.clearMarkers();

    markers.forEach((m) => {
      const container = document.createElement("div");
      container.innerHTML = `<div style="width:28px;height:28px;border-radius:9999px;background:#2563eb;border:2px solid white;box-shadow:0 2px 8px rgba(0,0,0,.2)"></div>`;
      container.title = m.id;
      const marker = new google.maps.marker.AdvancedMarkerElement({
        position: { lat: m.lat, lng: m.lng },
        content: container,
      });
      marker.addListener("gmp-click", () => onSelect(m.type, m.id));
      markersRef.current.push(marker);
    });

    clustererRef.current = new MarkerClusterer({ map, markers: markersRef.current });

    return () => {
      clustererRef.current?.clearMarkers();
      markersRef.current.forEach((m) => {
        m.map = null;
      });
    };
  }, [map, markers, useCluster, onSelect]);

  if (useCluster) return null;

  return (
    <>
      {markers.map((m) => (
        <AdvancedMarker
          key={m.id}
          position={{ lat: m.lat, lng: m.lng }}
          onClick={() => onSelect(m.type, m.id)}
        >
          {m.content}
        </AdvancedMarker>
      ))}
    </>
  );
}

const DRAW_STYLE = {
  fillColor: "#2563eb",
  fillOpacity: 0.15,
  strokeColor: "#2563eb",
  strokeWeight: 2,
};

function DrawTools({
  mode,
  onComplete,
}: {
  mode: "none" | "rectangle" | "circle" | "polygon";
  onComplete?: (shape: google.maps.Polygon | google.maps.Circle | google.maps.Rectangle) => void;
}) {
  const map = useMap();
  const geometry = useMapsLibrary("geometry");
  const previewRef = useRef<
    google.maps.Polygon | google.maps.Circle | google.maps.Rectangle | null
  >(null);

  useEffect(() => {
    if (!map || mode === "none") return;
    if (mode === "circle" && !geometry) return;

    const listeners: google.maps.MapsEventListener[] = [];
    let start: google.maps.LatLng | null = null;
    const polygonPath: google.maps.LatLng[] = [];

    function clearPreview() {
      overlaySetMap(previewRef.current, null);
      previewRef.current = null;
    }

    function finish(shape: google.maps.Polygon | google.maps.Circle | google.maps.Rectangle) {
      clearPreview();
      onComplete?.(shape);
    }

    if (mode === "polygon") {
      const polyline = new google.maps.Polyline({
        map,
        strokeColor: DRAW_STYLE.strokeColor,
        strokeWeight: DRAW_STYLE.strokeWeight,
      });
      listeners.push(
        map.addListener("click", (e: google.maps.MapMouseEvent) => {
          if (!e.latLng) return;
          polygonPath.push(e.latLng);
          polyline.setPath(polygonPath);
        })
      );
      listeners.push(
        map.addListener("dblclick", (e: google.maps.MapMouseEvent) => {
          e.stop();
          if (polygonPath.length < 3) return;
          const polygon = new google.maps.Polygon({
            paths: polygonPath,
            map,
            ...DRAW_STYLE,
          });
          polyline.setMap(null);
          finish(polygon);
        })
      );
      return () => {
        listeners.forEach((l) => google.maps.event.removeListener(l));
        polyline.setMap(null);
        clearPreview();
      };
    }

    if (mode === "circle") {
      listeners.push(
        map.addListener("click", (e: google.maps.MapMouseEvent) => {
          if (!e.latLng) return;
          if (!start) {
            start = e.latLng;
            previewRef.current = new google.maps.Circle({
              map,
              center: start,
              radius: 1,
              ...DRAW_STYLE,
            });
            return;
          }
          const radius = google.maps.geometry.spherical.computeDistanceBetween(start, e.latLng);
          const circle = new google.maps.Circle({
            map,
            center: start,
            radius,
            ...DRAW_STYLE,
          });
          finish(circle);
        })
      );
      listeners.push(
        map.addListener("mousemove", (e: google.maps.MapMouseEvent) => {
          if (!start || !e.latLng || !(previewRef.current instanceof google.maps.Circle)) return;
          const radius = google.maps.geometry.spherical.computeDistanceBetween(start, e.latLng);
          previewRef.current.setRadius(radius);
        })
      );
      return () => {
        listeners.forEach((l) => google.maps.event.removeListener(l));
        clearPreview();
      };
    }

    // rectangle: two corner clicks
    listeners.push(
      map.addListener("click", (e: google.maps.MapMouseEvent) => {
        if (!e.latLng) return;
        if (!start) {
          start = e.latLng;
          previewRef.current = new google.maps.Rectangle({
            map,
            bounds: new google.maps.LatLngBounds(start, start),
            ...DRAW_STYLE,
          });
          return;
        }
        const bounds = new google.maps.LatLngBounds(start, e.latLng);
        const rect = new google.maps.Rectangle({
          map,
          bounds,
          ...DRAW_STYLE,
        });
        finish(rect);
      })
    );
    listeners.push(
      map.addListener("mousemove", (e: google.maps.MapMouseEvent) => {
        if (!start || !e.latLng || !(previewRef.current instanceof google.maps.Rectangle)) return;
        previewRef.current.setBounds(new google.maps.LatLngBounds(start, e.latLng));
      })
    );

    return () => {
      listeners.forEach((l) => google.maps.event.removeListener(l));
      clearPreview();
    };
  }, [map, mode, onComplete, geometry]);

  if (mode === "none") return null;

  if (mode === "circle" && !geometry) {
    return (
      <div className="pointer-events-none absolute bottom-24 left-1/2 z-20 -translate-x-1/2 rounded-xl bg-white/95 px-4 py-2 text-xs text-muted shadow-lg">
        Loading draw tools…
      </div>
    );
  }

  return (
    <div className="pointer-events-none absolute bottom-24 left-1/2 z-20 max-w-sm -translate-x-1/2 rounded-xl bg-white/95 px-4 py-2 text-center text-xs font-medium text-primary shadow-lg">
      {mode === "polygon"
        ? "Click points, double-click to finish polygon"
        : mode === "circle"
          ? "Click center, then click edge for radius"
          : "Click opposite corners for rectangle"}
    </div>
  );
}

function MeasureTool({ active }: { active: boolean }) {
  const map = useMap();
  const geometry = useMapsLibrary("geometry");
  const [path, setPath] = useState<google.maps.LatLng[]>([]);
  const lineRef = useRef<google.maps.Polyline | null>(null);

  useEffect(() => {
    if (!map || !active) {
      overlaySetMap(lineRef.current, null);
      setPath([]);
      return;
    }
    const click = map.addListener("click", (e: google.maps.MapMouseEvent) => {
      if (!e.latLng) return;
      setPath((prev) => [...prev, e.latLng!]);
    });
    return () => {
      google.maps.event.removeListener(click);
    };
  }, [map, active]);

  useEffect(() => {
    if (!map) return;
    overlaySetMap(lineRef.current, null);
    if (path.length < 2) return;
    lineRef.current = new google.maps.Polyline({
      path,
      strokeColor: "#2563eb",
      strokeWeight: 3,
      map,
    });
  }, [map, path]);

  if (!active || path.length < 2 || !geometry) return null;
  let meters = 0;
  for (let i = 1; i < path.length; i++) {
    meters += google.maps.geometry.spherical.computeDistanceBetween(path[i - 1], path[i]);
  }
  return (
    <div className="pointer-events-none absolute bottom-24 left-1/2 z-20 -translate-x-1/2 rounded-xl bg-white/95 px-4 py-2 text-sm font-medium text-primary shadow-lg">
      Distance: {(meters / 1000).toFixed(2)} km
    </div>
  );
}

function DriverPin({
  name,
  availability,
  online,
  heading,
  speed,
  vehicleType,
  showLabel,
}: {
  name: string;
  availability: string;
  online: boolean;
  heading?: number | null;
  speed?: number | null;
  vehicleType?: string | null;
  showLabel: boolean;
}) {
  const color = driverMarkerColor(availability, online);
  return (
    <div
      className="flex flex-col items-center gap-0.5"
      style={{ transform: `rotate(${heading ?? 0}deg)` }}
    >
      <div
        className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-white shadow-lg"
        style={{ backgroundColor: color }}
        title={`${name} · ${availability}${speed != null ? ` · ${speed} km/h` : ""}`}
      >
        <span className="text-sm">{vehicleType ? (VEHICLE_ICONS[vehicleType] ?? "🚗") : "🧑‍✈️"}</span>
      </div>
      {showLabel && (
        <span className="max-w-[88px] truncate rounded bg-white/90 px-1.5 py-0.5 text-[10px] font-semibold text-primary shadow">
          {name.split(" ")[0]}
        </span>
      )}
    </div>
  );
}

export default function MapCanvas({
  data,
  layers,
  mapMode,
  theme,
  heatMetric,
  selectedId,
  onSelect,
  measureActive,
  drawMode,
  onDrawComplete,
  playbackFrames,
  playbackIndex = 0,
}: Props) {
  const center = data.default_center ?? GTA_DEFAULT_CENTER;

  const driverMarkers = useMemo(() => {
    if (!layers.drivers) return [];
    return data.drivers
      .filter((d) => d.location)
      .map((d) => ({
        id: d.id,
        type: "driver",
        lat: d.location!.lat,
        lng: d.location!.lng,
        content: (
          <DriverPin
            name={d.name}
            availability={d.availability}
            online={d.online}
            heading={d.heading}
            speed={d.speed_kmh}
            vehicleType={d.vehicle_type}
            showLabel={layers.labels}
          />
        ),
      }));
  }, [data.drivers, layers.drivers, layers.labels]);

  const vehicleMarkers = useMemo(() => {
    if (!layers.vehicles) return [];
    return data.vehicles
      .filter((v) => v.location)
      .map((v) => ({
        id: v.id,
        type: "vehicle",
        lat: v.location!.lat,
        lng: v.location!.lng,
        content: (
          <div
            className="flex h-8 w-8 items-center justify-center rounded-lg border-2 border-white text-sm shadow-lg"
            style={{ backgroundColor: VEHICLE_STATUS_COLORS[v.status] ?? "#2563eb" }}
            title={`${v.plate_number} · ${v.vehicle_class}`}
          >
            {VEHICLE_ICONS[v.vehicle_class] ?? "🚗"}
          </div>
        ),
      }));
  }, [data.vehicles, layers.vehicles]);

  const orderMarkers = useMemo(() => {
    if (!layers.orders) return [];
    return data.orders.map((o) => ({
      id: `${o.order_id}-${o.stop_type}`,
      type: "order",
      lat: o.location.lat,
      lng: o.location.lng,
      content: (
        <div
          className={`flex h-7 w-7 items-center justify-center rounded-full border-2 border-white text-xs font-bold text-white shadow ${
            o.stop_type === "pickup" ? "bg-amber-500" : "bg-secondary"
          } ${o.priority === "high" ? "ring-2 ring-red-500" : ""}`}
          title={`${o.tracking_number} · ${o.stop_type}`}
        >
          {o.stop_type === "pickup" ? "P" : "D"}
        </div>
      ),
    }));
  }, [data.orders, layers.orders]);

  const staticMarkers = useMemo(() => {
    const out: Array<{
      id: string;
      type: string;
      lat: number;
      lng: number;
      content: React.ReactNode;
    }> = [];
    if (layers.warehouses) {
      for (const w of data.warehouses) {
        out.push({
          id: w.id,
          type: "warehouse",
          lat: w.location.lat,
          lng: w.location.lng,
          content: (
            <div className="rounded bg-primary px-1.5 py-0.5 text-[10px] font-bold text-white shadow">
              WH
            </div>
          ),
        });
      }
    }
    if (layers.merchants) {
      for (const m of data.merchants) {
        if (!m.location) continue;
        out.push({
          id: m.id,
          type: "merchant",
          lat: m.location.lat,
          lng: m.location.lng,
          content: (
            <div className="rounded-full bg-violet-600 px-2 py-1 text-[10px] font-semibold text-white shadow">
              M
            </div>
          ),
        });
      }
    }
    if (layers.customers) {
      for (const c of data.customers) {
        if (!c.location) continue;
        out.push({
          id: c.id,
          type: "customer",
          lat: c.location.lat,
          lng: c.location.lng,
          content: (
            <div className="rounded-full bg-teal-600 px-2 py-1 text-[10px] font-semibold text-white shadow">
              C
            </div>
          ),
        });
      }
    }
    return out;
  }, [data, layers.warehouses, layers.merchants, layers.customers]);

  const allMarkers = [...driverMarkers, ...vehicleMarkers, ...orderMarkers, ...staticMarkers];

  const playbackMarker = playbackFrames?.[playbackIndex];

  if (!isGoogleMapsConfigured()) {
    return (
      <div className="flex h-full items-center justify-center bg-gradient-to-br from-[#eaf1fb] to-[#f6f9ff] p-8 text-center">
        <div>
          <p className="text-lg font-semibold text-primary">Google Maps API key required</p>
          <p className="mt-2 max-w-md text-sm text-muted">
            Set <code className="rounded bg-white px-1">NEXT_PUBLIC_GOOGLE_MAPS_API_KEY</code> to
            enable the live operations map. Operational data is still available in the side panels.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-full w-full">
      <Map
        defaultCenter={center}
        defaultZoom={GTA_DEFAULT_ZOOM}
        mapId="porterchain-live-map"
        mapTypeId={mapMode}
        gestureHandling="greedy"
        disableDefaultUI
        zoomControl
        fullscreenControl
        streetViewControl
        rotateControl
        className="h-full w-full"
        clickableIcons={false}
      >
        <MapLayersController layers={layers} theme={theme} heatMetric={heatMetric} data={data} />
        <DrawTools mode={drawMode} onComplete={onDrawComplete} />
        <MeasureTool active={measureActive} />
        <ClusteredMarkers markers={allMarkers} layers={layers} onSelect={onSelect} />
        {playbackMarker && (
          <AdvancedMarker position={{ lat: playbackMarker.lat, lng: playbackMarker.lng }}>
            <div className="h-4 w-4 animate-pulse rounded-full bg-red-500 ring-4 ring-red-300" />
          </AdvancedMarker>
        )}
        {layers.geofences &&
          data.geofences.map((g) => {
            const bounds = g.bounds as {
              north?: number;
              south?: number;
              east?: number;
              west?: number;
            };
            if (
              bounds.north == null ||
              bounds.south == null ||
              bounds.east == null ||
              bounds.west == null
            )
              return null;
            return (
              <GeofenceRect
                key={g.id}
                bounds={{
                  north: bounds.north,
                  south: bounds.south,
                  east: bounds.east,
                  west: bounds.west,
                }}
                name={g.name}
              />
            );
          })}
      </Map>
    </div>
  );
}

function GeofenceRect({
  bounds,
  name,
}: {
  bounds: { north: number; south: number; east: number; west: number };
  name: string;
}) {
  const map = useMap();
  useEffect(() => {
    if (!map) return;
    const rect = new google.maps.Rectangle({
      bounds: {
        north: bounds.north,
        south: bounds.south,
        east: bounds.east,
        west: bounds.west,
      },
      strokeColor: "#2563eb",
      strokeOpacity: 0.8,
      strokeWeight: 2,
      fillColor: "#2563eb",
      fillOpacity: 0.08,
      map,
    });
    return () => overlaySetMap(rect, null);
  }, [map, bounds, name]);
  return null;
}
