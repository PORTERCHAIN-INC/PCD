/**
 * Server-only helpers for Capacity Guide → Porterchain public guide API.
 */

import { getPorterchainApiBase } from "@/lib/api-base";

function ingestHeaders(): HeadersInit {
  const apiKey = (process.env.PUBLIC_INGEST_API_KEY ?? "").trim();
  return {
    "Content-Type": "application/json",
    ...(apiKey ? { "X-Ingest-Key": apiKey } : {}),
  };
}

async function guideFetch<T>(
  path: string,
  init?: RequestInit
): Promise<{ ok: true; data: T } | { ok: false; error: string; status: number }> {
  try {
    const res = await fetch(`${getPorterchainApiBase()}${path}`, {
      ...init,
      headers: {
        ...ingestHeaders(),
        ...(init?.headers ?? {}),
      },
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail =
        typeof body.detail === "string"
          ? body.detail
          : typeof body.error === "string"
            ? body.error
            : "guide_request_failed";
      return { ok: false, error: detail, status: res.status };
    }
    return { ok: true, data: body as T };
  } catch {
    return { ok: false, error: "guide_unreachable", status: 503 };
  }
}

export type GuideLeadResult = {
  id: string;
  created: boolean;
  status: string;
  email: string;
  phone: string | null;
};

export type GuideSlot = {
  start: string;
  end: string;
  label: string;
  meeting_type: string;
};

export async function upsertGuideLead(payload: {
  email: string;
  name?: string;
  phone?: string;
  business_name?: string;
  intent?: string;
  session_id?: string;
  visitor_id?: string;
  source_page?: string;
  notes?: string;
  guide_stage?: string;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
}): Promise<{ ok: true; data: GuideLeadResult } | { ok: false; error: string }> {
  const result = await guideFetch<GuideLeadResult>("/v1/public/guide/leads", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!result.ok) return { ok: false, error: result.error };
  return result;
}

export async function saveGuideTranscript(payload: {
  lead_id: string;
  session_id?: string;
  turns?: Array<{ role: string; content: string }>;
  summary?: string;
}): Promise<
  { ok: true; data: { lead_id: string; turn_count: number } } | { ok: false; error: string }
> {
  const result = await guideFetch<{ lead_id: string; turn_count: number }>(
    "/v1/public/guide/transcript",
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
  if (!result.ok) return { ok: false, error: result.error };
  return result;
}

export async function listGuideSlots(
  meetingType: "call" | "meeting" = "call"
): Promise<
  | { ok: true; data: { timezone: string; meeting_type: string; slots: GuideSlot[] } }
  | { ok: false; error: string }
> {
  const result = await guideFetch<{
    timezone: string;
    meeting_type: string;
    slots: GuideSlot[];
  }>(`/v1/public/guide/slots?meeting_type=${encodeURIComponent(meetingType)}`);
  if (!result.ok) return { ok: false, error: result.error };
  return result;
}

export async function bookGuideAppointment(payload: {
  lead_id: string;
  meeting_type: "call" | "meeting";
  start: string;
  session_id?: string;
  notes?: string;
}): Promise<
  | {
      ok: true;
      data: {
        task_id: string;
        lead_id: string;
        meeting_type: string;
        due_at: string;
        title: string;
      };
    }
  | { ok: false; error: string }
> {
  const result = await guideFetch<{
    task_id: string;
    lead_id: string;
    meeting_type: string;
    due_at: string;
    title: string;
  }>("/v1/public/guide/appointments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!result.ok) return { ok: false, error: result.error };
  return result;
}
