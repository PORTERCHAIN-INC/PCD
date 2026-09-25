"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport, getToolName, isToolUIPart, type UIMessage } from "ai";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  ArrowUp,
  BookOpen,
  CalendarCheck,
  CheckCircle2,
  Clock3,
  MapPin,
  Radio,
  X,
} from "lucide-react";
import type { FormEvent } from "react";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import {
  GUIDE_SUGGESTION_IDS,
  guideActionsForTopic,
  matchGuideTopic,
  type GuideTopicId,
} from "@/lib/home/capacity-guide";
import {
  DEFAULT_GUIDE_STATE,
  mergeGuideState,
  normalizeGuideState,
  type GuideSessionState,
} from "@/lib/home/guide-session";
import {
  LOGISTICS_CHAT_ANCHOR_ID,
  OPEN_LOGISTICS_CHAT_EVENT,
} from "@/lib/home/open-logistics-chat";
import { HUB_FROM } from "@/lib/marketing/config";
import { ANALYTICS_EVENTS, track } from "@/lib/seo/analytics";
import { cn } from "@/lib/utils";

import { getOrCreateVisitorId } from "@/lib/visitor-tracking";

const SESSION_KEY = "pc_capacity_guide_session";
const STATE_KEY = "pc_capacity_guide_state";

function messageText(message: UIMessage): string {
  return message.parts
    .filter((part): part is { type: "text"; text: string } => part.type === "text")
    .map((part) => part.text)
    .join("");
}

/** Unify guide session with durable visitor id for CRM ↔ quote stitching. */
function ensureSessionId(): string {
  if (typeof window === "undefined") return "";
  const visitorId = getOrCreateVisitorId();
  try {
    const existing = sessionStorage.getItem(SESSION_KEY);
    if (existing && existing === visitorId) return existing;
    if (visitorId) {
      sessionStorage.setItem(SESSION_KEY, visitorId);
      return visitorId;
    }
    if (existing) return existing;
    const id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `guide-${Date.now()}`;
    sessionStorage.setItem(SESSION_KEY, id);
    return id;
  } catch {
    return visitorId || `guide-${Date.now()}`;
  }
}

function loadGuideState(): GuideSessionState {
  if (typeof window === "undefined") return { ...DEFAULT_GUIDE_STATE };
  try {
    const raw = sessionStorage.getItem(STATE_KEY);
    if (!raw) return { ...DEFAULT_GUIDE_STATE };
    return normalizeGuideState(JSON.parse(raw));
  } catch {
    return { ...DEFAULT_GUIDE_STATE };
  }
}

function persistGuideState(state: GuideSessionState) {
  try {
    sessionStorage.setItem(STATE_KEY, JSON.stringify(state));
  } catch {
    /* ignore */
  }
}

type ToolCardModel = {
  id: string;
  name: string;
  state: string;
  output: Record<string, unknown> | null;
  approvalId?: string;
  input?: Record<string, unknown> | null;
};

function toolCardsFromMessage(message: UIMessage): ToolCardModel[] {
  const cards: ToolCardModel[] = [];
  for (const part of message.parts) {
    if (!isToolUIPart(part)) continue;
    const name = getToolName(part);
    const output =
      part.state === "output-available" && part.output && typeof part.output === "object"
        ? (part.output as Record<string, unknown>)
        : null;
    const input =
      "input" in part && part.input && typeof part.input === "object"
        ? (part.input as Record<string, unknown>)
        : null;
    const approvalId =
      "approval" in part &&
      part.approval &&
      typeof part.approval === "object" &&
      part.approval &&
      "id" in part.approval
        ? String((part.approval as { id: string }).id)
        : undefined;
    cards.push({
      id: part.toolCallId,
      name,
      state: part.state,
      output,
      approvalId,
      input,
    });
  }
  return cards;
}

function stateFromToolOutput(
  output: Record<string, unknown> | null
): Partial<GuideSessionState> | null {
  if (!output || typeof output.state !== "object" || !output.state) return null;
  return normalizeGuideState(output.state);
}

