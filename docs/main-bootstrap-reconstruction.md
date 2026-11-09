# MoulAI™ — Reconstruction locale de l’historique principal S1a

## Périmètre et provenance

Cette livraison reconstruit les prérequis de la chaîne principale sur une base
locale vide. Elle n’adopte pas la révision S1b, ne modifie pas une migration déjà
appliquée et n’utilise ni `stamp` ni écriture manuelle d’`alembic_version`.
Aucune connexion distante n’est nécessaire à sa répétition.

La DDL physique complète antérieure au 1er août 2026 n’a pas été retrouvée.
Il est donc impossible d’attester une copie exacte de ce socle originel.
Le contrat proposé est une **reconstruction historique de compatibilité**, dont
la provenance est explicite, et non une nouvelle preuve d’une archive inexistante.

Sources locales :

- Première série complète de modèles retrouvée :
  `59c4b9bb007b93ea61bacb92b537df8af0a2c144`, 28 août 2026.
- Déclarations historiques utilisées :
  `7a667633f593afbabc9949cef12f603535eba94e`, 16 octobre 2026,
  avant les expansions E1 et S1. Chaque colonne du contrat conserve son fichier,
  son attribut et sa déclaration ; les empreintes des fichiers sources sont incluses.
- DDL explicite des migrations principales : authoritative pour leurs propres
  tables, colonnes, clés étrangères et index. Les 13 tables et les colonnes créées
  par ces migrations sont exclues du bootstrap.
- Droits du schéma public : politique constatée dans le catalogue de développement
  déjà sauvegardé ; aucun droit de schéma pour PUBLIC. Les ACL internes Neon
  ne sont pas copiées à des rôles locaux fictifs.

Le générateur lit les objets Git, sélectionne uniquement les déclarations DDL
SQLAlchemy autorisées par AST, et n’importe ni n’exécute les modèles historiques.
Il ne lit pas les modèles actuels ni le baseline de test. Le contrat contient
33 tables ; les quatre tables agents/canaux/conversations/messages sont ensuite
créées réellement par la première migration.

## Compatibilité du graphe

Le graphe Alembic principal reste inchangé. Le bootstrap versionné est une étape
explicite **avant la base**, appliquée dans la même transaction que les migrations.
Le lanceur refuse toute relation préexistante ; il ne sert pas à adopter une copie
diagnostique ni à rejouer c413 sur dce91870b4a2.

Une installation déjà située dans l’historique principal continue avec cet historique,
sans bootstrap. Une installation dce/S1b demeure une autre histoire ; son passage au
principal exige une reconstruction contrôlée, sauvegardée et approuvée séparément.
Le générateur v1 correspond à l’inventaire des migrations de cette livraison ; toute
évolution de ce contrat doit être revue et versionnée explicitement.

Chemin exact :

```text
main-bootstrap-v1 (33 tables, aucune ligne Alembic)
17b6b58772b7 → 2d999b8ed18f → 4c3017ab0067 → 83fe3deff863
→ 1452679b0eb0 → fd29befe8baf → dc626cfd1aaf → 888e43fc4f9b
→ a9a5aec4604b → 43d4b74c965c → 084c58bd26bf → 9a92b84b5b11
→ c3a5f018d7e2 → 6bf21d4a8c30 → a91e7c2b4d10 → c413b7918a20
→ e1a92b200001 → s1a20261028
```

## Répétition locale reproductible

Depuis `D:\MoulAI`, avec PostgreSQL 18 installé :

```powershell
.\.venv\Scripts\python.exe -I -B scripts/freeze_main_bootstrap.py
.\.venv\Scripts\python.exe -I -B scripts/run_local_postgres_tests.py --backend native --profile main
```

Le premier contrôle reproduit le contrat sans écriture. Le second crée une instance
native neuve liée uniquement à 127.0.0.1:55432, une base `moulai_pytest`, un rôle
local sans SUPERUSER/CREATEDB/CREATEROLE et un marqueur d’instance aléatoire. Il
utilise UTF8 et le fournisseur de locale builtin C.UTF-8. Aucun mot de passe n’est
imprimé. L’instance est arrêtée dans `finally`.

