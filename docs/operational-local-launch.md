# Lancer l'intégration opérationnelle locale MoulAI™

Version locale : 9 novembre 2026. Cette entrée est distincte des revues synthétiques.

## Entrée utilisateur et ressources

Ouvrir **<https://127.0.0.1:5180/access>**. Le bouton de connexion conduit au
Keycloak local ; aucun personnage fictif ni seconde session D1 n'est demandé.
Les identifiants des comptes préparés sont conservés exclusivement dans le
dossier privé de l'instance. Ils ne sont pas inclus dans l'archive des sources.

| Ressource | Cible locale |
| --- | --- |
| Frontend et point d'entrée unique | HTTPS `127.0.0.1:5180` |
| API, derrière le proxy commun | HTTP `127.0.0.1:5582` |
| Keycloak | HTTPS `127.0.0.1:8444`, realm `moulai-local` |
| PostgreSQL métier isolé | `127.0.0.1:55433/moulai_integrated` |
| Instance possédée | `artifacts/operational-local/3fb5f85a6cc94868acaf7d95b3777a16` |
| Révision métier | `o420261108`, 101 tables publiques ; extensions locales O1 à O4 |

Les anciennes revues `5173/access` et `5574/dining-local` restent séparées.
Elles ne constituent pas une méthode de connexion au parcours intégré.
L'émetteur d'identités de recette et son endpoint de choix de personnage ne
sont pas montés dans la nouvelle API.

## Prérequis réellement utilisés

- Python du projet et dépendances déjà installées dans `.venv`.
- PostgreSQL 18 installé dans `C:\Program Files\PostgreSQL\18\bin`.
- Docker local Windows via le pipe explicite `npipe:////./pipe/docker_engine`.
- Image **déjà disponible localement** `quay.io/keycloak/keycloak:26.8.0`.
- Node 24 déjà disponible dans `artifacts/frontend-tooling` et dépendances frontend installées.

Le lanceur ne télécharge aucune image, ne recharge aucun crédit et n'installe
aucun certificat dans le système. Les certificats sont propres à cette instance
et limités au loopback. Le navigateur ordinaire peut donc afficher un avertissement
de confiance local. Les preuves Playwright utilisent une exception TLS limitée
à leur contexte de test ; le backend valide strictement sa CA locale. Cette
exception de navigateur n'est pas une configuration TLS de production.

## Démarrage et arrêt

Depuis PowerShell :

```powershell
Set-Location D:\MoulAI
.\start_or_keep_moulai.ps1
```

Cette commande utilise désormais la revue intégrée par défaut. Elle ne démarre
pas `app.main` avec la configuration historique de `.env`. Un serveur déjà
présent n'est conservé qu'après vérification du verrou, de l'identité d'instance
retournée par l'API et du frontend HTTPS avec la CA propre à l'instance.
Un service étranger, un frontend indisponible ou une préparation absente entraîne
un refus, sans initialisation, migration ou repli vers une autre base.

Commande Python équivalente :

```powershell
.\.venv\Scripts\python.exe -I -B scripts/run_operational_local.py serve --keep-running
```

L'ancien backend reste accessible explicitement par
`start_or_keep_moulai.ps1 -LegacyBackend` ou `run_moulai.ps1`. Ces commandes
historiques lisent leur configuration existante ; elles ne sont pas l'entrée de
la revue intégrée. Le contrôle du schéma y reste inchangé. Une erreur sur
`admin_logs.actor_admin_id`, `actor_name` ou `actor_subject` signifie que cette
base n'a pas reçu O1. **Ne pas exécuter une migration distante pour ouvrir la
revue locale.** Aucun de ces lanceurs n'applique de migration automatique.

`serve` réutilise l'instance désignée dans `artifacts/operational-local/active.json`.
Il vérifie son marqueur, son conteneur, le nom de base, le rôle, le port, le
commentaire de base et la révision. Il conserve les données de PostgreSQL,
Keycloak et les sessions serveur après redémarrage.
Un verrou de processus exclusif refuse un second lanceur avant toute action
sur les composants. Les ports applicatifs doivent aussi être libres avant leur
démarrage ; un conflit entraîne un arrêt, sans tuer le processus qui les occupe.

Pour arrêter uniquement cette instance identifiée :

```powershell
$instancePath = 'D:\MoulAI\artifacts\operational-local\3fb5f85a6cc94868acaf7d95b3777a16'
$expectedMarker = '3fb5f85a6cc94868acaf7d95b3777a16'
if ((Get-Content -LiteralPath "$instancePath\instance-marker" -Raw) -cne $expectedMarker) {
    throw 'Marqueur différent : arrêt refusé.'
}
Set-Content -LiteralPath "$instancePath\stop-request" -Value 'arrêt local contrôlé' -NoNewline
```

