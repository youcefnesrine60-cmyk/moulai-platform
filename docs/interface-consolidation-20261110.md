# MoulAI™ — consolidation locale de l’interface

10 novembre 2026. Base : `c07191a7e77a7043550eec4f974173fb3857ef3c`, branche
`codex/staging-preparation-20261109`. **Jalon local utilisable, avec réserves.**
L’amélioration de l’interface ne clôture ni l’intégration globale ni la recette
distante. Budget staging toujours en attente, aucun déploiement ni fournisseur
activé. Aucun nouveau schéma, migration ou droit personnel n’est nécessaire.

## Lots et changements

### 1 — Socle et accès

- Réutilisation de Sora et Tajawal déjà auto-hébergées, des tokens Light/Dark,
  composants Radix et images Gateway responsives existantes. Aucun remplacement
  de logo, favicon ou PNG officiel. Les deux accès aide/assistant restent à
  48 × 48 px, à gauche physique ; logo centré et préférences à droite en RTL aussi.
- Actions **Se connecter** / **Créer mon compte** ; inscription visible seulement
  en local authentifié. Le staging fermé n’annonce pas une inscription autonome.
  Indication discrète Environnement de test ; phrase de session courte.
- Détails Keycloak, absence d’auto-refresh, pertes possibles et reprise locale
  dans une disclosure native accessible au clavier. L’aide versionnée est mise
  à jour ; les fonctions déjà raccordées ne sont plus décrites comme futures.
- Sauvegarde volontaire de sept champs texte d’inscription pendant 30 minutes,
  même compte après reconnexion ; aucun fichier, consentement ou mot de passe.
  Aucune généralisation à staging ou aux autres formulaires. Les mécanismes de
  sauvegarde et de sécurité existants ne sont pas modifiés.
- Variables partagées pour hauteur tactile 44 px, texte de contrôle 14 px,
  gouttières, largeur de contenu et surface de travail opaque. Décodage asynchrone
  des images officielles ; dimensions et octets des originaux conservés.

### 2 — Écrans métier existants

- Les espaces authentifiés n’affichent plus une liste de liens vers des modules
  sans transport effectif. Navigation par exploitation, personnel/accès,
  abonnement et administration, avec page active. Les accès plateforme utilisent
  leurs permissions explicites, jamais une déduction du rôle.
- Les contextes entreprise/restaurant existants restent visibles ; la succursale
  est celle du workspace Dining vérifié côté serveur. Cuisine et finance accèdent
  d’abord à leur vue utile selon leurs capacités réelles. Aucune capacité nouvelle
  ni transition métier n’est créée. Section et date Dining sont conservées dans
  l’URL ; ce n’est pas une sauvegarde de formulaire.
- Les surfaces de travail sont opaques ; le fond illustré et la composition
  d’accueil sont conservés. Le flou local le plus fort passe de 20 à 4 px.
- Un registre de **drapeaux**, sans valeur de formulaire, signale les saisies
  non enregistrées avant sortie ou changement de rubrique/succursale. Rester
  conserve l’écran ; quitter est explicite. Aucun envoi n’est mis en attente.
  Un retour imposé à la connexion après expiration n’est jamais bloqué.
- Couverture du garde-fou : dossier initial, réponses documentaires non validées,
  demande de pays, formulaires D1 basés sur FormBox, justificatif SaaS, revue de
  fonds et éditeur des rappels. Les éditeurs legacy restants n’acquièrent pas
  silencieusement cette garantie ; leur traitement est listé dans la matrice.
- Paiements : chargement, liste vide, erreur temporaire et permission refusée
  sont distincts. Une réponse de mutation perdue reste incertaine ; les actions
  concernées sont bloquées jusqu’à une relecture réussie demandée explicitement.
  La relecture ne confirme pas le succès et ne rejoue aucun POST financier.
- Justificatif déposé, fonds vérifiés et état de période sont séparés. La lecture
  SaaS expose maintenant `subscription_status` depuis la jointure déjà autorisée :
  un renouvellement `scheduled` n’est pas présenté comme une période active.
- Une simulation ancienne disparaît lorsque ses choix changent. Sa devise est
  conservée avec le résultat, sans relabelliser un ancien montant. Les taux sont
  affichés comme taux, le score sans devise. B et tous les calculs restent serveur.
  Le −2 % électronique reste appliqué au montant avant ajustement, sans modifier B.
