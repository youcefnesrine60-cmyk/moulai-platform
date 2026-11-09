# Suite opérationnelle locale — contrat du 9 novembre 2026

## Paramétrage de l’ajustement du paiement

La réduction électronique de 2 % et la majoration cash de 2 % sont approuvées.
Le moteur lit maintenant `public.subscription_pricing_config`, ligne `id=1`,
colonne JSON `policies.payment_adjustment_rates`. Il n’existe pas de seconde
source dans le frontend. Les valeurs initiales explicites sont les chaînes
décimales `electronic: "-0.02"` et `cash: "0.02"`. Une absence ou une incohérence
de cette configuration bloque le nouveau calcul ; aucun taux de repli n’est utilisé.

Ordre conservé : B et couches de fonctionnalités → score → remises approuvées →
succursales → mois facturés → ajustement du mode de paiement, une seule fois →
arrondi final HALF_UP selon la précision configurée de la devise (deux pour DZD).
`parameters.B`, `final_price`, `payment_adjustment_rate`, `payment_adjustment`
et `final_amount_due` distinguent désormais la référence, l’assiette et le résultat.
Le montant B reste 3 000 DZD dans la revue ; les valeurs de tests sur le cluster
jetable ne sont pas des tarifs commerciaux publiés.

Les nouveaux instantanés retiennent les taux effectivement utilisés. Les
instantanés et factures antérieurs ne sont pas enrichis ni recalculés rétroactivement.
L’initialisation JSON est répétée après restauration d’une sauvegarde fraîche,
avec comparaison du catalogue, de toutes les tables et du rollback. Elle ne
nécessite aucune nouvelle migration SQL ; O4 reste la révision attendue.

## Remplacement explicite d’une offre

La route locale `POST .../saas-payments/{id}/replacement` vérifie l’identité,
l’appartenance à l’entreprise, le rôle propriétaire et `tenant.billing.checkout`.
Sans approbation, elle présente un calcul serveur et son empreinte. La confirmation
doit présenter cette même empreinte ; les sources et montants sont recalculés et
comparés dans la transaction de remplacement. Une modification entre les deux
étapes impose une nouvelle revue.

Seules les offres en attente, sans justificatif, référence financière, encaissement
ni règlement, sont remplaçables. L’ancienne offre et sa demande non payée sont
explicitement retirées de l’état en attente, sans suppression de leurs montants ni
de leurs instantanés. Le nouvel instantané conserve `replacement` avec les anciens
identifiants, l’approbation, l’identité vérifiée et la date. Les répétitions exactes
retrouvent le même successeur. Les verrous de restaurant/paiement et la transaction
empêchent une double demande et annulent aussi un échec financier tardif.

Tout justificatif, même non approuvé ou rejeté, impose un traitement administratif
distinct. Aucune règle de transfert, remboursement, affectation ou annulation
financière n’est inventée. Une ancienne preuve sans contexte suffisant reste bloquée.

## Pays de l’entreprise et périodes contractuelles

Décision propriétaire confirmée le 9 novembre : une décision administrative unique
valide le nouveau pays de l’entreprise à l’approbation. Chaque abonnement utilise
ensuite ce pays au début de sa propre prochaine période de service. Les anciennes
périodes conservent pays/devise, dates, montants et preuves ; aucun champ global
ne les réécrit. Un abonnement partagé, s’il est ultérieurement représenté par le
contrat, doit garder son échéance unique : aucun découpage par succursale n’est ajouté.

L’existant représente un abonnement par établissement. Le calcul sélectionne la
décision applicable au prochain début de couverture, et la version de B applicable
au calcul, selon les règles de renouvellement déjà retenues. Un couple pays/devise
ou un tarif absent bloque cette offre, sans conversion ou repli. Les nouvelles
offres obsolètes doivent être revues explicitement selon le processus ci-dessus.

## Compte Keycloak et reprise de saisie

Le compte se crée dans le formulaire natif du Keycloak local par Authorization Code,
state, nonce et PKCE. MoulAI ne collecte ni ne stocke de mot de passe. Le callback
associe le couple issuer/subject vérifié à une identité active, sans accorder de rôle
d’administration, d’entreprise ou de permission. Un compte suspendu n’est pas réactivé.

La session conserve sa durée de cinq minutes, sans renouvellement automatique.
Un avertissement apparaît pendant la dernière minute. Le formulaire d’inscription
permet une sauvegarde volontaire des seuls champs texte nommés : entreprise,
référence d’entité, nom, téléphone, courriel, établissement et première succursale.
Ces données sont personnelles même en dehors de la recette : elles restent chiffrées
avec Fernet dans le SQLite privé du serveur local, jamais dans localStorage.

Durée d’accès au brouillon : trente minutes depuis la dernière sauvegarde volontaire.
Les entrées expirées sont purgées au prochain accès au coffre. La suppression est
également explicite par bouton, et effectuée après soumission réussie par l’interface.
Un arrêt prolongé du serveur peut retarder la purge physique ; le brouillon expiré
n’est jamais restitué. Les dossiers métier déjà enregistrés reprennent depuis
PostgreSQL et ne sont pas remplacés par ce brouillon.

Après reconnexion, le serveur exige le même issuer/subject actif et un compte sans
rattachement ni dossier déjà persisté pour lire/restaurer cette première saisie.
La restauration exige un clic et n’envoie aucune commande. Aucun mot de passe,
jeton, fichier, consentement, validation humaine ou opération financière n’est
accepté dans ce coffre. Les autres formulaires ne bénéficient pas d’une récupération
générale ; leurs fichiers/choix sensibles doivent être ressaisis ou relus depuis
l’état métier persisté. L’avertissement ne sauvegarde rien silencieusement.

La vérification de propriété du courriel et la récupération du mot de passe par
courriel ne sont pas raccordées faute de messagerie locale configurée. L’inscription
reste une recette synthétique ; elle n’est pas ouverte à de véritables clients.

## Cible de construction future

Les modes `review`, `dining` et `operational` demeurent exclusivement locaux et
interdits en build de publication. La construction normale reste une interface
déconnectée : sa réussite ne prouve pas une intégration déployable.

Le transport `shared/access/sessionHttp.ts` est extrait et réutilisé par l’adaptateur
opérationnel. Il utilise uniquement une API same-origin, des cookies HttpOnly et
les refus serveur, sans hôte de recette, compte, secret, retry ou renvoi automatique.
Ce transport constitue une pièce réutilisable, pas une nouvelle cible activée.

La future cible authentifiée nécessite encore une composition serveur de production
séparée de la fabrique locale : issuer/clients et TLS approuvés, contrôle CSRF,
stockage de sessions, documents définitifs, conservation des preuves, habilitations,
services métier et exploitation validés. Les écrans mixtes qui portent encore des
contrats de recette doivent être séparés avant inclusion. Les fixtures et identités
locales ne seront pas copiées. Les garde-fous actuels ne sont pas désactivés pour
produire artificiellement un bundle connecté. Aucun déploiement n’est autorisé.
