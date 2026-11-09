# Base SaaS B — localisation et évolution pays/devise

Version de préparation : **2026-11-08.1**. Aucune nouvelle décision commerciale.

## Valeur actuellement affichée

Lecture réellement effectuée dans une transaction PostgreSQL **READ ONLY** :

| Élément | Emplacement exact |
| --- | --- |
| Serveur | `127.0.0.1`, port `55433` |
| Base | `moulai_integrated` |
| Schéma | `public` |
| Table | `subscription_pricing_config` |
| Clé primaire / enregistrement | `id = 1`, contrainte de singleton |
| Colonne | `base_price`, PostgreSQL `numeric(14,2)` |
| Valeur observée | **3 000,00 DZD** |
| Devise / précision existantes | `policies.currencies.DZD.decimals = 2` ; devise non portée par une colonne de cette table |
| Révision de la base de revue | `o220261108` |
| Version commerciale du paramètre | `policies.base_revision`, lue dans la preuve JSON ; distincte de la révision Alembic |
| Modèle ORM | `app/models/subscription_pricing.py`, `SubscriptionPricingConfig` ; `id` est hérité de `BaseModel` |
| Calcul | `app/services/business/pricing_service.py`, `configuration` → `base_breakdown` → `calculate_subscription_pricing` |
| Affichage propriétaire | `app/integration/offers.py`, `available_offer`, lecture DZD via `configuration` |
| Administration | `app/services/business/saas_pricing_admin.py`, `current_base` / `base_view` / `change_base` ; permission exacte `subscriptions.pricing.manage` |
| Migration d'origine | `alembic/versions/2026_10_28_subscription_pricing_s1.py`, révision `s1a20261028`, parent `e1a92b200001` |
| DDL effectivement appelé par S1a | `migration_support/subscription_s1.py`, `DDL` : CREATE TABLE puis INSERT du singleton |

Requête de consultation, à exécuter uniquement sur la connexion locale explicitement
choisie ; elle ne nécessite aucun secret dans le texte SQL :

```sql
BEGIN READ ONLY;

SELECT current_database() AS database_name,
       inet_server_addr() AS server_address,
       inet_server_port() AS server_port;

SELECT id,
       base_price,
       policies -> 'currencies' AS currency_policy,
       policies ->> 'base_revision' AS base_revision
FROM public.subscription_pricing_config
WHERE id = 1;

ROLLBACK;
```

Ne pas publier le JSON `policies` complet : il peut aussi contenir des identifiants
de destinataires de rappels sans rapport avec B. Les secrets de connexion ne sont
ni dans cette requête, ni dans l'archive de sources.

**Aucune synchronisation de cette valeur vers Neon n'a été effectuée dans ces
travaux locaux. Aucune connexion à Neon n'a été ouverte dans cette intervention.**
La valeur affichée est lue dans la base locale attestée. L'état actuel de Neon n'a
pas été consulté : une valeur identique peut déjà y exister indépendamment,
notamment après des opérations historiques autorisées. Cette livraison ne prétend
pas établir son absence sur la base distante.

## Couverture réelle du stockage précédent

Le singleton porte un B DZD. Le moteur contient également un chemin optionnel
`policies.currency_bases[devise]` pour d'autres devises, sous réserve de leur
configuration ; la lecture locale ne trouve aucune entrée de ce type.
Ce chemin JSON n'identifie **aucun pays**, ne permet pas deux B différents pour
deux pays utilisant la même devise et ne constitue pas un historique de tarifs
pays/devise. Le paramètre `market` sert déjà au ciblage des grilles de succursales ;
il n'était pas utilisé pour choisir B. Il n'est pas assimilé silencieusement au pays.

Le besoin pays/devise est donc **non couvert par le singleton actuel**.

## Évolution O3 préparée et testée séparément

Nouvelle migration `alembic/versions/2026_11_08_country_base_o3.py` :
`o320261108`, parent `o220261108`. Opérations dans
`migration_support/country_base_o3.py`. Les migrations historiques ne sont pas modifiées.

