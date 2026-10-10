"use client";

import { useEffect, useState } from "react";
import { useLocale } from "next-intl";
import {
  cancelOrder,
  getOrderActions,
  rateOrder,
  reportProblem,
  type FastApiError,
  type OrderActions,
  type ProblemKind,
} from "@/lib/api";

const COPY = {
  en: {
    section: "Manage this delivery",
    howWas: "How was your delivery?",
    ratingAria: "Rating, 1 to 5 stars",
    star: (n: number) => `${n} star${n > 1 ? "s" : ""}`,
    whatWrong: "What went wrong? We read every one.",
    sendFeedback: "Send feedback",
    thanks: (n: number) => `Thanks for rating this delivery ${n}/5.`,
    followUp: " Our team will follow up by email.",
    sendAgain: "Send again",
    receipt: "Receipt",
    emailed: "emailed to you",
    cancelled: "This delivery is cancelled.",
    refunded: "Your refund is on its way to your card (5–10 business days).",
    refunding: "Your full refund is being processed. We will email you when it is sent.",
    cancelQ: "Cancel this delivery?",
    cancelSub: "Full refund. This cannot be undone.",
    cancelling: "Cancelling…",
    yesCancel: "Yes, cancel",
    keep: "Keep it",
    cancelDelivery: "Cancel delivery",
    problem: "Report a problem",
    problemTitle: "What happened?",
    details: "Details (optional)",
    send: "Send to support",
    sent: (h: number) => `Got it. A person will reply by email within ${h} hours.`,
    kinds: {
      late: "Late or missed",
      damaged: "Damaged",
      missing: "Missing item",
      wrong_address: "Wrong place",
      return: "Return to sender",
      billing: "Billing",
      other: "Other",
    } as Record<ProblemKind, string>,
  },
  fr: {
    section: "Gérer cette livraison",
    howWas: "Comment s'est passée votre livraison?",
    ratingAria: "Note, de 1 à 5 étoiles",
    star: (n: number) => `${n} étoile${n > 1 ? "s" : ""}`,
    whatWrong: "Qu'est-ce qui n'a pas fonctionné? Nous lisons chaque message.",
    sendFeedback: "Envoyer",
    thanks: (n: number) => `Merci d'avoir noté cette livraison ${n}/5.`,
    followUp: " Notre équipe vous écrira par courriel.",
    sendAgain: "Réserver à nouveau",
    receipt: "Reçu",
    emailed: "envoyé par courriel",
    cancelled: "Cette livraison est annulée.",
    refunded: "Votre remboursement est en route vers votre carte (5 à 10 jours ouvrables).",
    refunding: "Votre remboursement complet est en traitement. Nous vous écrirons à l'envoi.",
    cancelQ: "Annuler cette livraison?",
    cancelSub: "Remboursement complet. Action définitive.",
    cancelling: "Annulation…",
    yesCancel: "Oui, annuler",
    keep: "La garder",
    cancelDelivery: "Annuler la livraison",
    problem: "Signaler un problème",
    problemTitle: "Que s'est-il passé?",
    details: "Détails (facultatif)",
    send: "Envoyer au soutien",
    sent: (h: number) => `C'est noté. Une personne vous répondra par courriel d'ici ${h} heures.`,
    kinds: {
      late: "Retard ou absence",
      damaged: "Endommagé",
      missing: "Article manquant",
      wrong_address: "Mauvais endroit",
      return: "Retour à l'expéditeur",
      billing: "Facturation",
      other: "Autre",
    } as Record<ProblemKind, string>,
  },
};

/**
 * The tracking link is the product: receipt, cancel before pickup, 1-tap rating, report a
 * problem / return and Send again, all behind the signed ?t= link from the email. No login.
 */
