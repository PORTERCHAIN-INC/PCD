export const MERCHANT_ID_COOKIE = "pc_merchant_id";

export function writeMerchantIdCookie(merchantId: string) {
  if (typeof document === "undefined" || !merchantId) return;
  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${MERCHANT_ID_COOKIE}=${encodeURIComponent(merchantId)}; Path=/; Max-Age=31536000; SameSite=Lax${secure}`;
}
