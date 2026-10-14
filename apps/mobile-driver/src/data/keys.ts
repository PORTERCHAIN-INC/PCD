/** Query keys. Only keys in PERSISTED are written (encrypted) to the device cache. */
export const qk = {
  handshake: ["handshake"] as const,
  route: ["dispatch", "route"] as const,
  earnings: ["earnings", "today"] as const,
  support: ["support", "hub"] as const,
  documents: ["documents"] as const,
  vehicle: ["vehicle"] as const,
  settings: ["settings"] as const,
  policy: ["policy"] as const,
  profile: ["profile"] as const,
  earningsFull: ["pay", "earnings"] as const,
  statements: ["pay", "statements"] as const,
  timesheets: ["time", "sheets"] as const,
  schedule: ["time", "schedule"] as const,
  inbox: ["inbox"] as const,
  tickets: ["tickets"] as const,
};

export const PERSISTED = new Set<string>([
  "handshake",
  "dispatch",
  "earnings",
  "support",
  "documents",
  "vehicle",
  "settings",
  "policy",
  "profile",
  "pay",
  "time",
  "inbox",
  "tickets",
]);

/** Pure: should this cached query be written to disk? (success only, allow-listed, no file bytes). */
export function shouldPersist(q: {
  queryKey: readonly unknown[];
  state: { status: string };
}): boolean {
  return q.state.status === "success" && PERSISTED.has(String(q.queryKey[0]));
}

/** "now", "12s", "4m", "2h", "3d" — for the subtle "updated … ago" line. */
export function agoLabel(updatedAt: number, now: number): string {
  if (!updatedAt) return "";
  const s = Math.max(0, Math.round((now - updatedAt) / 1000));
  if (s < 5) return "now";
  if (s < 60) return `${s}s ago`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 48) return `${h}h ago`;
  return `${Math.round(h / 24)}d ago`;
}
