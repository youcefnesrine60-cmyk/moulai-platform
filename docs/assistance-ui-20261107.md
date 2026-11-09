# MoulAI™ — Aide et assistant, revue locale du 7 novembre 2026

## Périmètre livré

Deux accès distincts dans le cadre supérieur de `/access` et `/dining-local`, au-dessus des langues et du thème. `? Aide` ouvre les procédures versionnées ; `Assistant MoulAI` ouvre un panneau conversationnel **non raccordé à un modèle**. Les formulaires métier restent montés. Les questions, brouillons et choix restent en mémoire lors de la fermeture de l’aide ; une fermeture/recharge de la page efface la conversation. Un changement d’identité ou de périmètre D1 remonte le composant pour éviter un historique partagé entre personnes.

La barre latérale affiche MoulAI™ centré, 24 px/700, puis le titre traduit centré, 14 px. Les logos officiels sont inchangés. Les icônes d’aide affichent un cercle de 18 px dans une cible de 44 × 44 px ; l’aide du libellé occupe la fin logique du groupe en RTL, sans décaler les contrôles. L’aide de rubrique répétée dans chaque formulaire a été retirée ; l’aide près des erreurs reste disponible.

Les listes affichent une explication courte du choix et un volet contenant tous les choix, leurs effets et conditions. Aucun bouton n’est placé dans une option native. Les profils métier de recette sont séparés des scénarios de contrôle. Les descriptions D1 correspondent au jeu initial et n’attribuent aucun droit : les habilitations actuelles du serveur restent la référence.

Sur `/access`, le guide explique entreprise, restaurant, succursale, rôles, absence de rattachement, accès suspendu et erreur temporaire. Le sélecteur de revue n’est jamais présenté comme une authentification réelle. Les libellés français Propriétaire/Responsable/Personnel remplacent Owner/Manager/Staff.

## Diagnostic factuel

| Fonction | État réellement livré | Limite |
| --- | --- | --- |
| Aide documentaire | Fonctionnelle localement, FR/EN/AR, RTL, procédures et aide d’élément | D1d et accès documentés ; une option inconnue reçoit un avertissement explicite |
| Conversation IA | Historique des questions, saisie au bas du panneau, Envoyer, état indisponible et accès au guide | Aucun transport assistant ni route authentifiée reliée à un modèle. **Aucune réponse IA ni fonctionnement génératif de bout en bout** |
| Lecture vocale | Commandes Écouter/pause/reprise/arrêt raccordées aux textes documentaires ; seulement voix locales déjà présentes | Aucun son émis pendant la recette. Pas de réponse IA à lire : la commande correspondante reste désactivée avec une raison |
| Microphone | Vérification locale explicite puis démarrage/arrêt ; transcription réinjectée dans le brouillon modifiable, jamais envoyée automatiquement | Nécessite une reconnaissance sur appareil et un paquet linguistique déjà installé. Refus si indisponible. Aucun microphone physique activé pendant la recette |

La cause établie du blocage est **l’absence d’intégration conversationnelle**, et non un solde vérifié. Le fichier `.env`, lu sans instancier le client, comporte des valeurs non vides pour OPENAI_API_KEY, OPENAI_BASE_URL et AI_MODEL. La configuration déclarative vise DeepSeek et `deepseek-chat`. Aucun de ces paramètres n’a été modifié. La validité de la clé, le solde actuel et l’acceptation du modèle n’ont pas été vérifiés. Le HTTP 402 de l’expérience antérieure reste une preuve historique, pas un diagnostic actuel.

`app/core/ai_client.py` existe mais n’est pas appelé par cette aide. Le sélecteur documentaire de `shared/dining/help/assistant.ts` est un mécanisme local non génératif : il n’est pas utilisé pour fabriquer une réponse de chat. Aucun moteur local confirmé n’est substitué. Aucun changement d’AIClient, ResponseGenerator ou AgentEngine.

L’historique actif ne contient que des questions marquées **non transmises au modèle**. Les messages d’indisponibilité sont des états locaux, pas des réponses assistant. Il n’existe donc pas encore de délai de génération, de traitement modèle ni d’erreur fournisseur à mesurer. Dix questions de 600 caractères maximum sont conservées par ouverture ; aucun stockage durable, outil métier ou transport n’est installé dans le composant.

## Habilitations vérifiées sur la revue locale

