/**
 * Capacity Guide conversation FSM (L2) — structured session state.
 * Client persists in sessionStorage; server injects into the system prompt.
 */

export const GUIDE_STAGES = ["discover", "qualify", "capture", "book", "handoff"] as const;

export type GuideStage = (typeof GUIDE_STAGES)[number];

export type GuideSessionState = {
  stage: GuideStage;
  leadId?: string;
  email?: string;
  phone?: string;
  name?: string;
  businessName?: string;
  intent?: string;
  industry?: string;
  volumeHint?: string;
  corridor?: string;
  timeline?: string;
  meetingType?: "call" | "meeting";
  openQuestions?: string[];
};

export const DEFAULT_GUIDE_STATE: GuideSessionState = {
  stage: "discover",
};

export function isGuideStage(value: unknown): value is GuideStage {
  return typeof value === "string" && (GUIDE_STAGES as readonly string[]).includes(value);
}

export function normalizeGuideState(raw: unknown): GuideSessionState {
  if (!raw || typeof raw !== "object") return { ...DEFAULT_GUIDE_STATE };
  const o = raw as Record<string, unknown>;
  const stage = isGuideStage(o.stage) ? o.stage : "discover";
  const str = (k: string) =>
    typeof o[k] === "string" && o[k].trim() ? String(o[k]).trim().slice(0, 255) : undefined;
  const meetingType =
    o.meetingType === "call" || o.meetingType === "meeting" ? o.meetingType : undefined;
  const openQuestions = Array.isArray(o.openQuestions)
    ? o.openQuestions
        .filter((x): x is string => typeof x === "string")
        .map((x) => x.slice(0, 200))
        .slice(0, 8)
    : undefined;
  return {
    stage,
    leadId: str("leadId"),
    email: str("email"),
    phone: str("phone"),
    name: str("name"),
    businessName: str("businessName"),
    intent: str("intent"),
    industry: str("industry"),
    volumeHint: str("volumeHint"),
    corridor: str("corridor"),
    timeline: str("timeline"),
    meetingType,
    openQuestions,
  };
}

export function mergeGuideState(
  current: GuideSessionState,
  patch: Partial<GuideSessionState>
): GuideSessionState {
  const next = { ...current, ...normalizeGuideState({ ...current, ...patch }) };
  // Keep explicit stage from patch when valid
  if (patch.stage && isGuideStage(patch.stage)) next.stage = patch.stage;
  return next;
}

export function formatGuideStateForPrompt(state: GuideSessionState): string {
  const lines = [
    `Current stage: ${state.stage}`,
    state.leadId ? `lead_id: ${state.leadId}` : null,
    state.email ? `email: ${state.email}` : null,
    state.phone ? `phone: ${state.phone}` : null,
    state.name ? `name: ${state.name}` : null,
    state.businessName ? `business: ${state.businessName}` : null,
    state.intent ? `intent: ${state.intent}` : null,
    state.industry ? `industry: ${state.industry}` : null,
    state.volumeHint ? `volume: ${state.volumeHint}` : null,
    state.corridor ? `corridor: ${state.corridor}` : null,
    state.timeline ? `timeline: ${state.timeline}` : null,
    state.meetingType ? `meeting_type: ${state.meetingType}` : null,
    state.openQuestions?.length ? `open_questions: ${state.openQuestions.join("; ")}` : null,
  ].filter(Boolean);
  return lines.join("\n");
}

export function stagePolicy(stage: GuideStage): string {
  switch (stage) {
    case "discover":
      return "Discover needs. Use lookup_knowledge for factual answers. Softly nudge toward quote/call when intent appears.";
    case "qualify":
      return "Qualify: industry, volume/corridor, timeline. Call qualify_lead when you have useful fields. Then move toward capture.";
    case "capture":
      return "Capture work email then mobile. Call capture_contact. Do not book without phone.";
    case "book":
      return "Offer slots, confirm verbally, then book_appointment (requires visitor confirmation / approval).";
    case "handoff":
      return "Confirm next steps, share /business or /contact?intent=quote, save_transcript_excerpt.";
    default:
      return "";
  }
}
