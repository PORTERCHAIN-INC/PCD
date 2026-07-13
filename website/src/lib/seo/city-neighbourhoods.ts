/**
 * Neighbourhood / district coverage on existing city & service-area URLs.
 * Charter: deepen metro pages — do NOT generate zip/FSA landing routes.
 */

export type CityNeighbourhood = {
  name: string;
  /** Representative FSA prefixes (first 3 chars) for schema + coverage UX */
  fsaPrefixes: string[];
};

/** service-area slug → neighbourhoods (core metros first). */
export const CITY_NEIGHBOURHOODS: Record<string, CityNeighbourhood[]> = {
  toronto: [
    { name: "Downtown / Core", fsaPrefixes: ["M5H", "M5V", "M5G"] },
    { name: "North York", fsaPrefixes: ["M2N", "M2J", "M3H"] },
    { name: "Scarborough", fsaPrefixes: ["M1B", "M1K", "M1T"] },
    { name: "Etobicoke", fsaPrefixes: ["M8V", "M9B", "M9W"] },
    { name: "East York / Midtown", fsaPrefixes: ["M4J", "M4S", "M4P"] },
  ],
  mississauga: [
    { name: "City Centre / Square One", fsaPrefixes: ["L5B", "L5A"] },
    { name: "Airport / Northeast", fsaPrefixes: ["L4V", "L4T", "L5T"] },
    { name: "Port Credit / Lakeshore", fsaPrefixes: ["L5G", "L5H"] },
    { name: "Meadowvale / Northwest", fsaPrefixes: ["L5N", "L5M"] },
  ],
  brampton: [
    { name: "Downtown Brampton", fsaPrefixes: ["L6T", "L6V"] },
    { name: "Bramalea", fsaPrefixes: ["L6T", "L6R"] },
    { name: "Mount Pleasant / Northwest", fsaPrefixes: ["L7A", "L6Y"] },
  ],
  vaughan: [
    { name: "Vaughan Metropolitan Centre", fsaPrefixes: ["L4K", "L4J"] },
    { name: "Concord / Highway 7", fsaPrefixes: ["L4K"] },
    { name: "Woodbridge", fsaPrefixes: ["L4L", "L4H"] },
  ],
  markham: [
    { name: "Markham Centre", fsaPrefixes: ["L3R", "L6G"] },
    { name: "Unionville", fsaPrefixes: ["L3R"] },
    { name: "Milliken", fsaPrefixes: ["L3R", "L6C"] },
  ],
  oakville: [
    { name: "Downtown Oakville", fsaPrefixes: ["L6J", "L6K"] },
    { name: "Uptown Core", fsaPrefixes: ["L6H", "L6M"] },
    { name: "Bronte", fsaPrefixes: ["L6L"] },
  ],
  hamilton: [
    { name: "Downtown Hamilton", fsaPrefixes: ["L8P", "L8R"] },
    { name: "Stoney Creek", fsaPrefixes: ["L8E", "L8G"] },
    { name: "Ancaster / Dundas", fsaPrefixes: ["L9G", "L9H"] },
  ],
  "kitchener-waterloo": [
    { name: "Downtown Kitchener", fsaPrefixes: ["N2G", "N2H"] },
    { name: "Uptown Waterloo", fsaPrefixes: ["N2L", "N2J"] },
    { name: "Cambridge corridors", fsaPrefixes: ["N1R", "N3H"] },
  ],
};

export function getCityNeighbourhoods(slug: string): CityNeighbourhood[] {
  return CITY_NEIGHBOURHOODS[slug] ?? [];
}

/** Distinct FSA prefixes for Service schema postalCode on the city URL. */
export function getCityPostalCodes(slug: string, limit = 12): string[] {
  const seen = new Set<string>();
  for (const n of getCityNeighbourhoods(slug)) {
    for (const fsa of n.fsaPrefixes) {
      if (!seen.has(fsa)) seen.add(fsa);
      if (seen.size >= limit) return [...seen];
    }
  }
  return [...seen];
}