- Remplacement d’offre : ancien montant et nouveau montant sont présentés côte
  à côte, avec motifs et confirmation existants. Aucun transfert de justificatif
  ou de fonds n’est ajouté.
- Client : contexte de table, panier et sous-total **indicatif** exact avec BigInt,
  sans flottants monétaires ; autorité du serveur conservée. Lecture d’une erreur
  et relecture avant répétition ; aucune assimilation scan → installation.

### 3 — Qualité transversale et documents

- FR/EN/AR, BDI pour références et montants, contrôles de reflow et focus. Les noms
  saisis par les utilisateurs restent des données et ne sont pas traduits.
- Le test historique de contraste supposait 60 % alors que le token était à 40 %.
  Il lit maintenant l’alpha effectif et conserve les seuils WCAG. Ce contrôle a
  révélé un contraste insuffisant sur certains fonds extrêmes ; **le fond de
  l’en-tête est porté à 60 %**, sans modification du logo. Les surfaces de lecture
  et de travail sont vérifiées séparément, sans abaisser les seuils pour faire passer
  les tests.
- La facture client possède déjà lignes figées et date de finalisation en base.
  Le lecteur protégé par la preuve de visite retourne désormais seulement
  description, quantité, prix unitaire, montant, révision et date. Il ne lit pas
  le catalogue actuel et ne transmet ni provenance, source de rapprochement ni
  identité du validateur. Aucune écriture financière ou règle fiscale nouvelle.
- L’interface et l’impression client lisent ces champs, avec montants exacts
  formatés sans arrondi navigateur et date explicitement UTC. Ancien contrat sans
  détail : récapitulatif annoncé comme tel. Les documents de recette portent une
  mention fictive. Le tableau reste consultable par défilement limité sur mobile.
- Le QR de validation d’une facture relève du mécanisme de document explicitement
  émis par une personne habilitée. Imprimer depuis la visite ne crée pas de lien
  public ni n’imprime son secret. Les PDF/QR d’émission existants restent distincts
  de cette vue d’impression du navigateur.

### 4 — Suites préparées, sans activation

L’aide documentaire est disponible. `AssistantConversation` présente un historique
local de questions et une indisponibilité explicite : **aucun connecteur génératif
n’est raccordé à ce panneau**. Il ne faut pas attribuer cette absence au paiement
ou à une clé manquante sans preuve. AIClient/ResponseGenerator existent ailleurs ;
ils ne constituent pas à eux seuls un transport d’assistance contextuelle.

La lecture vocale et la reconnaissance native possèdent des contrôles d’activation
volontaire et d’arrêt ; elles exigent des voix locales/une reconnaissance sur
l’appareil disponibles. Aucun micro ni téléchargement de modèle n’a été activé.
Darija, qualité audio et fonctionnement sur téléphone restent non validés.

Avant un agent capable d’agir : définir le transport, contexte autorisé, contrôles
serveur secteur/formule/permissions, outils fermés par défaut, confirmation des
opérations sensibles, idempotence et traçabilité, délais/quotas/repli et protection
des données. L’explication documentaire ne vaut jamais résultat d’une action.
Coût et fournisseur restent à soumettre séparément, sans activation implicite.

| Élément de l’assistance | État constaté | Limite avant intégration |
| --- | --- | --- |
| Documentation et guidage | Aide locale versionnée, contexte d’écran et explications d’éléments existants | Ne réalise aucune action métier |
| Texte conversationnel | Saisie et historique local de questions ; état indisponible explicite | Aucun transport vers un modèle, donc aucune réponse IA générée |
| Microphone | Contrôles volontaires, arrêt et transcription modifiable existants ; reconnaissance sur l’appareil exigée | Disponibilité des packs et qualité FR/EN/AR non validées sur appareil ; aucun pack installé par cette passe |
| Lecture | Voix natives locales uniquement, pause/arrêt ; alternative écrite conservée | Le panneau sans réponse IA ne propose pas d’écouter une réponse inexistante ; voix réelle non testée |
| Exécution | Aucun outil métier accordé à ce panneau | Contrats serveur secteur/formule/droits et confirmations à définir avant toute capacité d’action |
| Coût | Aucun appel ni activation de fournisseur | Chiffrage fournisseur/consommation à approuver séparément ; ne pas déduire un problème de facturation de l’absence de connecteur |

