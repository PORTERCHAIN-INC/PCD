export const LIGHT_MAP_STYLE: google.maps.MapTypeStyle[] = [];

export const DARK_MAP_STYLE: google.maps.MapTypeStyle[] = [
  { elementType: "geometry", stylers: [{ color: "#1d2c4d" }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#8ec3b9" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#1a3646" }] },
  { featureType: "administrative.country", elementType: "geometry.stroke", stylers: [{ color: "#4b6878" }] },
  { featureType: "administrative.land_parcel", elementType: "labels.text.fill", stylers: [{ color: "#64748b" }] },
  { featureType: "poi", elementType: "labels.text.fill", stylers: [{ color: "#6f9ba5" }] },
  { featureType: "poi.park", elementType: "geometry", stylers: [{ color: "#263c3f" }] },
  { featureType: "road", elementType: "geometry", stylers: [{ color: "#304a7d" }] },
  { featureType: "road", elementType: "geometry.stroke", stylers: [{ color: "#255763" }] },
  { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#2c6675" }] },
  { featureType: "transit", elementType: "labels.text.fill", stylers: [{ color: "#98a5be" }] },
  { featureType: "water", elementType: "geometry", stylers: [{ color: "#0e1626" }] },
];

export const DRIVER_STATUS_COLORS: Record<string, string> = {
  online: "#16a34a",
  offline: "#64748b",
  busy: "#f59e0b",
  break: "#8b5cf6",
  idle: "#0ea5e9",
  emergency: "#dc2626",
  available: "#2563eb",
};

export const VEHICLE_STATUS_COLORS: Record<string, string> = {
  available: "#16a34a",
  assigned: "#2563eb",
  busy: "#f59e0b",
  maintenance: "#ea580c",
  offline: "#64748b",
};

export const VEHICLE_ICONS: Record<string, string> = {
  sedan: "🚗",
  suv: "🚙",
  pickup_truck: "🛻",
  cargo_van: "🚐",
  sprinter_van: "🚐",
  box_truck: "🚚",
};

export function driverMarkerColor(availability: string, online: boolean): string {
  if (!online) return DRIVER_STATUS_COLORS.offline;
  return DRIVER_STATUS_COLORS[availability] ?? DRIVER_STATUS_COLORS.online;
}
