#!/usr/bin/env node
/**
 * Patches construction niche landing copy (personas + expanded FAQ) in en.json and fr.json.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const enPath = join(root, "messages/en.json");
const frPath = join(root, "messages/fr.json");

const en = JSON.parse(readFileSync(enPath, "utf8"));
const fr = JSON.parse(readFileSync(frPath, "utf8"));

const personaBlock = (items) => ({
  label: items.label,
  title: items.title,
  subtitle: items.subtitle,
  trustLinkLabel: items.trustLinkLabel,
  items: items.personas,
});

en.nicheLanding.constructionMaterials = {
  ...en.nicheLanding.constructionMaterials,
  meta: {
    title: "Construction material delivery GTA | Jobsite delivery for contractors & distributors",
    description:
      "Jobsite and distributor delivery for building supply, contractors, project managers, and supers in the GTA. Same-day urgent runs, pallet freight, foreman windows, and photo proof on every stop.",
  },
  hero: {
    title: "Construction material delivery in the GTA",
    subtitle:
      "For building supply distributors, general contractors, project managers, and site supers — same-day urgent, recurring yard-to-jobsite routes, and fleet overflow with timed windows, site access coordination, and proof on every drop.",
  },
  personas: personaBlock({
    label: "Who this is for",
    title: "Built for construction vendors, contractors, and site teams",
    subtitle:
      "Whether you run the yard, the jobsite schedule, or procurement review — PorterChain moves building materials with capacity you can trust.",
    trustLinkLabel: "Trust & documentation for procurement",
    personas: {
      vendor: {
        title: "Building supply vendors & distributors",
        description:
          "Counter-to-jobsite runs when your drivers are full, afternoon cut-offs slip, or peak season needs backup trucks — without hiring W-2 drivers. Photo proof tied to ticket or PO for your AR team.",
      },
      contractor: {
        title: "General contractors & trade contractors",
        description:
          "When the supplier truck no-shows or sends the wrong vehicle, your crew still has a pour, inspection, or rough-in tomorrow. Timed jobsite windows, gate and access notes, pickup through box truck matched to site constraints.",
      },
      projectManager: {
        title: "Project managers & site supers",
        description:
          "Your schedule assumes material lands before the next trade. ETA visibility without chasing drivers, photo proof with timestamps you can forward to the owner, and escalation when a same-day run is critical.",
      },
      operations: {
        title: "Operations & logistics managers",
        description:
          "Overflow and backup capacity without fleet capex. Multi-stop distributor routes across Peel, York, and Toronto — one partner for same-day urgent and recurring lanes, not a new courier every crisis.",
      },
      tradePartner: {
        title: "Electrical & plumbing trade partners",
        description:
          "Warehouse-to-jobsite and counter-to-contractor delivery for lumber, drywall, steel, and palletized building materials — coordinated with electrical and plumbing rough-in schedules.",
      },
      architect: {
        title: "Architects & design firms",
        description:
          "When specified millwork, fixtures, or finish samples must land before inspection or owner walkthrough — timed delivery with documented proof for GC and supplier records.",
      },
      legalProcurement: {
        title: "Legal, procurement & finance",
        description:
          "Photo and signature proof with shipment reference, GPS-backed timestamps, commercial insurance and COI on request, and SLA or MSA exhibits for enterprise construction programs.",
      },
    },
  }),
  faq: {
    title: "Frequently asked questions — construction delivery",
    q1: "Can you run our counter-to-contractor routes when our drivers are full?",
    a1: "Yes. Fleet overflow and backup capacity are core services — we dispatch matched vehicle and driver capacity for distributor and yard routes, often same day.",
    q2: "Do you deliver lumber, drywall, steel, and palletized building materials to job sites?",
    a2: "Yes. Pickups, cargo vans, and 16 ft box trucks for palletized lumber, drywall, steel, and bulk materials — matched to weight, dimensions, and site access.",
    q3: "Do you deliver when our supplier cannot make today's jobsite window?",
    a3: "Yes. Emergency and same-day jobsite delivery when a supplier truck no-shows or your schedule shifts — share the site window and access notes and we confirm capacity.",
    q4: "Can the driver coordinate with our site super or foreman on approach?",
    a4: "Yes. Share site contact, gate instructions, and timed windows when you book. Drivers complete delivery with photo proof your super can use for schedule and billing records.",
    q5: "Do you handle tight downtown Toronto jobsite access?",
    a5: "We match vehicle class to site access — sedan through box truck — and plan routes across Toronto, Peel, and York. Share access constraints and we confirm fit before dispatch.",
    q6: "Is proof of delivery included for billing and disputes?",
    a6: "Every stop includes photo proof, digital signature where required, GPS-backed timestamps, and a shareable tracking link — documentation your finance and legal teams can attach to invoices.",
    q7: "What GTA areas do you serve for construction delivery?",
    a7: "Toronto, Mississauga, Brampton, Vaughan, Markham, Oakville, Hamilton, Kitchener–Waterloo, and expanding Ontario metros — same process for yard, counter, and jobsite stops.",
  },
  cta: {
    title: "Get a quote for your jobsite lanes",
    description:
      "Tell us your materials, urgency, and GTA service areas. Same-day, urgent, or recurring — we respond within one business day with vehicle fit and a written quote.",
    primary: "Get a quote",
    secondary: "Contact us",
  },
};

en.nicheLanding.electricalDistribution = {
  ...en.nicheLanding.electricalDistribution,
  meta: {
    title: "Electrical distributor delivery GTA | Contractor & jobsite routes",
    description:
      "Electrical wholesale delivery for distributors, contractors, project managers, and supers in the GTA. Same-day wire and panel runs, counter cut-offs, jobsite windows, and proof on every stop.",
  },
  hero: {
    title: "Electrical distribution delivery in the GTA",
    subtitle:
      "For electrical wholesalers, contractors, project managers, and site supers — recurring counter-to-jobsite routes, same-day wire and panel capacity, and fleet overflow with tracking and proof on every shipment.",
  },
  personas: personaBlock({
    label: "Who this is for",
    title: "Built for electrical wholesalers, contractors, and site teams",
    subtitle:
      "From the warehouse counter to the rough-in schedule — capacity that respects contractor cut-offs and jobsite windows.",
    trustLinkLabel: "Trust & documentation for procurement",
    personas: {
      vendor: {
        title: "Electrical wholesalers & distributors",
        description:
          "Recurring van and box truck routes when counter cut-offs stack up or your fleet is maxed. Inside sales gets tracking links for contractors; ops gets overflow without new hires.",
      },
      contractor: {
        title: "Electrical contractors & GCs",
        description:
          "Wire, panels, and gear on site before rough-in or inspection — not after the crew stands down. Same-day emergency runs when the order was short or the supplier missed the window.",
      },
      projectManager: {
        title: "Project managers & site supers",
        description:
          "Documented proof when electrical material arrival affects the critical path. ETAs and photo POD your super can forward — fewer he-said/she-said disputes with the yard.",
      },
      operations: {
        title: "Operations & logistics managers",
        description:
          "Scale GTA delivery volume without dispatch headcount or owned trucks. Multi-stop wholesale routes across Peel and York with one capacity partner for scheduled and urgent freight.",
      },
      tradePartner: {
        title: "Electrical trade partners",
        description:
          "Counter stock, palletized wire, and equipment drops sized to your typical electrical freight — cars and vans for tight runs, larger vans and trucks for bulk stock.",
      },
      architect: {
        title: "Architects & specifiers",
        description:
          "When specified panels, fixtures, or equipment must align with drawing schedules — timed delivery with proof for GC and supplier coordination.",
      },
      legalProcurement: {
        title: "Legal, procurement & finance",
        description:
          "Shipment-level proof with timestamps for billing disputes, commercial insurance and COI for vendor review, and MSA or SLA exhibits for enterprise electrical programs.",
      },
    },
  }),
  faq: {
    title: "Frequently asked questions — electrical delivery",
    q1: "Do you work with electrical wholesalers and distributors?",
    a1: "Yes. We run recurring and same-day delivery for electrical supply houses and distributors across our Ontario service areas.",
    q2: "Can you meet same-day cut-offs for contractors?",
    a2: "Same-day is available subject to cut-off times and capacity. We confirm windows when we set up your account and on urgent requests.",
    q3: "Do you deliver wire, panels, and equipment to job sites?",
    a3: "Yes. Cars, vans, and trucks matched to your freight — counter runs through palletized wire and equipment to contractors and jobsites.",
    q4: "Can you cover delivery when our driver is out or routes are full?",
    a4: "Yes. Fleet overflow and backup capacity for wholesale counters — dispatch matched vehicle and driver without adding payroll.",
    q5: "How do contractors and site supers track deliveries?",
    a5: "Every shipment has a tracking link with live status and ETA. Share it with the foreman or PM; photo proof completes the record at delivery.",
    q6: "Is proof of delivery included for billing disputes?",
    a6: "Photo proof, signatures where required, GPS timestamps, and tracking history on every stop — documentation for AR and commercial disputes.",
    q7: "What areas do you serve for electrical wholesale delivery?",
    a7: "GTA, Toronto, Mississauga, Brampton, Vaughan, Hamilton, Kitchener–Waterloo, London, Niagara, and surrounding Ontario regions.",
  },
  cta: {
    title: "Get a quote for electrical delivery lanes",
    description:
      "Share your routes, cut-offs, and jobsite zones. We align capacity to your wholesale operation.",
    primary: "Get a quote",
    secondary: "Contact us",
  },
};

en.nicheLanding.plumbingSupply = {
  ...en.nicheLanding.plumbingSupply,
  meta: {
    title: "Plumbing supply delivery GTA | Wholesaler & contractor routes",
    description:
      "Plumbing wholesale delivery for distributors, plumbing contractors, project managers, and supers in the GTA. Pipe, fixtures, same-day emergency runs, and proof on every stop.",
  },
  hero: {
    title: "Plumbing supply delivery in the GTA",
    subtitle:
      "For plumbing wholesalers, plumbing contractors, project managers, and site supers — counter-to-plumber routes, emergency fitting runs, and recurring wholesale delivery with tracking and proof on every stop.",
  },
  personas: personaBlock({
    label: "Who this is for",
    title: "Built for plumbing wholesalers, contractors, and site teams",
    subtitle:
      "Pipe, fixtures, and water heaters — moved on schedule so rough-in and inspection do not slip.",
    trustLinkLabel: "Trust & documentation for procurement",
    personas: {
      vendor: {
        title: "Plumbing wholesalers & distributors",
        description:
          "Recurring routes to plumbing contractors and commercial accounts when your drivers are at capacity. Vans and box trucks for pipe, fixtures, and pallet stock with tracking your counter team can share.",
      },
      contractor: {
        title: "Plumbing contractors & subs",
        description:
          "Emergency fitting and water heater runs when rough-in is tomorrow and the counter missed the window. Jobsite drops with access notes and photo proof for the GC.",
      },
      projectManager: {
        title: "Project managers & site supers",
        description:
          "Plumbing material on site before the next trade mobilizes. Timed windows, driver coordination with your super, and documented proof when schedules are tight.",
      },
      operations: {
        title: "Operations & logistics managers",
        description:
          "Add wholesale delivery volume without fleet capex. One partner for recurring trade routes and same-day overflow across the GTA.",
      },
      tradePartner: {
        title: "Plumbing trade partners",
        description:
          "Long pipe, fixtures, and water heaters — vehicles matched to load dimensions. Counter stock to plumber vans and direct jobsite delivery same day.",
      },
      architect: {
        title: "Architects & design firms",
        description:
          "Specified fixtures and finish plumbing components that must arrive before inspection — timed delivery with proof for owner and GC records.",
      },
      legalProcurement: {
        title: "Legal, procurement & finance",
        description:
          "Proof of delivery with shipment reference for billing disputes, COI for vendor review, and enterprise SLA or MSA documentation on request.",
      },
    },
  }),
  faq: {
    title: "Frequently asked questions — plumbing supply delivery",
    q1: "Do you deliver for plumbing wholesalers and supply houses?",
    a1: "Yes. Recurring and same-day delivery to plumbing contractors, renovators, and commercial accounts across our Ontario service areas.",
    q2: "Can you handle pipe, long stock, and water heaters?",
    a2: "We use vans and trucks suited to your freight. Share dimensions and weight for specialty runs and we match vehicle class.",
    q3: "Do you run emergency same-day runs for plumbing contractors?",
    a3: "Yes. When a fitting or fixture must land today for rough-in or inspection, we dispatch matched capacity subject to cut-off and availability.",
    q4: "Do you deliver to job sites with timed windows?",
    a4: "Yes. Share site access, gate instructions, and superintendent contact. Drivers complete delivery with photo proof for your PM and billing teams.",
    q5: "Can you cover routes when our delivery fleet is full?",
    a5: "Yes. Fleet overflow and backup drivers for wholesale counters — without adding vehicles or payroll.",
    q6: "Is proof of delivery included?",
    a6: "Photo proof, signatures where required, GPS timestamps, and shareable tracking links on every shipment.",
    q7: "What GTA areas do you serve for plumbing supply delivery?",
    a7: "Toronto, Mississauga, Brampton, Vaughan, Hamilton, Kitchener–Waterloo, and surrounding regions — local ops for wholesale plumbing routes.",
  },
  cta: {
    title: "Get a quote for plumbing delivery lanes",
    description:
      "Share your routes and trade accounts. We run wholesale delivery with predictable capacity.",
    primary: "Get a quote",
    secondary: "Contact us",
  },
};

fr.nicheLanding.constructionMaterials = {
  ...fr.nicheLanding.constructionMaterials,
  meta: {
    title: "Livraison matériaux construction RGT | Chantier pour entrepreneurs et distributeurs",
    description:
      "Livraison chantier et distributeur pour fournisseurs construction, entrepreneurs, chargés de projet et contremaîtres dans le RGT. Urgence jour même, palettes, créneaux chantier et preuve photo à chaque arrêt.",
  },
  hero: {
    title: "Livraison de matériaux de construction dans le RGT",
    subtitle:
      "Pour distributeurs de construction, entrepreneurs généraux, chargés de projet et contremaîtres — urgence jour même, tournées récurrentes cour-chantier et débordement de flotte avec créneaux horaires, accès chantier et preuve à chaque livraison.",
  },
  solution: {
    title: "Porterchain pour matériaux de construction",
    description:
      "Un partenaire pour tournées distributeur et livraison chantier en Ontario. Chauffeurs locaux, véhicules adaptés au poids des palettes et à l'accès chantier, suivi complet de l'entrepôt au site.",
    bullet1: "Tournées planifiées et jour même pour distributeurs, cours et chantiers",
    bullet2: "Camionnettes, fourgonnettes et camions 16 pi pour matériaux et fret palette",
    bullet3: "Preuve photo, signatures et liens de suivi pour chaque envoi",
  },
  personas: personaBlock({
    label: "Pour qui",
    title: "Conçu pour fournisseurs, entrepreneurs et équipes chantier",
    subtitle:
      "Que vous gériez la cour, l'échéancier chantier ou l'approvisionnement — Porterchain déplace les matériaux avec une capacité fiable.",
    trustLinkLabel: "Confiance et documentation pour approvisionnement",
    personas: {
      vendor: {
        title: "Fournisseurs et distributeurs de construction",
        description:
          "Tournées comptoir-chantier quand vos chauffeurs sont à capacité, les cut-offs dérapent ou la haute saison exige des camions de secours — sans embaucher de chauffeurs permanents. Preuve photo liée au bon ou PO pour vos comptes clients.",
      },
      contractor: {
        title: "Entrepreneurs généraux et sous-traitants",
        description:
          "Quand le camion du fournisseur ne se présente pas ou envoie le mauvais véhicule, votre équipe a quand même une coulée, inspection ou préparation demain. Créneaux chantier, notes d'accès et véhicule adapté du pickup au camion cube.",
      },
      projectManager: {
        title: "Chargés de projet et contremaîtres",
        description:
          "Votre échéancier suppose que le matériel arrive avant le prochain corps de métier. ETA sans courir après le chauffeur, preuve photo horodatée pour le donneur d'ouvrage, escalade quand une course jour même est critique.",
      },
      operations: {
        title: "Gestionnaires des opérations et logistique",
        description:
          "Capacité de débordement sans investissement en flotte. Tournées multi-arrêts distributeur dans Peel, York et Toronto — un partenaire pour urgent et récurrent.",
      },
      tradePartner: {
        title: "Partenaires métiers électrique et plomberie",
        description:
          "Livraison entrepôt-chantier et comptoir-entrepreneur pour bois, gypse, acier et matériaux palettisés — coordonnée avec les échéanciers électrique et plomberie.",
      },
      architect: {
        title: "Architectes et bureaux de design",
        description:
          "Quand menuiserie sur mesure, luminaires ou échantillons doivent arriver avant inspection ou visite du propriétaire — livraison à heure fixe avec preuve pour le GC et le fournisseur.",
      },
      legalProcurement: {
        title: "Juridique, approvisionnement et finance",
        description:
          "Preuve photo et signature avec référence d'envoi, horodatage GPS, assurance commerciale et COI sur demande, annexes SLA ou MSA pour programmes construction entreprise.",
      },
    },
  }),
  faq: {
    title: "FAQ — livraison construction",
    q1: "Pouvez-vous assurer nos tournées comptoir-entrepreneur quand nos chauffeurs sont à pleine capacité?",
    a1: "Oui. Le débordement de flotte et la capacité de secours sont au cœur de notre offre — véhicule et chauffeur adaptés pour tournées distributeur et cour, souvent le jour même.",
    q2: "Livrez-vous bois, gypse, acier et matériaux palettisés sur chantier?",
    a2: "Oui. Camionnettes, fourgonnettes et camions 16 pi pour bois, gypse, acier et volumes en vrac — adaptés au poids, aux dimensions et à l'accès chantier.",
    q3: "Livrez-vous quand notre fournisseur ne peut pas respecter le créneau chantier d'aujourd'hui?",
    a3: "Oui. Livraison d'urgence et jour même quand un camion fournisseur ne se présente pas — partagez le créneau et les notes d'accès et nous confirmons la capacité.",
    q4: "Le chauffeur peut-il coordonner avec notre contremaître à l'approche?",
    a4: "Oui. Indiquez le contact chantier, les consignes de porte et les créneaux à la réservation. Preuve photo utilisable pour échéancier et facturation.",
    q5: "Gérez-vous l'accès chantier serré au centre-ville de Toronto?",
    a5: "Nous adaptons la classe de véhicule à l'accès — berline au camion cube — et planifions dans Toronto, Peel et York. Partagez les contraintes avant le déploiement.",
    q6: "La preuve de livraison est-elle incluse pour facturation et litiges?",
    a6: "Chaque arrêt inclut photo, signature numérique si requis, horodatage GPS et lien de suivi — documentation pour finance et juridique.",
    q7: "Quelles zones RGT desservez-vous pour la construction?",
    a7: "Toronto, Mississauga, Brampton, Vaughan, Markham, Oakville, Hamilton, Kitchener–Waterloo et métropoles ontariennes en expansion.",
  },
  cta: {
    title: "Obtenir un devis pour vos corridors chantier",
    description:
      "Indiquez matériaux, urgence et zones RGT. Jour même, urgent ou récurrent — réponse dans un jour ouvrable avec véhicule adapté et devis écrit.",
    primary: "Obtenir un devis",
    secondary: "Contactez-nous",
  },
};

fr.nicheLanding.electricalDistribution = {
  ...fr.nicheLanding.electricalDistribution,
  meta: {
    title: "Livraison distributeur électrique RGT | Tournées entrepreneurs et chantier",
    description:
      "Livraison grossiste électrique pour distributeurs, entrepreneurs, chargés de projet et contremaîtres dans le RGT. Fil et panneaux jour même, cut-offs comptoir, créneaux chantier et preuve à chaque arrêt.",
  },
  hero: {
    title: "Livraison distribution électrique dans le RGT",
    subtitle:
      "Pour grossistes électriques, entrepreneurs électriciens, chargés de projet et contremaîtres — tournées récurrentes comptoir-chantier, capacité jour même pour fil et panneaux, et débordement de flotte avec suivi et preuve.",
  },
  solution: {
    title: "Porterchain pour grossistes électriques",
    description:
      "Un partenaire pour livraison comptoir, entrepreneur et chantier. Chauffeurs locaux, véhicules flexibles et tableau de bord unique pour opérations et visibilité client.",
    bullet1: "Tournées récurrentes et capacité jour même pour fil, panneaux et équipement",
    bullet2: "Voitures, fourgonnettes et camions adaptés à votre fret électrique",
    bullet3: "Suivi en direct et preuve de livraison pour entrepreneurs et ventes internes",
  },
  personas: personaBlock({
    label: "Pour qui",
    title: "Conçu pour grossistes électriques, entrepreneurs et équipes chantier",
    subtitle:
      "Du comptoir entrepôt à l'échéancier de préparation — capacité qui respecte cut-offs et créneaux chantier.",
    trustLinkLabel: "Confiance et documentation pour approvisionnement",
    personas: {
      vendor: {
        title: "Grossistes et distributeurs électriques",
        description:
          "Tournées fourgon et camion cube quand les cut-offs s'accumulent ou la flotte est saturée. Ventes internes partage des liens de suivi; opérations obtient du débordement sans embauche.",
      },
      contractor: {
        title: "Entrepreneurs électriciens et GC",
        description:
          "Fil, panneaux et équipement sur chantier avant préparation ou inspection — pas après que l'équipe arrête. Courses d'urgence jour même quand la commande était incomplète.",
      },
      projectManager: {
        title: "Chargés de projet et contremaîtres",
        description:
          "Preuve documentée quand l'arrivée du matériel électrique affecte le chemin critique. ETA et POD photo que le contremaître peut transmettre.",
      },
      operations: {
        title: "Gestionnaires des opérations et logistique",
        description:
          "Augmentez le volume livraison RGT sans effectif répartition ni camions possédés. Tournées grossiste multi-arrêts dans Peel et York.",
      },
      tradePartner: {
        title: "Partenaires métier électrique",
        description:
          "Stock comptoir, fil palettisé et équipement — voitures et fourgonnettes pour courses serrées, camions pour stock en vrac.",
      },
      architect: {
        title: "Architectes et spécificateurs",
        description:
          "Panneaux, luminaires ou équipement spécifiés alignés sur les dessins — livraison à heure fixe avec preuve pour coordination GC.",
      },
      legalProcurement: {
        title: "Juridique, approvisionnement et finance",
        description:
          "Preuve par envoi avec horodatage pour litiges facturation, assurance et COI pour revue fournisseur, annexes MSA ou SLA pour programmes électriques entreprise.",
      },
    },
  }),
  faq: {
    title: "FAQ — livraison électrique",
    q1: "Travaillez-vous avec grossistes et distributeurs électriques?",
    a1: "Oui. Livraison récurrente et jour même pour maisons électriques et distributeurs dans nos zones ontariennes.",
    q2: "Pouvez-vous respecter les cut-offs jour même pour entrepreneurs?",
    a2: "Le jour même est disponible selon cut-off et capacité. Nous confirmons les fenêtres à l'ouverture de compte et sur demandes urgentes.",
    q3: "Livrez-vous fil, panneaux et équipement sur chantier?",
    a3: "Oui. Voitures, fourgonnettes et camions adaptés — du comptoir au fil palettisé et équipement sur chantier.",
    q4: "Pouvez-vous couvrir quand notre chauffeur est absent ou les tournées pleines?",
    a4: "Oui. Débordement de flotte et capacité de secours pour comptoirs grossiste.",
    q5: "Comment entrepreneurs et contremaîtres suivent-ils les livraisons?",
    a5: "Chaque envoi a un lien de suivi avec statut et ETA en direct. Partagez-le au contremaître; preuve photo complète le dossier.",
    q6: "La preuve de livraison est-elle incluse pour litiges?",
    a6: "Photo, signatures, horodatage GPS et historique de suivi à chaque arrêt.",
    q7: "Quelles zones pour livraison grossiste électrique?",
    a7: "RGT, Toronto, Mississauga, Brampton, Vaughan, Hamilton, Kitchener–Waterloo, London, Niagara et régions ontariennes.",
  },
  cta: {
    title: "Obtenir un devis pour vos corridors électriques",
    description:
      "Partagez tournées, cut-offs et zones chantier. Nous alignons la capacité sur votre opération grossiste.",
    primary: "Obtenir un devis",
    secondary: "Contactez-nous",
  },
};

fr.nicheLanding.plumbingSupply = {
  ...fr.nicheLanding.plumbingSupply,
  meta: {
    title: "Livraison plomberie RGT | Grossiste et entrepreneurs",
    description:
      "Livraison grossiste plomberie pour distributeurs, plombiers, chargés de projet et contremaîtres dans le RGT. Tuyaux, appareils, urgence jour même et preuve à chaque arrêt.",
  },
  hero: {
    title: "Livraison fournitures plomberie dans le RGT",
    subtitle:
      "Pour grossistes plomberie, entrepreneurs plombiers, chargés de projet et contremaîtres — tournées comptoir-plombier, courses d'urgence pour raccords, et livraison grossiste récurrente avec suivi et preuve.",
  },
  solution: {
    title: "Porterchain pour grossistes plomberie",
    description:
      "Un partenaire pour livraison métier dans votre territoire. Fourgonnettes et camions pour tuyaux et appareils, tournées récurrentes alignées sur votre rythme de répartition.",
    bullet1: "Tournées récurrentes vers entrepreneurs, rénovateurs et comptes commerciaux",
    bullet2: "Fourgonnettes et camions cube pour tuyaux, appareils et stock palettisé",
    bullet3: "Suivi et preuve de livraison à chaque arrêt",
  },
  personas: personaBlock({
    label: "Pour qui",
    title: "Conçu pour grossistes plomberie, entrepreneurs et équipes chantier",
    subtitle:
      "Tuyaux, appareils et chauffe-eau — livrés à temps pour que préparation et inspection ne glissent pas.",
    trustLinkLabel: "Confiance et documentation pour approvisionnement",
    personas: {
      vendor: {
        title: "Grossistes et distributeurs plomberie",
        description:
          "Tournées récurrentes vers plombiers et comptes commerciaux quand vos chauffeurs sont à capacité. Fourgonnettes et camions cube avec suivi que le comptoir peut partager.",
      },
      contractor: {
        title: "Entrepreneurs plombiers et sous-traitants",
        description:
          "Courses d'urgence pour raccords et chauffe-eau quand la préparation est demain et le comptoir a manqué la fenêtre. Livraisons chantier avec notes d'accès et preuve pour le GC.",
      },
      projectManager: {
        title: "Chargés de projet et contremaîtres",
        description:
          "Matériel plomberie sur chantier avant le prochain métier. Créneaux horaires, coordination avec le contremaître et preuve documentée.",
      },
      operations: {
        title: "Gestionnaires des opérations et logistique",
        description:
          "Augmentez le volume livraison grossiste sans flotte possédée. Un partenaire pour tournées métier récurrentes et débordement jour même dans le RGT.",
      },
      tradePartner: {
        title: "Partenaires métier plomberie",
        description:
          "Longs tuyaux, appareils et chauffe-eau — véhicules adaptés aux dimensions. Stock comptoir vers fourgon plombier et livraison directe chantier le jour même.",
      },
      architect: {
        title: "Architectes et bureaux de design",
        description:
          "Appareils spécifiés et composants finition plomberie avant inspection — livraison à heure fixe avec preuve pour propriétaire et GC.",
      },
      legalProcurement: {
        title: "Juridique, approvisionnement et finance",
        description:
          "Preuve de livraison avec référence d'envoi pour litiges, COI pour revue fournisseur, documentation SLA ou MSA entreprise sur demande.",
      },
    },
  }),
  faq: {
    title: "FAQ — livraison plomberie",
    q1: "Livrez-vous pour grossistes et maisons de plomberie?",
    a1: "Oui. Livraison récurrente et jour même vers entrepreneurs plombiers, rénovateurs et comptes commerciaux.",
    q2: "Pouvez-vous transporter tuyaux, longueurs et chauffe-eau?",
    a2: "Fourgonnettes et camions adaptés à votre fret. Partagez dimensions et poids pour courses spécialisées.",
    q3: "Faites-vous des courses d'urgence jour même pour plombiers?",
    a3: "Oui. Quand un raccord ou appareil doit arriver aujourd'hui pour préparation ou inspection, nous déployons la capacité selon cut-off et disponibilité.",
    q4: "Livrez-vous sur chantier avec créneaux horaires?",
    a4: "Oui. Indiquez accès, consignes de porte et contact contremaître. Preuve photo pour chargés de projet et facturation.",
    q5: "Pouvez-vous couvrir quand notre flotte livraison est pleine?",
    a5: "Oui. Débordement de flotte et chauffeurs de secours pour comptoirs grossiste.",
    q6: "La preuve de livraison est-elle incluse?",
    a6: "Photo, signatures, horodatage GPS et liens de suivi partageables sur chaque envoi.",
    q7: "Quelles zones RGT pour livraison plomberie?",
    a7: "Toronto, Mississauga, Brampton, Vaughan, Hamilton, Kitchener–Waterloo et régions environnantes.",
  },
  cta: {
    title: "Obtenir un devis pour vos corridors plomberie",
    description:
      "Partagez tournées et comptes métier. Livraison grossiste avec capacité prévisible.",
    primary: "Obtenir un devis",
    secondary: "Contactez-nous",
  },
};

for (const [key, cityName, regionName] of [
  ["toronto", "Toronto", "the GTA"],
  ["mississauga", "Mississauga", "Peel Region"],
  ["brampton", "Brampton", "Peel Region"],
]) {
  const block = en.serviceAreaLanding[key];
  if (block?.faq) {
    block.faq.q4 = `Do you deliver construction materials to job sites in ${cityName}?`;
    block.faq.a4 = `Yes. Jobsite delivery for building supply distributors, contractors, project managers, and supers in ${cityName} and ${regionName} — timed windows, site access notes, and photo proof on every stop.`;
    block.faq.q5 = `Can contractors and site supers track ${cityName} deliveries?`;
    block.faq.a5 = `Every shipment includes a live tracking link and photo proof of delivery — share with your foreman or PM without chasing the driver.`;
    block.industries = {
      ...block.industries,
      description: `Construction jobsite delivery, electrical and plumbing wholesale, pharmacy and medical, food distribution, and retail replenishment — for distributors, contractors, project managers, and operations teams in ${cityName} and ${regionName}.`,
    };
  }
  const frBlock = fr.serviceAreaLanding[key];
  if (frBlock?.faq) {
    frBlock.faq.q4 = `Livrez-vous des matériaux de construction sur chantier à ${cityName}?`;
    frBlock.faq.a4 = `Oui. Livraison chantier pour distributeurs construction, entrepreneurs, chargés de projet et contremaîtres à ${cityName} et ${regionName} — créneaux horaires, notes d'accès et preuve photo à chaque arrêt.`;
    frBlock.faq.q5 = `Les entrepreneurs et contremaîtres peuvent-ils suivre les livraisons à ${cityName}?`;
    frBlock.faq.a5 = `Chaque envoi inclut un lien de suivi en direct et une preuve photo — partagez avec le contremaître ou le chargé de projet sans courir après le chauffeur.`;
    frBlock.industries = {
      ...frBlock.industries,
      description: `Livraison chantier construction, gros électrique et plomberie, messagerie pharmacie, distribution alimentaire et réappro détaillant — pour distributeurs, entrepreneurs, chargés de projet et opérations à ${cityName} et ${regionName}.`,
    };
  }
}

writeFileSync(enPath, `${JSON.stringify(en, null, 2)}\n`);
writeFileSync(frPath, `${JSON.stringify(fr, null, 2)}\n`);
console.log("Patched construction persona content in en.json and fr.json");
