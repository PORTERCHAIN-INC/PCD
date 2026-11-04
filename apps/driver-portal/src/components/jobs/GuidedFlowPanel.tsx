"use client";

/** Doc 82 §1.2: illustrated step cards from the server flow spec (same props as mobile GuidedFlowCard). */
import { flowView, type Lang } from "@porterchain/driver-flows";
import { flowFor } from "@/lib/flow-context";
import type { DriverJobDetail } from "@/lib/jobs";

function browserLang(): Lang {
  return typeof navigator !== "undefined" && navigator.language?.toLowerCase().startsWith("fr")
    ? "fr"
    : "en";
}

export function GuidedFlowPanel({ job }: { job: DriverJobDetail }) {
  const { spec, ctx, completed } = flowFor(job);
  if (!spec) return null;
  const lang = browserLang();
  const cards = flowView(spec, ctx, lang, completed);
  return (
    <section data-testid="guided-flow" className="rounded-xl border border-black/10 p-3">
      <h3 className="text-sm font-semibold">{lang === "fr" ? "Étapes" : "Steps"}</h3>
      <ol className="mt-2 space-y-1">
        {cards.map((c, i) => (
          <li
            key={c.id}
            className="min-h-11 py-1"
            aria-current={c.state === "current" ? "step" : undefined}
          >
            <span
              className={
                c.state === "current" ? "font-semibold" : c.state === "done" ? "text-black/50" : ""
              }
            >
              {i + 1}. {c.title}
            </span>
            {c.state === "current" ? (
              <div className="text-xs text-black/70">
                <p>✓ {c.doText}</p>
                {c.dontText ? <p>✕ {c.dontText}</p> : null}
                {c.blockers.map((b) => (
                  <p key={b} role="alert">
                    ⚠ {b}
                  </p>
                ))}
              </div>
            ) : null}
          </li>
        ))}
      </ol>
    </section>
  );
}