export default function CapacityGuideChat({
  className,
  onClose,
  sourceSection = "home-capacity-guide",
}: {
  className?: string;
  onClose?: () => void;
  sourceSection?: string;
}) {
  const t = useTranslations("homeChooser.guide");
  const reduce = useReducedMotion();
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const formId = useId();
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [guideState, setGuideState] = useState<GuideSessionState>(DEFAULT_GUIDE_STATE);
  const guideStateRef = useRef(guideState);
  const trackedTools = useRef(new Set<string>());

  useEffect(() => {
    setSessionId(ensureSessionId());
    const loaded = loadGuideState();
    setGuideState(loaded);
    guideStateRef.current = loaded;
  }, []);

  useEffect(() => {
    function onOpen() {
      window.setTimeout(() => inputRef.current?.focus({ preventScroll: true }), 320);
    }
    window.addEventListener(OPEN_LOGISTICS_CHAT_EVENT, onOpen);
    return () => window.removeEventListener(OPEN_LOGISTICS_CHAT_EVENT, onOpen);
  }, []);

  useEffect(() => {
    guideStateRef.current = guideState;
    persistGuideState(guideState);
  }, [guideState]);

  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: "/api/capacity-guide",
        prepareSendMessagesRequest: ({ messages, id, trigger, messageId }) => ({
          body: {
            id,
            messages,
            trigger,
            messageId,
            sessionId: sessionId || undefined,
            guideState: guideStateRef.current,
          },
        }),
      }),
    [sessionId]
  );

  const { messages, sendMessage, status, error, clearError, addToolApprovalResponse } =
    useChat<UIMessage>({
      transport,
      messages: [
        {
          id: "welcome",
          role: "assistant",
          parts: [{ type: "text", text: t("welcome") }],
        },
      ],
      onFinish: ({ message }) => {
        track(ANALYTICS_EVENTS.CAPACITY_GUIDE_ASK, {
          sourceSection,
          from: HUB_FROM.chooser,
          topic: "groq",
          cta_label: messageText(message).slice(0, 80),
        });
        for (const card of toolCardsFromMessage(message)) {
          const patch = stateFromToolOutput(card.output);
          if (patch) {
            setGuideState((prev) => mergeGuideState(prev, patch));
          }
          if (card.state !== "output-available" || !card.output) continue;
          if (trackedTools.current.has(card.id)) continue;
          trackedTools.current.add(card.id);
          if (card.name === "capture_contact" && card.output.ok === true) {
            track(ANALYTICS_EVENTS.CAPACITY_GUIDE_LEAD_CAPTURED, {
              sourceSection,
              from: HUB_FROM.chooser,
              topic: "lead",
            });
            track(ANALYTICS_EVENTS.QUOTE_REQUEST, {
              source_section: sourceSection,
              path: "capacity_guide",
              topic: "lead",
            });
          }
          if (card.name === "book_appointment" && card.output.ok === true) {
            track(ANALYTICS_EVENTS.CAPACITY_GUIDE_APPOINTMENT_BOOKED, {
              sourceSection,
              from: HUB_FROM.chooser,
              topic: "appointment",
            });
          }
        }
      },
    });

  const busy = status === "submitted" || status === "streaming";

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: reduce ? "auto" : "smooth" });
  }, [messages, status, reduce]);

  async function ask(raw: string, source: "typed" | "suggestion") {
    const question = raw.trim();
    if (!question || busy) return;
    clearError();
    setInput("");
    if (source === "suggestion") {
      track(ANALYTICS_EVENTS.CAPACITY_GUIDE_SUGGESTION, {
        sourceSection,
        from: HUB_FROM.chooser,
        topic: matchGuideTopic(question),
        cta_label: question.slice(0, 80),
      });
    }
    await sendMessage({ text: question });
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void ask(input, "typed");
  }

  function suggestionLabel(id: GuideTopicId) {
    return t(`topics.${id}.prompt`);
  }

  function topicForAssistant(index: number): GuideTopicId | "fallback" {
    for (let i = index - 1; i >= 0; i -= 1) {
      if (messages[i]?.role === "user") {
        return matchGuideTopic(messageText(messages[i]));
      }
    }
    return "what";
  }

  return (
    <div
      id={onClose ? undefined : LOGISTICS_CHAT_ANCHOR_ID}
      className={cn(
        "relative flex h-[min(34rem,70dvh)] w-full flex-col overflow-hidden",
        "rounded-[1.75rem] border border-white/12 bg-[#070d18]/92 shadow-[0_24px_80px_rgba(0,0,0,0.45)] backdrop-blur-xl",
        "ring-1 ring-inset ring-white/5",
        className
      )}
      role="region"
      aria-label={t("ariaLabel")}
    >
      <div className="flex items-center justify-between gap-3 border-b border-white/10 px-4 py-3 sm:px-5">
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary/20 text-accent">
            <Radio className="h-4 w-4" aria-hidden />
            <span
              className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-emerald-400 ring-2 ring-[#070d18]"
              aria-hidden
            />
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold tracking-tight text-white">{t("title")}</p>
            <p className="truncate text-[11px] uppercase tracking-[0.18em] text-white/45">
              {busy ? t("thinking") : t("status")}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {!onClose ? (
            <p className="hidden text-[11px] text-white/40 sm:block">{t("hint")}</p>
          ) : null}
          {onClose ? (
            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-white/60 transition-colors hover:bg-white/10 hover:text-white"
              aria-label={t("closeAria")}
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          ) : null}
        </div>
      </div>

      <div
        ref={listRef}
        className="flex-1 space-y-3 overflow-y-auto px-3 py-4 sm:px-5"
        aria-live="polite"
      >
        <AnimatePresence initial={false}>
          {messages.map((msg, index) => {
            const text = messageText(msg);
            const tools = toolCardsFromMessage(msg);
            const isYou = msg.role === "user";
            const streamingEmpty =
              !isYou && !text && tools.length === 0 && busy && index === messages.length - 1;

            return (
              <motion.div
                key={msg.id}
                initial={reduce ? false : { opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.28 }}
                className={cn("flex", isYou ? "justify-end" : "justify-start")}
              >
                <div className={cn("max-w-[92%] sm:max-w-[85%]")}>
                  <p
                    className={cn(
                      "mb-1 text-[10px] font-semibold uppercase tracking-[0.16em]",
                      isYou ? "text-right text-accent/80" : "text-white/40"
                    )}
                  >
                    {isYou ? t("you") : t("guideName")}
                  </p>
                  {tools.length > 0 ? (
                    <div className="mb-2 space-y-1.5">
                      {tools.map((card) => (
                        <ToolResultCard
                          key={card.id}
                          card={card}
                          t={t}
                          onApprove={
                            card.approvalId
                              ? () =>
                                  void addToolApprovalResponse({
                                    id: card.approvalId!,
                                    approved: true,
                                  })
                              : undefined
                          }
                          onDeny={
                            card.approvalId
                              ? () =>
                                  void addToolApprovalResponse({
                                    id: card.approvalId!,
                                    approved: false,
                                  })
                              : undefined
                          }
                        />
                      ))}
                    </div>
                  ) : null}
                  {(text || streamingEmpty) && (
                    <div
                      className={cn(
                        "rounded-2xl px-4 py-3 text-sm leading-relaxed",
                        isYou
                          ? "rounded-br-md bg-secondary text-white"
                          : "rounded-bl-md border border-white/10 bg-white/[0.06] text-white/90"
                      )}
                    >
                      {streamingEmpty ? <TypingLine reduce={!!reduce} /> : text}
                    </div>
                  )}
                  {!isYou && text && status === "ready" ? (
                    <ActionRow topicId={topicForAssistant(index)} t={t} />
                  ) : null}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {error ? (
          <p className="rounded-xl border border-red-400/30 bg-red-500/10 px-3 py-2 text-xs text-red-100">
            {t("error")}
          </p>
        ) : null}
      </div>

      <div className="border-t border-white/8 px-3 pt-3 sm:px-5">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/35">
          {t("tryAsking")}
        </p>
        <div className="flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {GUIDE_SUGGESTION_IDS.map((id) => (
            <button
              key={id}
              type="button"
              disabled={busy}
              onClick={() => void ask(suggestionLabel(id), "suggestion")}
              className={cn(
                "shrink-0 rounded-full border border-white/12 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-white/75",
                "transition-colors hover:border-accent/40 hover:bg-white/[0.08] hover:text-white",
                "disabled:opacity-40"
              )}
            >
              {suggestionLabel(id)}
            </button>
          ))}
        </div>
      </div>

      <form
        id={formId}
        onSubmit={onSubmit}
        className="flex items-center gap-2 border-t border-white/10 p-3 sm:p-4"
      >
        <label htmlFor={`${formId}-input`} className="sr-only">
          {t("placeholder")}
        </label>
        <input
          ref={inputRef}
          id={`${formId}-input`}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t("placeholder")}
          disabled={busy}
          autoComplete="off"
          className={cn(
            "min-w-0 flex-1 rounded-xl border border-white/12 bg-white/[0.06] px-3.5 py-3 text-sm text-white",
            "placeholder:text-white/35 outline-none transition-shadow",
            "focus:border-accent/50 focus:ring-2 focus:ring-accent/20",
            "disabled:opacity-50"
          )}
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          aria-label={t("send")}
          className={cn(
            "inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-secondary text-white",
            "transition-colors hover:bg-[#1d4ed8] disabled:cursor-not-allowed disabled:opacity-40"
          )}
        >
          <ArrowUp className="h-5 w-5" aria-hidden />
        </button>
      </form>
    </div>
  );
}

