export type LatLng = { latitude: number; longitude: number };

export type MapMarker = LatLng & {
  id: string;
  title?: string;
  description?: string;
};

export type MapRegion = LatLng & {
  latitudeDelta: number;
  longitudeDelta: number;
};

export const DEFAULT_REGION: MapRegion = {
  latitude: 43.6532,
  longitude: -79.3832,
  latitudeDelta: 0.08,
  longitudeDelta: 0.08,
};
