# MoulAI™ — documents SaaS O5, recette locale

11 novembre 2026. Jalon documentaire distinct, préparé depuis
`3bebf39757c14929fecdfaccaeebbd6273caf6b2` sur
`codex/staging-preparation-20261109`. **PASS WITH RESERVATIONS sur le périmètre
local décrit**. Ni qualification fiscale, ni certification de production, ni
clôture de l’intégration globale.

## Parcours effectivement exécuté

Depuis `/access`, connexion Keycloak locale du propriétaire fictif
`billing-scenario`, entreprise, premier établissement, offre SaaS, puis lien
« Documents d’abonnement ». Le paiement synthétique déjà vérifié est consulté :
aucun document n’est émis par cette consultation.

Un nouveau compte fictif `saas-document-admin`, sans rattachement à une entreprise
cliente, reçoit explicitement **uniquement** `subscriptions.documents.issue` et
`subscriptions.documents.invalidate`. Les administrateurs existants ne sont pas
modifiés. Ce compte accède à l’espace documentaire depuis l’interface principale,
émet le document, puis l’invalide par un formulaire avec motif et confirmation.
Il ne peut pas consulter la file de revue financière `payments.review`.

Le propriétaire recharge sa page et consulte les mêmes référence, montant,
devise et période. Le paiement utilisé vaut `2940.00000000 DZD` : c’est le montant
historique conservé, pas un nouveau tarif commercial. La lecture de vérification
annonce ensuite l’invalidation. Aucun paiement, période, montant ou instantané
n’est réécrit par ces actions documentaires.

Les appels directs d’un propriétaire, du réviseur de paiements sans permission
documentaire et d’une autre entreprise sont refusés. Une émission répétée renvoie
le même document. Un paiement déjà réglé mais sans document définitif est présenté comme un
récapitulatif du paiement enregistré, jamais comme une nouvelle somme à payer.
La recette navigateur n’a pas été relancée pour refaire ses
écritures : les captures suivantes sont des lectures seules.

## Contrat et garanties

| Opération              | Source et autorité                                                                                                                                           | Résultat et limite                                                                                                  |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------- |
| Demande de paiement    | Paiement et montant retenus, consultation de l’établissement autorisé                                                                                        | Imprimable avant vérification ; aucun QR de document définitif ; ni reçu de fonds ni activation                     |
| Émission               | Permission exacte, paiement `paid`, date de règlement, preuve de virement approuvée ou encaissement cash enregistré, période traitée et instantané cohérents | Document immuable et événement émis dans la transaction du serveur ; aucun recalcul selon B ou le catalogue courant |
| Consultation détaillée | Identité et permission `tenant.billing.read`, entreprise, restaurant et paiement vérifiés côté serveur ; ou permission documentaire plateforme explicite     | Contenu historique et audit ; ni contenu du justificatif bancaire ni secret de session                              |
| Invalidation           | `subscriptions.documents.invalidate`, confirmation et motif obligatoires                                                                                     | Événement conservé avec auteur/date/motif ; original intact ; aucun remboursement, retrait de fonds ou suspension   |
| Remplacement           | `subscriptions.documents.issue`, prédécesseur explicitement désigné et déjà invalidé                                                                         | Filiation conservée, version suivante ; répétition idempotente ; modification financière ou de période refusée      |
| Vérification           | Référence aléatoire URL-safe de 43 caractères, circuit distinct des restaurants                                                                              | Seulement référence, émetteur, date d’émission et validité ; état inconnu sans diagnostic inventé                   |

La permission d’émission n’accorde pas celle d’invalidation, ni inversement.
Aucune déduction depuis un rôle, `payments.review`, `admins.manage` ou une
permission tarifaire. Le provisionnement local utilise un rôle propre au nouveau
compte fictif, sans accorder ces droits à tous les administrateurs.

