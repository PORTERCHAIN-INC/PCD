import type { GtaZone } from "./types";

/** Forward Sortation Area (FSA) — first 3 characters of Canadian postal codes */
export const GTA_ZONES: GtaZone[] = [
  {
    id: "downtown_toronto",
    name: "Downtown Toronto",
    fsaPrefixes: [
      "M4Y",
      "M4W",
      "M5A",
      "M5B",
      "M5C",
      "M5E",
      "M5G",
      "M5H",
      "M5J",
      "M5K",
      "M5L",
      "M5R",
      "M5S",
      "M5T",
      "M5V",
      "M5W",
      "M5X",
    ],
  },
  {
    id: "scarborough",
    name: "Scarborough",
    fsaPrefixes: [
      "M1B",
      "M1C",
      "M1E",
      "M1G",
      "M1H",
      "M1J",
      "M1K",
      "M1L",
      "M1M",
      "M1N",
      "M1P",
      "M1R",
      "M1S",
      "M1T",
      "M1V",
      "M1W",
      "M1X",
    ],
  },
  {
    id: "north_york",
    name: "North York",
    fsaPrefixes: [
      "M2H",
      "M2J",
      "M2K",
      "M2L",
      "M2M",
      "M2N",
      "M2P",
      "M2R",
      "M3A",
      "M3B",
      "M3C",
      "M3H",
      "M3J",
      "M3K",
      "M3L",
      "M3M",
      "M3N",
    ],
  },
  {
    id: "etobicoke",
    name: "Etobicoke",
    fsaPrefixes: [
      "M8V",
      "M8W",
      "M8X",
      "M8Y",
      "M8Z",
      "M9A",
      "M9B",
      "M9C",
      "M9P",
      "M9R",
      "M9V",
      "M9W",
    ],
  },
  {
    id: "mississauga",
    name: "Mississauga",
    fsaPrefixes: [
      "L4T",
      "L4W",
      "L4X",
      "L4Y",
      "L4Z",
      "L5A",
      "L5B",
      "L5C",
      "L5E",
      "L5G",
      "L5H",
      "L5J",
      "L5K",
      "L5L",
      "L5M",
      "L5N",
      "L5R",
      "L5S",
      "L5T",
      "L5V",
      "L5W",
    ],
  },
  {
    id: "brampton",
    name: "Brampton",
    fsaPrefixes: ["L6P", "L6R", "L6S", "L6T", "L6V", "L6W", "L6X", "L6Y", "L6Z", "L7A"],
  },
  {
    id: "oakville",
    name: "Oakville",
    fsaPrefixes: ["L6H", "L6J", "L6K", "L6L", "L6M"],
  },
  {
    id: "milton",
    name: "Milton",
    fsaPrefixes: ["L9T", "L9E"],
  },
  {
    id: "vaughan",
    name: "Vaughan",
    fsaPrefixes: ["L4H", "L4J", "L4K", "L4L", "L6A", "L3T"],
  },
  {
    id: "markham",
    name: "Markham",
    fsaPrefixes: ["L3P", "L3R", "L3S", "L6B", "L6C", "L6E", "L6G"],
  },
  {
    id: "hamilton",
    name: "Hamilton",
    fsaPrefixes: [
      "L8E",
      "L8G",
      "L8H",
      "L8J",
      "L8K",
      "L8L",
      "L8M",
      "L8N",
      "L8P",
      "L8R",
      "L8S",
      "L8T",
      "L8V",
      "L8W",
      "L9A",
      "L9B",
      "L9C",
      "L9G",
      "L9H",
      "L9K",
    ],
  },
];

const FSA_TO_ZONE = new Map<string, GtaZone>();

for (const zone of GTA_ZONES) {
  for (const fsa of zone.fsaPrefixes) {
    FSA_TO_ZONE.set(fsa.toUpperCase(), zone);
  }
}

export function resolveZoneByFsa(fsa: string): GtaZone | null {
  return FSA_TO_ZONE.get(fsa.toUpperCase()) ?? null;
}

export function getZoneById(id: string): GtaZone | undefined {
  return GTA_ZONES.find((z) => z.id === id);
}
