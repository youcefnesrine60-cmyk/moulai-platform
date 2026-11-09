# MoulAI™ — Raccordement local persistant D1

Livraison du 3 novembre 2026, limitée aux tables, réservations et facture alimentaire.
Le socle D1a reste une livraison historique distincte. Cette étape ajoute D1b et
les formulaires reliés aux vrais services sur PostgreSQL local jetable.

## Revue locale

Adresse : <http://127.0.0.1:5574/dining-local>.

Choisir une **identité de répétition**, ouvrir sa session, puis sélectionner
explicitement une succursale autorisée. Les formulaires apparaissent selon les
habilitations réellement relues en base. Le propriétaire peut configurer la seconde
succursale encore non paramétrée ; ses paramètres manquants ne sont pas remplacés
silencieusement par ceux de la première.

L’émetteur des identités est **simulé et local**. Chaque requête vérifie réellement
la signature RS256, la durée, l’émetteur, l’audience et le sujet. E1 et les
habilitations D1 sont contrôlés côté serveur. Cette démonstration ne valide pas
un raccordement Keycloak réel ni un accès de production.

Les écritures, relectures, transactions, contraintes d’exclusion et imputations
sont réelles dans la base jetable. Les personnes, restaurants, tarifs, commandes
sources et fonds sont **fictifs et explicitement signalés**. Les notifications
restent dans l’outbox sans transport. Aucun modèle IA n’est appelé.

Démarrage depuis la racine, ports 55432, 5581 et 5574 libres :

```powershell
Set-Location D:\MoulAI
.\.venv\Scripts\python.exe -B scripts/run_dining_local.py
```

Le lanceur crée son propre cluster PostgreSQL 18, applique le bootstrap et la
chaîne principale jusqu’à `d1b20261103`, puis charge uniquement ses fixtures.
Il ne lit aucune URL cible dans `.env`. Les mots de passe éphémères restent dans
le processus ; le fichier temporaire d’initialisation est supprimé.

Arrêt : `Ctrl+C` dans le terminal du lanceur, ou création du fichier `stop-request`
dont le chemin exact est donné dans le `review.json` de cette instance sous
`artifacts/dining-local-runs`. Cela ferme HTTP/Vite puis arrête son cluster. Un
redémarrage crée une **nouvelle base**, sans reprendre les données de la revue
précédente. Aucun service distant ni aucune migration permanente ne sont utilisés.

## Formulaires et garanties

- Référentiels FR/EN/AR, tables et caractéristiques, regroupements modifiables,
  désactivation sans suppression de l’historique.
- Paramètres explicites, calendrier hebdomadaire/exceptions, heures ambiguës
  sélectionnables, tarifs décimaux versionnés et habilitations séparées.
- Demandes, critères, correspondances descriptives sans confirmation implicite,
  sélection, devis, menus spéciaux et deux accords indépendants.
- Blocage, avance reçue, validation humaine, confirmation et QR consultable et
  imprimable en FR/EN/AR. Un QR annulé retourne `valid: false`.
- Arrivée réelle, facture rapprochée à des commandes existantes, finalisation et
  allocation unique, départ, début et fin de nettoyage distincts.
- Nettoyage et disponibilité ne se confondent pas. Un acteur cumulant les droits
  doit exécuter les deux actions ; les événements restent distincts.

Les montants nouveaux utilisent Decimal/Numeric. Le navigateur transmet et lit
les montants en chaînes. Les prix Float historiques restent diagnostiques ; la
facture exige des prix décimaux vérifiables, leur source, celle de la devise et
une référence de rapprochement. Aucun prix commercial n’est inféré des fixtures.

### Annulation avant arrivée

D1b ajoute uniquement `reservations.cancel_before_arrival`, sans attribution
automatique. Le propriétaire choisit les personnes et la succursale. Le seul
rôle de responsable de service ne donne pas ce droit.

Le client ou l’assistant peut enregistrer une demande, mise en attente pour les
personnes actuellement habilitées ; cela n’annule rien et ne prouve aucun envoi.
L’annulation humaine conserve auteur/date/motif/origine, libère les seuls claims
de la réservation et garde l’état physique, les autres blocages et les avances.
Une arrivée ou une facture déjà créée bloque l’opération. La décision et l’arrivée
se sérialisent atomiquement ; une répétition n’ajoute pas un deuxième événement.

## Validation et limites

Le rapport local et la matrice détaillée sont dans
[la livraison de raccordement](../artifacts/dining-integration-20261103/rapport.md).
Ils distinguent les tests HTTP/PostgreSQL, les contrôles hors ligne et les captures
navigateur. Les sources complètes modifiées sont livrées dans l’archive associée.

Les routes restent opt-in : aucun montage dans `app.main`, aucun changement K9/K10,
aucune ouverture aux utilisateurs. Le build de publication exclut `/dining-local`
et son client. Les annulations après arrivée/facturation, remboursements, partage
ou réutilisation d’un excédent restent bloqués sans politique validée. L’autonomie
de confirmation de l’assistant exige une transmission effective et un délai
écoulé ; sans transport réel elle ne peut pas être démontrée par cette revue.

Cette livraison est une validation locale du périmètre testé, sans certification
fiscale, de production ou de l’ensemble du projet.
