# Tables et réservations — présentation opérationnelle

Livraison locale vérifiée le 4 novembre 2026 (Africa/Lagos).

Les deux vues Tables utilisent désormais les mêmes cartes, badges et filtres :
la revue persistante `/dining-local` et la vue synthétique dans l’espace de travail.
Cette étape concerne exclusivement la présentation Frontend.

## Lecture de l’écran

- Le badge physique est placé à côté du numéro : vert disponible, orange occupée,
  ambre à nettoyer, violet maintenance, gris hors service. Chaque badge conserve
  un libellé et une icône ; les bordures et fonds sont discrets.
- L’état physique est celui de la dernière lecture, horodatée lorsque fournie par
  le serveur. Le planning porte sur la date sélectionnée, dans le fuseau du
  restaurant. Changer cette date ne change aucun état physique.
- Le planning complet et les réservations confirmées sont bleus. Ils ne changent
  pas le compteur physique « Disponible ». Les blocages et leur échéance sont
  distincts des paiements attendus/non validés et de la validation humaine.
- Les retards et conflits affichés demandent une intervention humaine ; ils ne
  déclenchent ni libération, ni annulation, ni encaissement.
- La légende explique les couleurs. Les compteurs et filtres « Tous », par état et
  « Réinitialiser » portent uniquement sur les tables chargées du périmètre autorisé.
  Un filtre sans résultat donne un message et une action de réinitialisation.
- Les heures réelles/prévues, les périodes et motifs déjà accessibles sont affichés.
  Une information absente reste « Non renseigné ». Aucun motif ou délai n’est inventé.

Les couleurs sont centralisées dans `frontend/src/shared/styles/tokens.css` et
adaptées séparément au thème sombre. Les cartes utilisent des surfaces opaques
légèrement teintées pour protéger la lisibilité devant le Gateway. Le bleu nuit,
le teal, les fichiers officiels du logo et leurs proportions sont conservés.

L’en-tête de la revue locale est compact. Ses détails d’environnement et d’identité
restent accessibles au clavier. Dans l’espace de travail, les dimensions compactes
s’appliquent uniquement à la route Tables. Les formulaires et actions métier gardent
leurs contrôles d’habilitation existants.

## Vérification

Le rapport, les sources intégrales et les comparaisons avant/après sont dans
[la livraison de lisibilité](../artifacts/dining-readability-20261103/rapport.md).
Les captures comparables utilisent les mêmes réponses HTTP de test, explicitement
signalées comme simulées et sans aucune écriture. Une vérification distincte a
consulté les vraies routes et PostgreSQL local en lecture seule après la connexion
de répétition. Les confirmations de paiement et transitions n’ont pas été rejouées.

Aucun code Backend, migration, contrat d’écriture, permission, montant, service
externe ou logo n’a été modifié. Cette vérification n’est pas une nouvelle
certification métier ou de production.
