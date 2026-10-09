import { COVERAGE_FSA_COUNT } from "@/lib/seo/delivery-programmatic";

/**
 * The one buyer FAQ (Oct 2026): ten questions, answer first, one or two sentences, one link.
 * Used by /faq (full + filter), /business and the home page (first six). FAQPage schema is
 * built from the same text, so what Google reads is what visitors read.
 */
export type CoreFaqGroup = "price" | "coverage" | "service" | "trust";
export type CoreFaq = {
  id: string;
  group: CoreFaqGroup;
  question: string;
  answer: string;
  link: { href: string; label: string };
};

type L = "en" | "fr";

export const CORE_FAQ_GROUPS: Record<L, Record<CoreFaqGroup, string>> = {
  en: {
    price: "Price & booking",
    coverage: "Coverage & timing",
    service: "Service",
    trust: "Proof, insurance & claims",
  },
  fr: {
    price: "Prix et réservation",
    coverage: "Couverture et horaires",
    service: "Service",
    trust: "Preuve, assurance et réclamations",
  },
};

const EN: CoreFaq[] = [
  {
    id: "price",
    group: "price",
    question: "How much does a delivery cost?",
    answer:
      "Enter two postal codes and a vehicle: the calculator shows the exact price with HST in seconds, no sign-up. It is the same engine we bill from.",
    link: { href: "/delivery-cost-calculator", label: "Get a price" },
  },
  {
    id: "start",
    group: "price",
    question: "How do I start?",
    answer:
      "Get a price and book it online in a few minutes. For regular volume, open a free business account; there is no contract or minimum.",
    link: { href: "/sign-up?intent=merchant&from=faq", label: "Open a business account" },
  },
  {
    id: "payment",
    group: "price",
    question: "How do I pay?",
    answer: "Pay by card when you book. Business accounts can apply for monthly invoicing.",
    link: { href: "/business", label: "Business accounts" },
  },
  {
    id: "coverage",
    group: "coverage",
    question: "Where do you deliver?",
    answer: `Same day across ${COVERAGE_FSA_COUNT} postal areas of the Greater Toronto Area, from Hamilton to Oshawa and north to Newmarket.`,
    link: { href: "/service-areas", label: "See service areas" },
  },
  {
    id: "cutoff",
    group: "coverage",
    question: "What is the same-day cut-off?",
    answer:
      "Order by 11 AM and it is delivered between 2 and 9 PM the same day, Monday to Saturday. Later orders go out the next operating day.",
    link: { href: "/delivery", label: "How same-day works" },
  },
  {
    id: "vehicles",
    group: "service",
    question: "Which vehicles can I book?",
    answer:
      "Sedan or SUV for parcels, cargo van for cartons and small pallets, 16 ft box truck for pallets and bulky freight. The calculator suggests the right one.",
    link: { href: "/vehicles", label: "Compare vehicles" },
  },
  {
    id: "shopify",
    group: "service",
    question: "Does it work with Shopify?",
    answer:
      "Yes. The PorterChain Shopify app adds a same-day rate at checkout and books the delivery when the order is paid.",
    link: { href: "/delivery/shopify-merchants", label: "Shopify delivery" },
  },
  {
    id: "pod",
    group: "trust",
    question: "Do I get tracking and proof of delivery?",
    answer:
      "Every delivery has a live tracking link for you and your receiver, and photo proof at drop-off. Signature or ID check is available when you need it.",
    link: { href: "/track", label: "Track a delivery" },
  },
  {
    id: "insurance",
    group: "trust",
    question: "Are deliveries insured?",
    answer: "Yes. Deliveries are insured, and we send a certificate of insurance on request.",
    link: { href: "/trust", label: "Trust center" },
  },
  {
    id: "claims",
    group: "trust",
    question: "What if something is damaged or missing?",
    answer:
      "Tell us with the tracking number and photos; we review it against the pickup and drop-off proof and reply within one business day.",
    link: { href: "/trust/claims", label: "Claims process" },
  },
];

const FR: CoreFaq[] = [
  {
    id: "price",
    group: "price",
    question: "Combien coûte une livraison?",
    answer:
      "Entrez deux codes postaux et un véhicule : le calculateur affiche le prix exact, TVH incluse, en quelques secondes, sans inscription.",
    link: { href: "/delivery-cost-calculator", label: "Obtenir un prix" },
  },
  {
    id: "start",
    group: "price",
    question: "Comment commencer?",
    answer:
      "Obtenez un prix et réservez en ligne en quelques minutes. Pour un volume régulier, ouvrez un compte entreprise gratuit, sans contrat ni minimum.",
    link: { href: "/sign-up?intent=merchant&from=faq", label: "Ouvrir un compte entreprise" },
  },
  {
    id: "payment",
    group: "price",
    question: "Comment payer?",
    answer:
      "Par carte à la réservation. Les comptes entreprise peuvent demander la facturation mensuelle.",
    link: { href: "/business", label: "Comptes entreprise" },
  },
  {
    id: "coverage",
    group: "coverage",
    question: "Où livrez-vous?",
    answer: `Le jour même dans ${COVERAGE_FSA_COUNT} zones postales du Grand Toronto, de Hamilton à Oshawa et jusqu'à Newmarket au nord.`,
    link: { href: "/service-areas", label: "Zones desservies" },
  },
  {
    id: "cutoff",
    group: "coverage",
    question: "Quelle est l'heure limite le jour même?",
    answer:
      "Commandez avant 11 h pour une livraison entre 14 h et 21 h le jour même, du lundi au samedi. Les commandes plus tardives partent le jour ouvrable suivant.",
    link: { href: "/delivery", label: "Livraison le jour même" },
  },
  {
    id: "vehicles",
    group: "service",
    question: "Quels véhicules puis-je réserver?",
    answer:
      "Berline ou VUS pour les colis, fourgon pour les cartons et petites palettes, camion de 16 pi pour les palettes et le volumineux.",
    link: { href: "/vehicles", label: "Comparer les véhicules" },
  },
  {
    id: "shopify",
    group: "service",
    question: "Est-ce compatible avec Shopify?",
    answer:
      "Oui. L'application Shopify de PorterChain ajoute un tarif le jour même au paiement et réserve la livraison une fois la commande payée.",
    link: { href: "/delivery/shopify-merchants", label: "Livraison Shopify" },
  },
  {
    id: "pod",
    group: "trust",
    question: "Ai-je le suivi et une preuve de livraison?",
    answer:
      "Chaque livraison a un lien de suivi en direct et une photo à la livraison. Signature ou vérification d'identité sur demande.",
    link: { href: "/track", label: "Suivre une livraison" },
  },
  {
    id: "insurance",
    group: "trust",
    question: "Les livraisons sont-elles assurées?",
    answer:
      "Oui. Les livraisons sont assurées et nous envoyons un certificat d'assurance sur demande.",
    link: { href: "/trust", label: "Centre de confiance" },
  },
  {
    id: "claims",
    group: "trust",
    question: "Et si un article est endommagé ou manquant?",
    answer:
      "Écrivez-nous avec le numéro de suivi et des photos; nous comparons avec les preuves de ramassage et de livraison et répondons en un jour ouvrable.",
    link: { href: "/trust/claims", label: "Réclamations" },
  },
];

export function coreFaq(locale: string): CoreFaq[] {
  return locale === "fr" ? FR : EN;
}
