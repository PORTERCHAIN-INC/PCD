import { getLocale } from "next-intl/server";
import { ArrowRight } from "lucide-react";
import { Link } from "@/i18n/navigation";
import SiteShell from "@/components/layout/SiteShell";
import Container from "@/components/ui/Container";

const COPY = {
  en: {
    title: "This page moved or never existed.",
    body: "Here is where people usually want to go:",
    links: [
      {
        href: "/delivery-cost-calculator",
        label: "Get an instant price",
        note: "Two postal codes, exact price with HST",
      },
      { href: "/track", label: "Track a delivery", note: "Enter your tracking number" },
      {
        href: "/delivery",
        label: "Same-day delivery by industry",
        note: "Shopify, pharmacy, furniture, trades, warehouses",
      },
      { href: "/faq", label: "FAQ", note: "Price, coverage, cut-off, insurance, claims" },
      { href: "/contact", label: "Contact us", note: "Mon–Fri 8 AM–6 PM · Sat 9 AM–2 PM" },
    ],
  },
  fr: {
    title: "Cette page a été déplacée ou n'existe pas.",
    body: "Voici ce que les visiteurs cherchent le plus souvent :",
    links: [
      {
        href: "/delivery-cost-calculator",
        label: "Obtenir un prix",
        note: "Deux codes postaux, prix exact avec TVH",
      },
      { href: "/track", label: "Suivre une livraison", note: "Entrez votre numéro de suivi" },
      {
        href: "/delivery",
        label: "Livraison le jour même par secteur",
        note: "Shopify, pharmacie, meubles, métiers, entrepôts",
      },
      { href: "/faq", label: "FAQ", note: "Prix, couverture, heure limite, assurance" },
      { href: "/contact", label: "Nous joindre", note: "Lun–ven 8 h–18 h · sam 9 h–14 h" },
    ],
  },
};

export default async function NotFound() {
  const locale = await getLocale();
  const c = COPY[locale === "fr" ? "fr" : "en"];
  return (
    <SiteShell>
      <section className="bg-white">
        <Container size="narrow" className="pb-16 pt-[calc(var(--nav-height)+3rem)] sm:pb-24">
          <p className="text-sm font-semibold text-muted">404</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-primary sm:text-4xl">
            {c.title}
          </h1>
          <p className="mt-3 text-lg text-muted">{c.body}</p>
          <ul className="mt-8 divide-y divide-primary/10 border-y border-primary/10">
            {c.links.map((l) => (
              <li key={l.href}>
                <Link
                  href={l.href}
                  className="group flex min-h-14 items-center justify-between gap-4 py-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary"
                >
                  <span>
                    <span className="block font-semibold text-primary">{l.label}</span>
                    <span className="block text-sm text-muted">{l.note}</span>
                  </span>
                  <ArrowRight
                    className="h-4 w-4 shrink-0 text-secondary transition-transform motion-safe:group-hover:translate-x-1"
                    aria-hidden
                  />
                </Link>
              </li>
            ))}
          </ul>
        </Container>
      </section>
    </SiteShell>
  );
}