Le document reprend les valeurs persistées du paiement, de l’abonnement et de
`subscription_pricing_snapshots`. Il conserve le JSON historique complet, sa
source et son empreinte SHA-256. L’interface affiche le montant exact et la
période, sans prétendre fournir les mentions d’une facture fiscale. Une période
`scheduled` reste explicitement programmée ; son état à l’émission est distingué
de l’état actuel du service.

La suppression d’un administrateur n’efface pas le document ni ses événements :
identifiant et nom d’auteur sont conservés comme traces. Les clés étrangères
`RESTRICT` empêchent l’effacement des sources financières référencées ; une
suppression d’entreprise ou de paiement ne peut pas effacer silencieusement ces
documents. Aucune nouvelle règle de remboursement n’est introduite.

Le QR ne contient qu’une origine explicite, la page de lecture
`/verify-saas-document`, une langue et la référence opaque dans le fragment. Il ne
contient aucun jeton de visite, justificatif bancaire ni URL administrative.
Le lecteur local limite les vérifications à 30 requêtes/minute par processus,
en complément des limites du serveur. Ce n’est pas une protection distribuée
certifiée pour la production. La fermeture actuelle du staging aux testeurs
reste inchangée.

## Stockage et compatibilité

Migration additive `2026_11_11_saas_documents_o5.py` :
`o420261108 → o520261111`, **101 → 103 tables**.

- `subscription_documents` : périmètre entreprise/restaurant, paiement,
  abonnement, instantané, référence opaque unique, version, filiation, contenu,
  empreinte, auteur et date. Unicité du couple paiement/version et du successeur
  d’un original.
- `subscription_document_events` : émission et invalidation, auteur conservé,
  motif et date, unicité document/type.
- Triggers interdisant modification, suppression et `TRUNCATE` sur ces deux
  historiques. Les opérations financières ne sont pas déplacées dans ce circuit.

Les lecteurs de configuration tarifaire, d’offre, de rappels, d’inscription et
Dining admettent explicitement ce descendant additif avant la migration locale.
Un compte disposant seulement du droit d’invalidation consulte uniquement les
paiements ayant déjà un document ; il ne reçoit pas la file des demandes non émises.
Une révision inconnue reste refusée. O4 reste lisible ; une demande documentaire
sur O4 reçoit un blocage explicite de migration manquante. L’initialisation d’une
nouvelle instance locale cible désormais O5.

Le lecteur privé d’un paiement accepte un filtre exact `payment_id`, après les
mêmes contrôles de périmètre : un ancien document ne dépend pas de sa présence
parmi les 50 derniers paiements. La file plateforme reste bornée aux 100 derniers
paiements ; sa pagination/recherche historique n’est pas ajoutée dans ce lot.

Aucune migration historique n’est réécrite. Aucun `stamp`, `create_all` substitutif
ou changement manuel de `alembic_version`.

## Sauvegarde, restauration et application locale

Cible attestée : `127.0.0.1:55433/moulai_integrated`, rôle
`moulai_integrated`, marqueur `3fb5f85a6cc94868acaf7d95b3777a16`.
Application arrêtée, ports de l’application libres, bail d’exclusivité et absence
d’autres clients PostgreSQL vérifiés avant l’opération.

La sauvegarde complète O4 est conservée sous le répertoire privé protégé de
l’instance, hors du suivi Git. Référence :
`o520261111-b4a092ab8377438791d1a07d49a3a4a5/before-o520261111.dump`.
SHA-256 : `4f89d6a7a23ee65b9c4242b17f40163cc877e2ca5d081a24ac53f70e2490a3ac`.
Aucun identifiant de connexion n’apparaît dans ce rapport.

L’archive a été effectivement restaurée sur un cluster distinct au port 55434.
Colonnes, types, contraintes, index, triggers, fonctions, ACL et empreintes des
lignes ont été comparés. Puis : migration O5 annulée par rollback identique,
migration O5 validée, anciennes lignes inchangées, restauration de récupération
O4 de nouveau identique. Le parent O4 retenu n’a pas été modifié pendant cette
répétition.

