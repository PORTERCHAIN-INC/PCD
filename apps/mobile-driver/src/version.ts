import { appVersion } from "./config";

/** Compare dotted versions: returns negative if a < b, 0 if equal, positive if a > b. */
export function compareVersions(a: string, b: string): number {
  const pa = a
    .replace(/^v/i, "")
    .split(".")
    .map((p) => parseInt(p, 10) || 0);
  const pb = b
    .replace(/^v/i, "")
    .split(".")
    .map((p) => parseInt(p, 10) || 0);
  const n = Math.max(pa.length, pb.length);
  for (let i = 0; i < n; i += 1) {
    const d = (pa[i] ?? 0) - (pb[i] ?? 0);
    if (d !== 0) return d;
  }
  return 0;
}

export function isBelowMinVersion(current: string, minVersion: string): boolean {
  return compareVersions(current, minVersion) < 0;
}

export function currentAppVersion(): string {
  return appVersion;
}
