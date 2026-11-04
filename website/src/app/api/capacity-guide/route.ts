/**
 * Capacity Guide chat — rule-based (doc 60 R2: no external AI vendors).
 * Streams a UI message (text + tool parts) the existing chat widget renders.
 */
import { createUIMessageStream, createUIMessageStreamResponse, type UIMessage } from "ai";
import { retrieveGuideKnowledge } from "@/lib/home/guide-knowledge";
import {
  bookGuideAppointment,
  listGuideSlots,
  saveGuideTranscript,
  upsertGuideLead,
} from "@/lib/home/guide-api";
import {
  classifyIntent,
  contactPrompt,
  extractEmail,
  extractPhone,
  extractTrackingNumber,
  FALLBACK_REPLY,
  meetingTypeFrom,
  parseSlotChoice,
  QUOTE_REPLY,
} from "@/lib/home/guide-rules";
import { mergeGuideState, normalizeGuideState } from "@/lib/home/guide-session";

export const maxDuration = 30;

type ToolEvent = { name: string; input: Record<string, unknown>; output: Record<string, unknown> };

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
  const body = await req.json().catch(() => ({}));
  const messages = (Array.isArray(body.messages) ? body.messages : []) as UIMessage[];
  const sessionId =
    typeof body.sessionId === "string" && body.sessionId.trim()
      ? body.sessionId.trim().slice(0, 128)
      : undefined;
  let state = normalizeGuideState(body.guideState);
  const text = lastUserText(messages).slice(0, 2000);
  const tools: ToolEvent[] = [];
  const reply: string[] = [];

  const email = extractEmail(text);
  const phone = extractPhone(text);
  if (email || phone) {
    const useEmail = email || state.email;
    if (useEmail) {
      const res = await upsertGuideLead({
        email: useEmail,
        phone: phone || state.phone,
        intent: state.intent || "quote",
        session_id: sessionId,
        visitor_id: sessionId,
        guide_stage: "capture",
        source_page: "/",
      });
      if (res.ok) {
        const savedPhone = res.data.phone || phone || state.phone;
        state = mergeGuideState(state, {
          stage: "capture",
          leadId: res.data.id,
          email: res.data.email,
          phone: savedPhone,
        });
        tools.push({
          name: "capture_contact",
          input: { email: useEmail, phone },
          output: {
            ok: true,
            lead_id: res.data.id,
            email: res.data.email,
            phone: savedPhone ?? null,
            contact_complete: Boolean(res.data.email && savedPhone),
            state,
          },
        });
        reply.push("Thanks — your details are saved and the team will follow up.");
      } else {
        reply.push("Sorry, I couldn't save your details just now. Please try again in a moment.");
      }
    } else {
      state = mergeGuideState(state, { phone });
    }
  }

  const choice = parseSlotChoice(text);
  const intent = classifyIntent(text);
  if (choice !== undefined && state.stage === "book" && state.leadId) {
    const meetingType = state.meetingType ?? "call";
    const slots = await listGuideSlots(meetingType);
    const slot = slots.ok ? slots.data.slots[choice] : undefined;
    if (slot) {
      const res = await bookGuideAppointment({
        lead_id: state.leadId,
        meeting_type: meetingType,
        start: slot.start,
        session_id: sessionId,
      });
      if (res.ok) {
        state = mergeGuideState(state, { stage: "handoff" });
        tools.push({
          name: "book_appointment",
          input: { start: slot.start },
          output: { ok: true, ...res.data, state },
        });
        reply.push(`Booked: ${slot.label}. You'll get a confirmation shortly.`);
      } else {
        reply.push(
          res.error === "phone_required"
            ? "Please share a mobile number first, then pick a slot again."
            : "That slot couldn't be booked — please pick another."
        );
      }
    } else {
      reply.push("That slot is no longer available — ask me for times again.");
    }
  } else if (intent === "track") {
    const num = extractTrackingNumber(text);
    reply.push(
      num
        ? `You can see live status at /track/${encodeURIComponent(num)}.`
        : "Share your tracking number, or open /track to look it up."
    );
  } else if (intent === "book") {
    const meetingType = meetingTypeFrom(text);
    const slots = await listGuideSlots(meetingType);
    if (slots.ok && slots.data.slots.length) {
      state = mergeGuideState(state, { stage: "book", meetingType });
      const list = slots.data.slots.slice(0, 4);
      tools.push({
        name: "list_meeting_slots",
        input: { meeting_type: meetingType },
        output: { ok: true, slots: list, state },
      });
      reply.push(
        `Next available ${meetingType === "meeting" ? "meetings" : "calls"} (${slots.data.timezone}):\n` +
          list.map((s, i) => `${i + 1}. ${s.label}`).join("\n") +
          "\nReply with the number to book."
      );
    } else {
      reply.push(
        "I couldn't load times right now — leave your email and mobile and we'll call you."
      );
    }
  } else if (intent === "quote") {
    reply.push(QUOTE_REPLY);
  } else if (intent === "question" && text.trim()) {
    const hit = retrieveGuideKnowledge(text, { limit: 1 })[0];
    reply.push(hit && hit.score > 2 ? hit.body.slice(0, 600) : FALLBACK_REPLY);
  }

  if (state.stage !== "handoff" && !(intent === "book" && state.stage === "book")) {
    const ask = contactPrompt(state);
    if (ask) reply.push(ask);
  }
  if (state.leadId && text.trim()) {
    void saveGuideTranscript({
      lead_id: state.leadId,
      session_id: sessionId,
      summary: text.slice(0, 500),
      turns: [{ role: "user", content: text.slice(0, 500) }],
    }).catch(() => undefined);
  }

  const finalState = state;
  const stream = createUIMessageStream({
    execute: ({ writer }) => {
      writer.write({ type: "start", messageMetadata: { guideState: finalState } });
      tools.forEach((t, i) => {
        const toolCallId = `rule-${i}`;
        writer.write({
          type: "tool-input-available",
          toolCallId,
          toolName: t.name,
          input: t.input,
        });
        writer.write({ type: "tool-output-available", toolCallId, output: t.output });
      });
      writer.write({ type: "text-start", id: "t" });
      writer.write({ type: "text-delta", id: "t", delta: reply.join("\n\n") || FALLBACK_REPLY });
      writer.write({ type: "text-end", id: "t" });
      writer.write({ type: "finish" });
    },
  });
  return createUIMessageStreamResponse({ stream });
}
