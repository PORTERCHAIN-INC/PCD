"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useLocale } from "next-intl";
import { Link } from "@/i18n/navigation";
import {
  readEmailPreferences,
  requestDataDeletion,
  saveEmailPreferences,
  unsubscribeAll,
  type EmailPreferences,
  type FastApiError,
} from "@/lib/api";

type Key = keyof EmailPreferences["preferences"];

const COPY = {
  en: {
    eyebrow: "Your data, your call",
    title: "Email preferences",
    forEmail: (e: string) => `For ${e}`,
    badLink: "This link is not valid. Use the link in your latest email.",
    rows: {
      tracking: ["Delivery updates", "Booked, out for delivery, delivered with photo, and any problem. Recommended."],
      reorder: ["Send-again reminders", "One email after a delivery with a one-tap link to book the same trip."],
      marketing: ["Tips and offers", "Occasional news and offers from PorterChain Logistics Inc. Only with your consent."],
    } as Record<Key, [string, string]>,
    consentGiven: (d: string) => `Consent given ${d}`,
    toggled: (t: string, on: boolean) => `${t} ${on ? "turned on" : "turned off"}.`,
    casl: "Turning on tips and offers records your consent under Canada\u2019s anti-spam law (CASL). You can turn it off at any time.",
    unsubAll: "Unsubscribe from everything except delivery updates",
    unsubDone: "Unsubscribed. You will only get emails about deliveries you book.",
    dataTitle: "Your data",
    dataBody1: "Download a copy of your data from your",
    account: "account",
    dataBody2: "(sign-in link sent to this email). Under PIPEDA and GDPR you can also ask us to delete it. See our",
    policy: "privacy policy",
    requested: "Deletion requested. A person reviews it, then it runs automatically. We email you when it is complete.",
    deleteQ: "Delete your PorterChain data?",
    deleteSub: "We keep only what the law requires (tax records, without your name or address). Open deliveries finish first.",
    yesDelete: "Yes, delete my data",
    keep: "Keep it",
    requestDelete: "Request deletion of my data",
    deleteDone: (ref: string, days: number) => `Request ${ref} received. Completed within ${days} days; we email you when done.`,
    dateLocale: "en-CA",
  },
  fr: {
    eyebrow: "Vos données, votre choix",
    title: "Préférences courriel",
    forEmail: (e: string) => `Pour ${e}`,
    badLink: "Ce lien n'est pas valide. Utilisez le lien de votre dernier courriel.",
    rows: {
      tracking: ["Suivi des livraisons", "Réservée, en route, livrée avec photo, et tout problème. Recommandé."],
      reorder: ["Rappels « Réserver à nouveau »", "Un courriel après une livraison avec un lien pour refaire le même trajet."],
      marketing: ["Conseils et offres", "Nouvelles et offres occasionnelles de PorterChain Logistics Inc. Seulement avec votre consentement."],
    } as Record<Key, [string, string]>,
    consentGiven: (d: string) => `Consentement donné le ${d}`,
    toggled: (t: string, on: boolean) => `${t} : ${on ? "activé" : "désactivé"}.`,
    casl: "Activer les conseils et offres enregistre votre consentement en vertu de la loi canadienne anti-pourriel (LCAP). Vous pouvez le retirer en tout temps.",
    unsubAll: "Me désabonner de tout sauf le suivi des livraisons",
    unsubDone: "Désabonné. Vous ne recevrez que les courriels sur vos livraisons.",
    dataTitle: "Vos données",
    dataBody1: "Téléchargez une copie de vos données depuis votre",
    account: "compte",
    dataBody2: "(lien de connexion envoyé à ce courriel). En vertu de la LPRPDE et du RGPD, vous pouvez aussi demander leur suppression. Voir notre",
    policy: "politique de confidentialité",
    requested: "Suppression demandée. Une personne la vérifie, puis elle s'exécute automatiquement. Nous vous écrirons une fois terminée.",
    deleteQ: "Supprimer vos données PorterChain?",
    deleteSub: "Nous gardons seulement ce que la loi exige (dossiers fiscaux, sans nom ni adresse). Les livraisons en cours se terminent d'abord.",
    yesDelete: "Oui, supprimer mes données",
    keep: "Les garder",
    requestDelete: "Demander la suppression de mes données",
    deleteDone: (ref: string, days: number) => `Demande ${ref} reçue. Traitée d'ici ${days} jours; nous vous écrirons une fois terminée.`,
    dateLocale: "fr-CA",
  },
};