Le profil historique reste accessible par `--profile subscription` et exige toujours
`s1b20261028`. Le profil `main` exige exclusivement `s1a20261028`. Les 219 scénarios
sélectionnés sont les mêmes ; le test de catalogue attend la révision du profil
sélectionné, sans accepter arbitrairement l’autre révision.

Les fixtures S1a conservent les neuf tables E1 et leurs politiques. Elles refusent
la présence de données de gouvernance de test dans ce parcours d’abonnement.
Elles tronquent leurs tables métier dépendantes, puis suppriment uniquement les
lignes legacy non liées dans cinq tables parentes. Les triggers E1 et les triggers
d’immutabilité S1 restent actifs ; aucun `DISABLE TRIGGER`, `session_replication_role`
ou contournement des contraintes n’est employé.

Pour une instance locale déjà provisionnée, le lanceur séparé utilise uniquement
la variable dédiée `MOULAI_MAIN_LOCAL_URL` fournie par le propriétaire du processus,
avec le marqueur réel de cette instance :

```powershell
# URL secrète locale fournie dans MOULAI_MAIN_LOCAL_URL ; jamais DATABASE_URL/.env.
.\.venv\Scripts\python.exe -I -B scripts/run_main_migrations.py --instance-id <marqueur-local-32-hex>
.\.venv\Scripts\python.exe -I -B scripts/run_main_migrations.py --instance-id <marqueur-local-32-hex> --confirm-empty-local
```

La première commande est une inspection en transaction READ ONLY. La seconde
refuse toute base déjà construite ; elle s’emploie donc sur une autre base locale
vide marquée, et non après la campagne ci-dessus. Ce lanceur est volontairement
local : les noms `neondb` et `neondb_test`, DNS Neon, autres ports, utilisateurs,
paramètres de routage et marqueurs étrangers sont refusés avant migration.

## Catalogue et différences à examiner

Catalogue reconstruit : **61 tables, 548 colonnes, 544 contraintes PostgreSQL 18
(y compris NOT NULL), 170 index, 54 séquences, 13 fonctions, 33 triggers, aucune
politique RLS**. La copie diagnostique avait 61/548 tables/colonnes mais 538
contraintes et 166 index. Le rapport machine compare toutes les catégories,
y compris types, défauts, contraintes, index, fonctions, triggers, ACL et séquences.

Différences établies :

- Aucun ajout/suppression de colonne et aucun changement de type.
- 166 positions physiques de colonnes diffèrent, conséquence de l’ordre des
  déclarations et des migrations ; ce n’est pas une différence de noms/types.
- Quatre `is_active` deviennent NOT NULL avec défaut serveur true : agents,
  channels, conversations, admin_sessions, conformément aux migrations principales.
- Quinze défauts serveur diffèrent : les quatre précédents, agents langue/nom/ton,
  six autorisations de méthodes de paiement restaurant, roles.is_active et users.consent.
  Ce sont des défauts historiques conservés, pas l’activation d’une passerelle réelle.
- Huit clés étrangères ont des noms différents. Sept conservent la même définition.
  **registration_requests.owner_id** passe de NO ACTION dans la copie diagnostique
  à **ON DELETE SET NULL** dans la migration principale. Cette différence de
  comportement est réelle et doit être acceptée avant reconstruction distante.
- Deux contraintes uniques supplémentaires et quatre NOT NULL expliquent les six
  contraintes nettes supplémentaires. L’unicité de users.chat_id fait doublon avec
  l’index unique historique ; elle n’est pas supprimée silencieusement.
- Les index ajoutés/remplacés viennent des migrations historiques ; les index
  supprimés incluent des doublons de clés primaires et l’ancienne forme d’index
  unique du jeton de session. Le détail nominal figure dans le JSON de comparaison.
- Les expressions du CHECK de review_status et de l’index partiel de souscription
  ont une représentation différente des casts de tableaux ; leur intention reste
  identique. Ce constat ne remplace pas les scénarios PostgreSQL exécutés.
- Les **33 triggers et 13 fonctions ont les mêmes définitions**, sans désactivation.
- Les six FK restent volontairement NOT VALID : fk_admin_identity,
  fk_owner_identity, fk_group_link_group_org, fk_group_link_restaurant_org,
  fk_groups_org, fk_restaurants_org. PostgreSQL continue de vérifier les nouvelles
  écritures ; l’historique antérieur n’a pas été certifié par VALIDATE CONSTRAINT.
