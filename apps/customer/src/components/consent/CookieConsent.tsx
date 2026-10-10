"use client";

import { useEffect, useState } from "react";

const KEY = "pc_consent";
const COPY = {
  en: {
    text: "We use essential cookies to sign you in and run deliveries. With your OK we'd also use optional analytics to improve the service. You can change this any time.",
    accept: "Allow optional",
    reject: "Essential only",
  },
  de: {
    text: "Wir verwenden notwendige Cookies für Anmeldung und Zustellung. Mit Ihrer Zustimmung nutzen wir zusätzlich optionale Analyse-Cookies. Sie können dies jederzeit ändern.",
    accept: "Optionale erlauben",
    reject: "Nur notwendige",
  },
} as const;

/** Has the visitor opted in to a non-essential category? Default: no (privacy by default). */
export function hasConsent(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie.split("; ").some((c) => c === `${KEY}=all`);
}

/** EU-style opt-in banner (ePrivacy / TKG 2021 §165). Shown only when the region requires it. */
export default function CookieConsent({ show, locale }: { show: boolean; locale: string }) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    setOpen(show && !document.cookie.split("; ").some((c) => c.startsWith(`${KEY}=`)));
  }, [show]);
  if (!open) return null;
  const t = locale.startsWith("de") ? COPY.de : COPY.en;
  const choose = (v: "all" | "essential") => {
    document.cookie = `${KEY}=${v}; path=/; max-age=${60 * 60 * 24 * 180}; samesite=lax; secure`;
    setOpen(false);
  };
  return (
    <div
      role="dialog"
      aria-label="Cookies"
      className="fixed inset-x-3 bottom-3 z-50 mx-auto max-w-xl rounded-2xl border border-black/10 bg-white p-4 text-sm shadow-xl"
    >
      <p>{t.text}</p>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          className="flex-1 rounded-full border px-4 py-2 font-semibold"
          onClick={() => choose("essential")}
        >
          {t.reject}
        </button>
        <button
          type="button"
          className="flex-1 rounded-full border px-4 py-2 font-semibold"
          onClick={() => choose("all")}
        >
          {t.accept}
        </button>
      </div>
    </div>
  );
}