export default function EmailPreferencesView() {
  const c = useLocale() === "fr" ? COPY.fr : COPY.en;
  const token = useSearchParams().get("t") ?? "";
  const [prefs, setPrefs] = useState<EmailPreferences | null>(null);
  const [error, setError] = useState<string | null>(token ? null : c.badLink);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    if (!token) return;
    readEmailPreferences(token)
      .then(setPrefs)
      .catch((e: FastApiError) => setError(e.message));
  }, [token]);

  async function run(fn: () => Promise<EmailPreferences>, message: string) {
    setBusy(true);
    setError(null);
    try {
      setPrefs(await fn());
      setNotice(message);
    } catch (e) {
      setError((e as FastApiError).message);
    } finally {
      setBusy(false);
    }
  }

  async function deleteData() {
    setBusy(true);
    setError(null);
    try {
      const res = await requestDataDeletion(token);
      setNotice(c.deleteDone(res.reference, res.sla_days));
      setPrefs((p) => (p ? { ...p, deletion_requested: true } : p));
      setConfirmDelete(false);
    } catch (e) {
      setError((e as FastApiError).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <p className="text-[13px] font-semibold uppercase tracking-[0.18em] text-primary/65">{c.eyebrow}</p>
      <h1 className="mt-2 text-4xl font-extrabold tracking-tight text-primary">{c.title}</h1>
      {prefs ? <p className="mt-3 text-primary/75">{c.forEmail(prefs.email)}</p> : null}

      {notice ? (
        <p role="status" className="mt-6 rounded-2xl bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-900">
          {notice}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mt-6 rounded-2xl bg-red-50 px-4 py-3 text-sm font-medium text-red-800">
          {error}
        </p>
      ) : null}

      {prefs ? (
        <>
          <ul className="mt-8 divide-y divide-primary/10 rounded-3xl border border-primary/10 bg-white">
            {(Object.keys(c.rows) as Key[]).map((key) => {
              const [title, body] = c.rows[key];
              const on = prefs.preferences[key];
              return (
                <li key={key} className="flex items-start justify-between gap-4 p-5">
                  <div>
                    <p className="font-bold text-primary">{title}</p>
                    <p className="mt-1 text-sm text-primary/75">{body}</p>
                    {key === "marketing" && prefs.marketing_consent_at ? (
                      <p className="mt-1 text-xs text-primary/70">
                        {c.consentGiven(new Date(prefs.marketing_consent_at).toLocaleDateString(c.dateLocale))}
                      </p>
                    ) : null}
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={on}
                    aria-label={title}
                    disabled={busy}
                    data-testid={`pref-${key}`}
                    onClick={() => void run(() => saveEmailPreferences(token, { [key]: !on }), c.toggled(title, !on))}
                    className={`relative mt-1 h-8 w-14 shrink-0 rounded-full transition ${on ? "bg-primary" : "bg-primary/25"}`}
                  >
                    <span
                      className={`absolute top-1 h-6 w-6 rounded-full bg-white shadow transition-all ${on ? "left-7" : "left-1"}`}
                    />
                  </button>
                </li>
              );
            })}
          </ul>
          {prefs.preferences.marketing === false ? <p className="mt-3 text-xs text-primary/70">{c.casl}</p> : null}

          <button
            type="button"
            disabled={busy || (!prefs.preferences.reorder && !prefs.preferences.marketing)}
            onClick={() => void run(() => unsubscribeAll(token), c.unsubDone)}
            data-testid="unsubscribe-all"
            className="mt-6 w-full rounded-2xl border border-primary/20 bg-white px-5 py-4 text-base font-bold text-primary disabled:opacity-50"
          >
            {c.unsubAll}
          </button>

          <div className="mt-10 border-t border-primary/10 pt-8">
            <h2 className="text-xl font-bold text-primary">{c.dataTitle}</h2>
            <p className="mt-2 text-sm text-primary/75">
              {c.dataBody1}{" "}
              <a href={prefs.portal_url} className="font-semibold underline underline-offset-4">
                {c.account}
              </a>{" "}
              {c.dataBody2}{" "}
              <Link href="/privacy" className="font-semibold underline underline-offset-4">
                {c.policy}
              </Link>
              .
            </p>
            {prefs.deletion_requested ? (
              <p className="mt-4 rounded-2xl bg-primary/5 px-4 py-3 text-sm text-primary" role="status">
                {c.requested}
              </p>
            ) : confirmDelete ? (
              <div className="mt-4 rounded-3xl border border-red-200 bg-red-50 p-5">
                <p className="font-bold text-red-900">{c.deleteQ}</p>
                <p className="mt-1 text-sm text-red-900/85">{c.deleteSub}</p>
                <div className="mt-4 flex gap-3">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void deleteData()}
                    data-testid="delete-confirm"
                    className="rounded-2xl bg-red-700 px-5 py-3 text-sm font-bold text-white disabled:opacity-60"
                  >
                    {c.yesDelete}
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirmDelete(false)}
                    className="rounded-2xl border border-red-200 bg-white px-5 py-3 text-sm font-bold text-red-900"
                  >
                    {c.keep}
                  </button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setConfirmDelete(true)}
                data-testid="delete-start"
                className="mt-4 text-sm font-semibold text-red-800 underline underline-offset-4"
              >
                {c.requestDelete}
              </button>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}