- Les propriétaires des objets sont remappés au rôle local. PUBLIC ne reçoit
  ni CREATE ni USAGE sur public ; son propriétaire est pg_database_owner,
  avec les droits du propriétaire effectif de la base. Les ACL E1 sont conservées
  avec le nom du rôle local. Les deux default ACL cloud_admin/neon_superuser
  propres à Neon sont absentes localement : elles exigent un contrôle distinct
  lors d’une opération distante, sans création de ces rôles à leur place.
- Locale logique builtin C.UTF-8 version 1 ; les champs LC_COLLATE/LC_CTYPE Windows
  restent C, contrairement à C.UTF-8 sur Linux. Cela limite la revendication
  d’identité physique avec Neon. PostgreSQL local 18.3, source sauvegardée 18.6.

Le démarrage vérifié utilise le véritable lifespan FastAPI et init_db, sans serveur
public ni connexion extérieure. L’URL applicative est remplacée uniquement dans le
processus par la cible locale attestée ; aucun fichier .env n’est modifié.

## Configuration commerciale et habilitations

Le principal installe les seuls paramètres approuvés par S1 : base 3000 DZD,
précision DZD 2, rappels 14/7/1/0, trois tranches progressives des succursales,
sept paliers de fidélité et trois paliers multi-restaurants.

**Restent absents** : formules/liaisons de fonctionnalités/prix des fonctionnalités,
grilles commerciales d’autres devises/marchés, coordonnées effectives des deux
canaux de rappel et responsable habilité pour l’encaissement cash. Les prix
synthétiques des fixtures ne sont pas des configurations commerciales installées.

La migration RBAC existante crée trois définitions de rôles et 28 liens
rôle-permission, puis c413/S1 ajoutent payments.review et la permission cash.
La reconstruction vide ne crée aucun administrateur/propriétaire/identité client :
**zéro attribution personnelle de rôle**. Les rôles de politique E1 restent fermés
selon leurs protections SQL. Cela ne constitue pas une validation de Keycloak réel.

## Limites de décision

Les résultats détaillés, l’identifiant de répétition, les tests réellement exécutés,
les tentatives intermédiaires et l’état Git sont dans
`artifacts/main-bootstrap-20261030/rapport.md`.
La reconstruction distante demeure interdite dans cette livraison. Le bootstrap
historique ne constitue ni une certification de tous les parcours métier ni une
validation de production. La reprise du socle et les différences recensées doivent
être examinées avant l’autorisation distincte de reconstruire neondb_test.


## Résultats finaux et archive canonique

- S1a : **219/219 scénarios réussis**, sans échec, ignore ni avertissement,
  757,65 s, répétition `fd0e2081597645d184f4261c000edbd2`.
- Admission hors ligne : **49/49 réussis**, incluant refus croisé S1a/S1b et refus
  de remplacer la variable dédiée par DATABASE_URL.
- Archive privée canonique : restauration locale réussie ; privilèges effectifs
  identiques ; 11 expressions CHECK/prédicat comparées sur 1150 combinaisons
  incluant valeurs autorisées, invalides et NULL, zéro divergence.
- Transition depuis le véritable ancien catalogue restauré : dce → S1a puis
  récupération complète du backup original, catalogue et empreintes identiques.
  Une erreur injectée prouve le rollback intégral. Schéma public et default ACL
  conservés. Démarrage réel également réussi sur cette transition.
- Les 23 fichiers de migrations présents dans les deux histoires sont inchangés
  par rapport au début de la mission. Aucun commit n’a été créé.

Le mode d’archive `--main-archive` est distinct du mode pytest : il reconstruit une
nouvelle instance, exporte uniquement les seeds approuvés, restaure puis contrôle
le catalogue et FastAPI, et n’annonce pas de campagne pytest dans ce mode.
L’archive reste hors dépôt ; tout fichier existant est refusé. Pour une nouvelle
répétition, choisir un nouveau nom dans le dossier privé protégé autorisé.
Le plan distant détaillé est préparé dans
`artifacts/main-bootstrap-20261030/plan-neondb-test.md`, sans exécution distante.
