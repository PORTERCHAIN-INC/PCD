/** Audited impersonation bearer helpers (browser). */

export const PC_IMP_STORAGE_KEY = "pc_imp_bearer";
export const PC_IMP_COOKIE = "pc_imp_bearer";

export function readImpersonationBearer(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const v = window.sessionStorage.getItem(PC_IMP_STORAGE_KEY);
    return v && v.startsWith("pc_imp_") ? v : null;
  } catch {
    return null;
  }
}

export function storeImpersonationBearer(token: string): void {
  if (typeof window === "undefined") return;
  if (!token.startsWith("pc_imp_")) return;
  window.sessionStorage.setItem(PC_IMP_STORAGE_KEY, token);
}

export function clearImpersonationBearer(): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(PC_IMP_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
