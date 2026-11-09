# Assistant MoulAI — proposition de connexion, sans activation

## État réellement présent

L’aide documentaire FR/EN/AR, le panneau de conversation et le contexte filtré de
l’interface existent. Aucun connecteur fournisseur n’est monté pour cet assistant.
Le message d’indisponibilité reste explicite ; aucun texte documentaire ne devient
une réponse IA par changement d’étiquette. L’ancien HTTP 402 DeepSeek reste une
preuve historique, sans démontrer le solde ou le blocage actuel de cet assistant.
Aucune vérification de solde ni tentative IA n’est effectuée dans ce lot.

## Connexion textuelle proposée

Proposition à autoriser séparément : API DeepSeek, modèle `deepseek-flash`, mode
non-thinking, sans outils, recherche ni fetch. La documentation officielle consultée
le 9 novembre 2026 indique cet alias et la version DeepSeek-V4.1-Flash-1017.
Ce choix ne modifie pas le modèle ni la clé du moteur existant.
[Modèles et tarifs DeepSeek](https://api-docs.deepseek.com/quick_start/pricing/).

Le fournisseur recevrait uniquement la question volontaire, la langue, des extraits
d’aide versionnés et un contexte autorisé fermé : écran, étape, type de contrôle,
erreur et conditions effectivement vérifiées. Aucun mot de passe, jeton, cookie,
justificatif, coordonnées client, facture ou historique inter-entreprises. Le serveur
doit refaire les contrôles d’identité et de permissions avant de construire ce
contexte ; la sélection frontend ne constitue jamais l’autorisation.

L’identité authentifiée et le périmètre d’entreprise doivent séparer les historiques
et compteurs. Les étapes proposées restent des indications : aucun accès à une API
qui modifie une réservation, un paiement, une commande ou un droit. En cas de fait
manquant, demander une précision ; aucune inférence sur des données inaccessibles.

Limites techniques proposées, non encore activées : 3 000 tokens d’entrée maximum,
500 tokens de sortie, délai maximal 15 secondes, aucune relance automatique,
compteur atomique par entreprise/utilisateur et réservation préalable du budget.
Un usage inconnu suspend les nouveaux appels. Les erreurs 401/402/429, délais dépassés
et réponses inexploitables doivent revenir à l’aide documentaire avec provenance
explicite. Ces contrôles restent à implémenter et tester avec le futur connecteur ;
les tests actuels de contexte/adaptateurs ne les certifient pas de bout en bout.

## Coût indicatif et décision requise

Hypothèse prudente sans cache, au tarif de pointe officiel consulté : entrée
0,30 USD / million de tokens, sortie 1,20 USD / million. Une question à 3 000 tokens
d’entrée et 500 de sortie coûterait au plus environ **0,0015 USD** pour ces tokens :
3 essais ≈ **0,0045 USD**, 1 000 questions ≈ **1,50 USD**. Hors taxes, change,
infrastructure et tout service vocal ; une tarification future peut changer.
L’estimation ne constitue ni un achat, ni une autorisation de consommer.
[Tarification officielle](https://api-docs.deepseek.com/quick_start/pricing/).

Budget autorisé actuel : **0 USD**. Aucun connecteur activé, appel, achat de crédits,
modification de clé ou changement de fournisseur. Avant activation : validation du
fournisseur/modèle, des données transmises, de leur conservation, du plafond et des
responsabilités, puis autorisation d’essais réellement génératifs distincte.

## Voix facultative, distincte de la génération

La lecture utilise uniquement une voix annoncée locale par le navigateur, sur clic,
avec pause/arrêt et maintien du texte. Le microphone doit exiger une activation
explicite, un traitement local confirmé et un pack déjà disponible, sans téléchargement
ou repli distant automatique. La transcription reste modifiable avant un envoi
volontaire. Aucun enregistrement audio n’est conservé par l’application.
[Voix locale](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesisVoice/localService),
[reconnaissance locale](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition/processLocally).

Coût fournisseur proposé pour cette option locale : 0 USD ; compatibilité, voix et
packs dépendent de l’appareil. Les contrôles avec API simulée ne prouvent ni une
lecture audible réelle ni un microphone fonctionnel. FR, EN et AR doivent être
évalués séparément sur l’appareil cible ; la darija reste non validée. Aucun service
vocal cloud n’est choisi : ses données transmises et son devis nécessiteraient une
décision distincte. Le retour au texte reste toujours disponible.
