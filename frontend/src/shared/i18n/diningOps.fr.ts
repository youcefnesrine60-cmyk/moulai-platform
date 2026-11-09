// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

export const diningOpsFr = {
  'ops.planningLabel': 'Planning',
  'ops.observationDetails': 'Détails du constat',

  'ops.board': 'État des tables et planning',
  'ops.currentPhysical': 'État physique actuel',
  'ops.observedAt': 'Données relues le',
  'ops.observationTimeMissing':
    'Heure du relevé non fournie — données de revue',
  'ops.planningDate': 'Planning de la date sélectionnée',
  'ops.separationNote':
    'L’état physique ne confirme pas la disponibilité à la réservation. Les heures prévues ne libèrent jamais une table.',
  'ops.filterPhysical': 'Filtrer l’état physique actuel',
  'ops.all': 'Tous',
  'ops.reset': 'Réinitialiser',
  'ops.legend': 'Légende des états et du planning',
  'ops.results': '{{visible}} table(s) affichée(s) sur {{total}}',
  'ops.available': 'Disponible',
  'ops.occupied': 'Occupée',
  'ops.dirty': 'À nettoyer',
  'ops.maintenance': 'En maintenance',
  'ops.out_of_service': 'Hors service',
  'ops.unknown': 'État non reconnu — à vérifier',
  'ops.full': 'Entièrement réservée sur les heures d’ouverture',
  'ops.confirmed': 'Réservation confirmée',
  'ops.hold': 'Blocage temporaire',
  'ops.holdExpired': 'Blocage échu — intervention requise',
  'ops.paymentPending': 'Paiement attendu',
  'ops.paymentReview': 'Paiement non validé',
  'ops.humanPending': 'Validation humaine de la demande attendue',
  'ops.closed': 'Indisponibilité au planning',
  'ops.planningUnknown': 'Planning non disponible — à vérifier',
  'ops.planningOccupation': 'Occupation enregistrée au planning',
  'ops.nextReservation': 'Prochaine réservation',
  'ops.noRegisteredClaim':
    'Aucun blocage ni réservation enregistré pour cette date. Disponibilité à confirmer.',
  'ops.recordedPeriods': 'Voir les périodes enregistrées ({{count}})',
  'ops.expires': 'Échéance du blocage',
  'ops.blockReason': 'Motif du blocage associé',
  'ops.notRecorded': 'Non renseigné',
  'ops.locationMissing': 'Localisation non renseignée',
  'ops.capacity': 'Capacité',
  'ops.arrivalActual': 'Installation réelle',
  'ops.endExpected': 'Fin prévue',
  'ops.cleanStartExpected': 'Début du nettoyage prévu',
  'ops.cleanEndExpected': 'Fin du nettoyage prévue',
  'ops.cleanStartActual': 'Début du nettoyage réel',
  'ops.cleanEndActual': 'Fin du nettoyage réelle',
  'ops.unavailableFrom': 'Indisponibilité depuis',
  'ops.unavailableUntil': 'Fin d’indisponibilité connue',
  'ops.occupationLate':
    'Fin prévue dépassée — table toujours occupée, intervention requise.',
  'ops.cleaningLate':
    'Fin du nettoyage prévue dépassée — intervention requise.',
  'ops.planningConflict':
    'Réservation et indisponibilité se chevauchent — vérification humaine requise.',
  'ops.manualReview': 'Intervention humaine requise',
  'ops.requests': 'Demandes liées à cette date',
  'ops.readOnly': 'Consultation — aucune action physique autorisée ici',
  'ops.authorizedActions': 'Voir les actions autorisées',
  'ops.noMatch':
    'Aucune table ne correspond à cet état physique. Réinitialisez le filtre pour retrouver toutes les tables.',
  'ops.noTables': 'Aucune table n’est accessible dans ce périmètre.',
  'ops.legend_available': 'État physique, sans autorisation de réservation.',
  'ops.legend_occupied': 'Occupation réelle, indépendante de la fin prévue.',
  'ops.legend_dirty':
    'Nettoyage à réaliser ou en cours ; libération humaine uniquement.',
  'ops.legend_maintenance': 'Maintenance distincte des réservations.',
  'ops.legend_out_of_service':
    'Retrait du service, durée inconnue si non renseignée.',
  'ops.legendPlanning':
    'Bleu : réservation ou planning complet. Ambre : blocage ou paiement attendu, avec libellés et icônes distincts. Horloge neutre : validation humaine. Rouge : intervention requise.',
  'ops.localNotice':
    'Revue locale : PostgreSQL jetable · identités et fonds fictifs · aucun envoi réel.',
  'ops.environmentDetails': 'Détails de l’environnement local',
  'ops.sessionSettings': 'Identité et établissement de revue',
  'ops.tablePlanning': 'Planning de la table {{table}}',
} as const;
