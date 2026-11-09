# D1 — Recette finale locale des tables et réservations

Cette livraison poursuit le socle validé. Les opérations de recette utilisent les véritables routes, transactions et autorisations sur PostgreSQL local jetable. L’émetteur d’identités reste simulé localement ; aucune connexion Keycloak réelle, notification, transaction monétaire réelle ou génération IA n’est effectuée.

## En-tête et apparence

Le bloc logo/signature occupe la colonne centrale d’une grille à colonnes latérales égales. Les contrôles ne décalent pas son centre ; sur mobile ils occupent une ligne distincte. Les PNG officiels `light01` et `dark01` sont inchangés, sans filtre ni déformation.

Quatre choix sont distincts : **Automatique, Clair, Sombre, Système**. Système conserve sa signification existante. Automatique utilise le fuseau vérifié de la succursale ; avant sélection, celui du navigateur. La configuration explicite est `frontend/public/appearance-schedule.json` : **07:00–19:00 clair, puis sombre**, proposition à faire approuver, pas une règle commerciale acquise. Les bornes sont inclusives au début et exclusives à la fin. Une plage traversant minuit est prise en charge.

La configuration est validée et insérée au build avant le script synchrone d’initialisation du thème. Une modification des heures nécessite donc une reconstruction/reprise du serveur Vite. L’horloge, le retour d’onglet et le changement de fuseau actualisent le thème sans rechargement. Le choix manuel reste prioritaire. Un indice de fuseau non sensible, propre à l’onglet et à la succursale de l’URL, réduit le flash avant restauration de session ; il ne donne aucune autorisation. La langue et les brouillons ne dépendent pas du thème.

## Autorisations financières séparées

| Opération | Capacité serveur | Complément |
| --- | --- | --- |
| Consulter avances, factures et commandes sources | `finance.read` | Le service seul ne voit pas ces documents |
| Constater une réception de fonds | `collect` | Acteur humain habilité, constat explicite |
| Créer un brouillon de facture | `invoices.create` | Données et provenance exactes requises |
| Finaliser une facture | `invoices.finalize` | Révision, cohérence et verrouillages contrôlés |
| Affecter une avance | `advances.allocate` | Également exigée si la finalisation doit affecter une avance |
| Consulter/imprimer un justificatif en tant que personnel | `finance.read` et autorisation du parcours | Le client conserve son accès propre vérifié |

Les droits s’appliquent au restaurant et à la succursale. Les routes directes recontrôlent l’identité et les droits à chaque opération. Une révocation s’applique aussi à une session déjà ouverte. L’absence de données, le refus d’accès et l’échec de chargement restent des états distincts ; une relecture échouée après commit ne déclenche aucune nouvelle tentative financière automatique.

La migration additive **D1b → `d1c20261104`** étend seulement la contrainte du vocabulaire des capacités. Aucun droit personnel n’est accordé par la migration. D1a/D1b et leurs historiques ne sont pas réécrits. Les anciennes installations doivent préparer cet upgrade et leurs attributions explicites avant usage des nouveaux pouvoirs. Aucun upgrade permanent n’est autorisé par cette recette. Le downgrade est volontairement refusé sans réconciliation séparément revue des droits existants.

## Guide court de recette manuelle

