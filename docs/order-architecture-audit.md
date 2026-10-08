# Audit architectural des commandes — 8 octobre 2026

## Conclusion et périmètre

Dernière validation après correction : **178 tests réussis, aucun échec, aucun avertissement**, avec couverture et cache activés et `-W error`. Journal : `warnings-fix-full-tests.log`.

Les corrections décrites ici portent sur les chemins de commandes inspectés :
API propriétaire, actions client, services métier et repositories associés.
Une exécution complète de référence enregistrée le 8 octobre 2026 a donné
**178 tests réussis, aucun échec, 3 avertissements**, en 18 min 13 s.
Ce résultat est une preuve sur les scénarios testés, pas une garantie générale
sur tous les accès, toutes les règles métier ou tous les cas de concurrence.

## Autorisation et frontières de restaurant

| Appelant | Contrôle observé | Limite |
| --- | --- | --- |
| API propriétaire | `Order.restaurant_id -> Restaurant.owner_id -> OwnerPrincipal`, vérifié par les dépendances d’autorisation de l’API. | Le contrôle porte sur le propriétaire. Un même propriétaire peut accéder aux commandes de plusieurs restaurants lui appartenant. |
| Client dans un restaurant | `Order.user_id -> User.chat_id`, complété par `Order.restaurant_id` lorsque le restaurant est fourni au service. | L’appelant doit fournir un contexte de restaurant fiable pour imposer cette frontière. |
| Client sans restaurant | Filtrage par compte client, sans filtre de restaurant. | Le mode global reste autorisé ; il ne constitue pas une isolation par restaurant. |
| Services administratifs internes | Reçoivent des identifiants de commande ; l’autorisation est effectuée à l’entrée de l’API. | Ces services ne constituent pas, à eux seuls, une frontière d’autorisation. |

Le terme « tenant » désigne ici la frontière logique du propriétaire utilisée
par l’API inspectée. Le contrôle ne démontre pas une isolation fondée sur un
identifiant tenant distinct, ni une politique RLS PostgreSQL.

Pour les actions de suivi, d’annulation et de modification, le restaurant du
contexte du canal prime sur l’entité extraite. Le helper convertit le contexte
en identifiant ; une valeur qu’il rejette produit le filtre `restaurant_id=0`.
Une valeur absente conserve le mode global.

La création et l’ajout d’items recherchent le produit dans le restaurant de la
commande. Le nom et le prix de base proviennent du catalogue serveur. La branche,
si fournie, doit appartenir au restaurant. La modification générique refuse de
réassigner `restaurant_id` ou `user_id`. Les noms et téléphones exposés proviennent
du profil client ; leur modification depuis une commande est explicitement refusée.

## Corrections et responsabilités

| Sujet | État du code inspecté |
| --- | --- |
| Création | L’API délègue au service métier. Les créations avec et sans items partagent le même noyau ; commande, items, historique, compteur, usage et métriques sont composés dans l’unité de travail. |
| Action de création | `OrderFoodAction` adapte les paramètres et les réponses. Le devis, le consentement et le placement sont dans `orders/placement.py`. |
| Transitions de commande | Les mutations de statut et l’historique passent par `transition_locked_order`. La politique client d’annulation reste distincte de la politique administrative. |
| Paiement | La confirmation vérifie le lien paiement-commande et modifie le registre de paiement sans remplacer le statut de préparation/livraison par `paid`. Répéter cette confirmation est sans effet supplémentaire. |
| Calculs | `item_total` porte la validation de quantité/prix et le calcul du montant d’un item ; `compute_order_totals` porte la formule commune des totaux. Cela ne constitue pas un audit exhaustif des promotions, options ou politiques tarifaires. |
| Repositories commandes | `OrdersRepository`, `OrderItemsRepository`, `OrderItemOptionsRepository`, `OrderStatusHistoryRepository` et `OrderPaymentsRepository` ont `commit_on_write=False`. Les méthodes héritées concernées ne committent ni ne rollbackent de façon autonome. |
| Repositories auxiliaires | Les repositories génériques conservent leur convention historique. Le drapeau `defer_repository_commit` reporte les commits/rollbacks des méthodes qui le respectent lorsqu’elles participent à l’unité de travail. |
| Contrats de réponse | Les paiements utilisent les schémas de commande existants, distincts des abonnements. La lecture détaillée sérialise la liste d’items retournée par le service. |

