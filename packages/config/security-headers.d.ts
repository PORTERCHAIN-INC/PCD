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
