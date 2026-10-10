"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { useLocale } from "next-intl";

const COPY = {
  en: {
    title: "Confirm your subscription",
    lead: "One click and you'll get PorterChain delivery news by email. You can unsubscribe at any time.",
    cta: "Yes, subscribe me",
    working: "Confirming…",
    ok: "You're subscribed. Thanks!",
    bad: "This link is invalid or has expired. Sign up again from the site footer.",
    missing: "Missing confirmation token.",
  },
  fr: {
    title: "Confirmez votre abonnement",
    lead: "Un clic et vous recevrez les nouvelles de livraison de PorterChain par courriel. Vous pouvez vous désabonner en tout temps.",
    cta: "Oui, abonnez-moi",
    working: "Confirmation…",
    ok: "Vous êtes abonné. Merci!",
    bad: "Ce lien est invalide ou expiré. Inscrivez-vous de nouveau depuis le pied de page.",
    missing: "Jeton de confirmation manquant.",
  },
} as const;

/**
 * Double opt-in landing. Confirmation needs a click (POST), so link scanners
 * that prefetch the email link can't confirm on the person's behalf.
 */
function ConfirmInner() {
  const token = useSearchParams().get("token") ?? "";
  const t = COPY[useLocale().startsWith("fr") ? "fr" : "en"];
  const [state, setState] = useState<"idle" | "working" | "ok" | "error">(token ? "idle" : "error");

  async function confirm() {
    setState("working");
    try {
      const res = await fetch("/api/newsletter/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      });
      setState(res.ok ? "ok" : "error");
    } catch {
      setState("error");
    }
  }

  return (
    <main className="mx-auto flex min-h-[50vh] max-w-lg flex-col justify-center px-6 py-16">
      <h1 className="text-2xl font-semibold text-slate-900">{t.title}</h1>
      {state === "ok" ? (
        <p className="mt-3 text-sm text-slate-700" role="status">
          {t.ok}
        </p>
      ) : state === "error" ? (
        <p className="mt-3 text-sm text-red-700" role="alert">
          {token ? t.bad : t.missing}
        </p>
      ) : (
        <>
          <p className="mt-3 text-sm text-slate-600">{t.lead}</p>
          <button
            type="button"
            onClick={confirm}
            disabled={state === "working"}
            className="mt-6 inline-flex min-h-11 items-center justify-center rounded-full bg-primary px-6 text-sm font-semibold text-white disabled:opacity-60"
          >
            {state === "working" ? t.working : t.cta}
          </button>
        </>
      )}
    </main>
  );
}

export default function NewsletterConfirmPage() {
  return (
    <Suspense fallback={<main className="p-8 text-sm text-slate-600">…</main>}>
      <ConfirmInner />
    </Suspense>
  );
}
