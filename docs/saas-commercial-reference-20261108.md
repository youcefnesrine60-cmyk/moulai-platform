# Référentiel SaaS consolidé MoulAI™

Version locale : **2026-11-08.3**. Établi le 8 novembre 2026.
Cette consolidation rapproche les décisions du propriétaire, les sources et la
configuration observée. Elle **ne constitue pas une nouvelle approbation commerciale**.
Le fichier et son empreinte feront partie de la livraison locale ; aucun commit
n'est autorisé dans cette intervention.

## Sources et statut des règles

| Élément | Référence vérifiable | Statut et emplacement |
| --- | --- | --- |
| Base SaaS B, référence actuelle 3 000 DZD | Décision explicite du propriétaire du 8 novembre 2026 ; `migration_support/subscription_s1.py` | Approuvée, configurable : `subscription_pricing_config`, ligne `id=1`, colonne `base_price`, `Numeric(14,2)`. Aucun second stockage du prix. |
| Lecture de B | `app/services/business/pricing_service.py`, `configuration` puis `base_breakdown` | Lecture réelle en base ; absence du singleton ou de la politique de devise : erreur explicite. Aucun repli vers 3 000 dans le moteur. |
| Modification de B | `app/services/business/saas_pricing_admin.py`, `change_base` | Permission exacte `subscriptions.pricing.manage`, transaction, verrou et comparaison stricte de version. Interface locale : prise d'effet immédiate explicite uniquement. Programmation future non raccordée, non approximée. |
| Révision de B | `subscription_pricing_config.policies.base_revision` ; `PricingParameters.base_revision` | Métadonnée de version, sans duplication du montant. Les nouveaux calculs retiennent B et cette révision. Les instantanés historiques ne sont ni recalculés ni rétroactivement renommés. Les anciens calculs sans révision explicite restent identifiables comme historiques. |
| Formules Basic / Professional / Enterprise | `docs/subscription-pricing-correction.md`, `subscription_contract.py`, `pricing_service.py` | Règles déjà définies : Basic `B+A` ; Professional `B+(P+A)×0,95` ; Enterprise `B+P×0,95+(E+A)×0,90`. Aucun calcul recopié dans le frontend. |
| Inclusions | `subscription_contract.py`, `INCLUDED` | Catalogue de codes approuvé dans le code existant ; sa présence ne prouve pas que les plans et fonctionnalités sont initialisés en base. |
| Succursales | Décision métier transmise ; `subscription_branch_pricing.py` et migrations S1 | Première gratuite ; suivantes par tranches 2–5 : 500, 6–20 : 400, 21+ : 300 DZD/mois. Trois tranches persistées observées ; valeurs lues en base, jamais converties implicitement vers une autre devise. |
| Fidélité | Décision métier transmise ; `subscription_calendar.py`, `loyalty_discount_repo.py`, S1 | Périodes payantes cumulées, interruptions et essai exclus, chevauchements fusionnés, seuils inclusifs. Sept paliers persistés. |
| Promotions | Décision métier transmise ; `promotion_repo.py`, `pricing_service.py` | Meilleur taux applicable, priorité administrative décroissante, identifiant croissant. Début inclus et fin exclue. Pas de cumul entre promotions. |
| Éditeur de campagnes | `saas_pricing_admin.py`, `schemas/saas_pricing.py` | Brouillon, modification avant publication, publication future et désactivation immédiate. Une campagne publiée n'est pas réécrite par ce service. Les cibles inexistantes ou incohérentes sont refusées. |
| Arrondi | Décision métier transmise ; `pricing_service.money` | Decimal pendant le calcul ; HALF_UP seulement sur le total final, selon la précision de la devise. |
| Cycles | `subscription_calendar.py`, `subscription_contract.py` | Mois calendaires 1/3/6/12 ; annuel facturé 10 mois ; ancrage conservé. Essai et fenêtre de mesure : 30 jours. |
| Rappels | S1 ; `subscription_reminders.py` | `policies.reminder_days=[14,7,1,0]` observé. L'existence du calendrier ne prouve aucun envoi. Aucun worker ni transport n'est démarré ici. |
| Paiement | `manual_payment_service.py`, `cash_collection_service.py`, `subscription_checkout_service.py` | Circuits existants à raccorder au lot 2 ; aucun justificatif ni choix cash ne vaut encaissement. Aucune transaction réelle ni activation payante effectuée dans cette passe. |
| Classification du restaurant | Décision métier et moteur existant | Classification descriptive ; aucun coefficient de type ajouté au calcul. |

