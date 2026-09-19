# ruff: noqa: E501
"""FR copy for guides, success stories, and FAQ clusters (seo-programmatic-fr.json)."""

GUIDES = {
    "delivery-operations-model": {
        "title": "Modèle d'opérations de livraison",
        "description": "Comment fonctionnent les opérations Porterchain: capacité, routage, plages horaires et exécution locale dans le RGT et l'Ontario.",
        "intro": "Les opérations Porterchain sont bâties autour de l'exécution locale. Nous alignons la capacité à votre volume et zones, planifions les tournées pour efficacité et plages horaires, et exécutons collecte et livraison avec visibilité complète.",
        "sections": [
            {
                "heading": "Capacité alignée à votre volume et zones",
                "body": "Nous ne traitons pas chaque course comme un one-shot. Pour tournées récurrentes, nous alignons chauffeurs et véhicules à votre horaire et zones. Le jour même utilise la même flotte locale; heures limites et plages sont convenues. Capacité planifiée par région — Toronto, Mississauga, Brampton, Kitchener-Waterloo, London, Niagara.",
            },
            {
                "heading": "Routage et plages horaires",
                "body": "Les tournées sont construites autour de vos arrêts, plages et véhicule adapté. Courses multi-arrêts optimisées pour les zones desservies; trafic et géographie pour des ETA réalistes. Vous fixez les exigences; nous exécutons dans ces plages.",
            },
            {
                "heading": "De la collecte à la livraison, une chaîne",
                "body": "De la collecte chez vous à la remise à destination, chaque arrêt est suivi. Chauffeurs formés sur manutention et plages; statut et ETA tout au long. Pour industries avec conformité (pharmacie, température), nous travaillons avec vous à l'intégration.",
            },
        ],
        "extraLinks": [
            {"path": "workflow", "label": "Comment fonctionne la livraison"},
            {"path": "onboarding", "label": "Intégration marchands"},
            {"path": "serviceAreas", "label": "Zones desservies"},
        ],
    },
    "merchant-onboarding-guide": {
        "title": "Guide d'intégration marchand",
        "description": "Comment intégrer un marchand Porterchain: volume, zones, CSV ou API et à quoi s'attendre. Opérationnel en jours, pas en semaines.",
        "intro": "L'intégration Porterchain est conçue pour être rapide. Nous ciblons volume, zones et flux pour confirmer couverture, aligner capacité et vous donner suivi et rapports. La plupart des marchands sont prêts en quelques jours.",
        "sections": [
            {
                "heading": "Ce dont nous avons besoin",
                "body": "Volume typique (arrêts par semaine ou par course), zones de livraison et plages ou exigences particulières. Vous pouvez commencer par feuille de calcul ou CSV; nous confirmons le format. Pas d'intégration complète le jour un — CSV ou courriel suffisent souvent.",
            },
            {
                "heading": "Couverture et capacité",
                "body": "Nous confirmons que nous desservons vos zones: RGT, Kitchener-Waterloo, London, Niagara, Oshawa et autres régions ontariennes. Une fois la couverture confirmée, nous alignons capacité et SLA. Vous savez où nous livrons avant de vous engager.",
            },
            {
                "heading": "Mise en service",
                "body": "Accès au tableau de bord et soumission de commandes ou arrêts. Tournées récurrentes configurées à votre cadence. Options jour même où nous opérons. Suivi et ETA dès la première course.",
            },
        ],
        "extraLinks": [
            {"path": "workflow", "label": "Comment fonctionne la livraison"},
            {"path": "integrations", "label": "Intégrations"},
            {"path": "serviceAreas", "label": "Zones desservies"},
        ],
    },
    "route-and-tracking-overview": {
        "title": "Aperçu routage et suivi",
        "description": "Comment fonctionnent routage et suivi Porterchain: statut, ETA et visibilité de la collecte à la livraison dans le RGT et l'Ontario.",
        "intro": "Chaque course Porterchain a un suivi complet de la collecte à la livraison. Statut et ETA dans votre tableau de bord; liens partageables avec clients ou partenaires.",
        "sections": [
            {
                "heading": "Comment les tournées sont construites et exécutées",
                "body": "Vous soumettez arrêts (CSV, API ou nos outils); nous construisons la tournée selon plages, véhicule et zones. Courses multi-arrêts optimisées localement. Chauffeurs reçoivent la tournée avec mises à jour temps réel.",
            },
            {
                "heading": "Statut et ETA",
                "body": "Dès la collecte, vous voyez statut et heure estimée. Tableau de bord sur toutes les courses; détail par arrêt. ETA mis à jour au fil de la tournée.",
            },
            {
                "heading": "Partager le suivi avec les clients",
                "body": "Chaque livraison peut avoir un lien de suivi partageable. Réduit les appels « où est ma commande? » et aligne tout le monde. Même expérience dans le RGT, Kitchener-Waterloo, London, Niagara et au-delà.",
            },
        ],
        "extraLinks": [
            {"path": "workflow", "label": "Comment fonctionne la livraison"},
            {"path": "onboarding", "label": "Intégration marchands"},
            {"path": "support", "label": "Soutien"},
        ],
    },
    "support-and-issue-handling": {
        "title": "Soutien et gestion des problèmes",
        "description": "Comment fonctionnent le soutien et la gestion des problèmes Porterchain: quand nous joindre, résolution et soutien opérationnel.",
        "intro": "Quand quelque chose ne va pas ou vous avez une question, nous sommes là. Le soutien Porterchain est orienté opérations: livraison, routage et réalités de la logistique locale.",
        "sections": [
            {
                "heading": "Quand contacter le soutien",
                "body": "Pour tout ce qui affecte la livraison: plage manquée, colis endommagé ou perdu, question chauffeur ou routage, changement de course. Aussi intégration et rapports. Mieux vaut clarifier tôt qu'escalader un problème.",
            },
            {
                "heading": "Comment nous traitons les problèmes",
                "body": "Chaque problème est enregistré et suivi jusqu'à résolution. Pour échecs de service, nous enquêtons et proposons prochaines étapes: crédits, reprises ou changements de processus. Mises à jour et chemin clair vers résolution.",
            },
            {
                "heading": "Signalement et escalade",
                "body": "Signalez via notre canal de soutien ou le flux de signalement. Incluez la référence course ou arrêt. Pour problèmes récurrents, nous travaillons sur cause racine et prévention.",
            },
        ],
        "extraLinks": [
            {"path": "support", "label": "Soutien"},
            {"path": "workflow", "label": "Comment fonctionne la livraison"},
            {"path": "onboarding", "label": "Intégration marchands"},
        ],
    },
}