function ToolResultCard({
  card,
  t,
  onApprove,
  onDeny,
}: {
  card: ToolCardModel;
  t: ReturnType<typeof useTranslations>;
  onApprove?: () => void;
  onDeny?: () => void;
}) {
  const awaitingApproval = card.state === "approval-requested";
  const pending =
    card.state === "input-streaming" ||
    card.state === "input-available" ||
    card.state === "approval-responded";
  const failed =
    card.state === "output-error" ||
    card.state === "output-denied" ||
    (card.output && card.output.ok === false);

  let title = awaitingApproval ? t("toolAwaitingApproval") : t("toolWorking");
  let detail: string | null = null;
  let Icon = Clock3;

  if (awaitingApproval && card.input) {
    const mt = typeof card.input.meeting_type === "string" ? card.input.meeting_type : "call";
    const start = typeof card.input.start === "string" ? card.input.start : "";
    detail = `${mt}${start ? ` · ${start}` : ""}`;
    Icon = CalendarCheck;
  } else if (!pending && !failed && card.output) {
    if (card.name === "capture_contact") {
      title = card.output.created === true ? t("toolContactSaved") : t("toolContactUpdated");
      detail = typeof card.output.email === "string" ? String(card.output.email) : null;
      Icon = CheckCircle2;
    } else if (card.name === "list_meeting_slots") {
      title = t("toolSlotsReady");
      const slots = Array.isArray(card.output.slots) ? card.output.slots : [];
      detail = slots
        .slice(0, 3)
        .map((s) =>
          s && typeof s === "object" && "label" in s ? String((s as { label: string }).label) : ""
        )
        .filter(Boolean)
        .join(" · ");
      Icon = Clock3;
    } else if (card.name === "book_appointment") {
      title = t("toolBooked");
      detail = typeof card.output.title === "string" ? String(card.output.title) : null;
      Icon = CalendarCheck;
    } else if (card.name === "save_transcript_excerpt") {
      title = t("toolTranscriptSaved");
      Icon = CheckCircle2;
    } else if (card.name === "lookup_knowledge") {
      title = t("toolKnowledge");
      detail = typeof card.output.count === "number" ? `${card.output.count} sources` : null;
      Icon = BookOpen;
    } else if (card.name === "get_tracking_help") {
      title = t("toolTracking");
      detail =
        typeof card.output.detail_path === "string"
          ? String(card.output.detail_path)
          : typeof card.output.hub_path === "string"
            ? String(card.output.hub_path)
            : null;
      Icon = MapPin;
    } else if (card.name === "qualify_lead") {
      title = t("toolQualified");
      Icon = CheckCircle2;
    } else if (card.name === "update_guide_state") {
      title = t("toolStateUpdated");
      Icon = CheckCircle2;
    }
  } else if (failed) {
    title = t("toolFailed");
  }

  return (
    <div
      className={cn(
        "flex flex-col gap-2 rounded-xl border px-3 py-2 text-xs",
        failed
          ? "border-red-400/25 bg-red-500/10 text-red-100"
          : awaitingApproval
            ? "border-amber-400/30 bg-amber-500/10 text-amber-50"
            : "border-emerald-400/20 bg-emerald-500/10 text-emerald-50"
      )}
    >
      <div className="flex items-start gap-2">
        <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 opacity-90" aria-hidden />
        <div className="min-w-0">
          <p className="font-semibold">{title}</p>
          {detail ? <p className="mt-0.5 truncate text-[11px] opacity-80">{detail}</p> : null}
        </div>
      </div>
      {awaitingApproval && onApprove && onDeny ? (
        <div className="flex gap-2 pl-5">
          <button
            type="button"
            onClick={onApprove}
            className="rounded-lg bg-secondary px-2.5 py-1 text-[11px] font-semibold text-white"
          >
            {t("toolApproveBook")}
          </button>
          <button
            type="button"
            onClick={onDeny}
            className="rounded-lg border border-white/20 px-2.5 py-1 text-[11px] font-semibold text-white/80"
          >
            {t("toolDenyBook")}
          </button>
        </div>
      ) : null}
    </div>
  );
}