## Configuration réellement observée

La nouvelle base locale identifiée `127.0.0.1:55433/moulai_integrated` a été
reconstruite par le bootstrap principal puis étendue localement jusqu'à `o220261108`.
L'inventaire JSON daté de la livraison précise les nombres effectivement lus.

- Un singleton tarifaire, B = 3 000,00 DZD ; précision DZD = 2 décimales.
- Trois tranches de succursales, sept paliers de fidélité et trois règles de multi-restaurants.
- Aucun plan commercial ni prix de fonctionnalité dans cette instance. Une référence technique `features.id=6`, code `orders`, a été ajoutée pour la clé étrangère du compteur historique lors de la recette alimentaire ; aucun droit payant ni tarif SaaS ne lui est associé.
- Aucun abonnement, justificatif SaaS ni instantané d'abonnement créé par ce raccordement.
- Les campagnes nommées `LOCAL ACCEPTANCE ONLY` sont des données explicites de recette. La campagne publiée pendant la vérification a été désactivée ; elles ne valent aucune décision commerciale.

Les valeurs présentes dans les exemples des tests de tarification n'ont pas été
importées comme tarifs commerciaux. Les anciens champs agrégés `base_price` des
plans ne sont pas utilisés pour reconstituer P ou E.

## Prix des fonctionnalités : décisions réellement manquantes

Pour cette instance, la table `feature_pricing` est vide. Les sources examinées
ne permettent pas d'attribuer un prix commercial séparé à partir des exemples.
La présente liste ne crée ni tarifs ni fonctionnalités disponibles.

| Fonctionnalité | Couche existante | Devise | Valeur commerciale retrouvée | Source / décision nécessaire |
| --- | --- | --- | --- | --- |
| `qr_menu` | Basic | DZD | Incluse dans B ; aucun tarif séparé établi | `INCLUDED.basic` ; ne pas interpréter « incluse » comme un tarif universel de 0. |
| `categories` | Basic | DZD | Incluse dans B | Même référence. |
| `products` | Basic | DZD | Incluse dans B | Même référence. |
| `hosting` | Basic | DZD | Incluse dans B | Même référence. |
| `dashboard` | Basic | DZD | Incluse dans B | Même référence. |
| `basic_support` | Basic | DZD | Incluse dans B | Même référence. |
| `orders` | Professional | DZD | Non établie | Faire approuver le coût mensuel et sa source ; aucun montant déduit de P=2 000 dans un test. |
| `reviews` | Professional | DZD | Non établie | Même décision nécessaire. |
| `best_customer` | Professional | DZD | Non établie | Même décision nécessaire. |
| `analytics` | Enterprise | DZD | Non établie | Faire approuver le coût mensuel et sa source ; aucun montant déduit de E=1 500 dans un test. |
| `delivery` | Enterprise | DZD | Non établie | Même décision nécessaire. |
| `whatsapp` | Enterprise | DZD | Non établie | Même décision nécessaire ; prix de la fonctionnalité distinct du coût d'un transport externe. |
| `multi_branch` | Enterprise | DZD | Non établie | Coût de la fonctionnalité distinct des tranches de succursales déjà approuvées. |
| Toutes les fonctionnalités | Selon formule | Autres devises | Non établie | Grille commerciale explicite par devise ; aucune conversion des tarifs DZD. |

Une offre nécessitant une fonctionnalité sans coût applicable doit rester
non publiable/non finalisable. L'absence de plan ou de fonctionnalité obligatoire
produit déjà une erreur du moteur ; aucun résultat « gratuit » de substitution
n'est renvoyé. La publication d'une campagne de remise n'est pas la publication
d'une offre tarifaire complète.

## Inscription : informations et consentements

L'existant `users.consent` et `UserConsentUpdate` exprime une acceptation booléenne
historique. Il ne constitue pas une preuve suffisante de présentation d'un texte
SaaS versionné : absence de version de document, langue, finalité et preuve de
présentation. Les accords D1 sur une version de devis/menu concernent une autre
opération ; ils ne peuvent pas être réutilisés comme consentement d'inscription.

