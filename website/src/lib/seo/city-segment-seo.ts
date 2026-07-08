/**
 * City + segment SEO URL matrix: industry, vehicle, and delivery-intent pages.
 * Powers routes like /toronto/van-delivery and /toronto/same-day-delivery.
 */

import {
  CITY_SEO_SLUGS,
  CITY_SEO_TO_SERVICE_AREA,
  getCityIndustrySeoPairs,
  isValidCitySeoSlug,
  isValidIndustrySeoSlug,
  resolveCityIndustrySeo,
  type CitySeoSlug,
  type IndustrySeoSlug,
} from "./city-industry-seo";

export { getCityIndustrySeoPairs };

export const VEHICLE_CITY_SEO_SLUGS = [
  "sedan-delivery",
  "suv-delivery",
  "van-delivery",
  "pickup-truck-delivery",
  "cargo-van-delivery",
  "medium-truck",
] as const;

export type VehicleCitySeoSlug = (typeof VEHICLE_CITY_SEO_SLUGS)[number];

export const DELIVERY_INTENT_CITY_SEO_SLUGS = [
  "same-day-delivery",
  "local-courier",
  "last-mile-delivery",
  "b2b-delivery",
  "recurring-delivery",
  "on-demand-delivery",
] as const;

export type DeliveryIntentCitySeoSlug = (typeof DELIVERY_INTENT_CITY_SEO_SLUGS)[number];

export const VEHICLE_SEO_TO_MESSAGE_KEY: Record<VehicleCitySeoSlug, string> = {
  "sedan-delivery": "sedan",
  "suv-delivery": "suv",
  "van-delivery": "van",
  "pickup-truck-delivery": "pickupTruck",
  "cargo-van-delivery": "cargoVan",
  "medium-truck": "mediumTruck",
};

export const DELIVERY_INTENT_SEO_TO_MESSAGE_KEY: Record<DeliveryIntentCitySeoSlug, string> = {
  "same-day-delivery": "sameDay",
  "local-courier": "localCourier",
  "last-mile-delivery": "lastMile",
  "b2b-delivery": "b2b",
  "recurring-delivery": "recurring",
  "on-demand-delivery": "onDemand",
};

export type CitySegmentType = "industry" | "vehicle" | "delivery-intent";

export type ResolvedCitySegment =
  | { type: "industry"; nicheSlug: string; serviceAreaSlug: string; segmentSlug: IndustrySeoSlug }
  | {
      type: "vehicle";
      vehicleKey: string;
      serviceAreaSlug: string;
      segmentSlug: VehicleCitySeoSlug;
    }
  | {
      type: "delivery-intent";
      intentKey: string;
      serviceAreaSlug: string;
      segmentSlug: DeliveryIntentCitySeoSlug;
    };

export function isValidVehicleCitySeoSlug(s: string): s is VehicleCitySeoSlug {
  return (VEHICLE_CITY_SEO_SLUGS as readonly string[]).includes(s);
}

export function isValidDeliveryIntentCitySeoSlug(s: string): s is DeliveryIntentCitySeoSlug {
  return (DELIVERY_INTENT_CITY_SEO_SLUGS as readonly string[]).includes(s);
}

export function resolveCitySegment(
  cityUrlSlug: string,
  segmentUrlSlug: string
): ResolvedCitySegment | null {
  if (!isValidCitySeoSlug(cityUrlSlug)) return null;
  const serviceAreaSlug = CITY_SEO_TO_SERVICE_AREA[cityUrlSlug];

  if (isValidIndustrySeoSlug(segmentUrlSlug)) {
    const industry = resolveCityIndustrySeo(cityUrlSlug, segmentUrlSlug);
    if (!industry) return null;
    return {
      type: "industry",
      nicheSlug: industry.nicheSlug,
      serviceAreaSlug: industry.serviceAreaSlug,
      segmentSlug: segmentUrlSlug,
    };
  }

  if (isValidVehicleCitySeoSlug(segmentUrlSlug)) {
    return {
      type: "vehicle",
      vehicleKey: VEHICLE_SEO_TO_MESSAGE_KEY[segmentUrlSlug],
      serviceAreaSlug,
      segmentSlug: segmentUrlSlug,
    };
  }

  if (isValidDeliveryIntentCitySeoSlug(segmentUrlSlug)) {
    return {
      type: "delivery-intent",
      intentKey: DELIVERY_INTENT_SEO_TO_MESSAGE_KEY[segmentUrlSlug],
      serviceAreaSlug,
      segmentSlug: segmentUrlSlug,
    };
  }

  return null;
}

export function getCityVehicleSeoPairs(): { city: CitySeoSlug; segmentSlug: VehicleCitySeoSlug }[] {
  const pairs: { city: CitySeoSlug; segmentSlug: VehicleCitySeoSlug }[] = [];
  for (const city of CITY_SEO_SLUGS) {
    for (const segmentSlug of VEHICLE_CITY_SEO_SLUGS) {
      pairs.push({ city, segmentSlug });
    }
  }
  return pairs;
}

export function getCityDeliveryIntentSeoPairs(): {
  city: CitySeoSlug;
  segmentSlug: DeliveryIntentCitySeoSlug;
}[] {
  const pairs: { city: CitySeoSlug; segmentSlug: DeliveryIntentCitySeoSlug }[] = [];
  for (const city of CITY_SEO_SLUGS) {
    for (const segmentSlug of DELIVERY_INTENT_CITY_SEO_SLUGS) {
      pairs.push({ city, segmentSlug });
    }
  }
  return pairs;
}

/** All (city, segment) pairs for static generation — industry, vehicle, and delivery intent. */
export function getAllCitySegmentPairs(): { city: CitySeoSlug; segmentSlug: string }[] {
  return [
    ...getCityIndustrySeoPairs().map((p) => ({
      city: p.city,
      segmentSlug: p.industrySlug,
    })),
    ...getCityVehicleSeoPairs().map((p) => ({
      city: p.city,
      segmentSlug: p.segmentSlug,
    })),
    ...getCityDeliveryIntentSeoPairs().map((p) => ({
      city: p.city,
      segmentSlug: p.segmentSlug,
    })),
  ];
}
