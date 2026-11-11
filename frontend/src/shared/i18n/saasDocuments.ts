// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Documentary labels describe actual persisted facts, without assigning an unapproved fiscal qualification.
const entries = [
  [
    'saasDoc.paymentStatus',
    'Situation du paiement consultée',
    'Payment status at viewing',
    'حالة الدفع عند الاطلاع',
  ],
  ['saasDoc.copy', 'Copier', 'Copy', 'نسخ'],
  ['saasDoc.copied', 'Copié', 'Copied', 'تم النسخ'],
  [
    'saasDoc.copyFailed',
    'Copie indisponible : sélectionnez le texte.',
    'Copy unavailable: select the text.',
    'النسخ غير متاح: حدّد النص لنسخه.',
  ],
  [
    'saasDoc.dateUnavailable',
    'Date non vérifiable',
    'Date cannot be verified',
    'تعذّر التحقق من التاريخ',
  ],
  [
    'saasDoc.openVerification',
    'Ouvrir la page de vérification',
    'Open verification page',
    'فتح صفحة التحقق',
  ],
  [
    'saasDoc.currentValidity',
    'La validité affichée correspond à cette consultation. Le QR permet de vérifier l’état actuel ; une copie ancienne ne se met pas à jour.',
    'Validity reflects this viewing. The QR checks the current state; an older copy does not update itself.',
    'تعكس الصلاحية هذه المعاينة. يتيح رمز QR التحقق من الحالة الحالية؛ النسخة القديمة لا تتحدّث تلقائيًا.',
  ],
  [
    'saasDoc.retainedPayment',
    'Récapitulatif du paiement enregistré',
    'Recorded payment summary',
    'ملخص الدفع المسجل',
  ],
  [
    'saasDoc.retainedHelp',
    'Ce récapitulatif reprend le paiement conservé. Il ne constitue pas une nouvelle demande de paiement ni une émission documentaire.',
    'This summary displays the retained payment. It is neither a new payment request nor documentary issuance.',
    'يعرض هذا الملخص بيانات الدفع المحفوظة. وهو ليس طلب دفع جديدًا ولا إصدارًا لوثيقة الاشتراك.',
  ],
  [
    'saasDoc.title',
    'Documents d’abonnement',
    'Subscription documents',
    'وثائق الاشتراك',
  ],
  ['saasDoc.request', 'Demande de paiement', 'Payment request', 'طلب دفع'],
  [
    'saasDoc.requestHelp',
    'Cette demande ne prouve ni la réception des fonds ni l’activation de l’abonnement.',
    'This request proves neither receipt of funds nor subscription activation.',
    'هذا الطلب لا يثبت استلام الأموال ولا تفعيل الاشتراك.',
  ],
  [
    'saasDoc.final',
    'Document SaaS émis',
    'Issued SaaS document',
    'وثيقة اشتراك صادرة',
  ],
  [
    'saasDoc.fake',
    'DOCUMENT FICTIF DE RECETTE — SANS VALEUR COMPTABLE — NE PAS UTILISER EN PRODUCTION',
    'FICTITIOUS ACCEPTANCE TEST DOCUMENT — NO ACCOUNTING VALIDITY — DO NOT USE IN PRODUCTION',
    'وثيقة وهمية للاختبار — دون قيمة محاسبية — يُمنع استخدامها في بيئة الإنتاج',
  ],
  [
    'saasDoc.unissued',
    'Aucun document définitif émis. La consultation du paiement ne vaut pas émission.',
    'No definitive document issued. Viewing the payment does not issue one.',
    'لم تصدر وثيقة نهائية. الاطلاع على الدفع لا يؤدي إلى إصدارها.',
  ],
  ['saasDoc.valid', 'Document valide', 'Valid document', 'وثيقة سارية'],
  [
    'saasDoc.invalidated',
    'Document invalidé — conserver l’original',
    'Invalidated document — retain the original',
    'وثيقة أُلغي اعتمادها — يُحتفظ بالأصل',
  ],
  [
    'saasDoc.unknown',
    'Document inconnu ou référence incorrecte',
    'Unknown document or incorrect reference',
    'الوثيقة غير معروفة أو المرجع غير صحيح',
  ],
  ['saasDoc.issue', 'Émettre le document', 'Issue document', 'إصدار الوثيقة'],
  [
    'saasDoc.replace',
    'Émettre une version de remplacement',
    'Issue replacement version',
    'إصدار نسخة بديلة',
  ],
  [
    'saasDoc.invalidate',
    'Invalider ce document',
    'Invalidate this document',
    'إلغاء اعتماد هذه الوثيقة',
  ],
  [
    'saasDoc.confirm',
    'Je confirme l’invalidation documentaire. Elle ne rembourse pas le paiement et ne suspend pas l’abonnement.',
    'I confirm documentary invalidation. It does not refund payment or suspend the subscription.',
    'أؤكد إلغاء اعتماد الوثيقة. هذا الإجراء لا يعيد الأموال ولا يوقف الاشتراك.',
  ],
  ['saasDoc.reason', 'Motif obligatoire', 'Required reason', 'السبب الإلزامي'],
  [
    'saasDoc.period',
    'Période de service conservée — UTC',
    'Retained service period — UTC',
    'فترة الخدمة المحفوظة — التوقيت العالمي UTC',
  ],
  [
    'saasDoc.scheduled',
    'Période programmée : ce document ne la présente pas comme déjà active.',
    'Scheduled period: this document does not represent it as already active.',
    'هذه فترة خدمة مبرمجة؛ لا تعني الوثيقة أنها مفعّلة الآن.',
  ],
  [
    'saasDoc.atIssue',
    'État de la période lors de l’émission',
    'Period status at issuance',
    'حالة فترة الخدمة عند إصدار الوثيقة',
  ],
  ['saasDoc.issuedAt', 'Date d’émission', 'Issued at', 'تاريخ الإصدار'],
  ['saasDoc.issuer', 'Émetteur', 'Issuer', 'الجهة المصدرة'],
  ['saasDoc.version', 'Version', 'Version', 'النسخة'],
  [
    'saasDoc.previous',
    'Document remplacé',
    'Replaced document',
    'الوثيقة السابقة',
  ],
  [
    'saasDoc.audit',
    'Décisions documentaires conservées',
    'Retained documentary decisions',
    'قرارات الوثيقة المحفوظة',
  ],
  ['saasDoc.issued', 'Émission', 'Issuance', 'إصدار'],
  [
    'saasDoc.invalidatedEvent',
    'Invalidation',
    'Invalidation',
    'إلغاء الاعتماد',
  ],
  [
    'saasDoc.verify',
    'Vérifier le document SaaS',
    'Verify SaaS document',
    'التحقق من وثيقة الاشتراك',
  ],
  [
    'saasDoc.verifyHelp',
    'Le lecteur expose uniquement la référence, l’émetteur, la date d’émission et la validité. Les détails restent privés.',
    'The reader exposes only reference, issuer, issuance date and validity. Details remain private.',
    'تعرض صفحة التحقق المرجع والجهة المصدرة وتاريخ الإصدار وصلاحية الوثيقة فقط. تبقى التفاصيل خاصة.',
  ],
  [
    'saasDoc.print',
    'Imprimer / enregistrer en PDF',
    'Print / save as PDF',
    'طباعة / حفظ بصيغة PDF',
  ],
  [
    'saasDoc.failure',
    'Opération non confirmée. Consultez l’état enregistré avant toute nouvelle tentative. Les saisies sont conservées.',
    'Operation not confirmed. Check the recorded state before another attempt. Entered values are retained.',
    'لم يتم تأكيد العملية. راجع الحالة المسجلة قبل المحاولة مجددًا. تبقى البيانات التي أدخلتها محفوظة.',
  ],
  [
    'saasDoc.migration',
    'Le stockage documentaire O5 doit être installé et vérifié sur cette instance locale.',
    'O5 documentary storage must be installed and verified on this local instance.',
    'يجب تثبيت تخزين الوثائق O5 والتحقق منه في هذه النسخة المحلية.',
  ],
  [
    'saasDoc.funds',
    'Émission refusée : les fonds ne sont pas vérifiés ou les références de service sont incomplètes.',
    'Issuance refused: funds are unverified or service references are incomplete.',
    'رُفض الإصدار: لم يتم التحقق من الأموال أو أن مراجع الخدمة غير مكتملة.',
  ],
  [
    'saasDoc.empty',
    'Aucun paiement d’abonnement consultable.',
    'No accessible subscription payment.',
    'لا يوجد دفع اشتراك متاح للاطلاع.',
  ],
] as const;
export const saasDocuments = Object.fromEntries(
  ['fr', 'en', 'ar'].map((locale, index) => [
    locale,
    Object.fromEntries(entries.map((row) => [row[0], row[index + 1]])),
  ]),
) as Record<'fr' | 'en' | 'ar', Record<string, string>>;