Les façades adaptent les contrats et composent les opérations. Les modules métier
portent les politiques et l’orchestration ; ils conservent aussi certaines
requêtes SQL directes. La séparation de tous les accès SQL vers les repositories
n’est donc pas complète. La centralisation décrite ci-dessus ne démontre pas
l’absence de toute duplication dans le reste de l’application.

## Propriété des transactions

Le comportement de [order_transaction](../app/services/business/orders/transaction.py)
dépend de l’état de la session SQLAlchemy :

| Situation à l’entrée | Comportement |
| --- | --- |
| Aucune transaction active | `session.begin()` ouvre une transaction ; sa sortie gère commit ou rollback. |
| Transaction racine implicite `AUTOBEGIN` | Un savepoint entoure l’opération, puis le service committe la transaction racine en cas de succès ou la rollbacke en cas d’échec. |
| Transaction explicite de l’appelant | Un savepoint entoure l’opération ; le commit/rollback racine reste à la charge de l’appelant. |
| Appel composé sous `order_unit_of_work` | Un savepoint imbriqué est créé ; cet appel ne finalise pas la transaction racine. |

Le cas `AUTOBEGIN` finalise la transaction entière de la session, y compris
ses éventuelles écritures antérieures. Un appelant souhaitant conserver la
propriété de ses écritures doit ouvrir une transaction explicite.

Les savepoints protègent les écritures exécutées dans leur périmètre. Ils ne
permettent pas d’affirmer que toute écriture antérieure sera annulée : SQLAlchemy
peut notamment flusher des changements en attente avant l’ouverture d’un savepoint.

Les chemins inspectés de statut, paiement et quantité prennent un verrou sur la
commande avant les contrôles sensibles. La validation du catalogue verrouille
le produit. Les tests ci-dessous ne simulent pas des écritures concurrentes et
ne démontrent donc pas tous les effets de ces verrous en concurrence réelle.

L’annulation avec remboursement met à jour le registre interne dans la même
unité de travail. Elle ne réalise pas de remboursement auprès d’une passerelle
bancaire externe. Aucune migration ni politique RLS n’a été ajoutée par cet audit.

## Preuves et limites des tests

Les 26 cas de [test_order_tenant_isolation.py](../tests/test_order_tenant_isolation.py)
se répartissent ainsi :

| Cas | Nombre | Preuve apportée |
| --- | ---: | --- |
| Autorisation propriétaire | 4 | Prédicats exécutés sur SQLite, accès autorisés et refusés. |
| Refus HTTP | 9 | Lecture, modification, statut, annulation, complétion, paiement, suppression, liste et statistiques refusés avant l’appel métier pour le propriétaire étranger. |
| Suivi client | 4 | Filtrage par client et restaurant, dont un restaurant différent du même propriétaire. |
| Mutations client refusées | 6 | Annulation ou modification hors client/restaurant, sans écriture observée dans l’adaptateur de test. |
| Contexte des actions | 3 | Services simulés : vérification de la priorité du restaurant du canal. |

Ces 26 cas ne sont donc pas tous des tests SQL : les trois tests d’actions
utilisent des mocks. Les tests de liste et statistiques prouvent un refus
à l’entrée, pas le filtrage du contenu d’une liste ou d’un agrégat autorisé.
SQLite ne valide ni les verrous PostgreSQL ni les transactions de production.

Les 18 cas de [test_order_postgres_transactions.py](../tests/test_order_postgres_transactions.py)
utilisent une vraie base PostgreSQL de test et des lectures depuis une seconde
session. Ils couvrent la persistance des créations et mutations, la propriété
des transactions implicites/explicites, le rollback après échec d’item,
d’historique, d’usage, de métriques ou de paiement, le refus de produit/paiement
étranger, les refus HTTP inter-propriétaires, la relecture détaillée, les
transitions, la suppression et l’atomicité annulation/remboursement interne.
Ils ne constituent pas une preuve de tous les entrelacements concurrents ni
d’un remboursement bancaire externe.

Les tests de [frontière d’architecture](../tests/test_order_architecture_boundaries.py)
contrôlent certaines opérations interdites dans l’action de création et des
entrées de prix/quantité invalides. Les tests de
[mode transactionnel des repositories](../tests/test_repository_transaction_mode.py)
vérifient notamment l’absence de commit/rollback lors d’un `update` pour les
cinq repositories commandes ; ils ne testent pas individuellement toutes leurs méthodes.