Une seule source de prix après O3 : **`public.subscription_base_prices`**.
Le singleton existant conserve uniquement ses politiques partagées ; O3 supprime
sa colonne `base_price` et les clés `currency_bases` / `base_revision` du JSON.
Un trigger refuse leur réintroduction dans ce JSON. Il n'y a donc pas deux
stockages tarifaires actifs à maintenir en parallèle.

| Champ de la version de B | Rôle |
| --- | --- |
| `id` | Identifiant stable de la version |
| `country_code` | Pays explicite, code de deux lettres majuscules ; ni déduit de la langue ni de la devise |
| `currency` | Devise explicite de trois lettres majuscules |
| `amount` | Valeur exacte `numeric(24,8)`, non négative et finie |
| `revision` | Version unique retenue par le calcul |
| `effective_from`, `effective_until` | Intervalle UTC : début inclus, fin exclue ; fin NULL pour une version courante |
| `recorded_at` | Date d'enregistrement |
| `author_admin_id` | Référence de l'auteur d'une nouvelle décision ; pas de FK CASCADE vers son compte |
| `source_reference` | Source/motif de la décision ; provenance technique explicite pour la reprise du singleton |

L'exclusion PostgreSQL interdit les périodes qui se chevauchent pour un même
couple pays/devise. La fermeture d'une période est autorisée une seule fois ;
le montant, le pays, la devise, la version et la source sont immuables. DELETE et
TRUNCATE sont refusés. La publication de remplacement ferme la période précédente
et ajoute une version, avec audit dans la même transaction. Aucun futur prix
n'est programmé automatiquement par ce service.

La migration transfère **la valeur réellement constatée** du singleton vers
`DZ/DZD`, pour l'Algérie déjà approuvée. Dans la revue inspectée, cette valeur est
3 000 DZD. Elle ne force pas un nouveau prix et ne crée aucun autre pays/devise.
Une ancienne configuration `currency_bases` non vide bloque la migration : il faut
d'abord décider explicitement du pays de chaque prix, sans le deviner.

La date de reprise est celle de la migration ; elle n'invente pas une date de
validité historique. Les instantanés, factures et périodes déjà retenus ne sont
ni recalculés ni réécrits. La version legacy disponible est conservée dans la
ligne importée. Les anciennes preuves JSON restent lisibles telles quelles.

**3 500, 4 000 et 5 000 DZD restent des exemples non programmés. Aucun de ces
montants n'est initialisé par O3. Aucun prix étranger ni conversion automatique
n'est ajouté.** Les contextes `ZZ/XTS` et la variation de 0,01 DZD rencontrés dans
les tests sont uniquement des fixtures explicites du cluster jetable, jamais
exportées comme décisions commerciales ni dans la base de revue.

## Modèle, services et calcul préparés

- ORM : `app/models/subscription_base_price.py`, `SubscriptionBasePrice`.
- Résolution : `subscription_country_base.resolve_country_base`, sélection exacte
  du pays, de la devise et de la période ; absence ou ambiguïté → erreur explicite.
- Publication : `publish_country_base`, autorisation serveur existante réutilisée,
  version attendue obligatoire, verrou sur le singleton pour sérialiser les
  publications, refus d'une version périmée ou d'un prix inchangé, audit retenu.
- Calcul existant : paramètre explicite `country_code` ajouté à `configuration`,
  `base_breakdown`, `calculate_plan_base_price` et `calculate_subscription_pricing`.
  Les formules ne sont pas recopiées. Avec ce paramètre, elles lisent la nouvelle
  version et renvoient `base_selection` : pays, devise, montant, identifiant,
  version et validité. La précision et l'arrondi continuent à provenir des
  politiques monétaires existantes.
- Un pays sans prix ou une devise sans politique explicite est bloqué ; aucun
  repli vers l'Algérie, un autre pays, une autre devise ou zéro.

Ces nouvelles fonctions sont des services internes préparés : aucun endpoint
de publication pays/devise n'est monté et aucune nouvelle permission personnelle
n'est attribuée. La lecture d'un tarif public ne donne accès à aucun indicateur,
facture ou donnée d'un autre propriétaire. Les routes futures doivent conserver
leurs contrôles de rattachement et d'isolation.

## Répétition réellement exécutée

Commande locale dédiée :

```powershell
Set-Location D:\MoulAI
.\.venv\Scripts\python.exe -I -B scripts/rehearse_country_base.py
```