Le lanceur d’application locale a ensuite revérifié l’empreinte de la sauvegarde,
les sources de migration et l’identité de la cible. Il a répété le rollback,
appliqué O5 transactionnellement et comparé le catalogue final à la copie répétée.
Le serveur HTTPS/FastAPI et Keycloak locaux ont redémarré sur O5 sans worker ni
envoi de notification. La persistance du document et des droits a été vérifiée
après redémarrage.

**Après l’émission d’un document, ne pas restaurer automatiquement l’ancienne
archive O4** : elle n’inclut pas ces nouveaux historiques. Le parent attendu et
les empreintes empêchent une relance de la transition déjà appliquée. Toute
intervention suivante exige une sauvegarde fraîche O5 et un plan conservant les
nouveaux documents. Aucun downgrade destructif n’est fourni.

Commandes effectivement utilisées, présentées pour traçabilité :

```powershell
# Répétition indépendante ; base jetable exclusivement.
.\.venv\Scripts\python.exe -I -B scripts/rehearse_country_base.py --saas-documents

# Déjà exécutées pour la transition locale ; ne pas les rejouer sur O5.
.\.venv\Scripts\python.exe -I -B scripts/prepare_operational_o4.py --target o520261111
.\.venv\Scripts\python.exe -I -B scripts/migrate_operational_local.py --target o520261111

# Observation explicitement en lecture seule de la revue locale.
.\.venv\Scripts\python.exe -I -B scripts/verify_saas_documents_local.py
```

Les commandes ne découvrent pas un `DATABASE_URL` global : cible, rôle, port et
marqueur sont contrôlés par les lanceurs. Aucune commande pour Neon n’a été
exécutée. Les artefacts staging O4 précédents ne sont pas convertis implicitement
en un plan de déploiement O5 ; leur actualisation et leur autorisation restent
une étape distincte.

## Vérifications réellement exécutées

| Contrôle                        | Preuve et résultat                                                                                                                                                           |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Reconstruction complète jetable | Bootstrap principal puis vraie chaîne jusqu’à O5, sans `stamp`                                                                                                               |
| PostgreSQL ciblé                | 54 tests réussis : 47 régressions O3/O4 et 7 tests documentaires, incluant routes réelles et sessions indépendantes                                                          |
| Admission                       | Avant fonds et après simple dépôt refusés ; permissions indépendantes ; isolation entre entreprises                                                                          |
| Transactions                    | Émission concurrente unique ; rollback tardif d’émission et d’invalidation ; répétitions sans doublon                                                                        |
| Historiques                     | Original/instantané/paiement conservés ; remplacement lié ; suppression d’administrateur sans perte d’auteur                                                                 |
| Période future                  | Véritable règlement après un essai synthétique maintenu ouvert ; période `scheduled`, aucune réécriture de période achetée                                                   |
| Cash                            | Devis cash et véritable service local d’encaissement synthétique, puis émission ; aucun justificatif bancaire substitué                                                      |
| Environnement                   | Refus serveur des documents fictifs en mode production                                                                                                                       |
| Frontend                        | 31 tests ciblés, dont 11 documentaires : langues/RTL, période programmée, demande sans QR, lecture fraîche avant impression, erreur sans impression/rejeu, langue du lecteur |
| QR partagé hors ligne           | 24 tests réussis, aucun appel fournisseur ni base                                                                                                                            |
| Navigateur réel                 | 6 contrôles avec vrais comptes Keycloak locaux et PostgreSQL retenu, accès depuis l’interface principale, refus et invalidation                                              |
| État indépendant                | Les 7 tables financières contrôlées identiques à la sauvegarde pré-O5 ; 1 document et 2 événements documentaires conservés                                                   |
| Visuel final                    | 12 captures propriétaire et 12 du lecteur anonyme, FR/EN/AR, clair/sombre, desktop/mobile ; aucun débordement horizontal détecté                                             |
| Clavier                         | Accès au bouton d’impression par Tab avec focus visible dans les trois langues ; gardes de saisie conservées                                                                 |
| Accessibilité automatique       | 24 vues finales sans violation Axe signalée ; pas une certification d’accessibilité                                                                                          |
| PDF                             | Trois vrais exports A4, une page chacun, rouverts et rendus avec Windows.Data.Pdf ; app/navigation/fond illustré exclus                                                      |
| Style et construction           | Black/Ruff sur les Python modifiés, Prettier, typecheck, builds staging/production et garde-fous Frontend                                                                    |

