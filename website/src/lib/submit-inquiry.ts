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
};

export async function submitInquiry(payload: InquiryPayload): Promise<{ id: string }> {
  const res = await fetch("/api/inquiries", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { error?: string };
    throw new Error(body.error ?? "submission_failed");
  }

  return res.json() as Promise<{ id: string }>;
}
