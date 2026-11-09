# Abonnements MoulAI — corrections et préparation locale du circuit espèces

Date : 29 octobre 2026. Branche : `feature/keycloak-k10-complete`.
Base Git : `0a29bfecb1fa47e6128477d3375480ff65fb260e`.
Modifications locales non commitées. Aucun accès à une base permanente ou distante.

## Périmètre et décision

Ce travail applique les décisions métier explicites de l'utilisateur aux calculs,
contrats, demandes d'abonnement, droits, historique, rappels et encaissements
manuels. Il prépare l'intégration ; il ne connecte pas les utilisateurs du
Frontend aux services réels et ne constitue pas une validation de production.

La vérification finale et son verdict figurent dans la section « Validation ».

## Calcul et paramètres conservés

`pricing_service.py` est la source de calcul commune. Le prix SaaS B est lu dans
`subscription_pricing_config`, les coûts des fonctionnalités dans
`feature_pricing`. Les champs historiques de base préagrégée des plans ne
servent plus à calculer les nouvelles souscriptions.

| Formule | Construction |
| --- | --- |
| Basic | B + A |
| Professional | B + (P + A) × 0,95 |
| Enterprise | B + P × 0,95 + (E + A) × 0,90 |

P et E sont les sommes des coûts des fonctionnalités des couches originales.
Les ajouts sont dédupliqués ; ceux déjà inclus sont exclus de A. Les inclusions
originales restent obligatoires, y compris lorsque des liaisons historiques
sont incomplètes. Leur retrait par le repository est refusé. Un coût manquant
ou ambigu est une erreur de configuration. Les trois formules commerciales
sont reconnues ; le plan technique d'essai reste distinct.

Le score est `(produits + 3 × catégories + 0,1 × commandes + panier/100) × 10`.
Il s'ajoute à la base pour former Val. Fidélité, multi-restaurants et promotion
sont calculées séparément sur cette même Val. Les frais progressifs des
succursales sont ajoutés après ces remises, puis les mois facturés et enfin
l'ajustement électronique −2 % ou espèces +2 % sont appliqués.

Les calculs utilisent `Decimal`. Seul le montant final dû est quantifié avec
`ROUND_HALF_UP`, à la précision persistée de la devise. Les contrats de paiement
conservent également `Decimal` ; leurs montants JSON sont des **chaînes décimales
exactes**, à prendre en compte par les futurs adaptateurs d'intégration. Les
valeurs de présentation ne sont pas réinjectées dans le calcul.

Un instantané conserve B/P/E/A, les coûts et identifiants tarifaires, les droits
inclus et ajoutés, les remises retenues, le cycle, la méthode, la devise, le marché,
les tranches et les valeurs intermédiaires exactes. Les montants retenus et dates
achetées ne sont pas recalculés après une modification tarifaire.

### Exemples complets vérifiés par les tests de parcours

Jeu entièrement synthétique : B=3 000, P=2 000, E=1 500, A=500 ;
100 produits, 10 catégories, 1 000 commandes terminées de valeur nette 2 000 ;
3 succursales → 1 000 de frais ; promotion générale 10 % ; cycle annuel payé
10 mois et servi 12 mois calendaires ; paiement électronique.

| Étape | Professional | Enterprise |
| --- | ---: | ---: |
| Base par couches | 5 375 | 6 700 |
| Score | 2 500 | 2 500 |
| Val | 7 875 | 9 200 |
| Fidélité | 393,75 (2 ans, 5 %) | 736 (3 ans, 8 %) |
| Multi-restaurants | 393,75 (3 restaurants, 5 %) | 1 380 (10 restaurants, 15 %) |
| Promotion | 787,50 | 920 |
| Après remises | 6 300 | 6 164 |
| Frais succursales | 1 000 | 1 000 |
| Mensualité | 7 300 | 7 164 |
| Dix mois facturés | 73 000 | 71 640 |
| Ajustement électronique | −1 460 | −1 432,80 |
| **Montant dû attendu** | **71 540,00 DZD** | **70 207,20 DZD** |

**Obtenu : 71 540,00 DZD et 70 207,20 DZD**, identiques aux montants attendus,
dans les tests de parcours complets des deux formules.

Les tests construisent les périodes de service et leurs paiements, les coûts
détaillés, les commandes et leur historique de fin, puis passent par le checkout,
la vérification manuelle CCP, l'activation, les droits et l'instantané. Ils
vérifient aussi la stabilité du montant et l'idempotence après changement tarifaire.

## Ancienneté, contexte et calendrier

