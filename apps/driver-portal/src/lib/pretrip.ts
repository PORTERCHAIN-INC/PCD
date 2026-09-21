export const PRETRIP_ITEMS = [
  { id: "lights", label: "Lights working" },
  { id: "tires", label: "Tires OK" },
  { id: "plates", label: "Plates visible" },
  { id: "leaks", label: "No fluid leaks" },
  { id: "winter_kit", label: "Winter kit on board" },
] as const;

export type PretripId = (typeof PRETRIP_ITEMS)[number]["id"];

export type PretripChecks = Record<PretripId, boolean>;

export const emptyPretrip = (): PretripChecks => ({
  lights: false,
  tires: false,
  plates: false,
  leaks: false,
  winter_kit: false,
});

export function pretripComplete(checks: PretripChecks): boolean {
  return PRETRIP_ITEMS.every((item) => checks[item.id]);
}
