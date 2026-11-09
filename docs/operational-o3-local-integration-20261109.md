# MoulAI™ — Raccordement O3/O4 et inscription locale

État du 9 novembre 2026 : **jalon local vérifié, intégration globale inachevée**.
Le rapport détaillé et la matrice sont dans
`artifacts/operational-o3-20261108/rapport.md`. La date du dossier correspond
au début des travaux, et non à une nouvelle phase de la feuille de route.

## Source tarifaire unique

La revue utilise exclusivement PostgreSQL local,
`127.0.0.1:55433/moulai_integrated`, schéma `public`, révision `o420261108`.
La valeur B n'a pas été synchronisée vers Neon dans cette intervention.

Le prix est dans `public.subscription_base_prices.amount`, de type
`NUMERIC(24,8)`. Une ligne porte un identifiant `id`, une `revision` unique,
`country_code`, `currency`, `effective_from` inclus et `effective_until` exclu.
Le couple actuel approuvé est `DZ/DZD`, montant **3 000 DZD**.
Les exemples 3 500, 4 000 et 5 000 ne sont pas des augmentations programmées.
Aucun prix pour un autre pays n'a été ajouté à la revue.

```sql
SELECT id, country_code, currency, amount, revision,
       effective_from, effective_until, source_reference
FROM public.subscription_base_prices
WHERE country_code = 'DZ'
  AND currency = 'DZD'
  AND effective_from <= CURRENT_TIMESTAMP
  AND (effective_until IS NULL OR CURRENT_TIMESTAMP < effective_until);
```

Le modèle est `app/models/subscription_base_price.py:SubscriptionBasePrice`.
Le résolveur est `subscription_country_base.resolve_country_base`, appelé par
le moteur `pricing_service` et les services de checkout/abonnement.
Le stockage est introduit par `2026_11_08_country_base_o3.py`, révision
`o320261108`. O4 ajoute les décisions de pays et leurs liens de provenance.
La table `subscription_pricing_config` conserve les politiques communes,
sans seconde colonne B sur O3/O4. Le mapping legacy séparé utilise cette même
table seulement sur les révisions anciennes explicitement reconnues.
Une révision inconnue, un couple absent ou ambigu provoque un refus.

Chaque devis retient la version B, le pays, la devise et la décision appliquée
dans son instantané immuable. Une modification administrative immédiate ne
réécrit aucune période payée ni calcul retenu. L'éditeur exige la permission
exacte `subscriptions.pricing.manage`, une version attendue et un motif.

## Pays de facturation et autorité

Les tables `billing_country_profiles`, `billing_country_evidence`,
`billing_country_requests` et `billing_country_decisions` séparent déclaration,
justificatif privé, demande et décision humaine immuable.

Seule `tenant.billing_country.manage`, attribuée explicitement, autorise la
revue. La permission n'est déduite ni d'un rôle ni d'une autre permission.
Une déclaration du propriétaire ne remplace jamais cette décision.
Le téléchargement du justificatif vérifie à nouveau l'identité et l'accès.
Un dossier réel est refusé : seule une preuve fictive locale est admise ici.

Pour un changement concernant une couverture active unique, la décision prend
effet à son échéance. Le checkout anticipé sélectionne le contexte de la
prochaine période, sans effacer les jours acquis. L'ancien historique reste
intact. Si plusieurs établissements ont des échéances différentes, la demande
est bloquée explicitement : la politique de transition multi-échéances manque.
Un changement d'entité juridique reste un examen distinct.

## Documents fictifs et inscription

Les documents FR/EN/AR portent le marquage explicite de recette, des identifiants
et une version `LOCAL-TEST-20261108-v1`. Les contenus et leurs empreintes sont
immuables. Une présentation est tracée séparément de l'acceptation contractuelle,
de l'information sur les données et du choix facultatif.

