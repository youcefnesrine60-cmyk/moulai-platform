# Pays de facturation — décision métier validée

Version : **2026-11-08.1**. Source : réponse explicite du propriétaire du projet
dans cette conversation. Ce document consigne une décision ; il ne constitue pas
une preuve que son implémentation est déjà terminée.

## Déclaration et validation

Le propriétaire déclare le pays d'établissement de l'entreprise facturée.
Le pays déclaré et le pays validé restent séparés. Aucune valeur par défaut
n'est déduite de la langue, de la localisation, de l'adresse IP, du téléphone,
de la nationalité, de la carte de paiement ou d'un reçu.

La validation relève d'un administrateur MoulAI disposant explicitement de
`tenant.billing_country.manage`. Cette permission n'est déduite ni du rôle,
ni de `subscriptions.pricing.manage`, `restaurants.manage` ou `payments.review`.
Aucune attribution personnelle ou distante n'est autorisée par ce document.

La preuve doit être un document officiel identifiant l'entreprise et son adresse
d'établissement : registre de commerce, immatriculation ou équivalent approprié.
En cas d'insuffisance ou contradiction, demander un complément et maintenir
l'attente. Les accès aux justificatifs sont restreints et seules les données
nécessaires sont recueillies. **La durée de conservation reste à définir avant
utilisation avec de véritables dossiers.** La recette utilise exclusivement des
entreprises et justificatifs fictifs explicitement marqués.

## Application tarifaire

Une offre définitive, un checkout ou un renouvellement utilise exclusivement
le pays validé côté serveur et un couple pays/devise configuré et approuvé.
Une simulation fondée sur le pays déclaré reste indicative, explicitement
provisoire et ne permet aucune activation commerciale.

La seule référence commerciale initiale acquise est **DZ/DZD = 3 000 DZD**.
Aucune conversion, tarification étrangère, hausse programmée ou réutilisation
silencieuse d'un autre contexte ne doit être introduite.

## Changement de pays

Le propriétaire soumet une demande motivée avec un nouveau justificatif ; il
ne modifie pas directement le pays validé. L'administration habilitée approuve
ou refuse en conservant l'ancien et le nouveau pays, le motif, la référence de
preuve, l'auteur, la date de décision et la date de prise d'effet.

Pour une entreprise avec abonnement en cours, le changement approuvé s'applique
au prochain renouvellement. Les factures, instantanés et périodes engagées ne
sont pas réécrits. Les offres non finalisées doivent être recalculées si leur
contexte applicable change. Un changement d'entité juridique exige un examen
distinct et ne peut pas être traité comme un simple changement de pays.

Lors du raccordement, identifier explicitement les cycles concernés lorsqu'une
entreprise possède plusieurs abonnements simultanés ; aucun choix implicite
entre plusieurs échéances ne doit être ajouté en dehors de la règle approuvée.

## Vérifications à implémenter dans le jalon O3

Refus par API directe sans permission, document absent, pays non validé,
couple tarifaire absent, validation/changement concurrent et conservation de
l'historique. La reprise des offres et le renouvellement doivent être testés
avec le contexte serveur réellement persisté.

La suppression de l'ancienne source n'est pas autorisée dans une revue contenant
encore des consommateurs incompatibles. Le raccordement, la sauvegarde restaurée,
la répétition représentative et la récupération doivent précéder la migration
de revue. Aucun de ces contrôles n'est remplacé par le présent document.
