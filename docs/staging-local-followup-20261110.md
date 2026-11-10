# MoulAI™ — Corrections locales et décision staging

État du 10 novembre 2026 : **PASS WITH RESERVATIONS sur le périmètre local testé**.
Base de départ : `c49c2241ed33c0cdaa2febef1d77f72b22c945d6`, branche
`codex/staging-preparation-20261109`. Cette passe ne clôture pas l’intégration
globale et n’active ni staging ni une ressource payante.

## Corrections livrées

| Demande | Avant | Résultat |
| --- | --- | --- |
| Titre d’onglet | Suffixe réintroduit par i18n | `MoulAI™` dans HTML et FR/EN/AR ; routes/langues vérifiées |
| Favicon | Approuvé | Fichiers inchangés par comparaison binaire avec le SHA de départ |
| Illustrations | Anciennes versions opaques | Nouveaux `Icon-help-MoulAI(2).png` et `Icon-Assistant-MoulAI(2).png`, copies binaires exactes |
| Position | Accès à droite au-dessus des préférences | Grille partagée : aide à gauche physique, logo centré, préférences à droite, y compris RTL |
| Dimensions | 48 × 48 px | Conservées ; clic 52/56 px, noms accessibles, infobulles et focus clavier |
| Reprise de saisie | Texte trop général entre environnements | Revue locale décrite précisément ; aucune promesse ni bouton de brouillon dans staging non vérifié |
| File de revue SaaS | Même paiement répété jusqu’à 100 fois | Suppression des quatre projections sans jointure ; une ligne par paiement |
| Diagnostics de recette | Un échec Node TLS pouvait inclure Cookie | Masquage des en-têtes Cookie/Set-Cookie/Authorization, test de régression et session locale concernée invalidée |

Les originaux fournis restent dans `assets/originals`. Les versions précédentes
ont été préservées dans `assets/originals/archive/20261109`, sans destruction.
Les composants actifs emploient seulement les nouveaux noms. Les PNG sont RGBA,
1254 × 1254 ; les coins transparents ont été lus dans le navigateur. Aucun
recadrage, filtre, ombre, fond ou changement de pixels n’a été appliqué.
La correspondance de nom avec la demande et la copie source/frontend sont
vérifiées ; aucune empreinte indépendante de pièce jointe n’a été fournie.
Le logo officiel et les petites aides contextuelles sont inchangés.

La file SaaS sélectionnait `SubscriptionPricingSnapshot.parameters/pricing` et
`Subscription.starts_at/expires_at` sans joindre ces tables. Ces valeurs n’étaient
pas retournées au client. Leur retrait corrige le produit cartésien sans changer
la permission `payments.review`, la transaction ou la validation des fonds.
La régression HTTP utilise des sessions PostgreSQL indépendantes et vérifie
l’unicité des identifiants avec plusieurs abonnements/instantanés existants.

## HTTPS local : diagnostic, installation et résultat

- CA : `CN=MoulAI isolated development CA`.
- Empreinte Windows : `F5CAE5D8ABE283E4A8C7E011B46560FF99D74E14`.
- CA valide du 7 novembre 2026 au 5 février 2027 ; certificat serveur valide
  du 7 novembre au 7 décembre 2026. SAN IP : `127.0.0.1` ; chaîne de deux certificats.
- Cause constatée : CA absente de `Cert:\CurrentUser\Root`, malgré une chaîne
  et une adresse correctes. `localhost` n’est pas un nom couvert ; utiliser l’IP prévue.
- Après refus initial de la revue automatique, le propriétaire a explicitement
  autorisé cette empreinte, ce magasin et cette provenance. Cette seule CA a été
  installée. Aucune modification du magasin machine ni de clé privée.
- Chromium a accédé à `/access`, à la découverte Keycloak et aux redirections
  d’authentification avec `ignoreHTTPSErrors: false`. Python a également vérifié
  HTTPS depuis le magasin système, sans CA de secours ni vérification désactivée.
- Les requêtes HTTP de Playwright passent par Node, dont le magasin est distinct :
  les recettes exigent `NODE_USE_SYSTEM_CA=1` avant le démarrage de Node. Ce choix
  utilise la confiance système autorisée ; il n’ignore pas les erreurs TLS.

Procédure de retrait, **non exécutée** :