Elle crée un nouveau cluster PostgreSQL 18 sur **127.0.0.1:55434**, base et rôle
non superutilisateur `moulai_base_rehearsal`, marqueur aléatoire réattesté. Les
deux bases de revue déjà actives ne sont ni arrêtées ni modifiées. Les secrets
générés restent dans le processus et le fichier temporaire privé est retiré.
L'initialisation exécute le bootstrap historique vérifié, toute la chaîne jusqu'à
O2, prépare un instantané et une période active synthétiques, puis fait avancer
**Alembic lui-même jusqu'à O3**, sans `stamp` ni modification manuelle de sa table.
L'environnement `alembic_country_base_local` exige la cible locale et sa transaction.

Résultat final : **19 tests PostgreSQL réussis**, zéro échec ni test ignoré,
un avertissement pytest relatif à la réécriture des assertions du plugin `anyio`
déjà importé. Le serveur de répétition est arrêté en fin d'exécution.

Couverture : transfert et suppression de l'ancienne source, conservation des
politiques, absence de prix pour les couples non configurés, contexte explicite,
frontières temporelles, contraintes SQL directes, permission insuffisante,
concurrence 1 succès / 1 refus, audit, conservation de l'instantané antérieur,
calcul réel avec la version pays/devise, refus d'une reprise legacy ambiguë,
rollback tardif sans fermeture/création partielle et indépendance pays/devise.

**60 contrôles hors ligne de régression** réussis. Black et Ruff passent sur les
dix fichiers Python de cette préparation. Aucune campagne générale ni test
Frontend sans rapport n'a été relancé.

Les premières tentatives sont conservées séparément : une tentative de lanceur
Windows interrompue avant les migrations, puis une tentative dont six tests de
recette étaient incorrects (contextes `pytest.raises` et paramètre JSON SQL).
Ces défauts du lanceur/tests ont été corrigés ; aucun contrôle métier n'a été
affaibli pour obtenir le résultat final.

## État de livraison et conditions du raccordement

**Préparation locale validée sur le périmètre testé ; O3 non activé dans la revue.**
La revue reste sous O2 avec son singleton à 3 000 DZD. Les garde-fous de l'hôte
opérationnel et son migrateur n'admettent pas O3 : ils ne sont pas assouplis dans
cette intervention. Le modèle ORM legacy du singleton reste volontairement celui
d'O2 pour cette revue ; O3 retire sa colonne de prix.

Avant une activation dans l'instance intégrée, compléter ensemble :

1. Le rattachement du **pays de facturation vérifié et persisté** à l'entreprise,
   ainsi que sa provenance et son changement contrôlé. Ne pas permettre au client
   de choisir librement un pays moins cher dans une requête de devis.
2. Les contrats d'inscription, de simulation, de checkout et de renouvellement
   pour transmettre ce contexte serveur fiable au même moteur. Aucun pays ne
   doit être inféré de l'ancien `market`, de la devise ou de l'interface.
3. Les lecteurs/éditeurs administratifs de B, l'offre propriétaire et l'ORM du
   singleton partagé. Les rappels doivent versionner leur politique sans recréer
   une clé `base_revision` tarifaire globale. Les anciennes routes ne doivent
   pas être utilisées sur O3 ; une lecture legacy y échoue faute de colonne,
   plutôt que de retourner silencieusement un mauvais prix.
4. La reprise de la recette intégrée et des tests d'abonnement pertinents sur ce
   raccordement complet, avec sauvegarde/restauration vérifiée avant toute cible
   durable. Le présent jeu ciblé ne remplace pas cette recette.

Le choix du rattachement pays de facturation est une décision de contexte à
préciser ; **B Algérie = 3 000 DZD et les tranches approuvées ne sont pas rouverts**.
Les prix des autres pays restent à approuver explicitement.
Le downgrade automatique est refusé pour préserver les versions ; une éventuelle
récupération exige un plan indépendant, sans effacement de décisions historiques.

Les preuves, la liste des fichiers et leurs sources intégrales sont dans
`artifacts/saas-base-country-20261108/`. Aucun `.env`, secret, backup, donnée privée,
commit, push, déploiement, paiement ou accès distant n'est inclus dans la livraison.
