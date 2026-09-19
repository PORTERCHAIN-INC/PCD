import { QUOTE_INTENT_KEY } from "@/lib/visitor-tracking";

export type InquiryPayload = {
  email: string;
  name?: string;
  phone?: string;
  business_name?: string;
  message?: string;
  intent?: string;
  inquiry_type?: string;
  source?: string;
  source_page?: string;
  form?: string;
  utm_source?: string;
  utm_campaign?: string;
  utm_medium?: string;
  referred_by_merchant_id?: string;
};

function referralFromUrl(): string | undefined {
  if (typeof window === "undefined") return undefined;
  try {
    const ref = new URLSearchParams(window.location.search).get("ref");
    return ref?.trim() || undefined;
  } catch {
    return undefined;
  }
}

function referralFromSession(): string | undefined {
  if (typeof window === "undefined") return undefined;
  try {
    const raw = sessionStorage.getItem(QUOTE_INTENT_KEY);
    if (!raw) return undefined;
    const parsed = JSON.parse(raw) as { ref?: string };
    return typeof parsed.ref === "string" ? parsed.ref.trim() || undefined : undefined;
  } catch {
    return undefined;
  }
}

export async function submitInquiry(payload: InquiryPayload): Promise<{ id: string }> {
  const referred_by_merchant_id =
    payload.referred_by_merchant_id?.trim() || referralFromUrl() || referralFromSession();
  const res = await fetch("/api/inquiries", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...payload,
      ...(referred_by_merchant_id ? { referred_by_merchant_id } : {}),
    }),
  });

  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { error?: string };
    throw new Error(body.error ?? "submission_failed");
  }

  return res.json() as Promise<{ id: string }>;
}