La fidélité utilise les périodes effectivement payées et activées, en fusionnant
les chevauchements. L'essai et les interruptions n'ajoutent aucune ancienneté.
Les interruptions conservent le cumul acquis. Convention de cumul : une horloge
calendaire virtuelle part du premier début payant et avance uniquement des durées
de service couvertes ; les anniversaires de cette ancre donnent les années
acquises. Le 29 février est ramené au dernier jour du mois cible lorsqu'il manque.
Les seuils sont inclusifs, sans attente du lendemain. Les taux globaux approuvés
1/2/3/4/5/10/15 ans → 2/5/8/11/15/20/25 % sont persistés.
Les règles d'un autre propriétaire sont exclues. Parmi les règles admissibles,
le seuil le plus élevé prime ; au même seuil, la règle du propriétaire prime
sur la générale, puis l'identifiant croissant rend la sélection stable.

Les grilles de succursales sont sélectionnées par devise, date, marché et formule.
La sélection privilégie le marché spécifique puis la formule spécifique ; à
spécificité égale, plusieurs grilles applicables sont refusées. Les rangs doivent
être contigus dès la deuxième succursale. Aucun taux de change ni tarif d'une
autre devise n'est utilisé par défaut. La configuration DZD approuvée est stockée
dans la migration : 2–5 à 500, 6–20 à 400, 21+ à 300. Les anciennes lignes sont
conservées mais désactivées pour revue.

Les promotions sont filtrées par propriétaire, restaurant, formule, activation et
intervalle `[début, fin[`. Une seule est retenue : taux maximal, priorité
administrative maximale, puis **identifiant le plus petit**.

Les périodes payantes sont de 1/3/6/12 mois calendaires ; les multiplicateurs
facturés sont 1/3/6/10. L'ancre initiale est conservée en fin de mois. Une période
payée en avance commence après la couverture déjà acquise : elle reste
`scheduled` jusqu'à son début, sans effacer les jours existants. L'essai conserve
sa durée fixe de 30 jours, une fois par propriétaire, avec verrouillage du
propriétaire et octroi effectif Basic + Orders + Delivery.
Le contrôle lit à nouveau le propriétaire verrouillé et consulte aussi les
périodes de service existantes : un cache ancien ou un indicateur hérité faux
ne permet pas d'obtenir un nouvel essai après un abonnement antérieur.

## Indicateurs et historique

Le collecteur partagé utilise une seule sélection des commandes actuellement
terminées, datée par leur dernier événement `completed`, sur `[fin−30j, fin[`.
Le panier net est `subtotal_amount − discount_amount`, hors taxes et livraison
séparées. Les montants hérités des commandes sont convertis en SQL vers Numeric
avant calcul Python ; leur ancien stockage flottant n'est pas réécrit ici.
Un événement de fin absent bloque le calcul au lieu d'être remplacé par une date
générique. Zéro commande admissible donne zéro commande et zéro panier.

Fin d'essai : dernier mois de l'essai. Renouvellement continu : fenêtre de
30 jours au calcul, même pour l'annuel. Retour : dernier mois actif enregistré
du dernier service, jamais les données d'inactivité ni le montant d'une ancienne
facture. Le panier exact est aussi conservé en texte décimal, sans quantification
intermédiaire lors de la restauration.

Les instantanés sont immuables en base et contrôlés par propriétaire, restaurant
et abonnement. Un historique absent ou incomplet bloque le parcours. Une
reconstitution manuelle exige `payments.review`, les quatre valeurs, une période
valide, une source et un auteur enregistrés ; elle ne fabrique aucune mesure.

`subscription_boundaries.process_boundaries` prépare les captures de mois actif,
l'expiration et le passage des périodes programmées à actives. Il ne reconstruit
pas des anciens comptes de produits/catégories après une échéance manquée.
Une résiliation anticipée limite la référence à sa date effective, sans attendre
l'ancienne échéance. Une résiliation héritée sans date vérifiable exige une revue
de l'historique, au lieu d'inventer une fin de service.

## Espèces : contrôle distinct du virement

`ManualCashProvider` crée une demande en attente, jamais une preuve de réception.
Le checkout applique +2 %. Un paiement ne peut changer la méthode du devis retenu
pour obtenir l'autre ajustement tarifaire. Les justificatifs CCP/BaridiMob restent
réservés au fournisseur `manual_transfer`.

`CashCollectionService.confirm` est une commande interne, sans nouvelle route
publique. Un futur adaptateur authentifié devra fournir l'identité administrative
vérifiée ; l'identifiant fourni par un propriétaire n'est pas une autorité.
La permission **explicite** `payments.cash.collect` est obligatoire, avec
administrateur et rôle actifs : `payments.review` et `*` seuls ne suffisent pas.
La migration définit cette permission sans l'attribuer à aucun rôle.

