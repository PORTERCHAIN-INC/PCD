import { groq } from "@ai-sdk/groq";
import {
  convertToModelMessages,
  jsonSchema,
  stepCountIs,
  streamText,
  tool,
  type UIMessage,
} from "ai";
import { buildCapacityGuideSystem } from "@/lib/home/capacity-guide-system";
import { retrieveGuideKnowledge } from "@/lib/home/guide-knowledge";
import {
  formatGuideStateForPrompt,
  mergeGuideState,
  normalizeGuideState,
  stagePolicy,
  type GuideSessionState,
} from "@/lib/home/guide-session";
import {
  bookGuideAppointment,
  listGuideSlots,
  saveGuideTranscript,
  upsertGuideLead,
} from "@/lib/home/guide-api";

export const runtime = "nodejs";
export const maxDuration = 60;

const MODEL = process.env.GROQ_MODEL?.trim() || "llama-3.3-70b-versatile";
/** Optional cheaper model for light routing hints (L3). */
const ROUTER_MODEL = process.env.GROQ_ROUTER_MODEL?.trim() || "llama-3.1-8b-instant";

async function routeIntentHint(lastUserText: string): Promise<string | null> {
  if (!lastUserText.trim() || !process.env.GROQ_API_KEY?.trim()) return null;
  try {
    const { generateText } = await import("ai");
    const result = await generateText({
      model: groq(ROUTER_MODEL),
      temperature: 0,
      maxOutputTokens: 40,
      prompt: `Classify this Porterchain website chat message into one label only: discover, qualify, capture, book, track, quote, other.
Message: ${lastUserText.slice(0, 400)}
Label:`,
    });
    const label = result.text
      .trim()
      .toLowerCase()
      .split(/\s+/)[0]
      ?.replace(/[^a-z]/g, "");
    if (!label) return null;
    return label;
  } catch {
    return null;
  }
}

function lastUserText(messages: UIMessage[]): string {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const m = messages[i];
    if (m.role !== "user") continue;
    return m.parts
      .filter((p): p is { type: "text"; text: string } => p.type === "text")
      .map((p) => p.text)
      .join(" ");
  }
  return "";
}