function TypingLine({ reduce }: { reduce: boolean }) {
  if (reduce) {
    return <span className="text-white/50">…</span>;
  }
  return (
    <span className="inline-flex items-center gap-1.5 py-0.5" aria-hidden>
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-accent"
          animate={{ opacity: [0.25, 1, 0.25], y: [0, -3, 0] }}
          transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.15 }}
        />
      ))}
    </span>
  );
}

function ActionRow({
  topicId,
  t,
}: {
  topicId: GuideTopicId | "fallback";
  t: ReturnType<typeof useTranslations>;
}) {
  const actions = guideActionsForTopic(topicId, HUB_FROM.chooser);
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {actions.map((action) => (
        <Link
          key={action.href + action.labelKey}
          href={action.href}
          onClick={() =>
            track(ANALYTICS_EVENTS.CAPACITY_GUIDE_ACTION, {
              sourceSection: "home-capacity-guide",
              from: HUB_FROM.chooser,
              topic: topicId,
              cta_label: action.labelKey,
            })
          }
          className={cn(
            "inline-flex items-center rounded-lg border border-white/15 bg-white/[0.05] px-3 py-1.5",
            "text-xs font-semibold text-accent transition-colors hover:border-accent/40 hover:bg-white/[0.1]"
          )}
        >
          {t(action.labelKey)} →
        </Link>
      ))}
    </div>
  );
}