```powershell
Get-Item 'Cert:\CurrentUser\Root\F5CAE5D8ABE283E4A8C7E011B46560FF99D74E14' |
  Select-Object Subject, Thumbprint, NotAfter
Remove-Item -LiteralPath 'Cert:\CurrentUser\Root\F5CAE5D8ABE283E4A8C7E011B46560FF99D74E14'
```

Vérifier le sujet et l’empreinte avant retrait. Après retrait, les navigateurs
peuvent nécessiter une réouverture et l’avertissement local revient. Renouveler
le certificat serveur avant le 7 décembre ; ne pas désactiver TLS pour prolonger
la recette. Le futur domaine staging utilisera sa propre chaîne publique HTTPS.

## Expiration et reprise effectivement vérifiées

La session locale dure 300 secondes, sans renouvellement automatique. Une nouvelle
inscription native Keycloak a été exécutée, suivie d’une expiration réelle,
du retour à la connexion et d’une reconnexion au même compte.

La sauvegarde est volontaire et limitée aux sept champs texte : entreprise,
référence d’entité, nom, téléphone, courriel, établissement, première succursale.
Le texte est chiffré dans le coffre privé local, lié à issuer/subject et accessible
pendant 30 minutes depuis la sauvegarde. Un brouillon expiré n’est plus restitué ;
sa purge physique intervient au prochain accès au coffre. Une restauration exige
un clic, un compte actif et un nouveau contrôle du périmètre et des droits.

Ni mot de passe, fichier, consentement, décision humaine ni opération financière
n’est restauré ou envoyé automatiquement. Les autres formulaires ne disposent
pas d’une récupération générale. Les dossiers déjà soumis sont relus depuis
PostgreSQL. Dans staging, la reprise des saisies reste **non vérifiée** et les
commandes de brouillon ne sont pas proposées par l’interface.

## Recette métier et portée des preuves

Une nouvelle société a été créée par l’interface, sans CLI de création d’entreprise :
compte authentifié → dossier → documents versionnés fictifs → pays déclaré →
refus sans validation → validation par le compte dédié → entreprise/restaurant/
succursale/essai atomiques. La répétition retrouve le même résultat après rechargement.
Les refus directs du compte tarifaire et d’une autre entreprise ont été vérifiés.

Son essai de 30 jours est resté intact. La tentative immédiate d’offre payante a
correctement répondu `trial_period_not_finished` ; ce refus n’a pas été contourné.
La suite financière utilise une **autre entreprise fictive**, créée par la même
interface, et une fixture locale explicite de fin d’essai. Elle conserve les dates
originales et les dates avancées, collecte les métriques réellement présentes dans
ses tables vides et refuse toute société ordinaire, tout devis/paiement antérieur
ou second passage. Ce n’est pas une observation de 30 jours de service commercial.

Sur cette seconde entreprise, le même compte a ensuite parcouru l’offre, le checkout,
le dépôt d’un justificatif fictif, le contrôle distinct des fonds fictifs, l’activation
et le renouvellement anticipé. La réception des fonds n’est jamais déduite du dépôt.
Le propriétaire et le validateur du pays ne peuvent pas approuver le paiement.
Les répétitions du checkout et de la revue retrouvent les mêmes identifiants.

Une connexion indépendante `READ ONLY` à la base locale attestée a confirmé :
deux paiements payés pour les deux périodes, aucune demande en double, période
initiale conservée et renouvellement commençant exactement à son échéance.
Le renouvellement est `scheduled` tant que la période suivante n’a pas commencé.
B et sa version sont inchangés : **3 000 DZD**. Dans ce scénario, le montant avant
ajustement est 3 000 DZD, le taux électronique est −0,02 et le dû **2 940 DZD**.
Les assertions utilisent les décimales exactes du contrat, pas les flottants affichés.

Les essais interrompus ont été conservés dans des dossiers distincts. Les erreurs
de contrat/sélecteur de recette ont été corrigées avant le résultat final ; elles
ne sont pas présentées comme des succès. Les demandes fictives éventuellement
restées en attente ne sont ni réglées, transférées ni supprimées automatiquement.

Le parcours restaurant existant a été rejoué : QR/menu → demande → validation par
le personnel habilité → cuisine/service → facture/règlement fictif → départ/
nettoyage, avec reprise après réponse perdue. **13 contrôles et 12 captures de
facture**, plus l’export QR, sont réussis. Le décodage natif est indisponible
dans le navigateur installé ; le scan sur téléphone physique reste **NON TESTÉ**.

