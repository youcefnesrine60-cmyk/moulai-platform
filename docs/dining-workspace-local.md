# D1 — Revue opérationnelle locale

La dernière recette, les capacités financières D1c, le mode Automatique horaire et les actions contextualisées sont décrits dans [la recette finale locale](dining-final-local-rehearsal.md). Les mentions ci-dessous des boutons radio et de l’ancien parcours nominal concernent la livraison précédente ; les transitions physiques sont maintenant proposées dans leur ordre légal, sans choix d’action ambigu.

Cette revue conserve deux environnements séparés. Aucun d’eux ne donne accès à une base permanente, à Keycloak distant, à un fournisseur IA ou à un transport de notification.

## Accès principal synthétique — port 5173

Fonction : consulter le Frontend MoulAI et ses données synthétiques, sans backend réel. Le mode `review` est interdit dans un build de publication. Le refus de connexion constaté le 4 novembre 2026 provenait de l’absence d’un processus en écoute, avant le traitement de `/access`.

Depuis PowerShell :

```powershell
Set-Location D:\MoulAI
$env:PATH = 'D:\MoulAI\artifacts\frontend-tooling\node-v24.22.1-win-x64;' + $env:PATH
npm.cmd --prefix frontend run dev:review -- --port 5173 --strictPort
```

URL : <http://127.0.0.1:5173/access>. Nécessite seulement Node et les dépendances Frontend déjà installées. Pas de PostgreSQL ni de serveur applicatif. Arrêt : `Ctrl+C` dans le terminal qui a lancé cette commande. Un port occupé produit une erreur ; aucun repli vers 5174 n’est autorisé.

## Revue D1 persistée — ports 5574, 5581 et 55432

Fonction : formulaires D1, signatures locales RS256, autorisations serveur et écritures réellement persistées dans **un PostgreSQL jetable local**. Les identités et les fonds restent fictifs. La sélection d’identité simule uniquement l’émission locale d’une identité de recette ; elle ne constitue pas une intégration Keycloak réelle.

```powershell
Set-Location D:\MoulAI
.\.venv\Scripts\python.exe -I -B scripts/run_dining_local.py --visual-fixtures
```

URL : <http://127.0.0.1:5574/dining-local>. Dépendances : Python du projet, PostgreSQL 18 natif dans `C:\Program Files\PostgreSQL\18\bin`, Node et dépendances Frontend locales. Le lanceur possède le cycle de vie du cluster 55432, de l’API 5581 et de Vite 5574. Le mode `dining` lie exclusivement le loopback et ne peut pas être publié. Le lanceur refuse un port occupé avec l’adresse exacte ; il ne tue pas son occupant.

Le lanceur ne charge pas une cible `.env`. Il construit une cible locale contrôlée et bloque le réseau sortant hors PostgreSQL local. Aucun worker, transport, fournisseur externe ou migration permanente n’est lancé.

L’option `--visual-fixtures` conserve les deux tables T1/T2 du parcours nominal et ajoute six tables V, avec les cinq états physiques, une occupation suivie d’une réservation, un nettoyage en retard, un planning complet et un blocage temporaire. Les demandes `VISUAL-FIXTURE` sont **des instantanés illustratifs persistés**, pas des confirmations financières issues du parcours nominal. Elles n’ont ni encaissement ni justificatif valide. L’interface le signale. Les montants commerciaux ne sont pas initialisés par cette option.

Sans l’option, le lanceur garde la fixture minimale du parcours D1. **Chaque lancement crée une nouvelle instance** ; les données restent consultables pendant sa vie et après rechargement du navigateur. Il ne s’agit pas d’un service Windows redémarrant automatiquement ni d’une base durable entre lancements. Les répertoires des instances précédentes ne sont pas supprimés.

### Arrêt contrôlé de la revue D1

Chaque lancement écrit sa propre référence non sensible `review.json` dans `D:\MoulAI\artifacts\dining-local-runs\<instance_id>`. Lire celle de l’instance active et créer **uniquement** son fichier `stop-request` :

