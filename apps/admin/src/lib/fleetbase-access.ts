/** Roles allowed to open Fleetbase console via PorterChain SSO (mirrors API). */
export const FLEETBASE_CONSOLE_ROLES = new Set([
  "super_admin",
  "admin",
  "dispatcher",
  "fleet_manager",
  "support",
  "support_lead",
]);

export function canOpenFleetbaseConsole(role: string | null | undefined): boolean {
  if (!role) return false;
  return FLEETBASE_CONSOLE_ROLES.has(role.trim().toLowerCase());
}

export function fleetbaseSsoErrorMessage(err: unknown): string {
  const detail = err instanceof Error ? err.message : String(err ?? "");
  if (detail.includes("fleetbase_console_forbidden")) {
    return "Your role cannot open the execution console.";
  }
  if (detail.includes("fleetbase_sso_disabled")) {
    return "Fleetbase SSO is disabled in this environment.";
  }
  if (detail.includes("fleetbase_console_unreachable")) {
    return "Fleetbase console is not running — start the Fleetbase stack (port 4200) and try again.";
  }
  if (detail.includes("porterchain_api_timeout") || detail.includes("Failed to fetch")) {
    return "PorterChain API unreachable — start the API and try again.";
  }
  if (detail.includes("missing_bearer") || detail.includes("staff_session")) {
    return "Sign in again, then retry.";
  }
  return detail || "Could not open Fleetbase console.";
}