export async function POST(req: Request) {
  if (!process.env.GROQ_API_KEY?.trim()) {
    return Response.json(
      { error: "GROQ_API_KEY is not configured on the website server." },
      { status: 503 }
    );
  }

  const body = await req.json();
  const messages = (body.messages ?? []) as UIMessage[];
  const sessionId =
    typeof body.sessionId === "string" && body.sessionId.trim()
      ? body.sessionId.trim().slice(0, 128)
      : undefined;
  let guideState = normalizeGuideState(body.guideState);

  const userText = lastUserText(messages);
  const intentHint = await routeIntentHint(userText);
  if (intentHint === "track" && guideState.stage === "discover") {
    // soft hint only in prompt; do not force stage
  } else if (
    intentHint &&
    ["qualify", "capture", "book"].includes(intentHint) &&
    guideState.stage === "discover"
  ) {
    guideState = mergeGuideState(guideState, {
      stage: intentHint as GuideSessionState["stage"],
    });
  }

  const system = buildCapacityGuideSystem(
    formatGuideStateForPrompt(guideState),
    `${stagePolicy(guideState.stage)}${intentHint ? ` Router hint this turn: ${intentHint}.` : ""}`
  );

  const result = streamText({
    model: groq(MODEL),
    system,
    messages: await convertToModelMessages(messages),
    temperature: 0.4,
    maxOutputTokens: 1000,
    stopWhen: stepCountIs(8),
    tools: {
      lookup_knowledge: tool({
        description:
          "Retrieve grounded Porterchain capacity facts (pricing factors, vehicles, coverage, industries, FAQ). Call before factual answers.",
        inputSchema: jsonSchema<{ query: string }>({
          type: "object",
          properties: {
            query: { type: "string", description: "Search query from the user need" },
          },
          required: ["query"],
        }),
        execute: async (input) => {
          const hits = retrieveGuideKnowledge(input.query, { limit: 5 });
          return {
            ok: true as const,
            count: hits.length,
            chunks: hits.map((h) => ({
              id: h.id,
              title: h.title,
              body: h.body.slice(0, 700),
              source: h.source,
              score: Number(h.score.toFixed(2)),
            })),
            message:
              hits.length === 0
                ? "No strong matches — avoid inventing facts; offer a written quote."
                : "Ground your answer in these snippets. Do not invent prices.",
          };
        },
      }),
      get_tracking_help: tool({
        description:
          "Help a visitor track a shipment. Returns /track links. Never invent live status.",
        inputSchema: jsonSchema<{ tracking_number?: string }>({
          type: "object",
          properties: {
            tracking_number: {
              type: "string",
              description: "Optional tracking / order number if the user shared one",
            },
          },
        }),
        execute: async (input) => {
          const raw = (input.tracking_number || "").trim();
          const encoded = raw ? encodeURIComponent(raw) : "";
          return {
            ok: true as const,
            hub_path: "/track",
            detail_path: encoded ? `/track/${encoded}` : null,
            message: encoded
              ? `Direct them to /track/${encoded} to view live status. Do not invent ETA or POD.`
              : "Ask for their tracking number or shareable link, then send them to /track.",
          };
        },
      }),
      update_guide_state: tool({
        description:
          "Update conversation stage and known fields (FSM). Call when stage or contact/qualification fields change.",
        inputSchema: jsonSchema<{
          stage?: "discover" | "qualify" | "capture" | "book" | "handoff";
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
        }>({
          type: "object",
          properties: {
            stage: {
              type: "string",
              enum: ["discover", "qualify", "capture", "book", "handoff"],
            },
            leadId: { type: "string" },
            email: { type: "string" },
            phone: { type: "string" },
            name: { type: "string" },
            businessName: { type: "string" },
            intent: { type: "string" },
            industry: { type: "string" },
            volumeHint: { type: "string" },
            corridor: { type: "string" },
            timeline: { type: "string" },
            meetingType: { type: "string", enum: ["call", "meeting"] },
            openQuestions: { type: "array", items: { type: "string" } },
          },
        }),
        execute: async (input) => {
          guideState = mergeGuideState(guideState, input);
          return {
            ok: true as const,
            state: guideState,
            message: `Stage is now ${guideState.stage}.`,
          };
        },
      }),
      qualify_lead: tool({
        description:
          "Save qualification fields (industry, volume, corridor, timeline) onto the CRM lead. Creates/updates lead if email known.",
        inputSchema: jsonSchema<{
          email?: string;
          name?: string;
          phone?: string;
          business_name?: string;
          industry?: string;
          volume_hint?: string;
          corridor?: string;
          timeline?: string;
          intent?: string;
        }>({
          type: "object",
          properties: {
            email: { type: "string" },
            name: { type: "string" },
            phone: { type: "string" },
            business_name: { type: "string" },
            industry: { type: "string" },
            volume_hint: { type: "string" },
            corridor: { type: "string" },
            timeline: { type: "string" },
            intent: { type: "string" },
          },
        }),
        execute: async (input) => {
          const email = (input.email || guideState.email || "").trim();
          if (!email) {
            return {
              ok: false as const,
              error: "email_required",
              hint: "Ask for work email, then call qualify_lead again.",
            };
          }
          const notes = [
            input.industry && `Industry: ${input.industry}`,
            input.volume_hint && `Volume: ${input.volume_hint}`,
            input.corridor && `Corridor: ${input.corridor}`,
            input.timeline && `Timeline: ${input.timeline}`,
          ]
            .filter(Boolean)
            .join("\n");
          const res = await upsertGuideLead({
            email,
            name: input.name || guideState.name,
            phone: input.phone || guideState.phone,
            business_name: input.business_name || guideState.businessName,
            intent: input.intent || guideState.intent || "quote",
            session_id: sessionId,
            source_page: "/",
            notes: notes || undefined,
          });
          if (!res.ok) return { ok: false as const, error: res.error };
          guideState = mergeGuideState(guideState, {
            stage: "qualify",
            leadId: res.data.id,
            email: res.data.email,
            phone: res.data.phone || guideState.phone,
            industry: input.industry,
            volumeHint: input.volume_hint,
            corridor: input.corridor,
            timeline: input.timeline,
            intent: input.intent || guideState.intent,
          });
          return {
            ok: true as const,
            lead_id: res.data.id,
            state: guideState,
            message: "Qualification saved on the lead.",
          };
        },
      }),
      capture_contact: tool({
        description:
          "Save or update the visitor as a CRM lead. Call when you have a valid work email; include phone when known.",
        inputSchema: jsonSchema<{
          email: string;
          name?: string;
          phone?: string;
          business_name?: string;
          intent?: string;
          notes?: string;
        }>({
          type: "object",
          properties: {
            email: { type: "string", description: "Visitor email" },
            name: { type: "string" },
            phone: { type: "string" },
            business_name: { type: "string" },
            intent: {
              type: "string",
              description: "quote | call | meeting | overflow | general",
            },
            notes: { type: "string" },
          },
          required: ["email"],
        }),
        execute: async (input) => {
          const res = await upsertGuideLead({
            email: input.email,
            name: input.name,
            phone: input.phone,
            business_name: input.business_name,
            intent: input.intent,
            session_id: sessionId,
            source_page: "/",
            notes: input.notes,
          });
          if (!res.ok) return { ok: false as const, error: res.error };
          guideState = mergeGuideState(guideState, {
            stage: input.phone || res.data.phone ? "capture" : "capture",
            leadId: res.data.id,
            email: res.data.email,
            phone: res.data.phone || input.phone,
            name: input.name,
            businessName: input.business_name,
            intent: input.intent,
          });
          return {
            ok: true as const,
            lead_id: res.data.id,
            created: res.data.created,
            email: res.data.email,
            phone: res.data.phone,
            state: guideState,
            message: res.data.created
              ? "Contact saved. Ask for mobile phone if missing before booking."
              : "Contact updated.",
          };
        },
      }),
      list_meeting_slots: tool({
        description:
          "List the next available call or in-person meeting slots (America/Toronto business hours).",
        inputSchema: jsonSchema<{ meeting_type?: "call" | "meeting" }>({
          type: "object",
          properties: {
            meeting_type: {
              type: "string",
              enum: ["call", "meeting"],
              description: "call = phone; meeting = in-person",
            },
          },
        }),
        execute: async (input) => {
          const meetingType = input.meeting_type === "meeting" ? "meeting" : "call";
          const res = await listGuideSlots(meetingType);
          if (!res.ok) return { ok: false as const, error: res.error };
          guideState = mergeGuideState(guideState, {
            stage: "book",
            meetingType,
          });
          return {
            ok: true as const,
            timezone: res.data.timezone,
            meeting_type: res.data.meeting_type,
            slots: res.data.slots.slice(0, 8).map((s) => ({
              start: s.start,
              label: s.label,
              meeting_type: s.meeting_type,
            })),
            state: guideState,
            message: "Offer 2–4 slots in plain language and wait for confirmation.",
          };
        },
      }),
      book_appointment: tool({
        description:
          "Book a confirmed call or meeting after the visitor explicitly confirms a slot. Requires lead_id and phone on the lead.",
        needsApproval: true,
        inputSchema: jsonSchema<{
          lead_id: string;
          meeting_type: "call" | "meeting";
          start: string;
          notes?: string;
        }>({
          type: "object",
          properties: {
            lead_id: { type: "string" },
            meeting_type: { type: "string", enum: ["call", "meeting"] },
            start: {
              type: "string",
              description: "ISO datetime from list_meeting_slots",
            },
            notes: { type: "string" },
          },
          required: ["lead_id", "meeting_type", "start"],
        }),
        execute: async (input) => {
          const res = await bookGuideAppointment({
            lead_id: input.lead_id,
            meeting_type: input.meeting_type === "meeting" ? "meeting" : "call",
            start: input.start,
            session_id: sessionId,
            notes: input.notes,
          });
          if (!res.ok) {
            return {
              ok: false as const,
              error: res.error,
              hint:
                res.error === "phone_required"
                  ? "Ask for a mobile number, call capture_contact with phone, then retry book."
                  : undefined,
            };
          }
          guideState = mergeGuideState(guideState, {
            stage: "handoff",
            leadId: res.data.lead_id,
            meetingType: res.data.meeting_type === "meeting" ? "meeting" : "call",
          });
          return {
            ok: true as const,
            task_id: res.data.task_id,
            title: res.data.title,
            due_at: res.data.due_at,
            meeting_type: res.data.meeting_type,
            state: guideState,
            message: "Appointment booked. Confirm the time back to the visitor.",
          };
        },
      }),
      save_transcript_excerpt: tool({
        description:
          "Persist a short factual summary of the conversation on the CRM lead timeline.",
        inputSchema: jsonSchema<{
          lead_id: string;
          summary: string;
        }>({
          type: "object",
          properties: {
            lead_id: { type: "string" },
            summary: { type: "string", description: "1–6 sentence factual summary" },
          },
          required: ["lead_id", "summary"],
        }),
        execute: async (input) => {
          const res = await saveGuideTranscript({
            lead_id: input.lead_id,
            session_id: sessionId,
            summary: input.summary,
            turns: [{ role: "assistant", content: input.summary }],
          });
          if (!res.ok) return { ok: false as const, error: res.error };
          return {
            ok: true as const,
            lead_id: res.data.lead_id,
            turn_count: res.data.turn_count,
          };
        },
      }),
    },
  });

  return result.toUIMessageStreamResponse({
    messageMetadata: () => ({ guideState }),
  });
}
