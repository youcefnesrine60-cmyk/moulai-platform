// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

export const diningOpsEn = {
  'ops.planningLabel': 'Planning',
  'ops.observationDetails': 'Observation details',

  'ops.board': 'Table state and planning',
  'ops.currentPhysical': 'Current physical state',
  'ops.observedAt': 'Data read at',
  'ops.observationTimeMissing': 'Observation time not supplied — review data',
  'ops.planningDate': 'Planning for the selected date',
  'ops.separationNote':
    'Physical state does not approve booking availability. Expected times never release a table.',
  'ops.filterPhysical': 'Filter current physical state',
  'ops.all': 'All',
  'ops.reset': 'Reset filters',
  'ops.legend': 'State and planning legend',
  'ops.results': '{{visible}} of {{total}} tables shown',
  'ops.available': 'Available',
  'ops.occupied': 'Occupied',
  'ops.dirty': 'Needs cleaning',
  'ops.maintenance': 'Under maintenance',
  'ops.out_of_service': 'Out of service',
  'ops.unknown': 'Unknown state — check required',
  'ops.full': 'Fully booked during opening hours',
  'ops.confirmed': 'Confirmed reservation',
  'ops.hold': 'Temporary hold',
  'ops.holdExpired': 'Hold expired — intervention required',
  'ops.paymentPending': 'Payment awaited',
  'ops.paymentReview': 'Payment not validated',
  'ops.humanPending': 'Human approval of the request awaited',
  'ops.closed': 'Planning unavailability',
  'ops.planningUnknown': 'Planning unavailable — check required',
  'ops.planningOccupation': 'Occupation recorded in planning',
  'ops.nextReservation': 'Next reservation',
  'ops.noRegisteredClaim':
    'No hold or reservation recorded for this date. Availability still requires confirmation.',
  'ops.recordedPeriods': 'View recorded periods ({{count}})',
  'ops.expires': 'Hold expiry',
  'ops.blockReason': 'Associated block reason',
  'ops.notRecorded': 'Not recorded',
  'ops.locationMissing': 'Location not recorded',
  'ops.capacity': 'Capacity',
  'ops.arrivalActual': 'Actual seating',
  'ops.endExpected': 'Expected end',
  'ops.cleanStartExpected': 'Expected cleaning start',
  'ops.cleanEndExpected': 'Expected cleaning end',
  'ops.cleanStartActual': 'Actual cleaning start',
  'ops.cleanEndActual': 'Actual cleaning end',
  'ops.unavailableFrom': 'Unavailable from',
  'ops.unavailableUntil': 'Recorded unavailability end',
  'ops.occupationLate':
    'Expected end passed — table remains occupied; intervention required.',
  'ops.cleaningLate': 'Expected cleaning end passed — intervention required.',
  'ops.planningConflict':
    'Reservation overlaps an unavailable period — human review required.',
  'ops.manualReview': 'Human intervention required',
  'ops.requests': 'Requests for this date',
  'ops.readOnly': 'View only — no physical action authorized here',
  'ops.authorizedActions': 'View authorized actions',
  'ops.noMatch':
    'No table matches this physical state. Reset the filter to show all tables.',
  'ops.noTables': 'No tables are accessible in this scope.',
  'ops.legend_available': 'Physical state, without booking approval.',
  'ops.legend_occupied': 'Actual occupation, independent of expected end.',
  'ops.legend_dirty': 'Cleaning required or underway; human release only.',
  'ops.legend_maintenance': 'Maintenance is separate from reservations.',
  'ops.legend_out_of_service':
    'Withdrawn from service; duration unknown unless recorded.',
  'ops.legendPlanning':
    'Blue: reservation or full planning. Amber: hold or payment awaited, with distinct labels and icons. Neutral clock: human approval. Red: intervention required.',
  'ops.localNotice':
    'Local review: disposable PostgreSQL · fictional identities and funds · no real delivery.',
  'ops.environmentDetails': 'Local environment details',
  'ops.sessionSettings': 'Review identity and establishment',
  'ops.tablePlanning': 'Planning for table {{table}}',
} as const;
