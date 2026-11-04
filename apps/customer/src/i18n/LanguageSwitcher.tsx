"use client";

import { chooseLocale, getLocale, type Locale } from "./core";

/** EN | FR toggle (sets pc_locale and reloads). */
export function LanguageSwitcher({ className = "" }: { className?: string }) {
  const cur = getLocale();
  const btn = (l: Locale, label: string) => (
    <button
      key={l}
      type="button"
      data-no-i18n=""
      aria-pressed={cur === l}
      aria-label={l === "fr" ? "Français" : "English"}
      onClick={() => cur !== l && chooseLocale(l)}
      className={`rounded-lg px-2 py-1 text-xs font-semibold transition ${
        cur === l ? "bg-primary text-white" : "text-gray-500 hover:bg-gray-bg hover:text-primary"
      }`}
    >
      {label}
    </button>
  );
  return (
    <div
      role="group"
      aria-label="Language"
      data-testid="language-switcher"
      className={`inline-flex items-center gap-0.5 rounded-xl border border-primary/10 bg-white p-0.5 ${className}`}
    >
      {btn("en", "EN")}
      {btn("fr", "FR")}
    </div>
  );
}
