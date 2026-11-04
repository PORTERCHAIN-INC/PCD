import { blockersFor } from "./checks";
import { blockMessage, CARD_ICON, cardCopy, type Lang } from "./copy";
import { visibleSteps } from "./machine";
import type { FlowContext, FlowSpec } from "./types";

export type CardView = {
  id: string;
  card: string;
  icon: string;
  title: string;
  doText: string;
  dontText: string;
  button: string;
  captures: string[];
  blockers: string[];
  state: "done" | "current" | "todo";
};

/** Same props on web and mobile (doc 82 §2.2 step 5: parity is checked on these props). */
export function flowView(
  spec: FlowSpec,
  ctx: FlowContext,
  lang: Lang = "en",
  completed = 0
): CardView[] {
  return visibleSteps(spec, ctx.flags).map((s, i) => {
    const c = cardCopy(s.card, lang);
    const state = i < completed ? "done" : i === completed ? "current" : "todo";
    return {
      id: s.id,
      card: s.card,
      icon: CARD_ICON[s.card] ?? "circle",
      title: c.title,
      doText: c.do,
      dontText: c.dont,
      button: c.button,
      captures: [...s.capture],
      blockers:
        state === "current"
          ? blockersFor(s.block_if, ctx, spec).map((b) => blockMessage(b, lang))
          : [],
      state,
    };
  });
}
