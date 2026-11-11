# MoulAI™ — facture client et continuité de navigation

11 novembre 2026. Jalon local depuis `d78a1e2b481a0c601fcd3639629deb41b102f35a`,
sur `codex/staging-preparation-20261109`. La consolidation globale reste ouverte.
Les preuves nouvelles sont séparées des preuves du jalon précédent, dans
`artifacts/interface-documents-20261110` (nom du dossier de début de cette passe).

Suite du jalon : [documents SaaS O5 et matrice actualisée](saas-documents-o5-20261111.md).
Le présent rapport conserve les résultats historiques du premier lot.

## Présentation et parcours

- Espacement explicite sous le badge de test ; marges périphériques réduites sur
  écran court, sans changer les dimensions ni les pixels du logo.
- Restaurant : contexte entreprise/restaurant conservé, succursale immédiatement
  identifiable, diagnostics et identité dans une zone dépliable. Les autres
  espaces sont accessibles par une disclosure ; la section active reste visible.
  Le doublon d’invitations est retiré du workspace intégré, avec conservation
  des accès existants à la page des invitations et de ses permissions serveur.
- Le menu public et ses messages reposent sur un panneau de lecture. L’erreur de
  consultation de facture possède aussi une surface lisible.
- Facture client : titre unique, légende distincte pour les lignes, vocabulaire
  FR/EN/AR harmonisé. Les en-têtes utilisent des coupures normales entre mots,
  sans `overflow-wrap: anywhere` sur les titres de colonnes. Défilement limité
  au tableau sur mobile ; composition A4 à l’impression.
- Les montants exacts restent des chaînes Decimal côté serveur et sont formatés
  sans recalcul financier. Date de finalisation et date de consultation sont en
  UTC. La **situation de règlement consultée** est séparée des lignes finalisées.
  Aucun paiement ultérieur ne réécrit les lignes ou le total historique.

## Cause du QR absent et raccordement

La vue `/menu`, protégée pour la facture par la preuve de visite indépendante,
imprimait son propre récapitulatif de facture via `PublicDiningPage`. Son lecteur
`POST /api/web/dining/public/invoice` exposait les lignes et le solde mais pas le
document émis. L’émission existait séparément dans
`DiningUnit.manage_public_link`, et les impressions privées dans
`public-links/{link_id}/print`. Ce n’était pas une absence de générateur QR.

L’émission `food_invoice` conserve les contrôles **`documents.issue` ET
`finance.read`**, avec acteur humain, périmètre restaurant/succursale et facture
finalisée. Le client n’acquiert aucun endpoint ni bouton d’émission.

Après vérification de sa visite et résolution de sa propre facture, le lecteur
cherche seulement le dernier document `food_invoice` de **cette facture dans ce
périmètre**. Un lien actif de la même révision fournit référence, version, adresse
de vérification et SVG issu des primitives existantes `public_read_url` et
`svg_for_public_url`. L’origine vient de la configuration du serveur ; le client
ne peut pas la fournir. La langue est admise explicitement en FR/EN/AR.

Le QR cible `/verify-document?locale=…#référence-opaque`, jamais le QR de table,
une URL administrative, le secret de visite ou la session. Le lecteur public
existant ne retourne que validité, référence, type, version et empreinte ; il
n’expose ni client ni montants ni justificatif. Le droit de lire les détails de
facture reste séparé.

Avant émission, après invalidation/remplacement ou en l’absence d’origine
configurée, un état traduit explique l’absence de QR. Le bouton d’impression
relit d’abord la facture et le document ; si la lecture échoue, il conserve les
données affichées et ne déclenche pas l’impression. Il ne rejoue aucune mutation.
La vérification du lien reste nécessaire au moment d’utiliser un exemplaire déjà
imprimé : un papier ne peut pas se mettre à jour après invalidation.

Les liens locaux indiquent explicitement leur limitation à cet ordinateur.
**127.0.0.1 n’est pas accessible depuis un autre téléphone.** Les documents restent
fictifs, sans valeur comptable ; aucune mention fiscale ou numérotation légale
n’est ajoutée.

## Éditeurs tarifaires et saisies

Le prix B et les campagnes utilisent désormais le garde-fou de navigation existant.
Rester conserve les saisies ; un échec récupérable les conserve aussi. Quitter,
annuler une édition ou remplacer le contexte est explicite. Publier une autre
campagne ne vide plus un formulaire indépendant non enregistré.

Le registre ne contient que des drapeaux, pas les valeurs des formulaires. Il
ne constitue pas une sauvegarde de brouillon et ne rejoue rien après reconnexion.
Les restaurations universelles de filtres/positions ne sont pas revendiquées ;
section et date Dining déjà présentes dans l’URL restent les références vérifiées.

## Nouvelles preuves et limites