L'hôte arrête ses propres processus et composants sans effacer leurs données.
Le prochain `serve` retire cette demande d'arrêt. Ne pas arrêter les autres revues
ni réinitialiser le dossier pour obtenir une session neuve.

`init` sert uniquement à préparer une **nouvelle** instance, sur des ports libres.
Il n'est pas une commande de redémarrage. Il applique le bootstrap principal et
la chaîne réelle sur une base vide ; il n'utilise aucun `stamp` ni URL distante.

## Comptes et rattachements de développement

Treize comptes Keycloak ont été préparés : `owner-a`, `owner-b`, `employee`,
`platform-admin`, `platform-reader`, `unlinked`, `d1-service`, `d1-kitchen`,
`d1-collector`, `d1-cleaner`, `country-reviewer`, `saas-reviewer`,
`billing-scenario`. Les mots de passe aléatoires
sont dans `private/acceptance-accounts.json`, avec des ACL Windows privées.
Ne pas copier ce fichier dans le dépôt, une capture, un journal ou une archive.

- `owner-a` : entreprise 8, restaurant 6, succursale 4.
- `owner-b` : entreprise 9, restaurant 7, succursale 5.
- `platform-admin` : droits MoulAI explicitement affectés, dont `subscriptions.pricing.manage`.
- `platform-reader` : seulement `admins.manage`, sans droit tarifaire.
- `unlinked` : initialement sans rattachement ; l'inscription UI a créé l'entreprise 10 et le restaurant 8.
- `billing-scenario` : inscription UI dans l'entreprise 11, restaurant 9, avec paiement entièrement fictif de recette.
- `country-reviewer` : permission explicite de validation du pays uniquement.
- `saas-reviewer` : permission explicite de revue des paiements uniquement.
- `employee` : compte authentifié ; son rattachement utilisé pour la recette de révocation est finalement révoqué, sans suppression d'historique.

Les comptes sont de véritables identités locales, associées à des données de
développement. Ils ne représentent ni des clients réels ni des comptes de production.
Les identifiants de compatibilité Telegram négatifs ne sont jamais une preuve
d'identité et aucun compte Telegram n'est contacté.

Le lanceur expose des opérations de préparation locale `account`, `company`,
`platform-admin` et `role-policy`. Elles reçoivent leur JSON sur **stdin**, jamais
de mot de passe dans les arguments. La configuration est épinglée à l'instance
locale. Un conflit de compte, de politique ou de cible provoque un arrêt ; une
politique existante ne peut pas être remplacée silencieusement.

Pour ajouter un compte local avec un secret saisi de façon interactive :

```powershell
$localUsername = Read-Host 'Nom du nouveau compte local, lettres minuscules, chiffres ou tirets'
$localCredential = Get-Credential -UserName $localUsername -Message 'Nouveau mot de passe local, au moins 14 caractères'
try {
    $accountInput = @{
        username = $localUsername
        password = $localCredential.GetNetworkCredential().Password
    } | ConvertTo-Json -Compress
    $accountInput | .\.venv\Scripts\python.exe -I -B scripts/run_operational_local.py account
} finally {
    Remove-Variable -Name accountInput,localCredential -ErrorAction SilentlyContinue
}
```

La sortie contient l'issuer et le subject non secrets à utiliser pour l'invitation
du compte existant. Le propriétaire invite ensuite cette identité dans
**Personnel et fonctions**. La personne accepte depuis **Mes invitations
professionnelles** ; le propriétaire active ensuite le rattachement et accorde
les permissions nécessaires, séparément. Une fonction descriptive ne les accorde pas.

La préparation d'une entreprise par CLI reste un outil technique. Le parcours
d'inscription, de documents fictifs versionnés, d'essai et de paiement fictif a
désormais une recette UI distincte sous O4 ; voir
`operational-o3-local-integration-20261109.md`. Cela ne clôture pas toutes ses
limites et ne permet pas l'inscription de clients réels.

## Sessions et absence de services externes

Le flux utilise code OIDC, PKCE S256, state, nonce, RS256/JWKS, introspection et
révocation auprès du Keycloak **local**. Les jetons restent chiffrés dans le
dossier privé du serveur. Le navigateur ne reçoit qu'un cookie opaque Secure,
HttpOnly, SameSite=Lax, limité à `/api/web`.

La session expire avec le jeton d'accès, actuellement après cinq minutes ; aucun
rafraîchissement automatique de ce jeton n'est implémenté dans cette première
version. La restauration est vérifiée auprès du fournisseur à chaque requête
protégée ; les permissions et rattachements sont relus côté serveur.

La mesure réelle de 300,492 secondes est conservée dans
`artifacts/operational-milestone-20261108/session-expiry.json` : après expiration,
la lecture protégée reçoit 401 et l'écran revient à `/access`. Les saisies non
envoyées sont perdues au démontage de l'écran ; elles ne sont ni sauvegardées,
ni restaurées, ni rejouées après reconnexion. Une notice l'indique à l'accès.
Ce comportement reste une limite d'usage, pas une protection de brouillon.

