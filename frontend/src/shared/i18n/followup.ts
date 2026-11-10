// MoulAI™ — reviewed local operational instructions, never provider-generated answers.
const entries = [
  [
    'followup.currentOffer',
    'Cette offre est encore à jour : aucun remplacement n’est nécessaire.',
    'This offer is still current; replacement is unnecessary.',
    'ما زال هذا العرض ساريًا ولا يحتاج إلى استبدال.',
  ],
  [
    'followup.previewChanged',
    'Le calcul a changé depuis l’aperçu. Examinez de nouveau l’offre avant de confirmer.',
    'The calculation changed since the preview. Review the offer again before confirming.',
    'تغيّر الحساب منذ المعاينة. راجع العرض مجددًا قبل التأكيد.',
  ],
  [
    'followup.missingPair',
    'Aucun tarif n’est configuré pour ce pays et cette devise. La finalisation reste bloquée.',
    'No tariff is configured for this country and currency. Finalization remains blocked.',
    'لا توجد تعريفة مُعدّة لهذا البلد وهذه العملة. لا يمكن إتمام العملية.',
  ],
  [
    'followup.countryRequired',
    'Le pays de facturation doit d’abord être validé par une personne habilitée.',
    'An authorized reviewer must validate the billing country first.',
    'يجب أن يعتمد شخص مخوّل بلد الفوترة أولًا.',
  ],
  [
    'followup.policyRequired',
    'Le paramétrage du mode de paiement manque ou est incohérent. Demandez sa vérification à l’administration MoulAI.',
    'Payment-method configuration is missing or inconsistent. Ask MoulAI administration to check it.',
    'إعداد طريقة الدفع مفقود أو غير متسق. اطلب من إدارة MoulAI التحقق منه.',
  ],

  [
    'followup.reason.base_revision',
    'La version tarifaire de B a changé.',
    'The B tariff version changed.',
    'تغيّر إصدار تعريفة B.',
  ],
  [
    'followup.reason.billing_country_decision_id',
    'Une nouvelle décision de pays s’applique à la période proposée.',
    'A new country decision applies to the proposed period.',
    'يُطبَّق قرار جديد لبلد الفوترة على الفترة المقترحة.',
  ],
  [
    'followup.reason.payment_adjustment_rates',
    'Le paramétrage du mode de paiement a été précisé ou modifié.',
    'Payment-method parameters were specified or changed.',
    'تم تحديد إعداد طريقة الدفع أو تغييره.',
  ],

  [
    'followup.retained',
    'Contexte conservé pour cette offre ou période',
    'Context retained for this offer or period',
    'السياق المحفوظ لهذا العرض أو فترة الاشتراك',
  ],
  [
    'followup.session',
    'La session expire dans {{seconds}} s.',
    'Session expires in {{seconds}} s.',
    'تنتهي الجلسة خلال {{seconds}} ثانية.',
  ],
  [
    'followup.sessionDraft',
    'Enregistrez le brouillon du dossier avant de vous reconnecter. Les fichiers et validations financières ne sont pas récupérés. Aucune action ne sera renvoyée automatiquement.',
    'Save the enrollment draft before reconnecting. Files and financial approvals are not recovered. No action will be resubmitted automatically.',
    'احفظ مسودة التسجيل قبل تسجيل الدخول مجددًا. لا تُستعاد الملفات أو الموافقات المالية، ولن يُعاد تنفيذ أي إجراء تلقائيًا.',
  ],
  [
    'followup.reconnect',
    'Se reconnecter',
    'Sign in again',
    'تسجيل الدخول مجددًا',
  ],
  [
    'followup.register',
    'Créer mon compte avec Keycloak de test',
    'Create my account with test Keycloak',
    'إنشاء حسابي عبر Keycloak التجريبي',
  ],
  [
    'followup.saveDraft',
    'Conserver ce brouillon 30 minutes',
    'Keep this draft for 30 minutes',
    'حفظ هذه المسودة لمدة 30 دقيقة',
  ],
  [
    'followup.restoreDraft',
    'Reprendre mon brouillon',
    'Restore my draft',
    'استعادة مسودتي',
  ],
  [
    'followup.deleteDraft',
    'Supprimer le brouillon',
    'Delete draft',
    'حذف المسودة',
  ],
  [
    'followup.draftInfo',
    'Texte du dossier uniquement, chiffré sur le serveur de test et lié à votre compte. Aucun mot de passe, justificatif ou consentement. Reprise explicite après vérification de votre identité ; aucune soumission automatique.',
    'Enrollment text only, encrypted on the test server and bound to your account. No password, evidence file or consent. Explicit recovery after identity verification; never automatic submission.',
    'يُحفظ نص استمارة التسجيل فقط، مشفرًا على خادم الاختبار ومرتبطًا بحسابك. لا تُحفظ كلمات المرور أو الوثائق أو الموافقات. تستعيد المسودة بنفسك بعد التحقق من هويتك، ولا تُرسل تلقائيًا.',
  ],
  [
    'followup.paymentRate',
    'Taux appliqué au montant avant ajustement',
    'Rate applied to the pre-adjustment total',
    'النسبة المطبقة على المبلغ قبل تعديل طريقة الدفع',
  ],
  [
    'followup.B',
    'B configuré, conservé dans le calcul',
    'Configured B retained in the calculation',
    'قيمة B المحفوظة في تفاصيل الحساب',
  ],
  [
    'offer.final_price',
    'Montant avant ajustement du paiement',
    'Total before payment adjustment',
    'المبلغ قبل تعديل طريقة الدفع',
  ],
  [
    'followup.preview',
    'Examiner le remplacement de cette offre',
    'Review replacement of this offer',
    'مراجعة عرض بديل لهذا العرض',
  ],
  [
    'followup.confirm',
    'Confirmer ces nouveaux montants et remplacer l’offre non payée',
    'Confirm these new amounts and replace the unpaid offer',
    'تأكيد هذه المبالغ واستبدال العرض غير المدفوع',
  ],
  [
    'followup.replacementInfo',
    'Le remplacement conserve l’ancienne offre. Tout justificatif ou fonds déjà engagé exige un traitement administratif distinct ; rien n’est transféré.',
    'Replacement retains the old offer. Existing evidence or committed funds require separate administrative handling; nothing is transferred.',
    'يُحتفظ بالعرض السابق. إذا وُجدت وثيقة دفع أو أموال مسجلة، تلزم مراجعة إدارية مستقلة، ولا يُنقل أي منها تلقائيًا.',
  ],
  [
    'followup.obsolete',
    'Le pays validé, la version de B ou les paramètres du paiement ont changé. Examinez le calcul ci-dessous avant de confirmer.',
    'The validated country, B version or payment parameters changed. Review the calculation below before confirming.',
    'تغيّر بلد الفوترة المعتمد أو إصدار B أو إعداد طريقة الدفع. راجع الحساب أدناه قبل التأكيد.',
  ],
  [
    'followup.financial',
    'Un justificatif ou des fonds sont liés à cette offre : décision administrative nécessaire. Aucun transfert ni annulation automatique.',
    'Evidence or funds are linked to this offer: an administrative decision is required. No automatic transfer or cancellation.',
    'ترتبط بهذا العرض وثيقة دفع أو أموال مسجلة، لذلك يلزم قرار إداري. لا يتم النقل أو الإلغاء تلقائيًا.',
  ],
] as const;
export const followup = Object.fromEntries(
  ['fr', 'en', 'ar'].map((language, i) => [
    language,
    Object.fromEntries(entries.map((row) => [row[0], row[i + 1]])),
  ]),
) as Record<'fr' | 'en' | 'ar', Record<string, string>>;