export default function TrackActions({
  tracking,
  token,
  refreshKey,
}: {
  tracking: string;
  token: string;
  refreshKey?: string;
}) {
  const c = useLocale() === "fr" ? COPY.fr : COPY.en;
  const [actions, setActions] = useState<OrderActions | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [score, setScore] = useState(0);
  const [comment, setComment] = useState("");
  const [problemOpen, setProblemOpen] = useState(false);
  const [kind, setKind] = useState<ProblemKind | null>(null);
  const [details, setDetails] = useState("");
  const [problemSent, setProblemSent] = useState<number | null>(null);

  useEffect(() => {
    getOrderActions(tracking, token)
      .then(setActions)
      .catch((e: FastApiError) => setError(e.message));
  }, [tracking, token, refreshKey]);

  if (!actions) {
    return error ? (
      <p role="alert" className="mb-8 rounded-2xl bg-red-50 px-4 py-3 text-sm font-medium text-red-800">
        {error}
      </p>
    ) : null;
  }

  async function run<T>(fn: () => Promise<T>, after: (v: T) => void) {
    setBusy(true);
    setError(null);
    try {
      after(await fn());
    } catch (e) {
      setError((e as FastApiError).message);
    } finally {
      setBusy(false);
    }
  }

  const doCancel = () =>
    run(() => cancelOrder(tracking, token), (a) => {
      setActions(a);
      setConfirming(false);
    });
  const submitRating = (value = score) => run(() => rateOrder(tracking, token, value, comment), setActions);
  const doRate = async (value: number) => {
    setScore(value);
    if (value >= 4) await submitRating(value);
  };
  const sendProblem = () =>
    kind ? run(() => reportProblem(tracking, token, kind, details), (r) => setProblemSent(r.reply_within_hours)) : undefined;

  const refund = actions.refund;
  const cancelled = actions.state === "CANCELLED";

  return (
    <section className="mb-8 space-y-3" aria-label={c.section} data-testid="track-actions">
      {actions.can_rate ? (
        <div className="rounded-3xl border border-primary/10 bg-white p-5">
          <p className="text-lg font-bold text-primary">{c.howWas}</p>
          <div className="mt-3 flex gap-2" role="radiogroup" aria-label={c.ratingAria}>
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                role="radio"
                aria-checked={score === n}
                aria-label={c.star(n)}
                disabled={busy}
                onClick={() => void doRate(n)}
                data-testid={`rate-${n}`}
                className={`h-12 w-12 rounded-2xl text-2xl transition ${
                  score >= n ? "bg-primary text-amber-300" : "bg-primary/5 text-primary/45 hover:bg-primary/10"
                }`}
              >
                ★
              </button>
            ))}
          </div>
          {score > 0 && score <= 3 ? (
            <div className="mt-4">
              <label className="block text-sm font-semibold text-primary">
                {c.whatWrong}
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  maxLength={1000}
                  rows={3}
                  className="mt-1.5 block w-full rounded-2xl border border-primary/15 px-4 py-3 text-base text-primary outline-none focus:border-primary"
                />
              </label>
              <button
                type="button"
                disabled={busy}
                onClick={() => void submitRating()}
                className="mt-3 rounded-2xl bg-primary px-5 py-3 text-sm font-bold text-white disabled:opacity-60"
              >
                {c.sendFeedback}
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
      {actions.rating ? (
        <p className="rounded-3xl bg-primary/5 px-5 py-4 text-sm font-medium text-primary" role="status">
          {c.thanks(actions.rating.score)}
          {actions.rating.score <= 3 ? c.followUp : ""}
        </p>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2">
        {actions.send_again_url && !cancelled ? (
          <a
            href={actions.send_again_url}
            data-testid="send-again"
            className="flex items-center justify-center rounded-2xl bg-primary px-5 py-4 text-base font-bold text-white shadow-lg shadow-primary/20"
          >
            {c.sendAgain}
          </a>
        ) : null}
        {actions.receipt?.url ? (
          <a
            href={actions.receipt.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center rounded-2xl border border-primary/20 bg-white px-5 py-4 text-base font-bold text-primary"
          >
            {c.receipt}
            {actions.receipt.receipt_number ? ` ${actions.receipt.receipt_number}` : ""}
          </a>
        ) : actions.receipt?.receipt_number ? (
          <p className="flex items-center justify-center rounded-2xl border border-primary/10 bg-white px-5 py-4 text-sm text-primary/80">
            {c.receipt} {actions.receipt.receipt_number} · {c.emailed}
          </p>
        ) : null}
      </div>

      {cancelled ? (
        <p className="rounded-3xl bg-primary/5 px-5 py-4 text-sm text-primary" role="status" data-testid="cancelled">
          {c.cancelled} {refund?.status === "refunded" ? c.refunded : refund ? c.refunding : ""}
        </p>
      ) : actions.can_cancel && confirming ? (
        <div className="rounded-3xl border border-red-200 bg-red-50 p-5">
          <p className="font-bold text-red-900">{c.cancelQ}</p>
          <p className="mt-1 text-sm text-red-900/80">{c.cancelSub}</p>
          <div className="mt-4 flex gap-3">
            <button
              type="button"
              disabled={busy}
              onClick={() => void doCancel()}
              data-testid="cancel-confirm"
              className="rounded-2xl bg-red-700 px-5 py-3 text-sm font-bold text-white disabled:opacity-60"
            >
              {busy ? c.cancelling : c.yesCancel}
            </button>
            <button
              type="button"
              onClick={() => setConfirming(false)}
              className="rounded-2xl border border-red-200 bg-white px-5 py-3 text-sm font-bold text-red-900"
            >
              {c.keep}
            </button>
          </div>
        </div>
      ) : null}

      {problemSent !== null ? (
        <p className="rounded-3xl bg-primary/5 px-5 py-4 text-sm font-medium text-primary" role="status" data-testid="problem-sent">
          {c.sent(problemSent)}
        </p>
      ) : problemOpen ? (
        <div className="rounded-3xl border border-primary/10 bg-white p-5" data-testid="problem-panel">
          <p className="text-lg font-bold text-primary">{c.problemTitle}</p>
          <div className="mt-3 flex flex-wrap gap-2" role="radiogroup">
            {(Object.keys(c.kinds) as ProblemKind[]).map((k) => (
              <button
                key={k}
                type="button"
                role="radio"
                aria-checked={kind === k}
                onClick={() => setKind(k)}
                data-testid={`problem-${k}`}
                className={`rounded-full border px-3.5 py-2 text-sm font-semibold ${
                  kind === k ? "border-primary bg-primary text-white" : "border-primary/15 text-primary"
                }`}
              >
                {c.kinds[k]}
              </button>
            ))}
          </div>
          <label className="mt-4 block text-sm font-semibold text-primary">
            {c.details}
            <textarea
              value={details}
              onChange={(e) => setDetails(e.target.value)}
              maxLength={2000}
              rows={3}
              className="mt-1.5 block w-full rounded-2xl border border-primary/15 px-4 py-3 text-base text-primary outline-none focus:border-primary"
            />
          </label>
          <button
            type="button"
            disabled={!kind || busy}
            onClick={() => void sendProblem()}
            data-testid="problem-send"
            className="mt-3 rounded-2xl bg-primary px-5 py-3 text-sm font-bold text-white disabled:opacity-50"
          >
            {c.send}
          </button>
        </div>
      ) : null}

      {/* Quiet secondary actions: one line, never competing with the primary button. */}
      {!confirming && !problemOpen && problemSent === null ? (
        <div className="flex flex-wrap items-center justify-between gap-3 px-1">
          {actions.can_cancel && !cancelled ? (
            <span className="text-xs text-primary/70">{actions.cancel_rule}</span>
          ) : (
            <span />
          )}
          <span className="flex gap-4">
            {actions.retail ? (
              <button
                type="button"
                onClick={() => setProblemOpen(true)}
                data-testid="problem-start"
                className="text-sm font-semibold text-primary underline underline-offset-4"
              >
                {c.problem}
              </button>
            ) : null}
            {actions.can_cancel && !cancelled ? (
              <button
                type="button"
                onClick={() => setConfirming(true)}
                data-testid="cancel-start"
                className="text-sm font-semibold text-red-800 underline underline-offset-4"
              >
                {c.cancelDelivery}
              </button>
            ) : null}
          </span>
        </div>
      ) : null}

      {error ? (
        <p role="alert" className="rounded-2xl bg-red-50 px-4 py-3 text-sm font-medium text-red-800">
          {error}
        </p>
      ) : null}
    </section>
  );
}
