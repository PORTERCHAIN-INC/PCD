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

/** After this many user turns, contact ask is mandatory every reply until complete. */
export const MAX_QUESTIONS_BEFORE_CONTACT = 1;

export function countUserTurns(messages: ReadonlyArray<{ role: string }>): number {
  return messages.reduce((n, m) => (m.role === "user" ? n + 1 : n), 0);
}

export function hasEmailAndPhone(state: GuideSessionState): boolean {
  return Boolean(state.email?.trim() && state.phone?.trim());
}

/**
 * Injected each turn so the model prioritizes email + phone in every conversation.
 * userTurnCount = number of user messages already in the thread (including this turn).
 */
export function contactCapturePolicy(state: GuideSessionState, userTurnCount: number): string {
  if (hasEmailAndPhone(state)) {
    return "Contact complete (email + phone on file). Do not re-ask; answer fully, then book or handoff.";
  }

  const missing: string[] = [];
  if (!state.email?.trim()) missing.push("work email");
  if (!state.phone?.trim()) missing.push("mobile phone");
  const missingLabel = missing.join(" and ");

  if (userTurnCount >= MAX_QUESTIONS_BEFORE_CONTACT) {
    return `BUSINESS-CRITICAL: Contact incomplete — still need ${missingLabel}. Answer the visitor's question helpfully (use lookup_knowledge when factual), THEN in the SAME reply ask clearly for ${missingLabel}. Do not end the message without that ask. Call capture_contact as soon as they provide either field; keep asking until BOTH are saved.`;
  }

  return `Contact incomplete (need ${missingLabel}). On your first reply: answer briefly, then ask for work email AND mobile phone together. Capture is mandatory in every conversation.`;
}

export function stagePolicy(stage: GuideStage): string {
  switch (stage) {
    case "discover":
      return "Answer maximally with lookup_knowledge. In the same reply ask for work email + mobile. Do not chat indefinitely without contact.";
    case "qualify":
      return "Qualify lightly while still chasing missing email/phone. Call qualify_lead when useful. Never skip the contact ask.";
    case "capture":
      return "Priority: capture work email AND mobile via capture_contact. Answer questions, but every reply must push for missing contact fields.";
    case "book":
      return "Offer slots only after phone is on file (or ask for phone first). Confirm verbally, then book_appointment.";
    case "handoff":
      return "If contact still incomplete, ask once more for email/phone. Then confirm next steps (/business or /contact?intent=quote) and save_transcript_excerpt.";
    default:
      return "";
  }
}
