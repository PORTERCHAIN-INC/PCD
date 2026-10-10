export type HeaderEntry = { key: string; value: string };
export function baselineCsp(opts?: { frameAncestors?: string }): string;
export function baselineSecurityHeaders(opts?: {
  frameAncestors?: string;
  frameDeny?: boolean;
}): HeaderEntry[];
export function websiteCsp(opts?: {
  apiUrl?: string;
  extraConnect?: string[];
  dev?: boolean;
}): string;
export function portalCsp(opts: {
  app: "admin" | "merchant" | "customer" | "driver";
  apiUrl?: string;
  mapTileUrl?: string;
  valhallaUrl?: string;
  frameAncestors?: string;
  dev?: boolean;
}): string;
export function portalSecurityHeaders(
  app: "admin" | "merchant" | "customer" | "driver",
  opts?: { frameAncestors?: string }
): HeaderEntry[];