Le remplacement explicite d’offre obsolète conserve sa preuve UI du 9 novembre ;
les régressions PostgreSQL actuelles vérifient à nouveau son unicité, ses refus et
ses historiques. Le changement de pays avec deux échéances distinctes a été
revalidé sur PostgreSQL jetable ; aucune nouvelle recette UI multi-échéances ni
validation distante n’est revendiquée.

## Contrôles de cette passe

| Contrôle | Résultat actuel |
| --- | --- |
| Frontend ciblé, six fichiers | 50 tests réussis |
| PostgreSQL O4 jetable après correction de file | 47 tests réussis, un avertissement pytest `anyio` déjà importé |
| File SaaS via vraie route et sessions PostgreSQL | Unicité vérifiée sans mock SQL ni transaction externe annulant les preuves |
| Assertions monétaires de recette | 5 cas exacts, dont notation scientifique et HALF_UP |
| Capture en-tête accès/espace/tables | 36 cas FR/EN/AR × Light/Dark × desktop/mobile réussis |
| Expiration/reconnexion | Temps réel, même identité, restauration volontaire, aucun renvoi automatique |
| Parcours financier local | Réussite de l’activation et du renouvellement, fonds/documents fictifs |
| Parcours restaurant | 13 contrôles réussis ; scan physique non effectué |
| Black/Ruff | Vérifiés sur les quatre fichiers Python nouveaux/modifiés |
| Construction | Build production, garde-fous de revue et image staging contrôlés séparément |
| Image staging | Imports, ressources statiques et routes anonymes ASGI vérifiés hors réseau, sans démarrer le lifespan |

Les preuves de migration et de récupération du précédent staging sont conservées.
Aucune migration distante n’a été rejouée. Le cluster PostgreSQL jetable reconstruit
localement est celui nécessaire aux tests ciblés, pas une nouvelle preuve distante.
L’avertissement pytest concerne la réécriture d’assertions d’un module `anyio` déjà
chargé ; aucun échec n’est masqué et il n’est pas compté comme un test ignoré.

## Render, coût et conditions restantes

Le relevé Render détaillé est conservé localement avec la provenance **captures
décrites par le propriétaire**, et non inspection directe par nos outils.
Les tentatives d’inventaire Windows ont été refusées par la revue automatique ;
aucun contenu de fenêtre personnelle n’a été lu. Les valeurs absentes restent
non vérifiées. Aucun Deploy Hook, domaine ou paramètre distant n’a été modifié.

Les éléments déterminants fournis sont : service `moulai-api`, Python 3, Frankfurt,
branche `main`, Auto-Deploy **Off**, Pre-Deploy vide, previews Off, offre **Free**
0,1 CPU/512 MB sans disque persistant. Le workspace est **Hobby**, distinct du plan
du service. Cette capacité ne remplace pas les deux nouveaux services proposés.
L’ancienne commande `app.main:app` ne livre pas le nouvel hôte et son frontend compilé.

| Ressource supplémentaire proposée | Mensuel USD | Justification et limite |
| --- | ---: | --- |
| API/SPA staging, 0.5c-512mb | 7,00 | Un worker, frontend statique inclus ; dimensionnement Linux sous charge encore à valider |
| Keycloak séparé, 1c-2g | 25,00 | JVM et identité isolée ; hypothèse prudente, pas capacité validée en charge |
| Disque API 1 GB | 0,25 | Sessions SQLite chiffrées, brouillons/justificatifs privés et persistance au redémarrage |
| Workspace Hobby | 0,00 fixe | Peut être conservé pour un propriétaire administrateur et ces services, hors options Pro |
| Base métier Neon et future base d’identité | 0,00 sous quotas Free | Rôles et cibles séparés ; base d’identité pas encore préparée, quotas à réattester |
| **Supplément de base proposé** | **32,25** | Avant taxes, dépassements et ressources non incluses |

