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
      "Enter two postal codes and a vehicle. You see the exact price, HST included, in about 10 seconds, before you share any details. It is the same engine we bill from.",
    link: { href: "/delivery-cost-calculator", label: "Get instant price" },
  },
  {
    id: "cutoff",
    group: "coverage",
    question: "Can you deliver today?",
    answer:
      "Yes. Book by 11 AM and it is delivered between 2 and 9 PM the same day, Monday to Saturday. Book later and it goes the next operating day, or pick a date.",
    link: { href: "/delivery", label: "How same-day works" },
  },
  {
    id: "coverage",
    group: "coverage",
    question: "Where do you deliver?",
    answer: `The GTA plus about 150 km: ${COVERAGE_FSA_COUNT} postal areas, from Hamilton to Oshawa and north to Newmarket. Our core areas are Vaughan, Concord, Brampton and Mississauga. The calculator confirms your postal codes instantly.`,
    link: { href: "/service-areas", label: "See service areas" },
  },
  {
    id: "vehicles",
    group: "service",
    question: "Which vehicle do I need?",
    answer:
      "Sedan or SUV up to about 80 kg, cargo van up to about 900 kg, 16 ft box truck up to about 3,000 kg. All are driven on a standard Ontario G licence. The calculator suggests one.",
    link: { href: "/vehicles", label: "Compare vehicles" },
  },
  {
    id: "insurance",
    group: "trust",
    question: "What if something is lost or damaged?",
    answer:
      "Every parcel includes $2,500 coverage. Shipping something valuable? Add $25,000 coverage for $10. Report it with the tracking number and photos; we reply within one business day.",
    link: { href: "/trust/claims", label: "Claims process" },
  },
  {
    id: "payment",
    group: "price",
    question: "How do I pay?",
    answer:
      "Businesses with a merchant account pay by Interac e-Transfer for each billing cycle. Customers pay by card when they book, processed by Stripe; we never store card numbers.",
    link: { href: "/business", label: "Business accounts" },
  },
  {
    id: "start",
    group: "price",
    question: "Do I need a contract?",
    answer:
      "No contract and no minimum. Price it, book it online in about a minute, and open a free business account when you have regular volume.",
    link: { href: "/sign-up?intent=merchant&from=faq", label: "Open a business account" },
  },
  {
    id: "pod",
    group: "trust",
    question: "Do I get tracking and proof of delivery?",
    answer:
      "Every delivery has a live tracking link for you and your receiver, and photo proof at drop-off. Receivers see the driver's first name only.",
    link: { href: "/track", label: "Track a delivery" },
  },
  {
    id: "medical",
    group: "service",
    question: "Can you carry medical deliveries that must stay cool?",
    answer:
      "Yes. For medical deliveries that need to stay cool we use coolers. We do not run refrigerated vehicles.",
    link: { href: "/delivery/pharmacy", label: "Medical & pharmacy delivery" },
  },
  {
    id: "shopify",
    group: "service",
    question: "Do you work with Shopify?",
    answer:
      "Our Shopify app is in review with Shopify. When it is live it will add a same-day rate at checkout. Until then, book Shopify orders online in about a minute.",
    link: { href: "/delivery/shopify-merchants", label: "Shopify delivery" },
  },
];

const FR: CoreFaq[] = [
  {
    id: "price",
    group: "price",
    question: "Combien coûte une livraison?",
    answer:
      "Entrez deux codes postaux et un véhicule. Vous voyez le prix exact, TVH incluse, en environ 10 secondes, sans donner vos coordonnées. C'est le même moteur que notre facturation.",
    link: { href: "/delivery-cost-calculator", label: "Obtenir un prix instantané" },
  },
  {
    id: "cutoff",
    group: "coverage",
    question: "Pouvez-vous livrer aujourd'hui?",
    answer:
      "Oui. Réservez avant 11 h et c'est livré entre 14 h et 21 h le jour même, du lundi au samedi. Plus tard, la livraison part le jour ouvrable suivant, ou à la date choisie.",
    link: { href: "/delivery", label: "Livraison le jour même" },
  },
  {
    id: "coverage",
    group: "coverage",
    question: "Où livrez-vous?",
    answer: `Le Grand Toronto et environ 150 km autour : ${COVERAGE_FSA_COUNT} zones postales, de Hamilton à Oshawa et jusqu'à Newmarket au nord. Nos zones principales : Vaughan, Concord, Brampton et Mississauga. Le calculateur confirme vos codes postaux instantanément.`,
    link: { href: "/service-areas", label: "Zones desservies" },
  },
  {
    id: "vehicles",
    group: "service",
    question: "Quel véhicule me faut-il?",
    answer:
      "Berline ou VUS jusqu'à environ 80 kg, fourgon jusqu'à environ 900 kg, camion de 16 pi jusqu'à environ 3 000 kg. Tous conduits avec un permis G standard de l'Ontario.",
    link: { href: "/vehicles", label: "Comparer les véhicules" },
  },
  {
    id: "insurance",
    group: "trust",
    question: "Et si un colis est perdu ou endommagé?",
    answer:
      "Chaque colis inclut une couverture de 2 500 $. Pour un envoi de valeur, ajoutez une couverture de 25 000 $ pour 10 $. Écrivez-nous avec le numéro de suivi et des photos; réponse en un jour ouvrable.",
    link: { href: "/trust/claims", label: "Réclamations" },
  },
  {
    id: "payment",
    group: "price",
    question: "Comment payer?",
    answer:
      "Les entreprises avec un compte marchand paient par virement Interac pour chaque cycle de facturation. Les clients paient par carte à la réservation, via Stripe; nous ne conservons jamais les numéros de carte.",
    link: { href: "/business", label: "Comptes entreprise" },
  },
  {
    id: "start",
    group: "price",
    question: "Faut-il un contrat?",
    answer:
      "Aucun contrat ni minimum. Obtenez un prix, réservez en ligne en environ une minute et ouvrez un compte entreprise gratuit quand votre volume devient régulier.",
    link: { href: "/sign-up?intent=merchant&from=faq", label: "Ouvrir un compte entreprise" },
  },
  {
    id: "pod",
    group: "trust",
    question: "Ai-je le suivi et une preuve de livraison?",
    answer:
      "Chaque livraison a un lien de suivi en direct pour vous et votre destinataire, et une photo à la livraison. Le destinataire ne voit que le prénom du chauffeur.",
    link: { href: "/track", label: "Suivre une livraison" },
  },
  {
    id: "medical",
    group: "service",
    question: "Transportez-vous des livraisons médicales à garder au frais?",
    answer:
      "Oui. Pour les livraisons médicales à garder au frais, nous utilisons des glacières. Nous n'avons pas de véhicules réfrigérés.",
    link: { href: "/delivery/pharmacy", label: "Livraison médicale et pharmacie" },
  },
  {
    id: "shopify",
    group: "service",
    question: "Travaillez-vous avec Shopify?",
    answer:
      "Notre application Shopify est en cours d'examen par Shopify. Une fois en ligne, elle ajoutera un tarif le jour même au paiement. D'ici là, réservez vos commandes Shopify en ligne en environ une minute.",
    link: { href: "/delivery/shopify-merchants", label: "Livraison Shopify" },
  },
];

export function coreFaq(locale: string): CoreFaq[] {
  return locale === "fr" ? FR : EN;
}
