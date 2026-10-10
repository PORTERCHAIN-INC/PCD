export function formatCents(cents: number | null | undefined, currency = "CAD"): string {
  if (cents == null || Number.isNaN(cents)) return "—";
  return new Intl.NumberFormat("en-CA", { style: "currency", currency }).format(cents / 100);
}

export function formatKm(meters: number | null | undefined): string {
  if (meters == null) return "—";
  if (meters < 1000) return `${Math.round(meters)} m`;
  return `${(meters / 1000).toFixed(1)} km`;
}

export function formatAccessLine(bits: {
  special_instructions?: string | null;
  access_unit?: string | null;
  access_buzzer?: string | null;
  access_dock?: string | null;
  call_on_arrival?: boolean | null;
  contact_phone_masked?: string | null;
}): string | null {
  const parts: string[] = [];
  if (bits.access_unit) parts.push(`Unit ${bits.access_unit}`);
  if (bits.access_buzzer) parts.push(`Buzzer ${bits.access_buzzer}`);
  if (bits.access_dock) parts.push(`Dock ${bits.access_dock}`);
  if (bits.call_on_arrival) parts.push("Call on arrival");
  if (bits.contact_phone_masked) parts.push(bits.contact_phone_masked);
  if (bits.special_instructions) parts.push(bits.special_instructions);
  return parts.length ? parts.join(" · ") : null;
}
