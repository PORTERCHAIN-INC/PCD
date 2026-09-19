/**
 * Prompt for a passkey and refresh the staff step-up window.
 * Call when a mutation returns `staff_step_up_required`.
 */

import { adminFetch } from "@/lib/api";
import { STAFF_COOKIE_TOKEN } from "@/lib/staff-session";
import { credentialToJson, getPasskey, passkeysSupported } from "@/lib/staff-webauthn";

export function isStaffStepUpRequired(err: unknown): boolean {
  return err instanceof Error && err.message.includes("staff_step_up_required");
}

export async function refreshStaffStepUp(token: string = STAFF_COOKIE_TOKEN): Promise<void> {
  if (!passkeysSupported()) {
    throw new Error("Passkey required — add one under Account → Security, then retry.");
  }
  const options = await adminFetch<Record<string, unknown>>(
    "/v1/auth/staff/step-up/options",
    token,
    { method: "POST", body: "{}" }
  );
  const challengeId = String(options.challenge_id || "");
  if (!challengeId) {
    throw new Error("step_up_options_failed");
  }
  const cred = await getPasskey(options);
  await adminFetch("/v1/auth/staff/step-up", token, {
    method: "POST",
    body: JSON.stringify({
      challenge_id: challengeId,
      passkey_assertion: { credential: credentialToJson(cred) },
    }),
  });
}

/** Run `fn`; on step-up required, confirm passkey once and retry. */
export async function withStaffStepUp<T>(token: string, fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (err) {
    if (!isStaffStepUpRequired(err)) throw err;
    await refreshStaffStepUp(token);
    return fn();
  }
}