Les tarifs compute/disque sont corroborés par
[Render Pricing](https://render.com/pricing?trk=public_profile__reactions-text).
Le workspace Hobby n’a pas de forfait mensuel mais facture l’usage ; il limite
notamment les membres et services. Les comptes de test MoulAI ne sont pas des
membres du workspace. Un passage Pro n’est pas requis pour ces deux services
simples ; il le serait pour des fonctions Pro choisies séparément.
[Fonctions par plan](https://render.com/docs/platform-features-by-plan).

Un échantillon local a relevé environ 165 MiB de working set pour l’API Windows et
781 MiB pour Keycloak dans un conteneur limité à environ 3,8 GiB. Ce n’est ni une
mesure Linux à 512 MB ni un test de capacité. La recommandation Keycloak de 2 GB
pour de petits déploiements justifie une réserve de mémoire, sans certifier ce
dimensionnement pour MoulAI. Un essai mesuré pourra affiner l’offre avant toute
augmentation. [Documentation mémoire Keycloak](https://www.keycloak.org/server/containers#_specifying_different_memory_settings).

Le service existant, son URL et son disque absent ne sont pas réaffectés. Le compte,
le dépôt, l’intégration GitHub et éventuellement le workspace sont réutilisables
sous contrôle. Les deux nouveaux noms de service recevront leurs propres origines.
Les quotas de services/domaines ne paient pas le calcul ni l’achat d’un domaine.
Un sous-domaine Render permet d’éviter un achat de domaine dans cette recette.

Pour une séparation supplémentaire, un workspace **Hobby dédié staging** peut être
retenu si le quota de workspaces le permet, sans changement du service existant.
Dans un même workspace Hobby, des noms de projets ne constituent pas une isolation
réseau entre environnements de niveau Pro. Le choix doit être confirmé avant
création ; aucune séparation réseau payante n’est supposée activée.

Ne sont pas inclus : taxes, bande passante et pipeline excédentaires, stockage
supplémentaire, éventuel dépassement Neon, domaine acheté, messagerie, Telegram,
Redis, IA, voix ou personnel supplémentaire dans Render. Le compte rendu du
propriétaire n’indique pas de moyen de paiement enregistré : toute saisie éventuelle
relèvera de lui après décision budgétaire, jamais de la conversation.

Avant activation : approuver le budget et les seuils d’arrêt ; choisir le workspace
et les deux origines HTTPS ; préparer realm/client Keycloak et base d’identité
distincts ; créer/tester le rôle runtime limité ; configurer les secrets via le
gestionnaire prévu ; vérifier les réseaux proxy ; préparer les sauvegardes de la
base métier, de Keycloak, du disque et de la clé Fernet avec restaurations adaptées.
Les limites très réduites du projet de répétition doivent être réexaminées avant
une recette prolongée, sans modification distante dans cette passe.

| Parcours futur | État réel et condition |
| --- | --- |
| Staging fermé | Préparé ; comptes invités avec rôle d’entrée staging et permissions métier distinctes |
| QR client sans compte personnel | Vérifié localement ; encore bloqué par le sas invité du premier staging fermé |
| Inscription autonome distante | Non activée ; route register staging refusée et realm à invitations |
| Telegram, IA, voix, notifications | Pas d’activation nouvelle ; raccordements/budgets distincts |

Après activation seulement : démarrage complet, attestation DB/runtime, OIDC réel,
proxy/TLS, permissions et isolation, persistance/redémarrage, expiration et saisies,
affichage sur appareils physiques, QR et caméra. Le test d’image hors réseau
ne remplace aucun de ces contrôles. Une récupération de base métier ne restaure
pas à elle seule Keycloak, les fichiers ou les clés de chiffrement.

Textes juridiques définitifs, conservation des justificatifs réels, prix de
fonctionnalités non retrouvés et coordonnées commerciales de paiement restent
des prérequis des opérations concernées. B configurable à 3 000 DZD et les grilles
de succursales approuvées ne sont pas rouverts. Le guide et les icônes ne valent
pas activation d’un assistant conversationnel ou vocal capable d’actions.

## Sauvegarde et livrables

La sauvegarde utilise seulement la branche de préparation, après revue des différences,
secrets et automatismes connus : source Render `main`/Auto-Deploy Off selon relevé
propriétaire, aucun workflow ajouté et aucun hook invoqué. Les utilisateurs du
Deploy Hook et les intégrations non observées restent non vérifiés ; aucune
garantie sur leurs déclencheurs inconnus n’est inventée.

SHA final, état local et correspondance GitHub sont consignés dans le rapport
local de livraison. Les captures, preuves PostgreSQL, matrice, relevé Render et
archive de sources complètes sont dans `artifacts/staging-local-followup-20261110`.
Les secrets, `.env`, clés, données et sauvegardes restent exclus du dépôt.

**Aucun déploiement ni écriture distante de configuration/base dans cette passe.
La décision d’activation et le budget restent au propriétaire.**
