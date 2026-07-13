"use client";

import { useState } from "react";
import { extractFsa } from "@/lib/traffic/postal";
import { resolveZoneByFsa } from "@/lib/traffic/zones";
import type { Locale } from "@/i18n/routing";
import { quoteContact } from "@/lib/seo/routes";

type Props = {
  locale: Locale;
  cityLabel?: string;
  trackSource: string;
};

const COPY = {
  en: {
    title: "Check delivery coverage",
    placeholder: "Postal code (e.g. M5H 2N2)",
    submit: "Check",
    inZone: (zone: string) =>
      `We run B2B routes in ${zone} and surrounding areas. Request a quote to confirm capacity for your lanes.`,
    ontarioMaybe:
      "This postal code may be in our extended Ontario network — share your lanes on a quote and we confirm within one business day.",
    unknown:
      "Share your full routes on a quote — we confirm GTA and Ontario coverage within one business day.",
    cta: "Get a quote",
  },
  fr: {
    title: "Vérifier la couverture",
    placeholder: "Code postal (ex. M5H 2N2)",
    submit: "Vérifier",
    inZone: (zone: string) =>
      `Nous exécutons des routes B2B à ${zone} et environs. Obtenez un devis pour confirmer la capacité sur vos trajets.`,
    ontarioMaybe:
      "Ce code postal peut être dans notre réseau ontarien élargi — partagez vos trajets via un devis; confirmation en un jour ouvrable.",
    unknown:
      "Partagez vos trajets complets via un devis — nous confirmons la couverture RGT et Ontario en un jour ouvrable.",
    cta: "Obtenir un devis",
  },
} as const;

function isOntarioFsa(fsa: string): boolean {
  const first = fsa.charAt(0);
  return first === "M" || first === "L" || first === "N" || first === "K";
}

export default function PostalCoverageChecker({ locale, cityLabel, trackSource }: Props) {
  const [input, setInput] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const t = COPY[locale === "fr" ? "fr" : "en"];
  const quoteHref = quoteContact(locale, trackSource);

  function handleCheck(e: React.FormEvent) {
    e.preventDefault();
    const fsa = extractFsa(input);
    if (!fsa) {
      setMessage(t.unknown);
      return;
    }
    const zone = resolveZoneByFsa(fsa);
    if (zone) {
      setMessage(t.inZone(cityLabel ? `${zone.name} (${cityLabel})` : zone.name));
      return;
    }
    setMessage(isOntarioFsa(fsa) ? t.ontarioMaybe : t.unknown);
  }

  return (
    <section className="site-section bg-gray-bg">
      <div className="site-container max-w-xl mx-auto px-4">
        <h2 className="text-xl font-semibold text-primary tracking-tight">{t.title}</h2>
        <form onSubmit={handleCheck} className="mt-4 flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={t.placeholder}
            className="flex-1 rounded-md border border-primary/15 px-3 py-2 text-primary"
            aria-label={t.placeholder}
          />
          <button
            type="submit"
            className="rounded-md bg-primary px-4 py-2 text-white font-medium hover:opacity-90"
          >
            {t.submit}
          </button>
        </form>
        {message && (
          <p className="mt-4 text-muted leading-relaxed">
            {message}{" "}
            <a href={quoteHref} className="text-primary font-medium underline">
              {t.cta}
            </a>
          </p>
        )}
      </div>
    </section>
  );
}
