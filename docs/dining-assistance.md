# MoulAI™ — Aide documentaire locale D1d

Version active : **D1d-help-2026-11-06.2**.

Cette version remplace la présentation de la livraison du 5–6 novembre. Les preuves et les sources de cette livraison antérieure restent conservées dans `artifacts/dining-assistance-20261105`.

## Ce qui est disponible

Le bouton « ? Aide » du bandeau ouvre la documentation locale, sans service IA. Onze guides FR/EN/AR décrivent le démarrage, les paramètres du restaurant, le personnel, les réservations, l’installation, les visites et QR, les commandes, la facturation, le nettoyage et le journal. Chaque guide précise qui peut agir, les conditions préalables, les étapes, le résultat et la conduite à tenir en cas de difficulté. Les textes arabes sont rédigés pour le personnel du restaurant ; les codes d’habilitation sont réservés aux détails techniques.

Les « ? » placés près des éléments les sélectionnent explicitement. Le panneau distingue champ, liste, bouton, case et groupe de choix. La fonction d’un bouton de validation est déterminée par l’opération du formulaire, et non par une description de champ facultatif. Un élément connu possède une explication de son rôle et de son utilisation, complétée par les prérequis de la procédure. Une explication absente est signalée sans supposer sa fonction.

L’aide ne lit pas les valeurs saisies. Elle consulte seulement l’identifiant DOM explicitement sélectionné, la clé de libellé autorisée, le type, l’opération et les indicateurs de validation/désactivation. Une cause de désactivation n’est affirmée que si elle est explicitement fournie : opération en cours ou type/code de référentiel fixe pendant une modification. Sinon, la cause exacte est indiquée comme non établie. Un simple focus précédent n’est pas une sélection.

Les icônes d’aide restent accessibles même près d’un champ ou d’un bouton désactivé : elles ouvrent uniquement la documentation et ne permettent pas de contourner la désactivation. L’ouverture et la fermeture du panneau conservent les formulaires montés et les brouillons. Le guidage peut mettre un champ existant en évidence ; il ne le remplit pas et n’envoie aucun formulaire.

Les contrôles de session sont alignés sur desktop, leurs libellés et aides occupant des lignes distinctes. Ils sont empilés sur mobile. Le titre latéral présente MoulAI™ centré à 24 px gras et le nom traduit du module centré à 14 px. Les accès à l’aide se trouvent dans le cadre du logo, au-dessus des contrôles de langue et de thème. Aucun accès à l’aide ne flotte au bas de la page.

## Ce qui reste à intégrer

**Le raccordement génératif reste absent.** Depuis la passe du 7 novembre, le bouton Assistant MoulAI ouvre un panneau distinct de la documentation : historique local des questions, brouillon, Envoyer, indisponibilité explicite et transcription modifiable. Aucun modèle ne reçoit ces questions, aucune réponse prédéfinie n’est présentée comme une génération IA. Le diagnostic courant, les descriptions des options et les prérequis sont détaillés dans [la mise à jour du 7 novembre](assistance-ui-20261107.md).

Les commandes de lecture des procédures et de reconnaissance sur appareil sont désormais raccordées à l’interface. Elles nécessitent des ressources locales déjà installées et un geste explicite. Le sélecteur documentaire non génératif n’est pas utilisé pour simuler un agent conversationnel. Les contrôles de voix restent hors ligne ; aucun microphone physique ni son réel n’a été testé. La darija algérienne n’est pas déclarée prise en charge.

La proposition d’intégration et l’estimation historique sont conservées dans les [sources complètes de la livraison précédente](../artifacts/dining-assistance-20261105/sources-completes.zip) et son rapport. Les tarifs, le traitement des données, le modèle, les limites, les permissions et les essais devront être revérifiés dans une demande distincte avant toute activation externe ou payante. Aucune autorisation ancienne d’appel fournisseur n’est réutilisée.

## Concordance métier et accès

La vérification de `transition_visit_order` dans `app/services/business/dining/public_resources.py` confirme les actions suivantes :

| Code technique — réservé aux détails | Explication utilisateur                                         |
| ------------------------------------ | --------------------------------------------------------------- |
| `orders.approve`                     | Autoriser l’envoi de la commande en cuisine                     |
| `orders.prepare`                     | Enregistrer le début de préparation et la disponibilité du plat |
| `orders.complete`                    | Confirmer le service effectivement réalisé auprès du client     |

Le service exige toujours une personne humaine avec la permission correspondante et une transition d’état autorisée. Les guides ne créent aucune habilitation et ne modifient aucune règle. Les fonctions descriptives du personnel restent distinctes des droits. La confirmation de disponibilité, l’installation et le nettoyage restent des actions distinctes. La facture, le paiement et l’affectation d’une avance ne sont jamais validés par l’aide.

Le journal conserve sa route de lecture autorisée, ses filtres et sa pagination. Les identifiants et noms d’éléments sont isolés pour respecter le sens de lecture RTL. Les données métier ne sont ni traduites artificiellement ni réécrites. Les noms synthétiques des fixtures peuvent donc rester en caractères latins.

## Validation de cette passe

Les preuves du 6 novembre restent conservées dans `artifacts/dining-help-polish-20261106/rapport.md`. La livraison courante, les fichiers complets et les captures sont dans [le rapport du 7 novembre](../artifacts/assistance-options-20261107/rapport.md). Les tests Frontend couvrent la sélection explicite, les types d’éléments, le bouton de validation, les explications absentes, les refus connus, le maintien du brouillon, le clavier et l’état non activé de l’assistant. La revue navigateur vérifie les géométries, les langues, le RTL, les deux thèmes et les formats desktop/mobile.

Cette passe est exclusivement locale. Aucun backend, schéma, permission métier ou fichier `.env` n’est modifié ; aucune migration, écriture distante, notification, connexion fournisseur, opération Git d’écriture ou déploiement n’est effectué.
