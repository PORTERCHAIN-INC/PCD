"use client";

import { useState } from "react";
import { Search } from "lucide-react";

/** Hides non-matching server-rendered FAQ items; opens matches. No data shipped to the client. */
export default function FaqFilter({ targetId, locale }: { targetId: string; locale: string }) {
  const [q, setQ] = useState("");
  const [count, setCount] = useState<number | null>(null);

  function apply(value: string) {
    setQ(value);
    const root = document.getElementById(targetId);
    if (!root) return;
    const needle = value.trim().toLowerCase();
    let shown = 0;
    root.querySelectorAll<HTMLDetailsElement>("[data-faq-item]").forEach((el) => {
      const hit = !needle || (el.dataset.faqText ?? "").includes(needle);
      el.hidden = !hit;
      el.open = Boolean(needle) && hit;
      if (hit) shown++;
    });
    root.querySelectorAll<HTMLElement>("[data-faq-group]").forEach((g) => {
      g.hidden = !g.querySelector("[data-faq-item]:not([hidden])");
    });
    setCount(needle ? shown : null);
  }

  const fr = locale === "fr";
  return (
    <div className="mb-8">
      <label className="flex h-12 items-center gap-2 rounded-2xl border border-primary/15 bg-white px-4 focus-within:border-secondary focus-within:ring-4 focus-within:ring-secondary/15">
        <Search className="h-4 w-4 text-muted" aria-hidden />
        <span className="sr-only">{fr ? "Chercher une question" : "Search questions"}</span>
        <input
          type="search"
          value={q}
          onChange={(e) => apply(e.target.value)}
          placeholder={
            fr ? "Chercher : prix, Shopify, assurance…" : "Search: price, Shopify, insurance…"
          }
          className="min-w-0 flex-1 bg-transparent text-base text-primary outline-none placeholder:text-muted"
        />
      </label>
      <p className="mt-2 min-h-5 text-sm text-muted" role="status" aria-live="polite">
        {count === null
          ? ""
          : fr
            ? `${count} résultat(s)`
            : `${count} result${count === 1 ? "" : "s"}`}
      </p>
    </div>
  );
}