## Vérifications effectivement exécutées

| Vérification | Résultat et portée |
| --- | --- |
| Frontend ciblé | **143 tests réussis / 11 fichiers** ; le dernier fichier paiement a été revalidé après son garde-fou de relecture, et le test d’expiration vérifie aussi un dialogue déjà ouvert |
| PostgreSQL jetable | **1 test réussi, 46 non sélectionnés**, un avertissement anyio déjà importé ; vraie route de lecture paiement/période et sessions indépendantes |
| Parcours restaurant réel local | **14 contrôles réussis** : identités Keycloak distinctes, preuve de visite, ordre/validation/cuisine/service, réponse perdue, facture figée, règlement fictif unique, départ/nettoyage |
| Images de comparaison | **36 avant + 36 après**, FR/EN/AR × clair/sombre × desktop/mobile, mêmes contextes et dimensions ; identité visuelle et titre MoulAI™ vérifiés |
| Axe sur vues principales | **18 états**, aucune violation signalée, hors certification |
| Axe sur facture publique | **6 états mobiles**, aucune violation signalée ; `color-contrast` reste indéterminé automatiquement sur certains fonds illustrés |
| Reflow | 320 CSS px et **6 états à 640 CSS px / densité 2** ; émulation géométrique, pas un test du zoom de l’interface Chrome ou d’un téléphone physique |
| Clavier | Disclosure native, aide/assistant, Escape, retour du focus, maintien de la saisie et décision de sortie vérifiés |
| Impression | Captures FR/EN/AR issues du vrai parcours ; mise en page finale compactée vérifiée sur fixture visuelle séparée, explicitement marquée ; pas de nouvel essai imprimante ou PDF physique |
| Build | Production et staging vérifiés, garde-fous de publication conservés ; aucun déploiement |
| Code | TypeScript, Prettier sur les changements ; Black/Ruff sur les trois Python ; pas de migration |

Les preuves intermédiaires et échecs de préparation restent archivés. Le premier
chargement a trouvé la revue arrêtée ; elle a été redémarrée avec son lanceur
existant. Un libellé de champ enrichi a d’abord changé son nom accessible :
la liaison label/description a été corrigée, sans supprimer le test. Les erreurs
de fixture et d’émulation n’ont pas été présentées comme des succès métier.

Les scripts de recette existants ont été adaptés aux nouveaux libellés de connexion.
Cette adaptation ne signifie pas que chacun a été rejoué : seuls les résultats
énumérés ici sont revendiqués. Les 17 tests du fichier de paiement et les cinq
tests de navigation revalidés en dernier sont inclus dans les 143, sans cumul.

### Documents existants et portée de cette passe

| Document | Composant existant | Vérification et réserve |
| --- | --- | --- |
| QR de table et confirmation de réservation | Émission autorisée et lecteurs publics `public_resources.py` / `public_print.py` | Export serveur de table vérifié ; lecture par URL distincte du décodage et du scan physique |
| Facture alimentaire émise | Snapshot financier et document explicitement émis | Lignes/date/révision et accès par preuve de visite vérifiés dans la nouvelle recette ; aucune émission publique automatique |
| Impression depuis la visite client | Vue `PublicDiningPage` et CSS print | Logo, lignes figées, total, payé, solde, devise et UTC ; disposition finale vérifiée sur fixture visuelle identifiée |
| Facture d’abonnement SaaS | Montants et états persistés, consultation dans le parcours SaaS | Document client imprimable autonome restant à raccorder ; aucune facture commerciale fabriquée |
| Justificatifs de paiement | Dépôt et revue distincts de la réception des fonds | Pas une preuve d’activation à eux seuls ; pas de nouveau document de paiement créé par la présentation |

### Reproduction des contrôles ciblés

Depuis `frontend`, avec le Node local déjà installé :

