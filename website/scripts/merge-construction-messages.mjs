#!/usr/bin/env node
/**
 * One-shot merge: construction niche + campaign copy into en.json / fr.json
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const messagesDir = path.join(__dirname, "../messages");

const nicheBlockEn = {
  constructionMaterials: {
    meta: {
      title: "Construction material delivery | Jobsite & distributor routes Ontario",
      description:
        "Porterchain delivers construction materials across the GTA and Ontario. Lumber, drywall, steel, and building supply — recurring jobsite routes, pallet delivery, proof of delivery, vans and box trucks.",
    },
    hero: {
      title: "Delivery built for construction materials",
      subtitle:
        "Your logistics partner for building supply distributors and jobsite delivery. We run recurring routes with vans, pickups, and box trucks — predictable capacity, live tracking, and proof of delivery on every drop.",
    },
    painPoints: {
      title: "Delivery challenges for construction supply",
      item1: "Getting materials to job sites on time without owning fleet or juggling couriers",
      item2: "Scaling pallet and bulk delivery as distributor volume and sites grow",
      item3: "Site teams and contractors expect visibility, POD, and reliable time windows",
    },
    solution: {
      title: "Porterchain for construction materials",
      description:
        "One partner for distributor runs and jobsite delivery across Ontario. Local drivers, vehicles matched to pallet weight and site access, and full tracking from warehouse to site.",
      bullet1: "Scheduled and same-day routes for distributors, yards, and job sites",
      bullet2: "Pickups, cargo vans, and 16 ft box trucks for materials and pallet freight",
      bullet3: "Photo proof, signatures, and tracking links for every shipment",
    },
    vehicleFit: {
      title: "Vehicle fit for construction delivery",
      description:
        "Pickups and vans for smaller runs and tight sites; 16 ft box trucks for palletized lumber, drywall, and bulk materials. We match capacity to weight, dimensions, and access.",
    },
    workflow: {
      title: "How construction delivery works",
      description: "From your yard or warehouse to the job site — predictable ops end to end.",
      step1Title: "You share routes and site details",
      step1Description:
        "Tell us your recurring stops, jobsite zones, time windows, and any access notes. We align vehicles and capacity.",
      step2Title: "We pick up and deliver",
      step2Description:
        "Our drivers complete the route with tracking on every stop. Site contacts get ETA and status updates.",
      step3Title: "You and your sites stay informed",
      step3Description:
        "Proof of delivery, reporting, and live status in one dashboard — no chasing drivers for updates.",
    },
    coverage: {
      title: "Ontario coverage for construction delivery",
      description:
        "GTA, Toronto, Mississauga, Brampton, Vaughan, Hamilton, Kitchener-Waterloo, London, Niagara, and expanding regions — same reliability in every zone.",
    },
    onboarding: {
      title: "Simple onboarding for distributors and contractors",
      description: "Get set up for jobsite delivery without building an in-house fleet.",
      step1Title: "Connect",
      step1Description:
        "Share volume, service areas, and typical materials. We align capacity and SLAs.",
      step2Title: "We deliver",
      step2Description:
        "Drivers run your routes with live tracking and proof of delivery on every stop.",
      step3Title: "You stay in control",
      step3Description:
        "Track every shipment, see ETAs, and get clear reporting for ops and billing.",
    },
    faq: {
      title: "Frequently asked questions — construction delivery",
      q1: "Do you deliver to job sites and trade customers?",
      a1: "Yes. We deliver to job sites, contractors, and trade accounts from distributors and yards. Share zones and access requirements and we'll confirm coverage.",
      q2: "What vehicles do you use for building materials?",
      a2: "Pickups and vans for smaller loads; 16 ft box trucks for palletized freight. We match the vehicle to your materials and site access.",
      q3: "Do you provide proof of delivery?",
      a3: "Every shipment includes photo proof, signatures where needed, and a shareable tracking link with real-time status.",
    },
    cta: {
      title: "Ready for reliable construction material delivery?",
      description:
        "Tell us your routes and volume. We'll show you how we run jobsite and distributor delivery — simply and reliably.",
      primary: "Talk to us",
      secondary: "Contact us",
    },
    inquiryHeading: "Get started with construction material delivery",
    inquirySubheadline:
      "A few details and we'll match capacity and vehicles to your distributor or jobsite routes.",
  },
  electricalDistribution: {
    meta: {
      title: "Electrical distributor delivery | Wholesale & contractor routes Ontario",
      description:
        "Porterchain delivers for electrical wholesalers and distributors across Ontario. Wire, panel, and equipment runs — same-day and recurring routes with tracking and proof of delivery.",
    },
    hero: {
      title: "Delivery built for electrical distribution",
      subtitle:
        "Your last-mile partner for electrical wholesalers. Recurring routes to contractors and job sites, same-day cutoffs when it matters, and tracking on every shipment.",
    },
    painPoints: {
      title: "Delivery needs for electrical distributors",
      item1: "Hitting contractor cut-offs and job-site windows without ad-hoc couriers",
      item2: "Scaling delivery volume across the GTA without adding fleet or dispatch staff",
      item3: "Trade customers expect tracking, ETAs, and proof on every run",
    },
    solution: {
      title: "Porterchain for electrical wholesalers",
      description:
        "One partner for counter, contractor, and jobsite delivery. Local drivers, flexible vehicles, and a single dashboard for ops and customer visibility.",
      bullet1: "Recurring routes and same-day capacity for wire, panel, and equipment",
      bullet2: "Cars, vans, and trucks sized for your typical electrical freight",
      bullet3: "Live tracking and proof of delivery for contractors and inside sales",
    },
    vehicleFit: {
      title: "Vehicle fit for electrical supply",
      description:
        "Cars and vans for counter and small contractor runs; larger vans and trucks for palletized stock and bulk wire. Matched to your product mix and routes.",
    },
    workflow: {
      title: "Typical delivery workflow for electrical distributors",
      description: "From your warehouse to contractors and sites — reliable and trackable.",
      step1Title: "You share volume and cut-offs",
      step1Description:
        "Routes, zones, same-day cut-off times, and account types. We align capacity to your dispatch pattern.",
      step2Title: "We pick up and deliver",
      step2Description:
        "Drivers complete runs with tracking links per shipment. Contractors see status and ETA.",
      step3Title: "Your team stays in the loop",
      step3Description:
        "Inside sales and ops get live status, POD, and reporting without chasing drivers.",
    },
    coverage: {
      title: "Service areas for electrical delivery",
      description:
        "GTA, Hamilton, Kitchener-Waterloo, London, Niagara, and Ontario regions — consistent local ops for wholesale delivery.",
    },
    onboarding: {
      title: "Onboarding for electrical wholesalers",
      description: "Live in days, not weeks — without building your own delivery fleet.",
      step1Title: "Connect",
      step1Description: "Share routes, cut-offs, and service areas. We align drivers and vehicles.",
      step2Title: "We deliver",
      step2Description: "Recurring and same-day runs with tracking and proof on every stop.",
      step3Title: "You scale with confidence",
      step3Description: "Add volume and zones as you grow — one partner, one dashboard.",
    },
    faq: {
      title: "Frequently asked questions — electrical delivery",
      q1: "Do you work with electrical wholesalers and distributors?",
      a1: "Yes. We run recurring and same-day delivery for electrical supply houses and distributors across our Ontario service areas.",
      q2: "Can you meet same-day cut-offs?",
      a2: "Same-day is available subject to cut-off times and capacity. We confirm windows when we set up your account.",
      q3: "How do contractors track deliveries?",
      a3: "Every shipment has a tracking link with live status and ETA — share it with contractors or site contacts.",
    },
    cta: {
      title: "Ready to run electrical distribution delivery with us?",
      description:
        "Share your routes and volume. We'll show you how Porterchain fits your wholesale delivery operation.",
      primary: "Talk to us",
      secondary: "Contact us",
    },
    inquiryHeading: "Get started with electrical distributor delivery",
    inquirySubheadline:
      "Tell us about your routes and we'll match capacity for your wholesale delivery.",
  },
  plumbingSupply: {
    meta: {
      title: "Plumbing supply delivery | Wholesaler & contractor routes Ontario",
      description:
        "Porterchain delivers for plumbing wholesalers across Ontario. Pipe, fixtures, and supply runs — recurring routes, same-day capacity, tracking and proof of delivery.",
    },
    hero: {
      title: "Delivery built for plumbing supply",
      subtitle:
        "Your logistics partner for plumbing wholesalers and supply houses. Recurring contractor routes, same-day runs when needed, and full visibility on every delivery.",
    },
    painPoints: {
      title: "Delivery challenges for plumbing supply",
      item1: "Reliable delivery to contractors without managing your own drivers",
      item2: "Handling pipe, fixtures, and pallet stock with the right vehicles",
      item3: "Customers expect tracking and on-time delivery to job sites and shops",
    },
    solution: {
      title: "Porterchain for plumbing wholesalers",
      description:
        "One partner for trade delivery across your service area. Vans and trucks for pipe and fixtures, recurring routes aligned to your dispatch rhythm.",
      bullet1: "Recurring routes to contractors, renovators, and commercial accounts",
      bullet2: "Vans and box trucks for pipe, fixtures, and palletized inventory",
      bullet3: "Tracking and proof of delivery on every stop",
    },
    vehicleFit: {
      title: "Vehicle fit for plumbing supply",
      description:
        "Cargo vans for pipe and fixture runs; box trucks for palletized stock and larger orders. Sized for your typical wholesale freight.",
    },
    workflow: {
      title: "How plumbing supply delivery works",
      description: "From your warehouse to contractors — simple and predictable.",
      step1Title: "You share routes and volume",
      step1Description:
        "Stops per day, zones, time windows, and product types. We align vehicles and drivers.",
      step2Title: "We pick up and deliver",
      step2Description:
        "Drivers complete routes with tracking per shipment. Contractors get ETA updates.",
      step3Title: "You keep visibility",
      step3Description: "Ops and counter staff see live status, POD, and clear reporting.",
    },
    coverage: {
      title: "Ontario coverage for plumbing delivery",
      description:
        "GTA, Hamilton, Kitchener-Waterloo, and surrounding regions — local ops for wholesale plumbing supply.",
    },
    onboarding: {
      title: "Onboarding for plumbing wholesalers",
      description: "Start delivering with Porterchain in days — no fleet to build.",
      step1Title: "Connect",
      step1Description: "Share your routes, volume, and service areas.",
      step2Title: "We deliver",
      step2Description: "Recurring and on-demand runs with full tracking.",
      step3Title: "You grow",
      step3Description: "Scale routes and zones with one logistics partner.",
    },
    faq: {
      title: "Frequently asked questions — plumbing supply delivery",
      q1: "Do you deliver for plumbing wholesalers?",
      a1: "Yes. We support plumbing supply houses with recurring and same-day delivery to contractors and trade accounts.",
      q2: "Can you handle pipe and long stock?",
      a2: "We use vans and trucks suited to your freight. Share dimensions and weight for specialty runs.",
      q3: "Do you offer proof of delivery?",
      a3: "Yes — photo proof, signatures, and tracking links on every shipment.",
    },
    cta: {
      title: "Ready for reliable plumbing supply delivery?",
      description:
        "Tell us your routes and volume. We'll show you how we can run your wholesale delivery.",
      primary: "Talk to us",
      secondary: "Contact us",
    },
    inquiryHeading: "Get started with plumbing supply delivery",
    inquirySubheadline:
      "Share your delivery patterns and we'll align capacity for your wholesale routes.",
  },
};

const nicheBlockFr = {
  constructionMaterials: nicheBlockEn.constructionMaterials,
  electricalDistribution: nicheBlockEn.electricalDistribution,
  plumbingSupply: nicheBlockEn.plumbingSupply,
};

// French overrides for key customer-facing strings
Object.assign(nicheBlockFr.constructionMaterials, {
  meta: {
    title: "Livraison de matériaux de construction | Tournées chantier et distributeurs Ontario",
    description:
      "Porterchain livre les matériaux de construction dans le RGT et l'Ontario. Bois, gypse, acier et fournitures — tournées récurrentes, palettes, preuve de livraison.",
  },
  hero: {
    title: "Livraison pour matériaux de construction",
    subtitle:
      "Votre partenaire logistique pour distributeurs de construction et livraison chantier. Fourgonnettes, camionnettes et camions — capacité prévisible et suivi en direct.",
  },
  painPoints: {
    title: "Défis de livraison pour la construction",
    item1: "Livrer les chantiers à l'heure sans flotte ni coursiers multiples",
    item2: "Augmenter les livraisons palettes et volumes sans ajouter de véhicules",
    item3: "Les équipes chantier exigent visibilité, POD et créneaux fiables",
  },
  cta: {
    title: "Prêt pour une livraison fiable de matériaux de construction?",
    description:
      "Décrivez vos trajets et volumes. Nous gérons la livraison chantier et distributeur.",
    primary: "Nous joindre",
    secondary: "Contactez-nous",
  },
});

Object.assign(nicheBlockFr.electricalDistribution, {
  meta: {
    title: "Livraison distributeur électrique | Tournées grossiste et entrepreneurs Ontario",
    description:
      "Porterchain livre pour les grossistes électriques en Ontario. Fil, panneaux et équipement — même jour et récurrent, suivi et preuve de livraison.",
  },
  hero: {
    title: "Livraison pour distribution électrique",
    subtitle:
      "Partenaire dernier kilomètre pour grossistes électriques. Tournées récurrentes vers entrepreneurs et chantiers, avec suivi sur chaque envoi.",
  },
  cta: {
    title: "Prêt pour la livraison distribution électrique?",
    description: "Partagez vos trajets. Nous adaptons la capacité à votre opération grossiste.",
    primary: "Nous joindre",
    secondary: "Contactez-nous",
  },
});

Object.assign(nicheBlockFr.plumbingSupply, {
  meta: {
    title: "Livraison fournitures plomberie | Grossiste et entrepreneurs Ontario",
    description:
      "Porterchain livre pour les grossistes en plomberie en Ontario. Tuyaux, fixtures et stock — tournées récurrentes et suivi complet.",
  },
  hero: {
    title: "Livraison pour fournitures de plomberie",
    subtitle:
      "Partenaire logistique pour grossistes en plomberie. Tournées entrepreneurs, capacité même jour, visibilité complète.",
  },
  cta: {
    title: "Prêt pour la livraison fournitures plomberie?",
    description: "Décrivez vos trajets. Nous gérons votre livraison grossiste.",
    primary: "Nous joindre",
    secondary: "Contactez-nous",
  },
});

function mergeConstruction(locale, nicheBlock) {
  const file = path.join(messagesDir, `${locale}.json`);
  const data = JSON.parse(fs.readFileSync(file, "utf8"));

  data.nicheLanding = { ...nicheBlock, ...data.nicheLanding };

  const campaignKeys = ["constructionMaterials", "electricalDistribution", "plumbingSupply"];
  for (const key of campaignKeys) {
    data.campaignLanding[key] = { ...data.nicheLanding[key] };
  }

  data.cityIndustryDelivery.industryLabels = {
    constructionMaterials: locale === "fr" ? "Matériaux de construction" : "Construction materials",
    electricalDistribution: locale === "fr" ? "Distribution électrique" : "Electrical distribution",
    plumbingSupply: locale === "fr" ? "Fournitures plomberie" : "Plumbing supply",
    ...data.cityIndustryDelivery.industryLabels,
  };

  if (locale === "en") {
    data.metadata.description =
      "Construction material, electrical, and plumbing supply delivery across the GTA. Same-day and recurring routes, pallet freight, proof of delivery. Book online or talk to our business team.";
    data.metadata.ogDescription =
      "Jobsite and distributor delivery for construction, electrical, and plumbing across Ontario.";
    data.industries.title = "Built for construction & trades";
    data.industries.subtitle =
      "Material delivery for building supply, electrical distribution, and plumbing wholesalers — plus logistics for every sector we serve.";
    data.industries.items.plumbing = {
      name: "Plumbing",
      description: "Pipe, fixtures & supply delivery",
    };
  } else {
    data.metadata.description =
      "Livraison matériaux de construction, électrique et plomberie dans le RGT. Tournées récurrentes, palettes, preuve de livraison.";
    data.metadata.ogDescription =
      "Livraison chantier et distributeur pour construction, électrique et plomberie en Ontario.";
    data.industries.title = "Conçu pour la construction et les métiers";
    data.industries.subtitle =
      "Livraison pour distributeurs de construction, électrique et plomberie — et tous les secteurs que nous desservons.";
    data.industries.items.plumbing = {
      name: "Plomberie",
      description: "Tuyaux, fixtures et fournitures",
    };
  }

  fs.writeFileSync(file, `${JSON.stringify(data, null, 2)}\n`);
  console.log(`Updated ${file}`);
}

mergeConstruction("en", nicheBlockEn);
mergeConstruction("fr", nicheBlockFr);