Le serveur exige un environnement de développement/test et atteste la véritable
base locale, son utilisateur, son marqueur et sa révision. Il refuse ces documents
en production avant toute requête SQL. Une version inconnue, retirée ou non
présentée ne peut être acceptée. Un refus facultatif n'empêche pas l'inscription.
Les choix sont initialement vides ; après rechargement, une réponse déjà conservée
est montrée comme enregistrée, sans créer une nouvelle acceptation.

Le compte doit être authentifié par Keycloak local et déjà reconnu par le serveur.
L'inscription crée réellement le dossier, puis atomiquement l'entreprise, le
premier restaurant, la première succursale, le rattachement et l'essai admissible.
La création de ces deux entreprises de recette n'a pas utilisé la CLI.
La préparation technique des comptes Keycloak reste locale et administrée ;
elle ne constitue pas une inscription publique au fournisseur d'identité.

Les documents juridiques définitifs et les durées de conservation réelles ne
sont pas validés. Aucun consentement fictif ne sera transformé en preuve réelle.
Les nouvelles versions devront conserver leur identité et leur historique propres.

## Paiement local et limites d'activation

Le propriétaire retient une offre calculée côté serveur. Le checkout crée une
demande en attente et conserve le même paiement pour une répétition identique.
Le dépôt d'un justificatif ne confirme pas les fonds.
Un autre compte, doté explicitement de `payments.review`, vérifie les montants,
la devise et la référence avant l'activation atomique existante.

La recette prouve ce chemin avec **fonds et document fictifs**, sans accès
postal/bancaire. Les coordonnées commerciales CCP/BaridiMob restent absentes.
Le connecteur manuel existant n'accepte que DZD : une grille B dans une autre
devise ne suffit pas à créer un circuit de paiement dans cette devise.
Le circuit cash existant n'est pas exposé par ce nouveau formulaire.

Une offre en attente dont la version B ou la décision de pays est devenue
obsolète est refusée à la finalisation. Son instantané n'est pas modifié.
**Le remplacement explicite de cette demande obsolète dans l'interface reste
à raccorder**, particulièrement lorsqu'un justificatif existe déjà. La simulation
courante est disponible ; ce verrou de sécurité ne vaut pas parcours de reprise
terminé. O3 n'est donc pas annoncé intégralement clôturé.

## Répétition et exploitation locales

La revue a été migrée une seule fois après sauvegarde fraîche, restauration
réelle sur une copie isolée, comparaison du catalogue et des lignes, rollback
de la migration et récupération effective du backup.
Les commandes ci-dessous décrivent le chemin exécuté, pas une invitation à
remigrer une revue déjà sous O4 :

```powershell
.\.venv\Scripts\python.exe -I -B scripts/prepare_operational_o4.py
.\.venv\Scripts\python.exe -I -B scripts/migrate_operational_local.py --target o420261108
.\.venv\Scripts\python.exe -I -B scripts/run_operational_local.py serve --instance D:\MoulAI\artifacts\operational-local\3fb5f85a6cc94868acaf7d95b3777a16
```

Le premier et le deuxième lanceur exigent l'arrêt de l'hôte, la liberté des ports
et le verrou d'instance. Le migrateur contrôle aussi l'empreinte de la sauvegarde,
du catalogue et des sources. Il n'utilise ni `stamp` ni `DATABASE_URL` implicite.
Les sauvegardes et identifiants restent privés, ignorés par Git et exclus des
archives livrées.

Les répétitions destructives utilisent seulement des bases jetables. Le profil
historique S1b utilise le port natif 55435 pour préserver l'instance D1 sur 55432.
Le nouveau jeu O4 utilise 55434 et reconstruit la chaîne principale réelle.
La revue conservée ne reçoit aucune suite de tests destructive.

Les rappels des comptes web restent bloqués sans contact autorisé ; le numéro
de compatibilité des anciens modèles ne devient pas une destination Telegram.
Aucun worker, appel IA, message externe ou déploiement n'a été activé.

Feuille de route conservée : **Frontend → Intégration métier → K11 → Pilote**.
