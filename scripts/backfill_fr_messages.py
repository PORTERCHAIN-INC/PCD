#!/usr/bin/env python3
"""Backfill missing fr.json keys from en.json structure with localized FR copy."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EN_PATH = ROOT / "website/messages/en.json"
FR_PATH = ROOT / "website/messages/fr.json"


def deep_merge_missing(base: dict, overlay: dict) -> dict:
    out = deepcopy(base)
    for key, value in overlay.items():
        if key not in out:
            out[key] = deepcopy(value)
        elif isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = deep_merge_missing(out[key], value)
    return out


def merchant_area_fr(
    city: str,
    region: str,
    *,
    pain1: str,
    pain2: str,
    pain3: str,
    solution_desc: str,
    bullet1: str,
    bullet2: str,
    bullet3: str,
    workflow_desc: str,
    step1_desc: str,
    onboarding_desc: str,
    step1_onboard: str,
    faq_q1: str,
    faq_a1: str,
    cta_desc: str,
    inquiry: str,
    inquiry_sub: str,
    vehicles_desc: str | None = None,
) -> dict:
    vehicles = {
        "title": f"Options de véhicules à {city}",
        "description": vehicles_desc
        or f"Voitures et fourgons pour {city} et {region}. Livraison même jour et récurrente — nous adaptons le véhicule à votre volume et trajets.",
    }
    return {
        "painPoints": {
            "title": f"Pourquoi les marchands de {city} choisissent la livraison locale",
            "item1": pain1,
            "item2": pain2,
            "item3": pain3,
        },
        "solution": {
            "title": f"Porterchain à {city} et {region}",
            "description": solution_desc,
            "bullet1": bullet1,
            "bullet2": bullet2,
            "bullet3": bullet3,
        },
        "workflow": {
            "title": f"Comment ça marche à {city}",
            "description": workflow_desc,
            "step1Title": "Vous partagez volume et trajets",
            "step1Description": step1_desc,
            "step2Title": "Nous récupérons et livrons",
            "step2Description": "Nos chauffeurs récupèrent et livrent. Lien de suivi par envoi.",
            "step3Title": "Vous et vos clients restez informés",
            "step3Description": f"Statut et ETA en temps réel dans un tableau de bord. Plus de relances pour les livraisons à {city}.",
        },
        "onboarding": {
            "title": f"Intégration simple pour les marchands de {city}",
            "description": onboarding_desc,
            "step1Title": "Connecter",
            "step1Description": step1_onboard,
            "step2Title": "Nous livrons",
            "step2Description": "Nos chauffeurs récupèrent et livrent dans vos zones. Suivi et tableau de bord pour chaque envoi.",
            "step3Title": "Vous gardez le contrôle",
            "step3Description": "Suivez chaque colis, ETA et rapports. Nous gérons les opérations; vous gardez la visibilité.",
        },
        "faq": {
            "title": f"Questions fréquentes — Livraison {city}",
            "q1": faq_q1,
            "a1": faq_a1,
            "q2": f"En combien de temps pouvons-nous démarrer à {city}?",
            "a2": "Partagez votre volume et trajets. Nous alignons la capacité et pouvons vous avoir en livraison en jours, pas en semaines.",
            "q3": f"Mes clients peuvent-ils suivre leur livraison à {city}?",
            "a3": "Chaque envoi a un lien de suivi partageable avec statut et ETA en temps réel.",
        },
        "cta": {
            "title": f"Prêt pour une livraison fiable à {city}?",
            "description": cta_desc,
            "primary": "Obtenir un devis",
            "secondary": "Contactez-nous",
        },
        "inquiryHeading": inquiry,
        "inquirySubheadline": inquiry_sub,
        "vehicles": vehicles,
    }


SERVICE_AREA_BACKFILL: dict[str, dict] = {
    "vaughan": merchant_area_fr(
        "Vaughan",
        "York Region",
        pain1="Desservir parcs d'affaires, détail et résidentiel à Vaughan et York sans ajouter de flotte",
        pain2="Trajets même jour et récurrents adaptés à votre croissance dans le corridor 400",
        pain3="Les clients à Vaughan et York Region s'attendent à la visibilité et à la livraison à l'heure",
        solution_desc="Un partenaire pour les trajets à Vaughan et York Region. Chauffeurs locaux et capacité pour livraisons suburbaines et commerciales.",
        bullet1="Trajets planifiés et même jour à Vaughan et dans l'est du GTA",
        bullet2="Voitures et fourgons pour parcs d'affaires, détail et livraisons résidentielles",
        bullet3="Suivi en direct et ETA pour vous et vos clients à Vaughan",
        workflow_desc="Processus simple et prévisible du ramassage à la livraison dans York Region.",
        step1_desc="Décrivez vos tournées à Vaughan ou dans York Region. Nous alignons la capacité locale et les créneaux.",
        onboarding_desc="Démarrez la livraison dans York Region sans gérer de flotte. Nous gérons chauffeurs et opérations; vous obtenez une capacité prévisible.",
        step1_onboard="Partagez votre volume et zones Vaughan/York. Nous alignons la capacité et les SLA.",
        faq_q1="Livrez-vous dans tout York Region?",
        faq_a1="Oui. Nous couvrons Vaughan et York Region. Indiquez vos zones ou codes postaux et nous confirmerons la couverture.",
        cta_desc="Décrivez votre volume et trajets dans York Region. Nous vous montrerons comment gérer votre livraison récurrente — de façon fiable et simple.",
        inquiry="Démarrez avec la livraison à Vaughan et York Region",
        inquiry_sub="Quelques détails et nous vous proposerons la capacité et les trajets adaptés à votre entreprise à Vaughan.",
    ),
    "markham": merchant_area_fr(
        "Markham",
        "York Region",
        pain1="Desservir corridors tech, détail et résidentiel à Markham et York sans ajouter de flotte",
        pain2="Trajets même jour et récurrents qui suivent votre croissance",
        pain3="Les clients à Markham et York Region s'attendent à la visibilité et à la livraison à l'heure",
        solution_desc="Un partenaire pour les trajets à Markham et York Region. Chauffeurs locaux et capacité pour un marché en forte croissance.",
        bullet1="Trajets planifiés et même jour à Markham et dans l'est du GTA",
        bullet2="Voitures et fourgons pour parcs de bureaux, détail et livraisons résidentielles",
        bullet3="Suivi en direct et ETA pour vous et vos clients à Markham",
        workflow_desc="Processus simple et prévisible du ramassage à la livraison dans York Region.",
        step1_desc="Décrivez vos tournées à Markham ou dans York Region. Nous alignons la capacité locale et les créneaux.",
        onboarding_desc="Démarrez la livraison dans York Region sans gérer de flotte. Nous gérons chauffeurs et opérations; vous obtenez une capacité prévisible.",
        step1_onboard="Partagez votre volume et zones Markham/York. Nous alignons la capacité et les SLA.",
        faq_q1="Livrez-vous à Markham et dans tout York Region?",
        faq_a1="Oui. Nous couvrons Markham et York Region. Indiquez vos zones ou codes postaux et nous confirmerons la couverture.",
        cta_desc="Décrivez votre volume et trajets dans York Region. Nous vous montrerons comment gérer votre livraison récurrente — de façon fiable et simple.",
        inquiry="Démarrez avec la livraison à Markham et York Region",
        inquiry_sub="Quelques détails et nous vous proposerons la capacité et les trajets adaptés à votre entreprise à Markham.",
    ),
    "oakville": merchant_area_fr(
        "Oakville",
        "Halton",
        pain1="Atteindre zones commerciales et résidentielles à Oakville et Halton sans jongler avec les coursiers",
        pain2="Augmenter livraison même jour et récurrente le long du corridor QEW",
        pain3="Les clients à Oakville et Halton s'attendent à la visibilité et à la livraison à l'heure",
        solution_desc="Un partenaire pour les trajets à Oakville et dans la région de Halton. Chauffeurs locaux et capacité pour livraisons suburbaines et commerciales.",
        bullet1="Trajets planifiés et même jour à Oakville et Halton",
        bullet2="Voitures et fourgons pour parcs d'affaires, détail et livraisons résidentielles",
        bullet3="Suivi en direct et ETA pour vous et vos clients dans Halton",
        workflow_desc="Processus simple et prévisible du ramassage à la livraison dans Halton.",
        step1_desc="Décrivez vos tournées à Oakville ou dans Halton. Nous alignons la capacité locale et les créneaux.",
        onboarding_desc="Démarrez la livraison à Halton sans gérer de flotte. Nous gérons chauffeurs et opérations; vous obtenez une capacité prévisible.",
        step1_onboard="Partagez votre volume et zones Oakville/Halton. Nous alignons la capacité et les SLA.",
        faq_q1="Livrez-vous dans tout Halton?",
        faq_a1="Oui. Nous couvrons Oakville et la région de Halton. Indiquez vos zones ou codes postaux et nous confirmerons la couverture.",
        cta_desc="Décrivez votre volume et trajets à Halton. Nous vous montrerons comment gérer votre livraison récurrente — de façon fiable et simple.",
        inquiry="Démarrez avec la livraison à Oakville et Halton",
        inquiry_sub="Quelques détails et nous vous proposerons la capacité et les trajets adaptés à votre entreprise à Oakville.",
    ),
    "burlington": merchant_area_fr(
        "Burlington",
        "Halton",
        pain1="Desservir parcs d'affaires, détail et résidentiel à Burlington et Halton sans ajouter de flotte",
        pain2="Trajets même jour et récurrents le long des corridors QEW et 403",
        pain3="Les clients à Burlington et Halton s'attendent à la visibilité et à la livraison à l'heure",
        solution_desc="Un partenaire pour les trajets à Burlington et dans la région de Halton. Chauffeurs locaux et capacité pour livraisons suburbaines et commerciales.",
        bullet1="Trajets planifiés et même jour à Burlington et Halton",
        bullet2="Voitures et fourgons pour parcs d'affaires, détail et livraisons résidentielles",
        bullet3="Suivi en direct et ETA pour vous et vos clients dans Halton",
        workflow_desc="Processus simple et prévisible du ramassage à la livraison dans Halton.",
        step1_desc="Décrivez vos tournées à Burlington ou dans Halton. Nous alignons la capacité locale et les créneaux.",
        onboarding_desc="Démarrez la livraison à Halton sans gérer de flotte. Nous gérons chauffeurs et opérations; vous obtenez une capacité prévisible.",
        step1_onboard="Partagez votre volume et zones Burlington/Halton. Nous alignons la capacité et les SLA.",
        faq_q1="Livrez-vous à Burlington et dans tout Halton?",
        faq_a1="Oui. Nous couvrons Burlington et la région de Halton. Indiquez vos zones ou codes postaux et nous confirmerons la couverture.",
        cta_desc="Décrivez votre volume et trajets à Halton. Nous vous montrerons comment gérer votre livraison récurrente — de façon fiable et simple.",
        inquiry="Démarrez avec la livraison à Burlington et Halton",
        inquiry_sub="Quelques détails et nous vous proposerons la capacité et les trajets adaptés à votre entreprise à Burlington.",
    ),
    "london": {
        "coverage": {
            "title": "Couverture London et région",
            "description": "Nous livrons à London, Ontario et la région avoisinante — même fiabilité et opérations locales pour votre entreprise.",
        },
        "solution": {
            "title": "Porterchain à London, Ontario",
            "description": "Un partenaire pour les trajets récurrents à London et dans le sud-ouest de l'Ontario. Chauffeurs locaux et capacité adaptés à votre volume.",
            "bullet1": "Trajets planifiés et même jour à London et la région",
            "bullet2": "Voitures et fourgons pour détail, B2B et livraisons résidentielles",
            "bullet3": "Suivi en direct et ETA pour vous et vos clients à London",
        },
        "onboarding": {
            "title": "Intégration simple pour les marchands de London",
            "description": "Démarrez la livraison à London sans gérer de flotte. Nous gérons chauffeurs et opérations; vous obtenez une capacité prévisible.",
            "step1Title": "Connecter",
            "step1Description": "Partagez votre volume et zones London. Nous alignons la capacité et les SLA.",
            "step2Title": "Nous livrons",
            "step2Description": "Nos chauffeurs récupèrent et livrent dans vos zones. Suivi et tableau de bord pour chaque envoi.",
            "step3Title": "Vous gardez le contrôle",
            "step3Description": "Suivez chaque colis, ETA et rapports. Nous gérons les opérations; vous gardez la visibilité.",
        },
        "vehicles": {
            "title": "Options de véhicules à London",
            "description": "Voitures et fourgons pour London et la région. Livraison même jour et récurrente — nous adaptons le véhicule à votre volume et trajets.",
        },
    },
    "oshawa": {
        "coverage": {
            "title": "Couverture Oshawa et Durham",
            "description": "Nous livrons à Oshawa et dans la région de Durham — même fiabilité et opérations locales pour votre entreprise.",
        },
        "solution": {
            "title": "Porterchain à Oshawa et Durham",
            "description": "Un partenaire pour les trajets récurrents à Oshawa et dans l'est du GTA. Chauffeurs locaux et capacité pour parcs d'affaires et livraisons suburbaines.",
            "bullet1": "Trajets planifiés et même jour à Oshawa, Ajax, Pickering et Durham",
            "bullet2": "Voitures et fourgons pour parcs d'affaires, détail et livraisons résidentielles",
            "bullet3": "Suivi en direct et ETA pour vous et vos clients dans Durham",
        },
        "onboarding": {
            "title": "Intégration simple pour les marchands d'Oshawa",
            "description": "Démarrez la livraison à Durham sans gérer de flotte. Nous gérons chauffeurs et opérations; vous obtenez une capacité prévisible.",
            "step1Title": "Connecter",
            "step1Description": "Partagez votre volume et zones Oshawa/Durham. Nous alignons la capacité et les SLA.",
            "step2Title": "Nous livrons",
            "step2Description": "Nos chauffeurs récupèrent et livrent dans vos zones. Suivi et tableau de bord pour chaque envoi.",
            "step3Title": "Vous gardez le contrôle",
            "step3Description": "Suivez chaque colis, ETA et rapports. Nous gérons les opérations; vous gardez la visibilité.",
        },
        "vehicles": {
            "title": "Options de véhicules à Oshawa",
            "description": "Voitures et fourgons pour Oshawa et Durham. Livraison même jour et récurrente — nous adaptons le véhicule à votre volume et trajets.",
        },
    },
}

VEHICLES_ONLY = {
    "toronto": {
        "title": "Options de véhicules à Toronto",
        "description": "Voitures, fourgons, camions et vélos-cargos dans le GTA. Nous adaptons le véhicule à votre volume — même jour centre-ville, tournées multi-arrêts suburbaines ou B2B cross-GTA. Un partenaire, un tableau de bord, une capacité prévisible.",
    },
    "mississauga": {
        "title": "Options de véhicules à Mississauga",
        "description": "Fourgons cargo, Sprinter, pickups et camions cube pour Peel. Nous adaptons le véhicule à votre volume — distribution entrepôt, fret palette ou réapprovisionnement détaillant.",
    },
    "brampton": {
        "title": "Options de véhicules à Brampton",
        "description": "Voitures, fourgons, camions et vélos-cargos à Brampton et Peel. Nous adaptons le véhicule à votre volume et zone — même jour, tournées multi-arrêts ou B2B.",
    },
    "kitchenerWaterloo": {
        "title": "Options de véhicules à Kitchener-Waterloo",
        "description": "Voitures et fourgons pour la région de Waterloo. Livraison même jour et récurrente — nous adaptons le véhicule à votre volume et trajets.",
    },
    "niagara": {
        "title": "Options de véhicules dans la région de Niagara",
        "description": "Voitures et fourgons pour Niagara. Livraison même jour et récurrente — nous adaptons le véhicule à votre volume et trajets.",
    },
}

CHOCOLATE_FR = {
    "meta": {
        "title": "Livraison chocolat et confiserie | Trajets locaux et récurrents pour artisans et détaillants",
        "description": "Porterchain livre pour chocolatiers et confiseurs. Trajets récurrents et même jour vers détaillants, cafés et partenaires. Manutention adaptée, traçable, un partenaire.",
    },
    "hero": {
        "title": "Livraison pour chocolat et confiserie",
        "subtitle": "Mettez vos produits chez détaillants, cafés et partenaires à l'heure. Nous gérons le dernier kilomètre pour que vous vous concentriez sur l'artisanat — manutention adaptée et livraison traçable.",
    },
    "painPoints": {
        "title": "Défis de livraison pour les chocolatiers",
        "item1": "Livrer détaillants et cafés à l'heure sans flotte interne",
        "item2": "Manutention et température qui protègent la qualité en transit",
        "item3": "Trajets récurrents et livraisons même jour qui suivent la demande saisonnière",
    },
    "coverage": {
        "title": "Zones desservies pour chocolat et confiserie",
        "description": "Couverture croissante dans les grandes métros canadiennes. Même fiabilité et opérations locales pour que vos routes détaillants et cafés tournent de façon constante.",
    },
    "vehicleFit": {
        "title": "Véhicules adaptés au chocolat et à la confiserie",
        "description": "Fourgons cargo et berlines pour livraisons cafés et réapprovisionnement détaillant; manutention soignée pour produits sensibles à la température en transit.",
    },
    "onboarding": {
        "title": "Intégration simple pour chocolatiers",
        "description": "Trois étapes vers une livraison locale prévisible. Pas de flotte à gérer.",
        "step1Title": "Connecter",
        "step1Description": "Partagez volume, trajets et exigences de manutention. Nous alignons capacité et SLA.",
        "step2Title": "Nous livrons",
        "step2Description": "Nos chauffeurs récupèrent et livrent avec suivi sur chaque envoi.",
        "step3Title": "Vous gardez le contrôle",
        "step3Description": "Suivez chaque livraison, ETA et rapports clairs pour opérations et facturation.",
    },
    "faq": {
        "title": "Questions fréquentes — livraison chocolat",
        "q1": "Gérez-vous des trajets récurrents vers détaillants et cafés?",
        "a1": "Oui. Trajets récurrents et même jour sont au cœur de nos services pour chocolatiers et confiseurs.",
        "q2": "Pouvez-vous protéger la qualité du produit en transit?",
        "a2": "Nous travaillons avec vous sur les exigences de manutention et fournissons suivi et preuve à chaque arrêt.",
        "q3": "Comment obtenir un devis?",
        "a3": "Partagez vos trajets, volume et urgence. Nous répondons sous un jour ouvrable avec véhicule adapté et tarification.",
    },
    "cta": {
        "title": "Obtenir un devis pour capacité livraison chocolat",
        "description": "Décrivez vos trajets, volume et exigences de manutention. Nous alignerons capacité véhicule-chauffeur pour vos routes détaillants et cafés.",
        "primary": "Obtenir un devis",
        "secondary": "Contactez-nous",
    },
    "inquiryHeading": "Démarrez avec la livraison chocolat et confiserie",
    "inquirySubheadline": "Partagez vos trajets et volume saisonnier. Nous quoterons la capacité adaptée à votre programme détaillants et cafés.",
}

VEHICLE_DELIVERY_FR = {
    "pickupTruck": {
        "pageTitle": "Livraison camionnette | Meubles et fret marketplace | Porterchain",
        "description": "Camionnettes pour meubles, enlèvements marketplace, électroménagers et fret moyen dans le GTA et en Ontario. Capacité flexible avec suivi complet.",
        "headline": "Camionnette pour fret local flexible",
        "subheadline": "Les pickups transportent meubles, électroménagers, chargements marketplace et fret B2B nécessitant benne ouvert ou chargement polyvalent — avec le même suivi et la même fiabilité que notre flotte fourgons.",
        "useCasesTitle": "Cas d'usage les plus adaptés",
        "useCases": "Livraison meubles et électroménagers, enlèvements marketplace et détail, matériaux construction pour benne pickup, et fret B2B quand un fourgon est trop fermé ou un camion boîte trop grand.",
        "volumeTitle": "Adéquation du volume",
        "volumeSuitability": "Idéal pour tournées à arrêt unique ou multi-arrêts avec articles volumineux, charges mixtes ou livraisons chantier où l'accès hayon compte. Augmentez avec des routes pickup supplémentaires selon le volume.",
        "whoForTitle": "Pour qui la livraison pickup",
        "whoFor": "Marques e-commerce meubles, détaillants électroménagers, vendeurs marketplace, entrepreneurs avec courses matériaux légères et marchands avec fret volumineux irrégulier dans le GTA.",
        "serviceAreaTitle": "Pertinence des zones desservies",
        "serviceAreaRelevance": "Routes pickup dans le GTA, Hamilton, Kitchener-Waterloo, London, Niagara et Durham. Adaptées aux accès urbains, suburbains et chantier.",
        "ctaTitle": "Prêt pour la livraison camionnette?",
        "ctaDescription": "Décrivez votre profil de fret et vos trajets. Nous confirmerons véhicule et capacité.",
        "ctaLabel": "Commencer",
    },
    "cargoVan": {
        "pageTitle": "Livraison fourgon cargo | E-commerce et routes wholesale | Porterchain",
        "description": "Fourgons cargo toit haut pour e-commerce, wholesale et tournées B2B multi-arrêts dans le GTA. Plus de capacité qu'un VUS, accès plus agile qu'un camion boîte.",
        "headline": "Fourgon cargo pour tournées colis à fort volume",
        "subheadline": "Fourgons cargo toit haut pour fulfillment e-commerce, réapprovisionnement wholesale et tournées multi-arrêts quand vous avez besoin de capacité fermée sans camion boîte complet.",
        "useCasesTitle": "Cas d'usage les plus adaptés",
        "useCases": "Tournées e-commerce et D2C multi-arrêts, livraisons wholesale aux détaillants, stock comptoir plomberie et électrique, boîtes abonnement et réapprovisionnement B2B récurrent dans le GTA.",
        "volumeTitle": "Adéquation du volume",
        "volumeSuitability": "Adapté à fort nombre d'arrêts avec fret fermé — dizaines de colis par tournée, chariots cage ou boîtes empilées. Passez aux camions boîte quand le fret palettes domine.",
        "whoForTitle": "Pour qui le fourgon cargo",
        "whoFor": "Marques e-commerce, distributeurs et marchands qui augmentent le volume colis à Toronto et dans le GTA sans posséder une flotte de fourgons.",
        "serviceAreaTitle": "Pertinence des zones desservies",
        "serviceAreaRelevance": "Fourgons cargo à Toronto, Mississauga, Brampton, Vaughan, Hamilton et métros ontariennes — mêmes normes de suivi et POD que toute notre gamme de véhicules.",
        "ctaTitle": "Prêt pour la livraison fourgon cargo?",
        "ctaDescription": "Décrivez vos trajets et profil colis. Nous alignerons la capacité fourgon à votre programme.",
        "ctaLabel": "Commencer",
    },
}

SECTIONS_FR = {
    "trust": {"description": "Suivi en direct, preuve de livraison et escalade opérationnelle quand les créneaux comptent."},
    "testimonials": {"placeholder": "D'autres témoignages de nos marchands à venir."},
}


def main() -> int:
    en = json.loads(EN_PATH.read_text(encoding="utf-8"))
    fr = json.loads(FR_PATH.read_text(encoding="utf-8"))

    sa = fr.setdefault("serviceAreaLanding", {})
    for slug, patch in SERVICE_AREA_BACKFILL.items():
        sa[slug] = deep_merge_missing(sa.get(slug, {}), patch)
    for slug, vehicles in VEHICLES_ONLY.items():
        sa[slug] = deep_merge_missing(sa.get(slug, {}), {"vehicles": vehicles})

    nl = fr.setdefault("nicheLanding", {})
    nl["chocolate"] = deep_merge_missing(nl.get("chocolate", {}), CHOCOLATE_FR)

    vd = fr.setdefault("vehicleDelivery", {})
    for slug, patch in VEHICLE_DELIVERY_FR.items():
        vd[slug] = deep_merge_missing(vd.get(slug, {}), patch)

    sections = fr.setdefault("sections", {})
    for key, patch in SECTIONS_FR.items():
        sections[key] = deep_merge_missing(sections.get(key, {}), patch)

    # Normalize quote CTAs on stub service areas still using legacy labels.
    for slug, area in sa.items():
        if isinstance(area.get("cta"), dict):
            primary = area["cta"].get("primary")
            if primary in ("Nous contacter", "Nous joindre", "Talk to us"):
                area["cta"]["primary"] = "Obtenir un devis"

    FR_PATH.write_text(json.dumps(fr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    en_keys = set()
    fr_keys = set()

    def flatten(obj: object, prefix: str = "") -> set[str]:
        keys: set[str] = set()
        if isinstance(obj, dict):
            for k, v in obj.items():
                p = f"{prefix}.{k}" if prefix else k
                keys.add(p)
                keys.update(flatten(v, p))
        return keys

    en_keys = flatten(en)
    fr_keys = flatten(fr)
    missing = sorted(en_keys - fr_keys)
    extra = sorted(fr_keys - en_keys)
    print(f"fr.json backfill complete — missing keys: {len(missing)}, extra keys: {len(extra)}")
    if missing:
        print("Still missing (first 20):")
        for k in missing[:20]:
            print(f"  {k}")
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