SUCCESS = {
    "construction-distributor-jobsite-delivery": {
        "title": "Comment un distributeur de matériaux du RGT a développé la livraison chantier",
        "description": "Un distributeur régional a remplacé coursiers ponctuels par tournées récurrentes en camion cube vers chantiers — avec preuve de livraison à chaque arrêt.",
        "headline": "Livraison chantier récurrente sans ajouter de flotte",
        "challenge": "Livraison de bois, gypse et fixtures vers des dizaines de chantiers actifs par semaine. Coursiers ponctuels: plages manquées, peu de preuve pour litiges avec entrepreneurs généraux, ops à relancer les chauffeurs.",
        "solution": "Tournées camion cube 16 pi alignées à la liste quotidienne — plages fixes, notes d'accès chantier, photo preuve à chaque livraison. Un tableau de bord pour ventes internes et répartition.",
        "outcome": "Plus de 40 livraisons chantier par semaine avec un partenaire. Moins de retards chantier, POD clair pour facturation, répartition sans jongler plusieurs apps coursiers.",
        "quote": "Il nous fallait livraison palette sur chantier avec preuve acceptée par nos EG. Porterchain l'a rendu répétable.",
        "quoteAttribution": "Gestionnaire des opérations, distributeur matériaux RGT",
        "outcomeMetric": "40+ livraisons chantier par semaine",
    },
    "coffee-roaster-wholesale-delivery": {
        "title": "Comment un torréfacteur torontois a développé la livraison grossiste",
        "description": "Un torréfacteur spécialisé dessert plus de 50 cafés dans le RGT avec tournées récurrentes et fraîcheur jour même. Sans flotte, un partenaire.",
        "headline": "Développer la livraison grossiste sans casse-tête opérationnel",
        "challenge": "Café fraîchement torréfié vers cafés et abonnés du RGT sur horaire prévisible, sans flotte interne ni plusieurs coursiers.",
        "solution": "Tournées récurrentes et plages jour même alignées au cycle de torréfaction. Un partenaire pour grossiste et abonnements, avec suivi pour cafés et abonnés.",
        "outcome": "Plus de 50 cafés et volume abonnement croissant avec un partenaire. Ops concentrées sur la torréfaction; nous gérons le dernier kilomètre.",
        "quote": "Il nous fallait un partenaire pour récurrent et jour même quand ça compte. Porterchain a simplifié.",
        "quoteAttribution": "Opérations, torréfacteur Toronto",
        "outcomeMetric": "50+ cafés desservis",
    },
    "pharmacy-patient-delivery": {
        "title": "Livraison pharmacie: conformité et rapidité",
        "description": "Une pharmacie locale a développé livraison patients et ordonnances avec logistique traçable et conforme. Jour même et tournées récurrentes.",
        "headline": "Livraison patients fiable sans ajouter de flotte",
        "challenge": "Étendre livraison patients et cliniques sans compromettre conformité ni ajouter véhicules et chauffeurs internes.",
        "solution": "Tournées récurrentes et à la demande avec suivi complet et visibilité chaîne de custody. Jour même où nécessaire, un tableau de bord pour répartition et statut.",
        "outcome": "Couverture élargie avec conformité maintenue. Patients et cliniques ont des ETA fiables; l'équipe pharmacie voit chaque course au même endroit.",
        "quote": "Il nous fallait un partenaire de confiance pour ordonnances. Suivi et constance étaient non négociables.",
        "quoteAttribution": "Opérations pharmacie, Ontario",
        "outcomeMetric": "Jour même dans le RGT",
    },
    "beauty-brand-d2c-fulfillment": {
        "title": "Comment une marque beauté a développé D2C et abonnements",
        "description": "Une marque cosmétiques a développé fulfillment D2C et boîtes abonnement avec livraison locale en Ontario. Un partenaire récurrent et jour même.",
        "headline": "Fulfillment D2C et abonnement qui scale",
        "challenge": "Dépassement des coursiers ponctuels; besoin de livraison prévisible et traçable pour D2C et abonnés sans fulfillment interne.",
        "solution": "Capacité alignée au volume et zones. Collecte et livraison récurrentes avec manutention soignée, plus jour même pour promotions. Lien de suivi par envoi.",
        "outcome": "Volume abonnement et D2C développé avec un partenaire. Moins de plages manquées et expérience client constante.",
        "quote": "Un partenaire pour récurrent et jour même a éliminé l'incertitude logistique de la croissance.",
        "quoteAttribution": "Opérations, marque beauté",
        "outcomeMetric": "Récurrent + jour même en Ontario",
    },
}

