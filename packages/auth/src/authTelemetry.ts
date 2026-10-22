/**
 * Client → server signal when sign-in / sign-up fails in a way the user cannot see
 * in our logs (Clerk never loaded, bot check stalled, offline, Clerk form error).
 * The app's `/api/auth-telemetry` route writes one structured log line per event.
 * No email, password or code is ever sent: only the kind, the page and Clerk's
 * short error code/message.
 */

export const AUTH_EVENT_KINDS = [
  "clerk_load_timeout",
  "bot_check_stall",
  "offline",
  "clerk_form_error",
] as const;
export type AuthEventKind = (typeof AUTH_EVENT_KINDS)[number];

export const AUTH_TELEMETRY_PATH = "/api/auth-telemetry";

export type AuthEventPayload = { kind: AuthEventKind; path: string; detail?: string };

const EMAILISH = /[^\s@]+@[^\s@]+/g;

/** Strip anything that looks like an email and cap the length. */
export function scrubDetail(detail: string | undefined | null): string | undefined {
  if (!detail) return undefined;
  const clean = detail.replace(EMAILISH, "[email]").replace(/\s+/g, " ").trim();
  return clean ? clean.slice(0, 160) : undefined;
}

export function isAuthEventKind(value: unknown): value is AuthEventKind {
  return typeof value === "string" && (AUTH_EVENT_KINDS as readonly string[]).includes(value);
}

/** Validates an untrusted body; returns null when it is not an auth event. */
export function parseAuthEvent(body: unknown): AuthEventPayload | null {
  if (!body || typeof body !== "object") return null;
  const b = body as Record<string, unknown>;
  if (!isAuthEventKind(b.kind)) return null;
  const path = typeof b.path === "string" ? b.path.slice(0, 120) : "";
  const detail = scrubDetail(typeof b.detail === "string" ? b.detail : undefined);
  return detail ? { kind: b.kind, path, detail } : { kind: b.kind, path };
}

const sent = new Set<string>();

/** Fire-and-forget; each kind+detail is reported once per page load. */
export function reportAuthEvent(kind: AuthEventKind, detail?: string): void {
  if (typeof window === "undefined") return;
  const payload: AuthEventPayload = {
    kind,
    path: window.location.pathname,
    detail: scrubDetail(detail),
  };
  const key = `${kind}|${payload.detail ?? ""}`;
  if (sent.has(key)) return;
  sent.add(key);
  const body = JSON.stringify(payload);
  try {
    if (navigator.sendBeacon?.(AUTH_TELEMETRY_PATH, new Blob([body], { type: "application/json" })))
      return;
  } catch {
    /* fall through */
  }
  void fetch(AUTH_TELEMETRY_PATH, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    keepalive: true,
  }).catch(() => undefined);
}

/** Shared server handler body: returns the log line to write, or null to ignore. */
export function authTelemetryLogLine(
  body: unknown,
  app: string,
  userAgent: string | null
): string | null {
  const event = parseAuthEvent(body);
  if (!event) return null;
  return JSON.stringify({
    msg: "auth_client_failure",
    app,
    kind: event.kind,
    path: event.path,
    detail: event.detail ?? null,
    ua: (userAgent ?? "").slice(0, 160),
  });
}