Résultat enregistré dans `completion-full-tests.log` :
**178 passed, 3 warnings in 1093.36s (0:18:13)**, code de sortie 0.
Les trois avertissements concernent la dépréciation FastAPI de
`HTTP_422_UNPROCESSABLE_ENTITY`. Aucun test n’a été signalé comme ignoré dans
cette exécution. La correction documentaire présente ne constitue pas une
nouvelle exécution des tests.

## Reproduction et environnement de test

Depuis la racine du projet, dans PowerShell :

```powershell
$env:DEBUG = 'false'
.venv\Scripts\python.exe -u -m pytest -W error --tb=short
```

Cette commande conserve le cache, active la couverture configurée dans pytest.ini et traite les avertissements comme des erreurs. `DEBUG=false` contourne la valeur `DEBUG=release` observée
lors de l’exécution précédente, sans modifier le fichier `.env`.

La configuration de [tests/conftest.py](../tests/conftest.py) utilise une base
dédiée dérivée de l’URL configurée, avec suffixe `_test`. Elle nettoie ses tables
par `TRUNCATE ... RESTART IDENTITY CASCADE` pour les tests utilisant `client`
ou `db_session` ; cette commande doit être exécutée avec une configuration de
base de test appropriée.

Les connexions de test utilisent un pool de cinq connexions au maximum,
`pool_pre_ping=True`, un délai de connexion de 60 secondes, un délai de commande
de 60 secondes et `lock_timeout=5000`. Le délai d’inactivité transactionnelle
est désactivé sur ces connexions. Le pool est fermé en fin de session pytest ;
les tests et fixtures asyncio partagent une boucle de session, tout en conservant
leur portée de fixture par test lorsqu’elle est déclarée ainsi.

Ces réglages ont été introduits après des timeouts de requête/connexion TLS et
une déconnexion au nettoyage lors des tentatives précédentes. Le serveur avait
alors indiqué `idle_in_transaction_session_timeout=5min` ; cela ne suffit pas
à attribuer avec certitude chaque déconnexion à ce seul paramètre. Le succès de
la dernière suite ne garantit pas l’absence future de problèmes réseau.
Les réglages de production n’ont pas été modifiés par ces ajustements de test.

## Correction de l’incident signalé après l’audit

Une exécution ultérieure fournie par l’utilisateur a donné **177 passed,
1 failed, 5 warnings**. L’échec concernait la mise à jour des moyens de paiement,
avec une connexion fermée pendant une lecture de `products`. Cette trace ne
permet pas d’identifier à elle seule la cause de la fermeture réseau.

Le repository des paramètres de paiement charge désormais uniquement ses champs
scalaires pour la lecture par restaurant et par identifiant. Il ne parcourt plus
le graphe restaurant/catalogue dans ce chemin. Le test de mise à jour vérifie
l’absence de lecture des restaurants, produits et catégories ainsi que la
persistance des moyens de paiement modifiés. Aucune écriture n’est rejouée
automatiquement après une déconnexion.

La constante dépréciée `HTTP_422_UNPROCESSABLE_ENTITY` a été remplacée par
`HTTP_422_UNPROCESSABLE_CONTENT` dans les API ; le code HTTP reste 422.
Le cache pytest utilise désormais `.cache/pytest`, dont l’écriture a été vérifiée,
plutôt que le répertoire `.pytest_cache` inaccessible. Le cache reste activé.
Une relance a aussi révélé un timeout TLS à l’ouverture d’une connexion après
15 secondes ; le délai de connexion du banc de test est maintenant de 60 secondes.

Validation ciblée : **22 passed**, sans avertissement, avec `-W error` et le cache
activé (`payment-warning-check.log`). La revalidation complète avec couverture,
cache et `-W error` a réussi : **178 passed in 1452.81s (0:24:12)**, aucun
avertissement, code de sortie 0. Couverture globale : **40 %**.
Journal : `warnings-fix-full-tests.log`.
Une tentative complète supplémentaire a réussi les tests de métriques mais a
échoué à leur nettoyage : la connexion de fixture était déjà fermée. Les fixtures
API ne font désormais plus les `refresh` de préparation inutiles après
`flush`/`commit`. Les identifiants sont déjà disponibles et les valeurs sont
conservées grâce à `expire_on_commit=False`. Cela évite de rouvrir une transaction
de lecture inactive et de conserver sa connexion pendant les requêtes API.
Les assertions, les commits nécessaires aux données de préparation et les
rollback/truncate de nettoyage sont conservés ; aucune erreur n’est ignorée.