import type { officeFr } from './office.fr';
export const officeEn: Record<keyof typeof officeFr, string> = {
  'office.activityIndicators': 'Restaurant activity',
  'office.additionalIndicators': 'Additional indicators',
  'office.recordRestaurant': 'Associated restaurant',
  'office.evidenceBoundary':
    'A receipt remains evidence to review. Its status replaces neither independent verification of funds nor an authorized subscription decision.',
  'office.orderChart': 'Orders by status',
  'office.categoryChart': 'Products by category',
  'office.chartNote':
    'Distribution of loaded local data. This chart represents neither received revenue nor a historical trend.',
  'office.subscription': 'Restaurant subscription',
  'office.plan': 'Plan',
  'office.cycle': 'Billing cycle',
  'office.monthly': 'Monthly',
  'office.yearly': 'Yearly',
  'office.active': 'Active',
  'office.trial': 'Trial',
  'office.expired': 'Expired',
  'office.starts': 'Starts',
  'office.expires': 'Expires',
  'office.noSubscription': 'No subscription available',
  'office.offerPreview': 'Prepare a subscription · simulation',
  'office.simulateCheckout': 'Simulate summary',
  'office.checkoutPreview': 'Simulated summary · no invoice created',
  'office.syntheticPricing':
    'Test amounts with no commercial value. Final pricing will come from the server.',
  'office.instructions': 'Transfer instructions · nonpayable example',
  'office.beneficiary': 'Recipient',
  'office.destination': 'Account / RIP',
  'office.accountKey': 'CCP key',
  'office.noTransfer':
    'Do not transfer funds. These details are deliberately fictional and nonpayable.',
  'office.transferSteps':
    'During integration: verify the recipient and amount with the service, keep the transfer reference, then submit receipt evidence. Funds must be verified independently.',
  'office.instructionsUnavailable':
    'Instructions are unavailable for this method. No transfer can be offered.',
  'office.invalidCheckout': 'Select an available plan, cycle and method.',
  'office.simulation': 'Local simulation only',
  'office.verification': 'Simulate receipt verification',
  'office.decision': 'Proposed decision',
  'office.fundsHypothesis': 'Test hypothesis: funds independently verified',
  'office.bankReference': 'Test bank reference',
  'office.receivedAmount': 'Test verified amount (DZD)',
  'office.currency': 'Currency',
  'office.noCurrency': 'No attestation',
  'office.note': 'Verification note',
  'office.simulateReview': 'Check simulation',
  'office.simulationApproved':
    'Consistent simulation: approval proposed, without received funds or subscription activation.',
  'office.simulationRejected':
    'Consistent simulation: rejection proposed, with no recorded decision.',
  'office.simulationError':
    'Simulation refused. Check pending status, the note and test evidence: matching reference, exact amount, DZD and independent confirmation. Rejection must not attest funds.',
  'office.previewNotSaved':
    'No payment, receipt, subscription or audit record was changed. Transactional server checks will remain mandatory.',
  'office.supervision': 'Records in this authorized list',
  'office.refreshList': 'Refresh this list',
  'office.resetSimulation': 'Clear simulation',
  'office.boundary':
    'Local review · Synthetic data. No actual payment, upload or change.',
  'office.reportsIntro':
    'Indicators for the selected restaurant, without combining other businesses.',
  'office.billingIntro':
    'Track manual payments and receipt evidence. A receipt does not prove that funds were received.',
  'office.orders': 'Recorded orders',
  'office.products': 'Products',
  'office.categories': 'Categories',
  'office.average': 'Average order value',
  'office.growth': 'Monthly growth',
  'office.unavailable': 'Unavailable',
  'office.metricsNote':
    'No period or trend is inferred from these totals. Missing financial indicators remain unavailable.',
  'office.empty': 'No results to display',
  'office.emptyHelp':
    'No records are available in this context or for this filter.',
  'office.status': 'Status',
  'office.all': 'All statuses',
  'office.pending': 'Pending',
  'office.paid': 'Paid',
  'office.failed': 'Failed',
  'office.cancelled': 'Cancelled',
  'office.refunded': 'Refunded',
  'office.approved': 'Approved',
  'office.rejected': 'Rejected',
  'office.receipt_submitted': 'Receipt submitted',
  'office.payment': 'Payment',
  'office.amount': 'Amount',
  'office.method': 'Payment method',
  'office.created': 'Date',
  'office.receipt': 'Receipt',
  'office.noReceipt': 'No receipt',
  'office.receiptStatus': 'Receipt status',
  'office.reference': 'Transaction reference',
  'office.localDraft': 'Prepare a receipt · local preview',
  'office.file': 'PNG, JPEG or PDF file (2 MiB maximum)',
  'office.fileNote':
    'Select a test file only. Its contents are neither read nor sent. Server validation will still be required.',
  'office.preview': 'Check local preview',
  'office.invalid':
    'Check the reference (3–120 characters) and file (allowed type, nonempty, 2 MiB maximum).',
  'office.previewReady': 'Preview ready · no receipt sent',
  'office.edit': 'Edit draft',
  'office.integrationRequired':
    'This operation will be available after Business Integration and server-side permission validation.',
  'office.send': 'Send receipt',
  'office.checkout': 'Create subscription payment',
  'office.checkoutNote':
    'Plan discovery, transfer instructions and authoritative server pricing must be connected before any purchase.',
  'office.details': 'View details',
  'office.platformIntro':
    'Administration is separate from business access. Each section requires its platform permission.',
  'office.requestsHelp':
    'Legacy registration requests. Approval does not create an Identity link or a K9 membership.',
  'office.receiptsHelp':
    'Independently verify funds before approving receipt evidence. No financial decision is executed here.',
  'office.auditHelp':
    'Read-only administrative history. No sensitive raw content, tokens or receipt binaries are displayed.',
  'office.approve': 'Approve',
  'office.reject': 'Reject',
  'office.identifier': 'Identifier',
  'office.ccp': 'CCP',
  'office.baridimob': 'BaridiMob',
};