Un avertissement pytest concerne la réécriture d’`anyio` déjà importé dans le
lanceur. Les 24 contrôles QR ont aussi signalé le cache pytest Windows déjà
existant ; ces avertissements sont conservés. Les premières répétitions en échec
restent disponibles : lecteur de révision incomplet, preuves synthétiques
identiques et tentative de modification d’une période achetée dans une fixture.
Les protections ont été conservées et les préparations de test corrigées.

Axe laisse le contrôle de contraste incomplet sur dix vues propriétaire ; les
douze vues du lecteur et les deux vues propriétaire arabe mobile n’ont pas ce
point incomplet. La revue visuelle ne remplace pas une mesure exhaustive des
contrastes ni une validation au lecteur d’écran.

La première composition PDF contenait encore la mise en page générale. Les
preuves finales proviennent du document isolé dans un conteneur d’impression,
avec attente des images/polices et relecture des données. Les premiers exports
restent des preuves intermédiaires, pas les livrables finaux.

Les documents du parcours ont été **volontairement invalidés**. Les PDF finaux
annoncent cet état ; leur QR le confirme. Les noms de fichiers `invoice-fr.pdf`,
`invoice-en.pdf`, `invoice-ar.pdf` suivent la convention technique du moteur de
rendu existant, sans qualifier ces documents de factures fiscales.

## Matrice actualisée

| Exigence                 | Interface                                                       | Route/service                                             | Preuve actuelle                                                                | Limite restante                                                     |
| ------------------------ | --------------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------- |
| Documents SaaS distincts | Offre propriétaire → documents ; espace documentaire plateforme | `saas_document_routes`, `SubscriptionDocumentService`     | Raccordé et vérifié localement depuis `/access`                                | Documents fictifs ; mentions définitives à valider                  |
| Permission d’émission    | Bouton visible pour le grant exact                              | `subscriptions.documents.issue` et contrôle serveur       | UI et refus par API directe                                                    | Aucun droit attribué à distance                                     |
| Invalidation             | Motif + confirmation explicite                                  | `subscriptions.documents.invalidate`                      | Original conservé et QR invalidé                                               | Ni remboursement ni suspension                                      |
| Paiement/activation      | Workflow existant réutilisé                                     | Paiement, preuve, abonnement, instantané                  | Virement et cash vérifiés sur base jetable ; virement historique dans la revue | Interface cash SaaS non ajoutée dans ce lot                         |
| Période programmée       | Mention spécifique                                              | État conservé lors de l’émission                          | Test PostgreSQL et tests FR/EN/AR                                              | Non présentée comme déjà active                                     |
| QR SaaS                  | Lecteur distinct, consultation limitée                          | `/verify-saas-document`, `/api/web/saas-documents/verify` | Validité/invalidation et lecteur anonyme local vérifiés                        | Téléphone physique et URL staging non vérifiés                      |
| Facture restaurant       | Livraison précédente                                            | Circuit Dining inchangé                                   | Régressions de référence ; lecture après O5 contrôlée séparément               | Pas de répétition de la campagne financière complète                |
| Catalogue et rapports    | Services/écrans existants                                       | Contrats legacy à qualifier                               | Aucun nouveau raccordement revendiqué                                          | Permissions, métriques, périmètres, périodes et devises à finaliser |
| Options de commande      | Structure existante                                             | Contrat public sans options tarifaires exactes            | Aucun Float converti silencieusement                                           | Prix/devise et règles de sélection à raccorder                      |
| Continuité legacy        | Garde-fous déjà étendus à certains éditeurs                     | Navigation et erreurs                                     | Régressions précédentes + reprise d’impression SaaS                            | Autres éditeurs/filtres non couverts restent ouverts                |
| Assistant IA/voix        | Accès distinct conservé                                         | Documentation locale existante                            | Aucune génération ni voix activée                                              | Connecteur/contexte/quotas/voix et coût à traiter séparément        |
| Recette distante         | Préparation antérieure                                          | Hébergement/identité/migrations staging                   | Pas d’activation dans ce lot                                                   | Ressources, budget et plan O5 distant à valider                     |

