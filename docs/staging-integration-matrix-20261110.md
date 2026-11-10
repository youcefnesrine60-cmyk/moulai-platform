# Matrice d’intégration — 10 novembre 2026

Existant = code présent ; raccordé = interface/routes reliées ; vérifié = preuve
réellement exécutée dans le périmètre indiqué. Aucun statut local ne signifie
validation distante ou production. Les détails techniques sensibles restent privés.

| Exigence | Interface | Route / service | État / preuve | Limite restante |
| --- | --- | --- | --- | --- |
| Titre, favicon, nouveaux PNG et placement | Accès, espace, tables | Shared header / AssistanceLaunchers / i18n | Raccordé et vérifié : 36 captures, empreintes, 50 tests ciblés | Validation visuelle du propriétaire |
| Authentification sans scénario fictif | `/access`, formulaire natif Keycloak | OIDC local / identité persistée | E2E local : nouveau compte natif, même identité après reconnexion | Realm distant fermé invité, non activé |
| HTTPS sans contournement | Accès et redirections | CA CurrentUser explicitement autorisée / SAN IP | Chromium et Python confiance système ; Node avec magasin système | Certificat serveur à renouveler avant le 7 décembre ; domaine staging distinct |
| Expiration 5 min | Avertissement et reconnexion | Session locale, sans auto-refresh | Temps réel observé, aucun renvoi métier | Autres formulaires non récupérables ; staging non vérifié |
| Brouillon volontaire | Inscription locale | Coffre chiffré lié issuer/subject | Sauvegarde/reprise de 7 champs et 30 min, reconnexion requise | Aucun fichier/consentement ni soumission automatique ; pas de promesse staging |
| Dossier et acceptations | Inscription autonome locale | Enrollment / documents versionnés | Nouveau dossier UI, versions fictives traçables, rechargement | Textes définitifs et rétention réelle à valider avant clients réels |
| Pays déclaré/validé distinct | Dossier puis revue administrative | Billing country / `tenant.billing_country.manage` | UI et PostgreSQL, refus des comptes non habilités | Pas de vérification commerciale réelle de documents |
| Entreprise, restaurant, succursale et essai | Finaliser l’inscription | Finalisation transactionnelle / trial | E2E local sans CLI entreprise, répétition identique | Essai réel de 30 jours non attendu : preuve distincte de refus immédiat |
| Fin d’essai pour recette financière | Aucun contrôle utilisateur de changement de dates | Script local strictement gardé | Deuxième entreprise vide dédiée, dates initiales conservées | Fixture explicite, pas un historique commercial observé |
| B pays/devise et offre | Consultation de l’offre propriétaire | Pricing / country context / snapshots | B 3 000 DZD, version inchangée, 47 régressions PG O4 | Tarifs de fonctionnalités absents restent bloquants pour les offres concernées |
| Électronique −2 % | Offre et checkout | Decimal / ajustement final | 3 000 → 2 940 DZD ; 5 assertions monétaires exactes | Aucun changement de B, aucune conversion devise |
| Justificatif distinct des fonds | Paiement propriétaire puis revue dédiée | Receipt / funds review / `payments.review` | E2E UI deux paiements, dépôt reste pending, propriétaire/pays reviewer refusés | Fonds/PDF explicitement fictifs, aucune banque connectée |
| File de revue sans doublons | Cartes de paiements | `GET /api/web/platform/saas-payments` | Corrigé produit cartésien, test vraie route PG et UI finale | Pas d’élargissement des droits |
| Activation et renouvellement uniques | Checkout, revue et retour propriétaire | Payment approval / subscription activation | Paiements 6/7 et abonnements 15/16 : répétitions et connexion DB indépendante | Renouvellement futur scheduled, pas d’attente calendaire simulée comme exécution réelle |
| Conservation des périodes | Abonnement et historiques | Snapshot / service de renouvellement | Connexion READ ONLY : période suivante commence à l’échéance existante | Pas de réécriture d’historique |
| Offre obsolète | Remplacement explicite de l’offre | Supersession / guards | Preuve UI du 9 novembre conservée ; régressions PG actuelles | Pas de nouvelle recette UI revendiquée pour cette variante inchangée |
| Pays à plusieurs échéances | Admin / contexte de chaque période | Décision unique, application au prochain renouvellement | Régressions PG actuelles deux échéances, absence double application | Pas de nouvelle UI multi-échéances ni validation distante |
| QR → menu → commande | Client et personnel intégrés | Dining O4 routes et services locaux | Recette rejouée 13 contrôles / 12 captures, reprise réponse perdue | Scan téléphone physique non testé ; sas staging fermé bloquera QR public |
| Cuisine → service → facture → règlement → départ/nettoyage | Tables, personnel, client | Permissions D1 / facture Decimal / paiements locaux | E2E local actuel, reload et idempotence | Fonds fictifs, aucun remboursement/notification automatique ajouté |
| Assistant | Icône et panneau d’état | Aide locale, service IA absent/inactif | Panneau indisponibilité vérifié, aucune réponse prédéfinie présentée IA | Conversation/voix/actions : intégration et budget séparés |
| Image déployable | SPA compilée dans nouvel hôte | Docker / run_staging / image check | Build et smoke hors réseau, ni lifespan ni DB ni fournisseur démarré | Démarrage distant complet/runtime/OIDC/persistance encore à faire |
| Migration et récupération | Plan staging existant | Répétition Neon isolée précédente | Preuves antérieures préservées, pas de nouvelle écriture distante | Sauvegardes identité/fichiers/clés distinctes et rôle runtime à préparer |
| Ressources et coût | Render propriétaire | Relevé de captures, non inspection outil | Free existant conservé ; proposition supplémentaire 32,25 USD | Autorisation payante absente, limites sous charge non mesurées |
| Sauvegarde GitHub | Branche codex uniquement | Commit/push normaux, contrôles de références | Résultat final dans livraison locale | Aucun déploiement, main et autres références à contrôler avant/après |

Les tentatives interrompues restent archivées : elles ne sont pas écrasées par
les preuves finales. Les demandes financières fictives non abouties restent
en attente sans réaffectation automatique. Les comptes sont synthétiques mais
effectivement authentifiés et leurs données sont persistées localement.