La preuve espèces conserve abonnement, paiement, montant attendu et reçu,
devise, date de collecte, date de confirmation, responsable et référence de reçu
normalisée et unique. Montant partiel, devise différente, date future et seconde
preuve contradictoire sont refusés. L'activation commence à la confirmation,
sans antidater l'accès à la date déclarée de collecte.

Chaque tentative dispose d'un événement durable avant validation, y compris si
l'autorisation ou le paiement sont invalides. Succès, répétition idempotente et
refus sont ensuite tracés sans journaliser de secret. Un arrêt brutal peut laisser
une tentative `requested`, à rapprocher plutôt qu'à considérer comme payée.
Preuve, paiement et activation sont atomiques ; un échec annule ces trois effets
sans effacer la tentative. La preuve et ses événements sont immuables. Le verrou
du paiement et l'unicité empêchent doubles encaissements et doubles droits.

## Rappels préparés, aucun envoi réel

Le calendrier `[14,7,1,0]` est persisté et modifiable en base. Les destinataires
sont le propriétaire et le responsable MoulAI désigné. Les événements sont
uniques par abonnement, échéance, décalage et destinataire. Une confirmation de
renouvellement annule les rappels obsolètes non envoyés et programme la nouvelle
échéance ; une demande ou un justificatif non validé ne le fait pas.

Le traitement revendique et confirme durablement chaque envoi avant l'appel au
transport. Un refus prouvé peut être repris ; le succès de l'autre destinataire
n'est pas répété. Une issue ambiguë reste `uncertain` et une interruption après
revendication reste `delivering` : rapprochement manuel, sans réessai aveugle.
Telegram n'apporte pas de garantie générale d'envoi exactement une fois.

Le message indique abonnement, échéance et besoin de renouveler, sans annoncer
un futur prix définitif. Le transport est injecté depuis un canal existant déjà
autorisé ; les tests utilisent exclusivement un faux transport local.

**Prérequis d'intégration non activés ici :** ordonnanceur, capture régulière
des mois actifs, coordonnées du responsable et canal autorisé. Une coordonnée
manquante produit un rappel `blocked`, et non un faux succès. Les échecs et issues
incertaines devront être supervisés. Aucune connexion Telegram n'a été ouverte.

## Migrations et application permanente

- Migration principale préparée : `s1a20261028`, après `e1a92b200001`.
- Historique jetable : `s1b20261028`, après `dce91870b4a2`.
- DDL commune figée : `migration_support/subscription_s1.py`.
- Profil local `subscription` : **52 tables**, sans monter les routes K9/K10.

La migration ajoute cinq tables (configuration, instantanés, rappels, preuves
espèces, tentatives), les champs de devise/contexte/ancrage/priorité, les colonnes
monétaires Numeric, les contraintes d'unicité et les protections d'immutabilité.
Elle initialise seulement les règles commerciales approuvées, jamais un
historique de clients ou une activation.

Avant conversion, des montants hérités non valides ou non arrondis, des devises
héritées non prises en charge ou des paliers globaux contradictoires provoquent
un refus explicite. Les doublons de droits/demandes peuvent aussi bloquer les
contraintes uniques. Aucun nettoyage automatique de ces données n'est effectué.
Le downgrade destructif est refusé : une stratégie de conservation doit être
approuvée séparément.

**Aucune migration permanente n'a été exécutée.** Une future application exige
inventaire des données héritées, sauvegarde/restauration vérifiée, résolution
explicite des incohérences et validation distincte. Les montants historiques ne
sont pas réécrits commercialement ; les fonctionnalités/grilles par devise et
les contacts devront être renseignés et contrôlés dans l'environnement cible.
La chaîne Alembic principale complète n'a pas été exécutée : la preuve locale
porte sur sa DDL partagée, appliquée via l'historique jetable dédié, sans rouvrir
K9/K10.

## Validation

Les diagnostics initiaux restent conservés dans
`artifacts/subscription-verification-20261028`. Les régressions durables sont dans
`tests/subscription_diagnostics`, `test_subscription_lifecycle.py`,
`test_subscription_decisions.py` et `test_cash_collection.py`.

Les 112 diagnostics ont conservé les attentes métier approuvées. Les anciennes
caractérisations de tranches plates, de fin de promotion incluse et de durées
fixes ont été adaptées uniquement aux décisions explicites du 29 octobre. Le
comparateur Decimal évite les écarts dus à la représentation binaire d'un nombre
attendu écrit en Python ; aucune tolérance commerciale n'est ajoutée.

Commandes locales :

```powershell
.\.venv\Scripts\python.exe -I -B scripts/run_local_postgres_tests.py --backend native --profile subscription
```

