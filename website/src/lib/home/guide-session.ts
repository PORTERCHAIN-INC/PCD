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