```powershell
npm.cmd run test -- tests/unit/interface-access.test.tsx tests/unit/unsaved-navigation.test.tsx tests/unit/routes.test.tsx tests/unit/enrollment.test.tsx tests/unit/dining-workspace.test.tsx tests/unit/assistance-launchers.test.tsx tests/unit/dining-public.test.tsx tests/unit/dining-operational.test.tsx tests/unit/operational-access.test.ts tests/unit/brand-surfaces.test.ts tests/unit/appearance.test.ts
npm.cmd run build
npm.cmd run build:staging
npm.cmd run test:guards
node scripts/check-interface-quality.mjs
node scripts/check-interface-reflow.mjs
node scripts/check-invoice-presentation.mjs
node scripts/check-operational-dining-o4.mjs --interface-quality
```

Les recettes navigateur nécessitent la revue HTTPS locale existante, ses comptes
fictifs et la confiance CA déjà autorisée, sans désactiver TLS. La recette Dining
crée des enregistrements de recette locaux ; ne pas la pointer vers une base distante.
Le contrôle PG sélectionné a utilisé le lanceur jetable existant avec
`PYTEST_ADDOPTS=-k test_country_checkout_and_manual_activation_are_single` et
`scripts/rehearse_country_base.py --billing-country`. Il ne constitue pas une
campagne générale ni une migration de la base de revue.

### Accessibilité et performance : limites des mesures

Objectif WCAG 2.2 AA, **sans certification**. Les seuils examinés sont notamment
4,5:1 pour le texte courant et 3:1 pour les grands textes/indicateurs concernés.
Les zones principales visent 44 px, au-dessus du minimum AA de 24 px sous ses
conditions. Sources : [contraste](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html),
[zones de cible](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
et [focus non masqué](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html).
La revue visuelle des fonds, un lecteur d’écran et les appareils physiques restent
nécessaires. Zéro violation Axe ne signifie pas zéro difficulté d’usage.

Sur neuf navigations Vite locales instrumentées : DCL médian **1 193 ms**, FCP
médian **1 304 ms** (plages respectives 967–1 352 et 1 072–1 516 ms).
Les transferts relevés sont d’environ 19–21 Mo en développement instrumenté.
Le routage d’interception Playwright désactive le cache HTTP ; ces valeurs ne
sont ni une mesure de bundle publié ni une prévision mobile/staging.
[Documentation Playwright](https://playwright.dev/docs/api/class-browsercontext#browser-context-route).
Les images originales des deux icônes totalisent environ 3,7 Mo : leur poids est
une limite réseau connue. Aucun gain chiffré n’est attribué au seul décodage async.
Les variantes Gateway et sous-ensembles de polices restent chargés à la demande.

## Réserves et poursuite

- Généralisation des avertissements à tous les éditeurs legacy et restauration
  de chaque filtre/position de liste : partielle, pas de garantie universelle.
- Les listes planning/journal possèdent déjà leurs filtres/compteurs/pagination.
  Aucune pagination artificielle n’est ajoutée aux petits jeux de paiements ;
  les bornes serveur restent visibles dans l’inventaire de raccordement.
- Rapports intégrés, catalogue administratif autonome, détails complets de
  fonctionnalités incluses/exclues de chaque offre et facture SaaS imprimable :
  raccordements à compléter. Les simulations existantes restent identifiées,
  aucune statistique ou facture réelle n’est inventée.
- La sélection d’options produit dans le menu public exige un contrat de commande
  complémentaire ; le transport actuel présente produits, prix et quantités.
- Textes juridiques définitifs, prix de fonctionnalités non approuvés, rétention
  des pièces réelles et intégrations externes restent des prérequis distincts.
  B 3 000 DZD et les grilles de succursales approuvées ne sont pas rouverts.
- Scan physique, impression réelle, voix/micro, accès public QR distant, inscription
  autonome distante, charge hébergée et validation de staging restent à faire
  après leurs prérequis. Aucun secret de visite ne doit être ajouté à un QR.

Le [référentiel commercial](saas-commercial-reference-20261108.md) et le
[plan staging antérieur](staging-local-followup-20261110.md) restent applicables.
Le budget proposé de 32,25 USD/mois attend toujours la décision du propriétaire.

Les pièces locales sont dans `artifacts/interface-consolidation-20261110` :
inventaire, galerie avant/après, matrice, résultats bruts, performances et sources
complètes. Les captures de recette serveur et les fixtures visuelles sont séparées.
Le SHA publié et son attestation distante figurent dans le rapport local de livraison.
**Aucun déploiement, fournisseur payant, nouvelle écriture distante de base,
changement de service Render ou de magasin de certificats dans cette passe.**