Le lanceur crée une instance neuve PostgreSQL 18.3 sur `127.0.0.1:55432`, avec
identité et identifiants dédiés, vérifie sa destination, applique uniquement le
schéma jetable et l'arrête après les tests. Aucun `.env` n'est modifié.

| Exécution | Sélection | Résultat |
| --- | --- | --- |
| `785d837bb50b48e0bf8c371de3f3e60b` | Espèces et décisions métier, première vérification | 57/57 réussis |
| `18544f7377214a0f99a6a0474aa38122` | Sélection complète ciblée, comprenant les 112 diagnostics/régressions initiaux | 215 réussis, 1 échec de connexion sur 216 |
| `345de4c5fe0e4907aba804eb5fff2955` | Modules concernés après derniers correctifs : lifecycle, décisions, espèces, workflow manuel | **91/91 réussis**, 142,41 s |
| `44fc2a7ddb8f4c7e8de50dd184e38f02` | Dernier garde-fou de retour sans nouvel essai, lifecycle complet et horloge d'essai | **15/15 réussis**, 73,68 s |

Aucun test ignoré, erreur de collecte ou avertissement dans ces quatre campagnes.
Les instances ont été arrêtées ; les garde-fous réseau n'ont relevé aucune
tentative vers une destination interdite. Les transports de notification sont
factices ; aucun canal externe n'a été utilisé.

L'échec isolé de la sélection de 216 tests est un timeout pendant l'ouverture
de la seconde connexion PostgreSQL du test concurrent d'essai, avant son appel
au service. Les deux connexions sont désormais préparées indépendamment avant
le déclenchement de la course ; les assertions métier et la fenêtre de concurrence
restent inchangées. Ce test passe dans la dernière sélection. Celle-ci couvre
également les ultimes corrections de fidélité, de résiliation et leurs nouveaux
cas, ainsi que les contrats monétaires et les virements manuels.

Les deux dernières exécutions ne sont **pas** une nouvelle exécution complète des 216 tests.
Les sélections se recouvrent : leurs compteurs ne doivent pas être additionnés
comme un nombre de scénarios distincts. Les 112 diagnostics/régressions initiaux
ont réussi dans la sélection complète ; les cas concernés par les dernières
modifications sont revérifiés dans la sélection finale.

Commande de revérification effectivement exécutée :

```powershell
.\.venv\Scripts\python.exe -I -B scripts/run_local_postgres_tests.py --backend native --profile subscription --test-paths tests/test_subscription_lifecycle.py tests/test_subscription_decisions.py tests/test_cash_collection.py tests/test_manual_payment_workflow.py
.\.venv\Scripts\python.exe -I -B scripts/run_local_postgres_tests.py --backend native --profile subscription --test-paths tests/test_subscription_lifecycle.py tests/test_subscription_trial_clock.py
```

Preuves : `artifacts/postgres-local-tests/<identifiant>/validation.json`,
`postgres-results.xml` et `postgres-tests.log`. Les tests et assertions durables
référencés ci-dessus permettent de reproduire les contrôles. Les exécutions
intermédiaires restent conservées ; aucun résultat initial n'est effacé.

Black et Ruff : contrôles ciblés des 47 fichiers Python ajoutés/modifiés réussis.
`git diff --check` réussi.

### État Git à la livraison

Branche `feature/keycloak-k10-complete`, HEAD inchangé
`0a29bfecb1fa47e6128477d3375480ff65fb260e`. Index vide ; modifications locales
non commitées : 27 fichiers suivis modifiés et 21 nouveaux fichiers, dont ce
rapport. L'inventaire et les empreintes sont conservés dans
`artifacts/subscription-correction-20261029/delivery-evidence.json`.
Les fichiers d'artefacts restent ignorés.

Références locales inchangées :

- `main` : `7a667633f593afbabc9949cef12f603535eba94e`.
- `fix/render-health-only` : `b4774a26f221796e82c7468c196361dd9ef302ee`.

Aucune consultation réseau Git n'a été effectuée dans cette intervention ; les
références distantes locales ne constituent pas une vérification de GitHub actuel.

**Verdict : PASS local sur le périmètre corrigé et les scénarios exécutés.**
La préparation de l'intégration peut commencer en environnement isolé. L'ouverture
aux utilisateurs et la mise en service réelle restent conditionnées aux migrations
autorisées, aux configurations et habilitations vérifiées, à l'adaptateur cash
authentifié et au branchement opérationnel des captures et rappels. Aucun arbitrage
commercial supplémentaire n'est requis pour les règles implémentées ici.

## Limite de livraison

Budget externe engagé : **0 USD**. Aucun appel IA, paiement réel, notification
réelle, changement Frontend, migration permanente, commit, push ou déploiement.
La roadmap reste Frontend → Intégration métier → K11 Production Security → Pilote.