1. Depuis `D:\MoulAI`, lancer `.\.venv\Scripts\python.exe -I -B scripts/run_dining_local.py`. Ouvrir <http://127.0.0.1:5574/dining-local>. Ne pas ajouter `--visual-fixtures` pour cette recette : les réservations illustratives existantes empêchent légitimement certaines modifications de paramètres. Chaque lancement possède sa propre base neuve ; aucune base permanente n’est visée.
2. Déplier **Session active**, choisir le profil fictif puis **Ouvrir la session**. Vérifier le profil effectivement actif et le restaurant/la succursale. La sélection seule n’authentifie pas. À chaque changement, les lectures et formulaires précédents sont invalidés.
3. Comme **propriétaire**, ouvrir Configuration : paramètres/fuseau/devise, horaires, table, critères, événement, tarifs et habilitations. Les identités/membres éligibles, un socle minimal de référentiels et une commande alimentaire historique de 6 000 DZD sont préparés par le lanceur. Leur création n’est pas prétendue réalisée par ces écrans.
4. Pour reproduire exactement le cas de recette : durée 90 minutes ; table T1 à **986,66 DZD/heure** ; menu de deux unités à **10,005 DZD** ; préparation forfaitaire **0 DZD**. Cela donne **1 479,99 + 20,01 = 1 500 DZD**. Ces prix sont exclusivement fictifs. Créer leurs versions par le formulaire Tarifs, sans chevauchement ; ne jamais les reprendre comme grille commerciale.
5. Comme **service manager**, créer la demande avec personnes, période, tables cochées, événement et critères ; préparer le devis détaillé et noter sa référence courte `R-…`. La référence technique reste copiable dans les détails. Passer au profil **client** pour accepter cette même version ; revenir au service pour l’accord restaurant sur le menu spécial.
6. Enregistrer la validation humaine explicite de toute la période protégée, puis le blocage temporaire. Vérifier son échéance avant la réception des fonds. Une couleur verte ou une fin de nettoyage ne remplace jamais cette validation.
7. Comme **responsable d’encaissement**, enregistrer la réception fictive de 1 500 DZD, sa devise, date et référence. Revenir au service pour le contrôle final et la confirmation atomique. Le lien de consultation/impression suit la langue FR/EN/AR ; l’arabe est RTL. Le QR utilise la vérification locale réelle.
8. À l’heure réelle d’arrivée, utiliser **Voir les actions autorisées** sur la table : table et réservation sont présélectionnées. Saisir la fin prévue et enregistrer l’arrivée. Le serveur revérifie droits, état et conflits.
9. Comme **consultation financière**, vérifier que les documents sont visibles et les formulaires de mutation absents. Comme **facturation**, rapprocher la commande alimentaire fictive, documenter prix exact, devise et arrondi, puis finaliser avec les droits de finalisation et d’affectation. Après rechargement : ventes **6 000 DZD**, avance **1 500**, solde **4 500**, une seule affectation. Une répétition ne doit pas doubler l’action financière.
10. Comme **nettoyage**, constater le départ puis commencer et terminer le nettoyage, en trois actions distinctes. Le profil ne peut pas confirmer la disponibilité d’une réservation. Comme service, réaliser au besoin une nouvelle validation humaine séparée.
11. Créer une seconde réservation future sur T2 (90 minutes à 1 000 DZD/heure), avec ses accords, blocage, réception fictive et confirmation. Comme titulaire de `reservations.cancel_before_arrival`, annuler avec motif/origine. Le créneau est libéré, le QR devient invalide et la réception reste enregistrée pour traitement humain. Les annulations après arrivée/facturation restent bloquées.

Pour les choix d’heure ambigus, seul le résolveur authentifié détermine si une occurrence doit être choisie. Exemple de recette distinct : succursale fictive Europe/Paris, 31 octobre 2027 à 02:30 ambigu ; 03:30 ordinaire ; 28 mars 2027 à 02:30 inexistant. Ne pas changer le fuseau d’une succursale ayant déjà des engagements pour contourner une règle.

## Reproduction automatisée ciblée

La revue doit être prête avant Playwright. Les commandes ne téléchargent rien et ne doivent viser aucune autre URL.

```powershell
Set-Location D:\MoulAI
$env:PATH = 'D:\MoulAI\artifacts\frontend-tooling\node-v24.22.1-win-x64;' + $env:PATH
.\.venv\Scripts\python.exe -I -B scripts/run_dining_local.py
# Dans un second terminal, une fois les ports 5574/5581 prêts :
Set-Location D:\MoulAI\frontend
$env:DINING_FINAL_SUITE = 'ui'
node node_modules/@playwright/test/cli.js test -c playwright.dining-final.config.ts --grep 'complete UI rehearsal'
```

Le test UI complet écrit de véritables données fictives et doit partir d’une revue neuve. Il ne rejoue pas automatiquement les paiements. Les tests de présentation utilisent un harness HTTP simulé et sont signalés dans leurs captures ; ils ne constituent pas une preuve de transactions. Pour arrêter, utiliser uniquement le `stop-request` de l’instance active décrit dans `docs/dining-workspace-local.md`, puis vérifier `safety.json`. Ne pas lancer le cluster natif de tests en parallèle de cette revue sur 55432.

## Ergonomie et limites restantes

- Résumé des cartes conservé, détails secondaires repliables, date de contexte unique et dates conservées pour les périodes multi-jours. Les faits physiques restent indépendants du planning.
- Cases à cocher avec libellés/capacité/état et résumé de sélection ; parcours clavier, pas de sélection multiple native.
- Actions contextualisées et libellées précisément. Les transitions de nettoyage apparaissent dans leur ordre légal ; la fin prévue ne libère aucune table.
- Messages après enregistrement indiquant la prochaine action et le rôle concerné. Une erreur conserve les valeurs dans le formulaire tant que le contexte et les autorisations restent valides ; les changements de profil effacent volontairement les données de l’ancien profil.
- Les accords des deux parties et les validations humaines restent volontairement distincts. Les profils nécessitent encore une navigation entre rubriques et le choix d’un devis dans certains formulaires ; la référence courte facilite la recherche, sans automatiser une approbation.
- Les champs natifs date/heure suivent la présentation du navigateur ; leur aperçu traduit et leur fuseau sont affichés. Pas de preuve fournie pour tous les navigateurs ou une impression papier physique.
- La recette prouve D1 localement, pas une intégration de l’ensemble du Frontend, un fournisseur d’identité distant ou une aptitude à la production. Aucun transport réel, remboursement automatique, annulation après arrivée/facturation ni politique commerciale non approuvée n’est ajouté.