| Contrôle                  | Résultat et portée                                                                                                                                                                              |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Frontend ciblé            | 55 tests sur six fichiers, plus deux tests de l’éditeur tarifaire : 57 cas distincts                                                                                                            |
| QR hors ligne             | 24 cas réussis ; un avertissement du cache pytest existant, sans connexion à une base                                                                                                           |
| Recette restaurant        | 17 contrôles locaux avec vrais comptes Keycloak de développement et PostgreSQL local ; API et formulaires, fonds fictifs                                                                        |
| Émission                  | Action du formulaire de personnel habilité ; refus d’émission sans permission ; lecture de la bonne référence/type/version                                                                      |
| QR                        | SVG identique à l’export autorisé, référence distincte de la table, pas de secret de visite ; référence inconnue signalée invalide et mauvaise preuve refusée                                   |
| Paiement                  | Lignes et référence émises inchangées après règlement ; répétitions de règlement sans deuxième encaissement                                                                                     |
| Invalidation              | Vérification publique invalidée ; lecture client sans URL/SVG actif ; relecture avant impression et refus d’imprimer après erreur de lecture                                                    |
| Comparatifs               | 36 vues avant/après FR/EN/AR, clair/sombre, desktop/mobile ; 36 vues supplémentaires sur écrans courts 720/667 px ; 12 paires de facture à données constantes sur fixture explicitement séparée |
| Accessibilité automatique | Six états mobiles du vrai parcours et six de la fixture finale sans violation Axe signalée ; contraste automatiquement indéterminé sur certains fonds, sans certification                       |
| PDF                       | Trois exports réels, réouverts avec Windows.Data.Pdf et rendus en PNG ; chacun tient sur une page A4 après correction des espacements                                                           |
| Zoom interactif           | Non vérifié : l’hôte de contrôle du navigateur a répondu indisponible ; aucune émulation n’est présentée comme un zoom réel                                                                     |
| Lecteur d’écran           | Non vérifié dans cette passe ; navigation clavier et noms accessibles ne constituent pas une recette avec lecteur d’écran                                                                       |

Les PDF ont été exportés pendant la validité des documents, **puis leurs liens
ont été volontairement invalidés** pour la recette. Un contrôle ultérieur doit
donc annoncer l’invalidation. Ils restent des exemples locaux, pas des documents
actifs à remettre à un client.

La première recette s’est arrêtée sur un sélecteur resté au libellé « Quantité
exacte », avant création de commande. Le sélecteur a été adapté au libellé réel.
Une première composition PDF occupait deux pages ; elle est conservée à part.
Seules les preuves finales sont retenues pour les résultats ci-dessus.

Le rendu des PDF utilise l’API Windows déjà installée, sans logiciel téléchargé :
[documentation Microsoft](https://learn.microsoft.com/en-us/uwp/api/windows.data.pdf.pdfpage.rendertostreamasync).
Le script `scripts/render_local_invoice_pdfs.ps1` n’admet que les trois fichiers
connus sous le répertoire `artifacts` du dépôt. Ni impression papier, ni décodage
QR indépendant, ni scan physique n’a été effectué.

## Matrice actualisée et suites

| Lot demandé           | Présent/raccordé                                                                  | Vérifié dans ce jalon                                          | Suite                                                                                                     |
| --------------------- | --------------------------------------------------------------------------------- | -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| 1. Présentation       | Accès, contexte et surfaces allégés                                               | Captures comparatives et tests concernés                       | Relecture finale du propriétaire                                                                          |
| 2. Facture client     | Lignes figées et règlement séparés ; impression A4                                | Recette persistée, trois PDF rendus et revue visuelle FR/EN/AR | Papier réel et documents plus volumineux                                                                  |
| 3. QR de facture      | Émission existante raccordée au lecteur de visite et à l’impression               | Émission humaine, concordance, refus, invalidation             | Scan physique et adresse staging après activation autorisée                                               |
| 4. Continuité         | Garde-fou étendu à B et aux campagnes                                             | Erreur récupérable, rester/quitter, absence de renvoi          | Autres éditeurs legacy et filtres non couverts                                                            |
| 5. SaaS               | Paiements, instantanés, périodes, permissions existants                           | Aucune émission SaaS revendiquée dans ce premier lot           | Règles d’émission/invalidation désormais approuvées le 11 novembre, implémentation distincte à poursuivre |
| 6. Catalogue/rapports | Services catalogue, APIs et métriques legacy présents                             | Pas de nouvelle recette opérationnelle dans ce lot             | Transport intégré, permissions, indicateurs et devises à qualifier avant raccordement                     |
| 7. Options            | Groupes `required`/`multiple_choice`, disponibilité et supplément Float existants | Aucun supplément Float converti implicitement                  | Prix exact/devise et limites de sélection non représentées dans le contrat public actuel                  |
| 8. Revue humaine      | Revue visuelle FR/EN/AR et vrais PDF                                              | Mise en page des trois exports contrôlée                       | Zoom réel, lecteur d’écran, validation linguistique propriétaire, papier et téléphone                     |
| 9. Agent              | Documentation et panneau indépendant existants                                    | Aucune activation fournisseur                                  | Contrats d’outils, contrôles secteur/formule/droits et budget restent un lot séparé                       |
| 10. Livraison         | Branche de préparation uniquement                                                 | Index, secrets et SHA à attester lors de la publication        | Aucune fusion, écriture distante de base ou activation staging                                            |

## Décision SaaS acquise pour le lot suivant

Avant fonds confirmés : demande de paiement propriétaire distincte, sans preuve
d’encaissement ou d’activation. Document définitif seulement après fonds vérifiés,
traitement d’abonnement persisté et références/montant/devise/période cohérents.
Une période `scheduled` reste annoncée comme future.

Deux permissions explicitement attribuées : `subscriptions.documents.issue` et
`subscriptions.documents.invalidate`, sans déduction de `payments.review`,
`admins.manage` ou du rôle. Invalidation avec motif, confirmation, auteur/date,
audit et conservation de l’original ; aucune incidence automatique sur les fonds
ou l’abonnement. Remplacement avec filiation explicite. QR SaaS distinct, lecteur
minimal de référence/émetteur/date/validité, non énumérable et protégé contre les
abus. Répétition d’émission idempotente pour la même référence/version.

Ces règles sont approuvées, **pas encore une preuve d’implémentation**. Leur
qualification fiscale/comptable reste ouverte. Aucun prix, consentement juridique
ou droit personnel supplémentaire n’est inventé. Financement et déploiement
staging restent en attente ; aucune écriture distante n’est autorisée.
