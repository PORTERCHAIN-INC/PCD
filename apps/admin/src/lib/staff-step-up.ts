/**
 * Staff step-up: sensitive mutations need a Keycloak login (password + TOTP) in the last
 * 15 minutes. On `staff_step_up_required` we send the browser through `prompt=login` and
 * bring it back to the same page; the user repeats the action afterwards.
 */

const MARK = "pc_admin_step_up_at";

export function isStaffStepUpRequired(err: unknown): boolean {
  return err instanceof Error && err.message.includes("staff_step_up_required");
}

export function stepUpUrl(returnTo: string): string {
  return `/auth/login?prompt=login&return_to=${encodeURIComponent(returnTo)}`;
}

/** Redirects to Keycloak re-authentication. Throws if a re-login just happened (avoid loops). */
export function refreshStaffStepUp(): Promise<never> {
  const last = Number(window.sessionStorage.getItem(MARK) || 0);
  if (Date.now() - last < 60_000) {
    return Promise.reject(new Error("Re-authentication did not complete. Sign in again."));
  }
  window.sessionStorage.setItem(MARK, String(Date.now()));
  window.location.assign(stepUpUrl(`${window.location.pathname}${window.location.search}`));
  return new Promise<never>(() => {});
}

/** Run `fn`; on step-up required, re-authenticate with Keycloak. */
export async function withStaffStepUp<T>(_token: string, fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (err) {
    if (!isStaffStepUpRequired(err)) throw err;
    return refreshStaffStepUp();
  }
}