Le profil métier est appliqué uniquement au nouveau processus : base locale,
DEBUG et DB_ECHO faux, fabrique opérationnelle propre. `app.main`, le fichier
`.env` et les services Health-Only déjà déployés ne sont pas modifiés.

Les imports legacy initialisent encore un objet `AIClient` avec la configuration
existante. Cela **n'est pas un appel IA**. Le garde-fou Python refuse les
connexions hors des deux ports locaux autorisés et les canaux DNS/UDP alternatifs.
Son rapport ne vaut pas un pare-feu système ni une preuve d'isolation de tous
les autres processus de l'ordinateur. Aucun worker, webhook, envoi Telegram,
notification réelle ou fournisseur IA n'est activé par ce lanceur.

Le réseau Docker est dédié, sans masquerade, avec publication du seul HTTPS
sur loopback. Keycloak reste un serveur de développement local ; son HTTP
interne n'est pas publié. Aucun fournisseur d'identité distant n'est configuré.

## Limites du raccordement livré

Le lot 1 couvre l'identité, les périmètres, les invitations et le module D1
intégré. L'éditeur tarifaire actuel traite B, les campagnes et les échéances des
futures programmations de rappels, pas encore toute
l'administration SaaS. Les prix manquants et les textes d'inscription sont
inventoriés dans `saas-commercial-reference-20261108.md`.
Les dates de campagne sont saisies et affichées explicitement en **UTC**.
Le fuseau horaire de l'appareil ne modifie pas leur signification. Une date
persistée inchangée conserve sa précision d'origine lors d'une autre modification.

Les routes publiques `/menu` et `/verify-document` sont raccordées au même proxy
local sans utiliser une identité du personnel comme preuve de visite. Leur
présence seule ne prouve pas un parcours. La recette du 8 novembre vérifie
effectivement le parcours local QR → menu → quantités du panier → demande →
validation de service → cuisine → service → facture → règlement synthétique
enregistré → départ → nettoyage, avec des comptes distincts et une preuve de
visite cliente séparée. Voir `operational-milestone-20261108/dining-journey.json`
dans les artefacts. Le décodage du QR n'a pas pu être vérifié avec le navigateur
installé ; le scan sur téléphone physique reste NON VÉRIFIÉ.
Les commandes à emporter/livraison et les notifications externes restent des
travaux distincts. Un téléphone physique ne peut pas utiliser le loopback d'un
autre ordinateur ; aucune exposition réseau n'a été faite pour le permettre.

Coût externe constaté pour cette validation : **0 USD**. Les composants utilisent
les logiciels et l'image déjà présents. Aucun hébergement distant n'est nécessaire
pour la recette locale. Le coût d'une exploitation future ne peut pas être déduit
de cette validation : il dépendra du dimensionnement et des services choisis.

## Extensions locales et répétition

O1 conserve les décisions administratives après suppression de leur auteur ;
O2 ajoute le règlement restant d'une facture alimentaire finalisée, en Decimal.
Elles sont additives, sans modification des migrations historiques. La nouvelle
instance vide exécute le bootstrap principal puis la chaîne jusqu'à O2. Pour
une instance existante possédée, arrêter d'abord son hôte puis utiliser, une
seule fois par étape :

```powershell
.\.venv\Scripts\python.exe -I -B scripts/migrate_operational_local.py --target o120261108
.\.venv\Scripts\python.exe -I -B scripts/migrate_operational_local.py --target o220261108
```

Ces commandes sont déjà appliquées à l'instance de revue : ne pas les répéter.
Le lanceur exige le parent exact, le marqueur local, les ports libres et l'absence
de clients concurrents. Il sauvegarde en privé, vérifie l'inventaire, répète avec
rollback puis applique dans une transaction. Aucune cible permanente ou distante
n'est admise. Les nouveaux backups ont leur inventaire contrôlé ; leur restauration
complète n'a pas été répétée dans ce jalon. Ne pas les présenter comme restaurés.

La répétition sur une nouvelle base marquée, sans modifier l'instance active :

```powershell
.\.venv\Scripts\python.exe -I -B scripts/rehearse_operational_o1.py
```

Le nom historique du script est conservé ; il reconstruit désormais jusqu'à O2
et exécute six tests PostgreSQL ciblés, pas une campagne générale. Arrêter d'abord
l'hôte de revue, car le port de recette est partagé. Aucun prix SaaS de ces tests
n'est importé dans la base de revue.

Le catalogue `LOCAL DEV` et les tables `DEV-…` sont des données de développement.
La référence `features.id=6`, code `orders`, est nécessaire à la clé étrangère du
compteur historique ; elle n'accorde aucun abonnement, prix ou droit payant.
Les permissions des quatre comptes D1 sont attribuées explicitement après
invitation acceptée et activation, jamais déduites du nom de fonction.
