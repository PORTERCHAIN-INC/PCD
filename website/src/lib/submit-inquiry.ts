import { readStoredConsent } from "@/lib/marketing/consent";
import { getOrCreateVisitorId, QUOTE_INTENT_KEY } from "@/lib/visitor-tracking";

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
  visitor_id?: string;
  consent?: {
    marketing?: boolean;
    sms?: boolean;
    whatsapp?: boolean;
    analytics?: boolean;
    experience?: boolean;
    source?: string;
    text_version?: string;
    captured_at?: string;
    actor?: string;
  };
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

function consentSnapshot(payload: InquiryPayload): InquiryPayload["consent"] | undefined {
  if (payload.consent) return payload.consent;
  const stored = readStoredConsent();
  if (!stored) {
    // Newsletter / explicit marketing forms default to marketing opt-in.
    if (payload.form === "newsletter" || payload.inquiry_type === "newsletter") {
      return { marketing: true };
    }
    return undefined;
  }
  return {
    marketing: stored.marketing,
    analytics: stored.analytics,
    experience: stored.experience,
    source: "website_cmp",
    text_version: "casl_v1_marketing",
    captured_at: new Date().toISOString(),
    actor: "lead",
  };
}

export async function submitInquiry(payload: InquiryPayload): Promise<{ id: string }> {
  const referred_by_merchant_id =
    payload.referred_by_merchant_id?.trim() || referralFromUrl() || referralFromSession();
  const visitor_id =
    payload.visitor_id?.trim() ||
    (typeof window !== "undefined" ? getOrCreateVisitorId() : "") ||
    undefined;
  const consent = consentSnapshot(payload);

  const res = await fetch("/api/inquiries", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...payload,
      ...(referred_by_merchant_id ? { referred_by_merchant_id } : {}),
      ...(visitor_id ? { visitor_id } : {}),
      ...(consent ? { consent } : {}),
    }),
  });

  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { error?: string };
    throw new Error(body.error ?? "submission_failed");
  }

  return res.json() as Promise<{ id: string }>;
}
