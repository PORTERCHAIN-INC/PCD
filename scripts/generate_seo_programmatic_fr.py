#!/usr/bin/env python3
"""Generate website/messages/seo-programmatic-fr.json from embedded FR copy."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "website/messages/seo-programmatic-fr.json"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from seo_programmatic_fr_rest import FAQ, GUIDES, SUCCESS  # noqa: E402

DATA = {
    "hubs": {
        "compare": {
            "title": "Comparer les options de livraison | Porterchain",
            "description": "Comparez Porterchain à la livraison interne, aux coursiers ponctuels et à la répartition par feuille de calcul.",
        },
        "faq": {
            "title": "FAQ livraison pour marchands | Porterchain",
            "description": "Réponses sur la tarification, l'intégration, les CSV, les API, les zones desservies et la livraison par secteur.",
        },
        "guides": {
            "title": "Guides livraison locale | Porterchain",
            "description": "Guides pratiques sur le fonctionnement de Porterchain, l'intégration, le suivi et le soutien pour les marchands du RGT.",
        },
        "successStories": {
            "title": "Histoires de réussite marchands | Porterchain",
            "description": "Comment torréfacteurs, pharmacies et marques beauté développent leur livraison avec Porterchain.",
        },
    },
    "compare": {
        "in-house-delivery": {
            "title": "Porterchain vs livraison interne",
            "description": "Comparez la livraison gérée avec Porterchain à une flotte interne. Visibilité, coûts prévisibles et un partenaire pour livraison récurrente et le jour même.",
            "intro": "Beaucoup de marchands commencent par une livraison interne quand le volume est faible. En grandissant, les coûts de flotte, l'embauche, l'entretien et la planification peuvent devenir une distraction. Porterchain offre un partenaire et un tableau de bord pour livraison récurrente et le jour même — sans flotte ni chauffeurs à gérer. Vous gardez le contrôle des zones et des plages horaires; nous gérons la capacité, le routage et l'exécution du dernier kilomètre.",
            "alternativeLabel": "Livraison interne",
            "comparisonRows": [
                {
                    "dimension": "Visibilité et suivi",
                    "porterchain": "Un tableau de bord pour statut et ETA; visibilité complète de la collecte à la livraison.",
                    "alternative": "Dépend de vos outils et chauffeurs. Souvent téléphones et feuilles de calcul — visibilité manuelle et tardive.",
                },
                {
                    "dimension": "Prévisibilité des coûts",
                    "porterchain": "Tarification alignée sur arrêts, zones et volume. Coût prévisible sans véhicules, entretien ni paie chauffeurs.",
                    "alternative": "Coûts fixes et variables: véhicules, carburant, assurance, salaires, entretien. Difficile d'ajuster à la demande.",
                },
                {
                    "dimension": "Récurrent et jour même",
                    "porterchain": "Tournées récurrentes et options jour même au même endroit. Un partenaire pour les deux modèles.",
                    "alternative": "Vous planifiez et affectez pour les deux. Le jour même implique souvent heures supplémentaires ou courses ponctuelles.",
                },
                {
                    "dimension": "Mise à l'échelle",
                    "porterchain": "Nous alignons la capacité à votre volume. Ajoutez arrêts ou zones sans nouveaux véhicules ni embauches.",
                    "alternative": "La croissance signifie plus de véhicules et de chauffeurs. Capital et recrutement deviennent le goulot.",
                },
            ],
            "extraLinks": [
                {"path": "onboarding", "label": "Comment fonctionne l'intégration"},
                {"path": "serviceAreas", "label": "Zones desservies"},
            ],
        },
        "ad-hoc-courier": {
            "title": "Porterchain vs coursier ponctuel",
            "description": "Comparez la livraison récurrente et jour même gérée par Porterchain à la réservation de coursiers course par course.",
            "intro": "Réserver un coursier pour chaque course convient aux envois occasionnels. Pour livraison récurrente ou régulière le jour même, le ponctuel apporte souvent tarifs variables, peu de visibilité et du temps à coordonner chaque course. Porterchain est conçu pour les marchands à volume récurrent: un partenaire, capacité stable et une vue sur chaque course.",
            "alternativeLabel": "Coursier ponctuel",
            "comparisonRows": [
                {
                    "dimension": "Tarification et prévisibilité",
                    "porterchain": "Tarification liée à votre volume et zones. Une facture, coût prévisible par arrêt ou tournée.",
                    "alternative": "Tarifs par réservation variables selon demande, distance et fournisseur.",
                },
                {
                    "dimension": "Visibilité",
                    "porterchain": "Un tableau de bord pour toutes les courses. Statut et ETA au même endroit.",
                    "alternative": "Suivi selon le coursier utilisé. Plusieurs apps ou liens; pas de vue unique.",
                },
                {
                    "dimension": "Tournées récurrentes",
                    "porterchain": "Tournées récurrentes au cœur du modèle. Même capacité, même partenaire, même processus.",
                    "alternative": "Récurrent = re-réserver à chaque fois. Coordination et variabilité augmentent avec le volume.",
                },
                {
                    "dimension": "Temps opérationnel",
                    "porterchain": "Soumettez commandes ou arrêts (CSV ou API); nous exécutons. Pas de réservation quotidienne.",
                    "alternative": "Chaque course exige disponibilité, réservation et communication. Le temps s'accumule.",
                },
            ],
            "extraLinks": [
                {"path": "onboarding", "label": "Comment fonctionne l'intégration"},
                {"path": "pricing", "label": "Tarification"},
            ],
        },
        "unmanaged-same-day": {
            "title": "Porterchain vs livraison jour même non gérée",
            "description": "Comparez la livraison jour même gérée par Porterchain aux flux manuels. Visibilité, heures limites et un partenaire pour récurrent et à la demande.",
            "intro": "La livraison jour même non gérée coordonne souvent chauffeurs ou coursiers manuellement, avec peu de visibilité avant la livraison. Porterchain offre du jour même géré dans nos zones: vous fixez heures limites et plages; nous gérons capacité et exécution avec statut et ETA dans un tableau de bord.",
            "alternativeLabel": "Flux jour même non gérés",
            "comparisonRows": [
                {
                    "dimension": "Heures limites et plages",
                    "porterchain": "Heures limites et plages convenues. Nous alignons la capacité pour des promesses réalistes.",
                    "alternative": "Souvent ad hoc: vous savez au moment de la course si la plage est tenable.",
                },
                {
                    "dimension": "Visibilité",
                    "porterchain": "Statut et ETA en temps réel pour vous et vos clients.",
                    "alternative": "Mises à jour manuelles ou après coup. Moins de capacité à informer les clients.",
                },
                {
                    "dimension": "Récurrent + jour même",
                    "porterchain": "Tournées récurrentes et jour même au même endroit. Un partenaire, un processus, une vue.",
                    "alternative": "Récurrent et jour même sont souvent séparés. Plus de coordination et de lacunes.",
                },
                {
                    "dimension": "Cohérence",
                    "porterchain": "Un processus et un SLA. Même qualité et visibilité à chaque course.",
                    "alternative": "Dépend de qui exécute chaque course. Qualité et communication variables.",
                },
            ],
            "extraLinks": [
                {"path": "onboarding", "label": "Comment fonctionne l'intégration"},
                {"path": "serviceAreas", "label": "Zones desservies"},
            ],
        },
        "spreadsheet-dispatch": {
            "title": "Porterchain vs répartition par feuille de calcul seule",
            "description": "Comparez la visibilité et livraison gérée de Porterchain à une répartition uniquement par tableur. Un tableau de bord, suivi et soutien CSV ou API.",
            "intro": "Les feuilles de calcul listent les arrêts et les partagent avec chauffeurs ou coursiers. La lacune est la visibilité: une fois la liste transmise, le statut en temps réel manque souvent. Porterchain accepte CSV pour démarrer, mais chaque course a suivi complet et un tableau de bord unique.",
            "alternativeLabel": "Répartition par feuille de calcul seule",
            "comparisonRows": [
                {
                    "dimension": "Visibilité après répartition",
                    "porterchain": "Chaque course a statut et ETA dans un tableau de bord.",
                    "alternative": "Arrêts dans une feuille; exécution ailleurs. Statut souvent manuel ou absent.",
                },
                {
                    "dimension": "Soumission",
                    "porterchain": "Téléversement CSV ou API. Même format pour tournées récurrentes; nous exécutons avec suivi.",
                    "alternative": "Feuille envoyée au chauffeur ou coursier. Pas de suivi intégré ni vue globale.",
                },
                {
                    "dimension": "Mise à l'échelle",
                    "porterchain": "Ajoutez volume ou zones sans changer la soumission. Nous gérons capacité et routage.",
                    "alternative": "Plus de volume = plus de feuilles et coordination, même lacune de visibilité.",
                },
                {
                    "dimension": "Tournées récurrentes",
                    "porterchain": "Tournées récurrentes avec le même CSV ou API. Un partenaire, processus constant.",
                    "alternative": "Récurrent = feuilles mises à jour à chaque fois. Pas de vue unifiée historique.",
                },
            ],
            "extraLinks": [
                {"path": "onboarding", "label": "Comment fonctionne l'intégration"},
                {"path": "integrations", "label": "Intégrations"},
            ],
        },
    },
}

DATA["faq"] = FAQ
DATA["guides"] = GUIDES
DATA["successStories"] = SUCCESS


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(DATA, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