| Élément | État confirmé | Travail et décision restant nécessaires |
| --- | --- | --- |
| Conditions contractuelles SaaS | Principe d'acceptation explicite confirmé | Texte, version, période d'application et traductions FR/EN/AR à valider. |
| Information relative aux données personnelles | Information distincte demandée | Identifier les traitements réellement retenus puis faire valider le contenu de l'information et sa présentation. Ne pas transformer automatiquement toute information en consentement. |
| Consentements spécifiques | Séparation par finalité demandée | Définir les traitements qui les nécessitent ; aucune liste juridique inventée. |
| Communications commerciales | Choix facultatif, non précoché | Texte et finalités à valider ; un refus ne doit pas empêcher l'inscription. |
| Traçabilité | Compte authentifié, version, langue et date requis | Prévoir présentation et réponse par document/finalité ; conserver la preuve exacte et distinguer acceptation, refus et absence de réponse. |

La finalisation du dossier qui dépend de textes non publiés doit être refusée
explicitement ; les fonctions indépendantes restent utilisables. Aucun texte
définitif ni consentement universel n'est fabriqué par cette consolidation.

## Réserves d'intégration

Les interfaces d'inscription, de paiement SaaS et de publication complète des
offres restent à raccorder. L'offre du propriétaire lit B et les formules réelles
sous `tenant.billing.read`, puis utilise le moteur existant pour la simulation.
La base de revue sans formule reste explicitement bloquée ; aucun tarif de
substitution n'est ajouté. Les écritures préparatoires de métriques du moteur
sont annulées par savepoint dans ce parcours de consultation.

O1 remplace localement le lien CASCADE du journal par SET NULL et retient un
instantané de l'identifiant, du nom et du subject de l'auteur. Les triggers
refusent la réécriture, la suppression et TRUNCATE du journal, en permettant
uniquement le nettoyage du lien vivant par la FK. Les relations ORM ne suppriment
plus les journaux orphelins. Les anciens noms antérieurs à la capture ne sont pas
reconstituables ; la migration capture seulement l'information disponible.
Les anciennes opérations de purge/modification du journal seraient désormais
refusées par PostgreSQL ; elles ne sont pas montées dans cet hôte.
Ces protections ne prétendent pas résister à un propriétaire de base modifiant
les triggers. Aucun endpoint de suppression d'administrateur n'est raccordé ici.

Les six tests PostgreSQL ciblés prouvent qu'une modification de B affecte le
nouveau calcul et le renouvellement recalculé, tout en conservant l'instantané,
le montant retenu et la couverture déjà payée. La fenêtre de mesure du renouvellement mensuel testé est de 30 jours ;
la règle annuelle de 30 jours reste celle du contrat existant, sans nouveau test annuel ici. La programmation future de B reste non raccordée. Le calendrier des
rappels est éditable pour les prochaines programmations seulement : aucune
réécriture de rappels existants, aucun envoi ni destinataire implicite. Le
calendrier de revue est revenu à 14/7/1/0 après recette ; B est resté à 3 000 DZD.

Les montants alimentaires et leur encaissement synthétique local relèvent d'un
autre contrat. Le mode cash alimentaire n'applique pas la majoration SaaS de 2 %.
Une permission D1 `collect` ou `finance.read` n'accorde aucun droit tarifaire SaaS.

Cette livraison locale n'autorise aucune configuration distante, attribution
personnelle distante, migration permanente, dépense, publication ou mise en production.

## Préparation complémentaire de B par pays et devise

Le singleton actuellement affiché reste celui de la revue O2, à 3 000 DZD. Il
n'identifie pas le pays. L'évolution O3 est préparée et testée sur un autre
PostgreSQL jetable ; elle remplace la colonne de prix et l'ancien JSON
`currency_bases` par une seule table de versions pays/devise. Elle n'est pas
appliquée à la revue ni à Neon. Les exemples 3 500/4 000/5 000 DZD ne sont pas
des hausses programmées. Aucun tarif étranger n'est initialisé.

Voir [le stockage, la requête SELECT, la migration et ses limites de raccordement](saas-base-country-preparation-20261108.md).