Les contrôles de zoom réel, de lecteur d’écran, de papier et de téléphone
physique ne sont pas remplacés par Axe, une émulation ou un PDF. Aucun nouveau
décodage QR indépendant n’est revendiqué.

## Sources et livraison

Les sources complètes modifiées et leurs empreintes sont fournies dans l’archive
locale de livraison. L’inventaire distingue migration/modèles/service, routes,
lecteurs compatibles, lanceurs de répétition/provisionnement/observation,
interface, traductions, tests et documentation. Les secrets, archives PostgreSQL,
comptes privés et données de recette ne sont pas publiés dans Git.

Preuves locales : `artifacts/saas-documents-20261111`, avec `rehearsals`,
`restore-proof.json`, `review-migration.json`, `browser/journey.json`,
`independent-observer.json`, `final` et `reader-final`. Le relevé de publication
séparé contient le SHA exact sauvegardé sur la branche de préparation.

Aucun changement Render, Neon, Redis, Telegram ou Keycloak distant. Aucun achat,
fournisseur IA, notification réelle, merge ou déploiement. La nouvelle identité
et la migration sont exclusivement locales et synthétiques.

## Inventaire exhaustif des sources de ce lot

Les noms ci-dessous désignent les fichiers ajoutés ou modifiés. Leurs rôles
sont détaillés dans les sections contrat, compatibilité, outils et recette ;
l’archive fournit chaque fichier complet, avec un manifeste d’empreintes.

- `alembic/versions/2026_11_11_saas_documents_o5.py`.
- `alembic_country_base_local/env.py`.
- `alembic_operational_local/env.py`.
- `app/core/security/platform_permissions.py`.
- `app/integration/local_setup.py`.
- `app/integration/offers.py`.
- `app/integration/saas_document_routes.py`.
- `app/integration/saas_payment_routes.py`.
- `app/integration/web.py`.
- `app/models/subscription_document.py`.
- `app/repositories/subscription_configuration.py`.
- `app/services/business/document_qr.py`.
- `app/services/business/enrollment_documents.py`.
- `app/services/business/subscription_documents.py`.
- `app/services/business/subscription_reminders.py`.
- `docs/interface-documents-20261111.md`.
- `docs/saas-documents-o5-20261111.md`.
- `frontend/scripts/capture-saas-documents.mjs`.
- `frontend/scripts/capture-saas-reader.mjs`.
- `frontend/scripts/check-saas-documents.mjs`.
- `frontend/src/app/Shell.tsx`.
- `frontend/src/app/router.tsx`.
- `frontend/src/features/integration/OperationalPages.tsx`.
- `frontend/src/features/integration/SaasDocuments.tsx`.
- `frontend/src/features/integration/SaasPayments.tsx`.
- `frontend/src/features/integration/saasDocuments.module.css`.
- `frontend/src/shared/i18n/index.ts`.
- `frontend/src/shared/i18n/saasDocuments.ts`.
- `frontend/tests/unit/saas-documents.test.tsx`.
- `migration_support/operational_revisions.py`.
- `migration_support/saas_documents_o5.py`.
- `scripts/migrate_operational_local.py`.
- `scripts/prepare_operational_o4.py`.
- `scripts/prepare_saas_document_account.py`.
- `scripts/rehearse_country_base.py`.
- `scripts/verify_saas_documents_local.py`.
- `tests/integration_local/test_country_base_postgres.py`.
- `tests/integration_local/test_followup_postgres.py`.
- `tests/integration_local/test_saas_documents_postgres.py`.
