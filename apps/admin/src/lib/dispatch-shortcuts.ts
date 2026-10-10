/** Dispatcher keyboard map — pure so it can be unit tested. */

export type ShortcutAction =
  | { kind: "tab"; index: number }
  | { kind: "plan" }
  | { kind: "approve" }
  | { kind: "new" }
  | { kind: "refresh" }
  | { kind: "help" }
  | { kind: "close" };

export function shortcutFor(key: string): ShortcutAction | null {
  if (/^[1-5]$/.test(key)) return { kind: "tab", index: Number(key) - 1 };
  switch (key.toLowerCase()) {
    case "p":
      return { kind: "plan" };
    case "a":
      return { kind: "approve" };
    case "n":
      return { kind: "new" };
    case "r":
      return { kind: "refresh" };
    case "?":
      return { kind: "help" };
    case "escape":
      return { kind: "close" };
    default:
      return null;
  }
}

export function isTypingTarget(t: EventTarget | null): boolean {
  if (!t || typeof (t as HTMLElement).tagName !== "string") return false;
  const el = t as HTMLElement;
  return el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName);
}

export type FleetSection = "drivers" | "vehicles" | "partners" | "data";

export const FLEET_SECTIONS: { id: FleetSection; label: string }[] = [
  { id: "drivers", label: "Drivers" },
  { id: "vehicles", label: "Vehicles" },
  { id: "partners", label: "Partners" },
  { id: "data", label: "Data" },
];
