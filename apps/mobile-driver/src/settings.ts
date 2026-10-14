/**
 * App settings: saved on the phone instantly (AsyncStorage; nothing sensitive), then synced to
 * the server (PUT /settings) so they follow the driver to a new phone. Server wins on first load
 * only for keys the phone has never changed.
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useSyncExternalStore } from "react";

export type NavApp = "auto" | "google" | "apple" | "waze";
export type AppSettings = {
  nav_app: NavApp;
  voice: boolean;
  drive_mode_auto: boolean;
  text_scale: number; // 0.9 | 1 | 1.15 | 1.3
  haptics: boolean;
  battery_saver_pct: number; // 0 = off
  notify_jobs: boolean;
  notify_messages: boolean;
  notify_route_changes: boolean;
  notify_documents: boolean;
  language: "en" | "fr";
};

export const DEFAULT_SETTINGS: AppSettings = {
  nav_app: "auto",
  voice: true,
  drive_mode_auto: false,
  text_scale: 1,
  haptics: true,
  battery_saver_pct: 20,
  notify_jobs: true,
  notify_messages: true,
  notify_route_changes: true,
  notify_documents: true,
  language: "en",
};

const KEY = "pcd.driver.settings.v1";
let state: AppSettings = DEFAULT_SETTINGS;
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((l) => l());

/** Pure: keep only known keys with valid values. */
export function sanitize(raw: unknown): Partial<AppSettings> {
  if (!raw || typeof raw !== "object") return {};
  const r = raw as Record<string, unknown>;
  const out: Partial<AppSettings> = {};
  if (["auto", "google", "apple", "waze"].includes(r.nav_app as string))
    out.nav_app = r.nav_app as NavApp;
  if (r.language === "en" || r.language === "fr") out.language = r.language;
  for (const k of [
    "voice",
    "drive_mode_auto",
    "haptics",
    "notify_jobs",
    "notify_messages",
    "notify_route_changes",
    "notify_documents",
  ] as const)
    if (typeof r[k] === "boolean") out[k] = r[k] as boolean;
  if (typeof r.text_scale === "number" && r.text_scale >= 0.85 && r.text_scale <= 1.6)
    out.text_scale = r.text_scale;
  if (
    typeof r.battery_saver_pct === "number" &&
    r.battery_saver_pct >= 0 &&
    r.battery_saver_pct <= 50
  )
    out.battery_saver_pct = Math.round(r.battery_saver_pct);
  return out;
}

/** Server payload: "auto" nav is local-only (server knows google/apple/waze). */
export function toServer(s: Partial<AppSettings>): Record<string, unknown> {
  const { nav_app, ...rest } = s;
  return nav_app && nav_app !== "auto" ? { ...rest, nav_app } : rest;
}

export function getSettings(): AppSettings {
  return state;
}

export async function loadSettings(): Promise<AppSettings> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    if (raw) state = { ...DEFAULT_SETTINGS, ...sanitize(JSON.parse(raw)) };
  } catch {
    /* defaults */
  }
  emit();
  return state;
}

export function setSettings(patch: Partial<AppSettings>): AppSettings {
  state = { ...state, ...sanitize(patch) };
  emit();
  void AsyncStorage.setItem(KEY, JSON.stringify(state)).catch(() => undefined);
  return state;
}

/** Apply the server copy without overwriting anything changed on this phone. */
export function mergeServer(server: unknown, localTouched: boolean): AppSettings {
  if (localTouched) return state;
  return setSettings(sanitize(server));
}

export async function resetSettings(): Promise<void> {
  state = DEFAULT_SETTINGS;
  emit();
  await AsyncStorage.removeItem(KEY).catch(() => undefined);
}

export function useSettings(): AppSettings {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    () => state,
    () => state
  );
}
