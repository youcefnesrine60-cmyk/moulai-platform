# Matrice — consolidation locale de l’interface

10 novembre 2026. Présent, raccordé et vérifié sont des états distincts.
Un test mocké n’est pas une preuve d’authentification ou de persistance.

| Exigence | Présent / raccordé | Vérification actuelle | Limite ou suite |
| --- | --- | --- | --- |
| 1. Identité/design partagé | Logo, favicon, Sora/Tajawal et Gateway existants ; tokens de contrôle et surface de travail consolidés | Empreintes PNG/manifestes, 36 vues, contrastes et tests de thèmes | Originaux lourds conservés ; mesure réseau physique à faire |
| 2. Accès simple | Actions courtes, badge test, détails de session, inscription locale seulement | Unit FR/EN/AR local/staging ; lecture réelle HTTPS ; clavier et captures | Pas d’inscription autonome en staging fermé |
| 3. Reprise précise | Aide liée au coffre existant, sept champs/30 min ; pas de fichiers/consentements | Régressions d’inscription et conservation des textes lors de l’aide | Aucun nouveau stockage ; reprise staging et autres formulaires non promise |
| 4. Lisibilité | Travail opaque, contrôles partagés, flou réduit ; accueil illustré conservé | Axe 18 cas, bornes RGB, revue FR/AR, Light/Dark | Axe incomplet sur certains fonds illustrés ; examen humain requis |
| 5. Navigation/contexte | Groupes intégrés et liens autorisés ; entreprise/restaurant et succursale ; section/date Dining dans URL | Vraies vues et routes ; garde-fou sortie/rubrique/branche ; expiration ne bloque pas | Pas de reprise universelle de tous filtres et positions |
| 6. Rôles | Vue initiale cuisine/finance selon capacités ; menus plateforme selon permissions explicites | Tests de présentation et 14 étapes avec comptes distincts | Pas de nouveau tableau de bord ni de priorité métier inventée |
| 7. Formulaires | Champs visibles, obligation/facultatif, formats, état busy, protection des saisies sur formulaires décrits | Unit et conservation réelle pendant aide/sortie ; erreur récupérable | Prix/admin legacy : couverture de garde-fou à étendre ; pas de promesse générale |
| 8. États | Chargement/vide/403/500 distincts ; mutation perdue incertaine et relecture avant répétition | 143 cas ciblés, retest financier sans POST automatique ; perte réelle d’une réponse restaurant | Injection HTTP unitaire explicitement mockée ; pas de panne distante revendiquée |
| 9. Abonnement/paiement | Résultats serveur et devise conservée, taux/score corrects, comparaison ancien/nouveau, étapes séparées | Vraie route PG pour état période ; tests actif/scheduled/absent ; calculs inchangés | Fonctions incluses/exclues détaillées et facture SaaS autonome à raccorder |
| 10. Listes/terrain | Filtres/compteurs planning et journal existants ; bornes serveur conservées | Régressions des vues affectées et pas de liste vide sur erreur | Pas de nouvel audit général de tous tableaux |
| 11. Client mobile | QR/menu/visite/panier/commande/facture protégé ; sous-total indicatif exact | 14 contrôles locaux réels, répétition sans doublon, 12 captures client | Options produit à contractualiser ; aucun scan physique effectué |
| 12. Aide/agent | Documentation et panneau conversationnel distincts ; voix native conditionnelle existante | Aide, focus et brouillon vérifiés ; aucun appel IA | Connecteur, outils autorisés, secteur/formule/droits, confirmations, quotas et budget à intégrer séparément |
| 13. FR/EN/AR | Nouveaux textes complets, BDI, devise et date UTC | Parité des clés, captures, absence de clés visibles sur les états testés | Relecture linguistique finale propriétaire ; données utilisateur non traduites |
| 14. Accessibilité/performance | Objectif AA, contrastes effectifs, cibles/focus, polices et rendu responsive | Axe 18 + 6 cas sans violation signalée ; 320 px et émulation 640 px/DPR 2 ; mesures Vite | Pas de certification, vrai zoom navigateur/lecteur d’écran/téléphone/charge distant non validés |
| 15. Impression | Lignes figées et date finalisée raccordées au lecteur de visite ; impression et documents QR existants distincts | Projection réelle sans provenance privée ; 3 langues ; fixture de mise en page explicite séparée | Imprimante/PDF physique non testé ; QR émis par action humaine, jamais secret de visite |
| 16. Réalisation progressive | Lots socle, métier ciblé, qualité et suites documentés | Journaux et comparatifs archivés, échecs intermédiaires conservés | Ce jalon ne clôture pas les 17 thèmes globalement |
| 17. Sauvegarde | Branche codex uniquement, liste explicite de sources | Empreintes, secrets/exclusions, index, SHA distant et autres branches à contrôler à publication | Aucune activation de staging, merge ni force push |

Les preuves de migration/récupération précédentes restent valides et n’ont pas été
rejouées à distance. Les nouvelles données, commandes, documents et fonds sont
fictifs et locaux. Le test PG sélectionné travaille sur une base jetable distincte.