```powershell
# Remplacer uniquement par l’identifiant du lancement actif, relevé dans son review.json.
$instance = 'd97f9604b455456090a1de5899824764'
$root = [IO.Path]::GetFullPath('D:\MoulAI\artifacts\dining-local-runs')
$directory = [IO.Path]::GetFullPath((Join-Path $root $instance))
if ((Split-Path $directory -Parent) -ne $root) { throw 'Instance hors périmètre' }
$review = Get-Content -LiteralPath (Join-Path $directory 'review.json') -Raw | ConvertFrom-Json
if ($review.instance_id -ne $instance) { throw 'Instance non concordante' }
$expectedStop = Join-Path $directory 'stop-request'
if ($review.stop_request -ne $expectedStop) { throw 'Chemin de cycle de vie non concordant' }
Set-Content -LiteralPath $expectedStop -Value 'local-review-stop' -Encoding ascii
```

Le moniteur arrête HTTP/Vite, puis le `finally` arrête le cluster possédé. Vérifier ensuite `safety.json` et la libération des trois ports. Ne pas lancer en parallèle le lanceur de tests natif sur 55432.

## Session, navigation et lisibilité

- La session active et le restaurant/la succursale restent visibles indépendamment du profil de test sélectionné. Le profil en attente ne donne aucun droit.
- Les noms viennent de la base, uniquement pour les contextes admis. Les identifiants et diagnostics restent dans les détails techniques.
- Les changements de session et de contexte invalident les lectures précédentes. Une resélection identique ne vide pas l’écran. Un verrou synchrone empêche deux soumissions avant même le prochain rendu React.
- La navigation utilise les styles du menu latéral MoulAI et des onglets mobiles. Elle expose les rubriques permises par les capacités retournées ; elle ne remplace jamais l’autorisation serveur.
- Un 401 efface l’identité et les données. Un 403 efface les anciennes données. Les erreurs de chargement et les états vides ne sont pas assimilés. Une écriture réussie dont la relecture échoue déclenche un message spécifique, sans répétition automatique.
- Les surfaces de travail sont opaques, avec les couleurs sémantiques du thème actif. Le Gateway reste autour. Les actions physiques ont des choix radio lisibles ; les autres choix affichent aussi leur libellé complet sous le sélecteur.
- Les dates lues portent une date longue et le fuseau de la succursale. Les champs natifs peuvent utiliser la présentation du navigateur, mais leur aperçu traduit affiche le temps mural et son fuseau sans conversion implicite.

## Contrôles reproductibles

Après installation existante des dépendances, sans téléchargement :

```powershell
npm.cmd --prefix frontend run test -- tests/unit/dining-workspace.test.tsx tests/unit/dining-local.test.ts tests/unit/dining-operational.test.tsx tests/unit/dining.test.ts
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run test:guards

# Avec la revue D1 active : captures et scénarios client simulant explicitement HTTP.
Set-Location D:\MoulAI\frontend
node node_modules/@playwright/test/cli.js test -c playwright.dining-workspace.config.ts

# Sur une revue enrichie neuve : vrai parcours via navigateur, sans interception métier.
node node_modules/@playwright/test/cli.js test -c playwright.dining-workspace-live.config.ts --grep 'real UI nominal'

# Avec la revue D1 arrêtée : routes/services et fixtures sur un cluster jetable possédé.
Set-Location D:\MoulAI
.\.venv\Scripts\python.exe -B scripts/run_local_postgres_tests.py --backend native --profile dining --test-paths tests/dining/test_signed_http.py
```

Le parcours nominal écrit des données fictives, notamment un encaissement de recette. Le lancer sur une revue neuve ; ce n’est pas un test de lecture seule. Ne jamais remplacer sa cible par une base permanente. Les preuves de cette livraison et les limites se trouvent dans `artifacts/dining-workspace-20261104/rapport.md`.