def _faq(slug, title, description, intro, items, extra_links=None):
    out = {"title": title, "description": description, "intro": intro, "items": items}
    if extra_links:
        out["extraLinks"] = extra_links
    return out


FAQ = {
    "construction-delivery": _faq(
        "construction-delivery",
        "Livraison matériaux construction: FAQ chantier et distributeur",
        "FAQ sur livraison matériaux en Ontario — chantiers, palettes, preuve de livraison et tournées récurrentes.",
        "Distributeurs et entrepreneurs ont besoin de livraison respectant plages chantier, fret palettisé et preuve à chaque arrêt. Porterchain exécute tournées récurrentes et jour même dans le RGT avec véhicules adaptés.",
        [
            {"question": "Livrez-vous matériaux sur chantier?", "answer": "Oui. Bois, gypse, acier, agrégats et matériaux généraux vers chantiers et clients professionnels. Partagez tournées, accès chantier et plages; nous alignons capacité et véhicules."},
            {"question": "Quels véhicules pour fret construction?", "answer": "Camionnettes et fourgons cargo pour petites courses; camions cube 16 pi pour palettes et charges plus lourdes. Véhicule adapté au poids, dimensions et accès."},
            {"question": "Preuve de livraison sur chantier?", "answer": "Photo preuve, signatures numériques si requis et lien de suivi. Statut et ETA en temps réel pour vous et équipes chantier."},
            {"question": "Quelles zones pour construction?", "answer": "RGT, Toronto, Mississauga, Brampton, Vaughan, Hamilton, Kitchener-Waterloo, London, Niagara, Oshawa et régions ontariennes environnantes."},
        ],
        [{"path": "serviceAreas", "label": "Zones desservies"}, {"path": "pricing", "label": "Tarification"}],
    ),
    "electrical-distributor-delivery": _faq(
        "electrical-distributor-delivery",
        "Livraison distributeur électrique: FAQ grossiste et entrepreneur",
        "FAQ livraison pour grossistes électriques — jour même, fil et panneaux, tournées récurrentes en Ontario.",
        "Distributeurs électriques ont besoin de dernier kilomètre fiable vers entrepreneurs, chantiers et comptes comptoir. Porterchain exécute tournées récurrentes et jour même avec suivi.",
        [
            {"question": "Livrez-vous pour grossistes électriques?", "answer": "Oui. Tournées récurrentes vers entrepreneurs, chantiers et comptes professionnels. Partagez volume, zones et heures limites; nous alignons capacité locale."},
            {"question": "Courses jour même pour fournitures électriques?", "answer": "Jour même disponible dans nos zones selon heures limites et capacité. Plages convenues pour que entrepreneurs reçoivent matériaux à temps."},
            {"question": "Comment les entrepreneurs suivent la livraison?", "answer": "Lien de suivi avec statut et ETA en direct. Partagez avec entrepreneurs ou contacts chantier."},
            {"question": "Quelles villes pour livraison électrique?", "answer": "RGT, Hamilton, Kitchener-Waterloo, London, Niagara et autres régions ontariennes."},
        ],
        [{"path": "serviceAreas", "label": "Zones desservies"}],
    ),
    "plumbing-supply-delivery": _faq(
        "plumbing-supply-delivery",
        "Livraison plomberie: FAQ grossiste et entrepreneur",
        "FAQ livraison plomberie — tuyaux, fixtures et tournées grossistes en Ontario.",
        "Maisons de plomberie ont besoin de livraison prévisible vers entrepreneurs et sites commerciaux. Porterchain exécute tournées récurrentes avec véhicules adaptés.",
        [
            {"question": "Livrez-vous pour grossistes plomberie?", "answer": "Oui. Tournées récurrentes vers entrepreneurs et comptes professionnels. Indiquez routes, volume et plages; nous alignons capacité."},
            {"question": "Que transportez-vous pour plomberie?", "answer": "Fourgons et camions cube pour tuyaux, fixtures, raccords et stock palettisé. Poids et dimensions pour courses spécialisées."},
            {"question": "Tournées récurrentes aux mêmes entrepreneurs?", "answer": "Oui. Tournées récurrentes au cœur du modèle. Chauffeurs et véhicules alignés à vos motifs hebdomadaires ou quotidiens."},
            {"question": "Où livrez-vous plomberie?", "answer": "RGT, Toronto, Mississauga, Brampton, Vaughan, Hamilton, Kitchener-Waterloo et autres zones ontariennes."},
        ],
        [{"path": "serviceAreas", "label": "Zones desservies"}],
    ),
    "delivery-pricing": _faq(
        "delivery-pricing",
        "Tarification livraison: comment les marchands sont tarifés",
        "Comment Porterchain tarifie livraison récurrente et jour même. Tarification par arrêt, zone et volume.",
        "La tarification Porterchain est conçue pour marchands à volume récurrent. Coût aligné à routes, zones et volume — prévisible sans frais surprises.",
        [
            {"question": "Comment la tarification est-elle structurée?", "answer": "Généralement par arrêts, zones et volume. Tournées récurrentes souvent tarif par arrêt ou par tournée. Jour même peut être par zone ou distance. Confirmation après analyse de votre volume et zones."},
            {"question": "Volume minimum ou engagement?", "answer": "Nous travaillons avec marchands à besoins récurrents ou réguliers. Minimums et engagement discutés à l'intégration. Pas d'engagement long terme avant confirmation d'adéquation et tarification."},
            {"question": "Tarification par industrie?", "answer": "Oui. Patterns et exigences diffèrent (grossiste vs abonnement, pharmacie vs détail). Tarification adaptée à votre flux et zones."},
            {"question": "Voir tarification pour ma zone?", "answer": "Nous desservons RGT, Toronto, Mississauga, Brampton, Kitchener-Waterloo, London, Niagara, Oshawa et autres régions. Contactez-nous avec volume et zones pour tarification."},
        ],
        [{"path": "pricing", "label": "Tarification"}, {"path": "serviceAreas", "label": "Zones desservies"}],
    ),
    "onboarding": _faq(
        "onboarding",
        "Intégration marchand: comment démarrer",
        "Comment fonctionne l'intégration Porterchain. Étapes, délais et attentes.",
        "Démarrer avec Porterchain est conçu pour être rapide. Nous ciblons volume, zones et flux pour aligner capacité et SLA sans longs formulaires.",
        [
            {"question": "Combien de temps prend l'intégration?", "answer": "La plupart des marchands sont prêts en jours, pas semaines. Confirmation couverture, alignement capacité, accès suivi et rapports. Intégrations API peuvent prendre plus longtemps — nous le précisons dès le départ."},
            {"question": "Que dois-je fournir pour démarrer?", "answer": "Volume (arrêts par semaine), zones de livraison et plages ou exigences. Feuilles de calcul ou courriel pour commencer; pas d'intégration complète le jour un."},
            {"question": "Contrat ou engagement?", "answer": "Nous confirmons adéquation et tarification avant engagement. Objectif: mise en service rapide pour voir comment la livraison fonctionne avec un partenaire."},
            {"question": "Démarrer dans ma ville?", "answer": "Nous opérons RGT, Toronto, Mississauga, Brampton, Vaughan, Markham, Oakville, Burlington, Oshawa, Kitchener-Waterloo, London, St. Catharines et Niagara."},
        ],
        [{"path": "onboarding", "label": "Comment fonctionne l'intégration"}],
    ),
    "csv-uploads": _faq(
        "csv-uploads",
        "Téléversements CSV et commandes en lot",
        "Comment utiliser CSV pour commandes récurrentes ou en lot avec Porterchain.",
        "Beaucoup de marchands gèrent arrêts en feuilles de calcul. Nous acceptons CSV pour envoyer tournées sans intégration immédiate.",
        [
            {"question": "Supportez-vous CSV pour commandes?", "answer": "Oui. Soumettez commandes ou arrêts par CSV pour exécuter vos tournées. Utile pour courses récurrentes ou lots ponctuels. Format et colonnes confirmés à l'intégration."},
            {"question": "Quel format CSV?", "answer": "Modèle avec adresse, contact, plage horaire et champs référence. Même format réutilisable pour téléversements récurrents."},
            {"question": "Passer de CSV à API plus tard?", "answer": "Oui. Beaucoup commencent par CSV ou courriel puis ajoutent API. Nous aidons à la transition sans rupture."},
            {"question": "Quelles industries utilisent CSV?", "answer": "Torréfacteurs, pharmacies, marques beauté et autres marchands à tournées récurrentes utilisent souvent CSV dans nos zones."},
        ],
        [{"path": "onboarding", "label": "Comment fonctionne l'intégration"}],
    ),
    "api-integrations": _faq(
        "api-integrations",
        "API et intégrations pour la livraison",
        "Comment intégrer Porterchain via API et quelles intégrations nous supportons.",
        "Porterchain offre accès API pour pousser commandes, récupérer suivi et automatiser depuis vos systèmes.",
        [
            {"question": "Avez-vous une API commandes et suivi?", "answer": "Oui. Création commandes, mises à jour statut et suivi pour intégrer livraison dans e-commerce, ERP ou outils ops. Documentation et soutien à l'intégration."},
            {"question": "Avec quoi puis-je intégrer?", "answer": "Vos systèmes via API. Nous travaillons avec marchands sur plateformes e-commerce, abonnements et outils internes."},
            {"question": "Durée intégration API?", "answer": "Dépend de votre système. Portée et délais définis à l'intégration. Beaucoup commencent par CSV puis ajoutent API."},
            {"question": "API dans toutes les zones?", "answer": "Oui. Même couverture que CSV ou autres méthodes dans toutes nos zones ontariennes."},
        ],
        [{"path": "integrations", "label": "Intégrations"}],
    ),
    "local-service-areas": _faq(
        "local-service-areas",
        "Zones desservies: où nous livrons",
        "Couverture Porterchain: RGT, Toronto, Mississauga, Kitchener-Waterloo, London, Niagara, Oshawa et plus.",
        "Nous exécutons livraison récurrente et jour même dans des zones locales définies en Ontario. Chaque région a couverture dédiée pour livraison fiable.",
        [
            {"question": "Quelles villes et régions desservez-vous?", "answer": "RGT (Toronto, Mississauga, Brampton, Vaughan, Markham, Oakville, Burlington), Oshawa et Durham, Kitchener-Waterloo, London, St. Catharines et Niagara. Page dédiée par zone."},
            {"question": "Livrez-vous à mon adresse?", "answer": "Consultez nos pages zones. En zone listée, nous pouvons généralement vous servir. Contactez-nous avec adresse ou code postal pour confirmation."},
            {"question": "Hors du RGT?", "answer": "Oui. Kitchener-Waterloo, London, Niagara, St. Catharines, Oshawa et autres régions. Voir le hub zones desservies."},
            {"question": "Jour même dans ma zone?", "answer": "Disponible selon heures limites et capacité. Voir page zone ou contactez-nous avec volume et zones typiques."},
        ],
        [{"path": "serviceAreas", "label": "Voir toutes les zones desservies"}],
    ),
    "pharmacy-delivery": _faq(
        "pharmacy-delivery",
        "Livraison pharmacie: conformité et patients",
        "FAQ livraison pharmacie et ordonnances: conformité, chaîne de custody et zones.",
        "Porterchain soutient livraison pharmacie et patients avec suivi et visibilité chaîne de custody.",
        [
            {"question": "Livrez-vous ordonnances?", "answer": "Oui. Tournées avec manutention et suivi appropriés de la collecte à la livraison."},
            {"question": "Chaîne de custody et conformité?", "answer": "Suivi complet et visibilité statut pour chaque course. Besoins conformité discutés à l'intégration."},
            {"question": "Zones pour pharmacie?", "answer": "RGT, Toronto, Mississauga, Brampton, Kitchener-Waterloo, London, Niagara, Oshawa, St. Catharines et autres régions."},
            {"question": "Tournées récurrentes cliniques ou patients?", "answer": "Oui. Tournées récurrentes alignées à votre horaire avec plages constantes si nécessaire."},
        ],
        [{"path": "serviceAreas", "label": "Zones desservies"}],
    ),
    "coffee-roaster-delivery": _faq(
        "coffee-roaster-delivery",
        "Livraison torréfacteur: grossiste et cafés",
        "FAQ livraison torréfacteurs: grossiste, cafés, abonnement et jour même.",
        "Torréfacteurs utilisent Porterchain pour grossiste vers cafés, boîtes abonnement et jour même quand la fraîcheur compte.",
        [
            {"question": "Livraison grossiste vers cafés?", "answer": "Oui. Tournées grossiste récurrentes avec suivi pour que cafés sachent quand attendre la livraison."},
            {"question": "Jour même pour torréfaction fraîche?", "answer": "Disponible dans nos zones. Heures limites et plages convenues pour comptes clés ou abonnés."},
            {"question": "Quels véhicules pour café?", "answer": "Voitures, fourgons ou vélos cargo selon volume et densité urbaine."},
            {"question": "Où livrez-vous pour torréfacteurs?", "answer": "RGT, Toronto, Mississauga, Brampton, Kitchener-Waterloo, London, Niagara, Oshawa et autres régions."},
        ],
        [{"path": "serviceAreas", "label": "Zones desservies"}],
    ),
    "cosmetics-delivery": _faq(
        "cosmetics-delivery",
        "Livraison cosmétiques et marques beauté",
        "FAQ fulfillment D2C et abonnement pour marques beauté.",
        "Marques beauté utilisent Porterchain pour D2C et abonnements avec collecte et livraison récurrentes et liens de suivi.",
        [
            {"question": "D2C et abonnements?", "answer": "Oui. Collecte et livraison récurrentes avec lien de suivi par envoi."},
            {"question": "Jour même pour promotions?", "answer": "Disponible dans nos zones. Capacité adaptable pour lancements ou pics."},
            {"question": "Suivi pour clients?", "answer": "Lien de suivi par envoi. Réduit soutien « où est ma commande? »."},
            {"question": "Régions pour beauté?", "answer": "RGT, Toronto, Mississauga, Brampton, Kitchener-Waterloo, London, Niagara, Oshawa et autres zones."},
        ],
        [{"path": "serviceAreas", "label": "Zones desservies"}],
    ),
    "same-day-delivery": _faq(
        "same-day-delivery",
        "Livraison jour même: heures limites, zones et fiabilité",
        "FAQ jour même: fonctionnement, heures limites et disponibilité.",
        "Jour même disponible dans nos zones. Heures limites, plages et capacité convenues pour fiabilité.",
        [
            {"question": "Comment fonctionne le jour même?", "answer": "Soumission avant heure limite convenue; collecte et livraison le même jour. Plages et ETA via suivi."},
            {"question": "Quelles heures limites?", "answer": "Varient par zone et volume. Confirmées à l'ouverture du compte."},
            {"question": "Jour même dans ma ville?", "answer": "Offert dans RGT, Toronto, Mississauga, Brampton, Kitchener-Waterloo, London, Niagara, Oshawa, St. Catharines et autres."},
            {"question": "Mélanger jour même et récurrent?", "answer": "Oui. Tournées récurrentes et jour même pour pics — un partenaire, un tableau de bord."},
        ],
        [{"path": "serviceAreas", "label": "Zones desservies"}],
    ),
    "how-much-does-local-delivery-cost-toronto": _faq(
        "how-much-does-local-delivery-cost-toronto",
        "Combien coûte la livraison locale à Toronto?",
        "Tarification livraison locale Toronto et RGT. Comment Porterchain tarifie récurrent et jour même — et obtenir un devis.",
        "Le coût dépend du volume, type de tournée (récurrent vs jour même) et zones. Porterchain tarifie généralement par arrêts, zones et volume. Partagez arrêts typiques par semaine et zones pour un devis Toronto/RGT.",
        [
            {"question": "Tarification différente Toronto vs autres villes RGT?", "answer": "Peut varier par zone dans le RGT. Tarification pour vos zones précises quand vous partagez volume et routes."},
            {"question": "Qu'est-ce qui affecte le coût?", "answer": "Nombre d'arrêts, récurrent vs jour même, plages horaires et véhicule (vélo cargo vs fourgon)."},
            {"question": "Obtenir un devis Toronto?", "answer": "Contactez-nous avec volume, zones et exigences horaires. Confirmation couverture et tarification — sans engagement avant adéquation."},
            {"question": "Ailleurs en Ontario?", "answer": "Oui. Kitchener-Waterloo, London, Niagara, St. Catharines, Oshawa et autres. Page zone par région."},
        ],
        [{"path": "pricing", "label": "Tarification"}, {"path": "serviceAreas", "label": "Zones desservies"}],
    ),
    "how-to-set-up-recurring-deliveries-coffee-roaster": _faq(
        "how-to-set-up-recurring-deliveries-coffee-roaster",
        "Comment configurer livraisons récurrentes pour un torréfacteur",
        "Configurer livraison récurrente torréfaction: grossiste cafés, abonnements et jour même avec Porterchain.",
        "Partagez volume et routes (ex. livraisons cafés hebdomadaires); nous confirmons couverture et capacité; vous êtes opérationnel avec un partenaire et un tableau de bord. CSV ou feuille de calcul pour démarrer.",
        [
            {"question": "Que fournir pour démarrer?", "answer": "Volume hebdomadaire, zones et plages (ex. matin pour cafés). Feuille de calcul ou modèle CSV. Confirmation capacité et SLA."},
            {"question": "Grossiste et abonnement avec un partenaire?", "answer": "Oui. Beaucoup de torréfacteurs combinent grossiste cafés et abonnements/D2C avec Porterchain."},
            {"question": "Jour même pour torréfaction fraîche?", "answer": "Disponible dans nos zones avec heures limites et plages convenues."},
            {"question": "Zones pour torréfacteurs?", "answer": "RGT, Kitchener-Waterloo, London, Niagara, Oshawa et autres régions ontariennes."},
        ],
        [{"path": "onboarding", "label": "Comment fonctionne l'intégration"}, {"path": "serviceAreas", "label": "Zones desservies"}],
    ),
    "how-pharmacy-courier-delivery-works-gta": _faq(
        "how-pharmacy-courier-delivery-works-gta",
        "Comment fonctionne la livraison pharmacie dans le RGT",
        "Comment Porterchain exécute livraison pharmacie et patients dans le RGT: conformité, suivi, tournées récurrentes.",
        "Vous partagez besoins (patients, cliniques, récurrent); nous confirmons couverture RGT et configurons tournées avec suivi et chaîne de custody. Nous gérons flotte et dernier kilomètre; vous avez un tableau de bord.",
        [
            {"question": "Suivi et chaîne de custody?", "answer": "Suivi complet collecte à livraison. Visibilité pour audit; besoins conformité à l'intégration."},
            {"question": "Tournées récurrentes patients ou cliniques?", "answer": "Oui. Quotidien ou hebdomadaire avec plages constantes si nécessaire."},
            {"question": "Zones RGT pharmacie?", "answer": "Toronto, Mississauga, Brampton, Vaughan, Markham, Oakville, Burlington, Oshawa et RGT élargi. Aussi Kitchener-Waterloo, London, Niagara."},
            {"question": "Démarrer livraison pharmacie?", "answer": "Contactez-nous avec volume, zones et exigences conformité ou plages. Confirmation couverture et intégration."},
        ],
        [{"path": "onboarding", "label": "Comment fonctionne l'intégration"}, {"path": "serviceAreas", "label": "Zones desservies"}],
    ),
    "how-to-onboard-merchant-csv-upload": _faq(
        "how-to-onboard-merchant-csv-upload",
        "Comment intégrer un marchand avec téléversement CSV",
        "Intégration marchand par CSV: format, processus et passage à l'API.",
        "Nous confirmons zones et volume, fournissons modèle CSV (adresse, contact, plage, référence); le marchand téléverse ou envoie par courriel; nous exécutons la tournée. Intégration en jours. Passage API possible plus tard.",
        [
            {"question": "Colonnes ou format CSV?", "answer": "Modèle avec champs requis: adresse livraison, contact, plage ou ID référence. Format confirmé à l'intégration."},
            {"question": "CSV pour tournées récurrentes?", "answer": "Oui. Fichier mis à jour chaque cycle; même format réutilisable avec suivi."},
            {"question": "Passer à l'API plus tard?", "answer": "Oui. Nous aidons la transition CSV vers API sans interruption."},
            {"question": "Quelles industries utilisent CSV?", "answer": "Torréfacteurs, pharmacies, beauté et autres marchands récurrents ou en lot."},
        ],
        [{"path": "onboarding", "label": "Comment fonctionne l'intégration"}, {"path": "integrations", "label": "Intégrations"}],
    ),
    "what-vehicle-right-for-parcel-volume": _faq(
        "what-vehicle-right-for-parcel-volume",
        "Quel véhicule pour mon volume de colis?",
        "Choisir véhicule Porterchain selon volume, dimensions et type de marchandise — voiture, fourgon, camion cube.",
        "Le bon véhicule dépend du volume, dimensions colis, accès et type de marchandise. Porterchain aligne capacité sans que vous gériez une flotte.",
        [
            {"question": "Comment choisir le véhicule?", "answer": "Partagez volume typique, dimensions/poids et accès (chantier, comptoir, entrepôt). Nous recommandons voiture, fourgon métier, fourgon cargo ou camion cube."},
            {"question": "Petit volume ou colis légers?", "answer": "Voitures ou vélos cargo pour densité urbaine et petits colis (cafés, pharmacie légère, D2C)."},
            {"question": "Palettes ou matériaux construction?", "answer": "Camionnettes, fourgons cargo ou camions cube 16 pi selon charge et accès chantier."},
            {"question": "Changer de véhicule en grandissant?", "answer": "Oui. Nous ajustons capacité et véhicule quand volume ou mix de marchandises évolue — sans embauche ni achat véhicule de votre côté."},
        ],
        [{"path": "serviceAreas", "label": "Zones desservies"}, {"path": "pricing", "label": "Tarification"}],
    ),
}