Les appels de session ne font qu’émettre un cookie synthétique RS256 ; les lectures de session et workspace consultent la base jetable existante. La preuve complète est `artifacts/assistance-options-20261107/profile-grants-observed.json`, sans cookie ni clé.

- Propriétaire : configure/read + service/clean/collect/finance.read/invoices.create/invoices.finalize/advances.allocate/reservations.cancel_before_arrival explicitement accordés par la recette.
- Responsable de service : read/service. Nettoyage : read/clean. Encaissement : read/collect/finance.read/advances.allocate.
- **Facturation, consultation financière et cuisine : read seulement dans le jeu initial observé.** Le nom ne donne pas les droits manquants.
- Service + nettoyage : read/service/clean ; deux actions restent distinctes. Annulation : read et permission dédiée.
- Assistant synthétique : read/assistant, sans modèle. Client et autre établissement : workspace de cet établissement refusé (403). Nouveau compte : aucun périmètre admis, accès refusé (403).

Ces observations ne sont pas des permissions commerciales universelles et n’ajoutent aucune habilitation.

## Proposition de raccordement ultérieur — non activée

1. Ajouter un port d’assistance en lecture/génération seulement, distinct des outils d’AgentEngine. Une route authentifiée devra reconstruire côté serveur les seules permissions utiles et un contexte fermé : écran, étape, code d’erreur autorisé, version de documentation. Ne jamais accepter les droits envoyés par le navigateur comme preuve.
2. Envoyer uniquement une question explicitement soumise, des extraits de documentation versionnée et ce contexte filtré. Exclure mots de passe, jetons, valeurs des formulaires, pièces clients et enregistrements audio. Le fournisseur recevrait ces textes et les métadonnées techniques de sa connexion ; rétention/traitement du fournisseur à valider avant activation.
3. Valider le fournisseur, le modèle et les réglages (notamment mode de raisonnement), adapter le client synchrone existant sans bloquer le serveur, fixer délai maximal, limites de tokens, quotas/coût global, sans retry implicite. Retour structuré avec provenance modèle, usage et références documentaires ; erreurs sans secrets. Rejet des diagnostics non étayés et demandes de précision pour les cas ambigus.
4. Vérifier les réponses, permissions, indisponibilités et limites hors ligne avant un essai génératif séparément autorisé. Aucun accès aux opérations métier. Aucun appel IA dans cette livraison.

### Coût estimatif, avant toute activation

**Dépense fournisseur de cette passe : 0 USD.** La voix native installée ne déclenche pas de facturation API dans notre implémentation ; aucune installation de paquet, voix distante ou solution cloud de transcription n’est activée. La disponibilité locale varie par appareil/langue ; darija non validée.

À titre de proposition seulement, DeepSeek Flash : au tarif de pointe non mis en cache consulté le 7 novembre 2026 (0,30 USD/M tokens d’entrée et 1,20 USD/M de sortie), 3 000 tokens d’entrée + 250 de sortie donnent environ **0,0012 USD/question**, soit 0,0036 USD pour trois ou 1,20 USD pour mille. Hypothèse sans tokens de raisonnement ni retries, hors hébergement/taxes. Ce n’est ni un plafond implémenté pour le futur service, ni une autorisation d’utiliser Flash à la place du modèle déclaré `deepseek-chat`. Fournisseur/modèle, confidentialité et budget effectif exigent une validation distincte.

Sources : [tarification DeepSeek](https://api-docs.deepseek.com/quick_start/pricing/), [voix locale](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesisVoice/localService), [reconnaissance sur appareil](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition/processLocally).

## Limites de validation

Les tests de voix utilisent un port hors ligne : ils prouvent les gestes explicites, pause/reprise/arrêt, contrôle local préalable et retour de transcription au brouillon, pas la qualité acoustique d’un appareil. Le navigateur de recette n’a pas reçu d’autorisation microphone ; aucune reconnaissance réelle FR/EN/AR ni compréhension de darija n’est revendiquée. Mobile émulé, pas téléphone physique.

Le parcours génératif réel, les réponses contextualisées d’un modèle, ses états de traitement/erreurs et la lecture de réponses réelles restent **non disponibles** tant que le raccordement n’est pas réalisé et autorisé. Cette limite est affichée, sans conversation prédéfinie présentée comme IA.

La revue D1 réutilise PostgreSQL local jetable, sans écriture métier pendant les contrôles. Aucune migration, notification, connexion distante, opération Git d’écriture ou déploiement.
