// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

// Presentation only: these labels never change session, financial or permission rules.
const entries = [
  [
    'quality.recheck',
    'Vérifier l’état enregistré',
    'Check the recorded state',
    'التحقق من الحالة المحفوظة',
  ],
  [
    'quality.simulation',
    'Résultat de simulation — sans activation',
    'Simulation result — no activation',
    'نتيجة المحاكاة — دون تفعيل',
  ],
  ['access.signin', 'Se connecter', 'Sign in', 'تسجيل الدخول'],
  ['followup.register', 'Créer mon compte', 'Create my account', 'إنشاء حسابي'],
  ['quality.test', 'Environnement de test', 'Test environment', 'بيئة اختبار'],
  [
    'integration.sessionLimit',
    'Session de test : 5 minutes. Reconnectez-vous après expiration.',
    'Test session: 5 minutes. Sign in again after it expires.',
    'مدة جلسة الاختبار 5 دقائق. سجّل الدخول مجددًا بعد انتهائها.',
  ],
  [
    'quality.sessionDetails',
    'Connexion, expiration et reprise des saisies',
    'Sign-in, expiry and recovering your input',
    'تسجيل الدخول وانتهاء الجلسة واستعادة المدخلات',
  ],
  [
    'quality.identity',
    'La connexion utilise Keycloak. Saisissez votre mot de passe uniquement sur sa page de connexion. Vos accès sont vérifiés côté serveur ; aucun choix de profil ne les accorde.',
    'Sign-in uses Keycloak. Enter your password only on its sign-in page. Access is checked by the server; choosing a profile never grants it.',
    'يتم تسجيل الدخول عبر Keycloak. أدخل كلمة مرورك في صفحة تسجيل الدخول الخاصة به فقط. يتحقق الخادم من صلاحياتك، ولا يمنحك اختيار ملف مهني أي صلاحية.',
  ],
  [
    'quality.localDraft',
    'Vous pouvez sauvegarder volontairement votre brouillon d’inscription et le reprendre pendant 30 minutes, après reconnexion avec le même compte. Seuls les sept champs texte pris en charge sont inclus : entreprise, référence d’entité, nom, téléphone, courriel, établissement et première succursale. Les fichiers, mots de passe, consentements et autres formulaires sont exclus. Aucune demande n’est envoyée automatiquement.',
    'You can explicitly save your enrollment draft and recover it within 30 minutes after signing in to the same account. Only seven supported text fields are included: company, entity reference, name, phone, email, establishment and first branch. Files, passwords, consents and other forms are excluded. No request is sent automatically.',
    'يمكنك حفظ مسودة التسجيل باختيارك واستعادتها خلال 30 دقيقة بعد الدخول إلى الحساب نفسه. يشمل الحفظ سبعة حقول نصية فقط: اسم المؤسسة ومرجعها واسم المسؤول وهاتفه وبريده واسم المطعم والفرع الأول. لا يشمل الملفات أو كلمات المرور أو الموافقات أو النماذج الأخرى، ولا يُرسل أي طلب تلقائيًا.',
  ],
  [
    'quality.expiry',
    'La session n’est pas renouvelée automatiquement. Les saisies non sauvegardées peuvent être perdues. Après reconnexion, l’identité, le périmètre et les permissions sont revérifiés avant toute action.',
    'Sessions do not refresh automatically. Unsaved input may be lost. After sign-in, identity, scope and permissions are checked again before any action.',
    'لا تُجدَّد الجلسة تلقائيًا، وقد تفقد المدخلات غير المحفوظة. بعد الدخول مجددًا، يُعاد التحقق من الهوية ونطاق العمل والصلاحيات قبل أي إجراء.',
  ],
  [
    'quality.noPublicRegistration',
    'Cet environnement utilise des comptes de test invités. L’inscription autonome n’y est pas ouverte.',
    'This environment uses invited test accounts. Self-registration is not open here.',
    'تُستخدم في هذه البيئة حسابات اختبار مدعوّة. إنشاء الحسابات ذاتيًا غير متاح هنا.',
  ],
  ['quality.operations', 'Exploitation', 'Operations', 'العمليات اليومية'],
  [
    'quality.people',
    'Personnel et accès',
    'Staff and access',
    'الموظفون وصلاحيات الوصول',
  ],
  [
    'quality.subscription',
    'Abonnement MoulAI',
    'MoulAI subscription',
    'اشتراك MoulAI',
  ],
  [
    'quality.administration',
    'Administration MoulAI',
    'MoulAI administration',
    'إدارة MoulAI',
  ],
  ['quality.required', 'Obligatoire', 'Required', 'مطلوب'],
  ['quality.optional', 'Facultatif', 'Optional', 'اختياري'],
  [
    'quality.processing',
    'Traitement en cours…',
    'Processing…',
    'جارٍ تنفيذ العملية…',
  ],
  [
    'quality.uncertain',
    'Le résultat n’est pas confirmé. Vérifiez l’état enregistré avant toute nouvelle tentative ; ne renvoyez pas une opération financière à l’aveugle.',
    'The outcome is unconfirmed. Check the saved state before trying again; never blindly resend a financial operation.',
    'لم تتأكد نتيجة العملية. تحقّق من الحالة المحفوظة قبل المحاولة مجددًا، ولا تُعِد إرسال عملية مالية دون التحقق.',
  ],
  [
    'quality.readFailed',
    'Impossible de charger ces données. Ce résultat ne signifie pas que la liste est vide.',
    'These records could not be loaded. This does not mean the list is empty.',
    'تعذّر تحميل هذه البيانات. هذا لا يعني أن القائمة فارغة.',
  ],
  [
    'quality.unsavedTitle',
    'Saisies non enregistrées',
    'Unsaved changes',
    'مدخلات غير محفوظة',
  ],
  [
    'quality.unsavedBody',
    'Quitter cet écran peut faire perdre vos saisies. Rien ne sera envoyé ou récupéré automatiquement. Restez sur l’écran pour terminer ou sauvegarder explicitement lorsque cette fonction est disponible.',
    'Leaving may discard your input. Nothing will be sent or recovered automatically. Stay here to finish or explicitly save where that feature is available.',
    'قد تفقد مدخلاتك إذا غادرت هذه الشاشة. لن يُرسل أو يُستعاد أي شيء تلقائيًا. ابقَ لإتمام العمل، أو احفظ صراحةً إذا كانت خاصية الحفظ متاحة.',
  ],
  [
    'quality.stay',
    'Rester sur cet écran',
    'Stay on this screen',
    'البقاء في هذه الشاشة',
  ],
  [
    'quality.leave',
    'Quitter sans enregistrer',
    'Leave without saving',
    'المغادرة دون حفظ',
  ],
  [
    'quality.noPayments',
    'Aucune demande de paiement SaaS enregistrée.',
    'No SaaS payment request is recorded.',
    'لا يوجد طلب دفع مسجّل لاشتراك المنصة.',
  ],
  [
    'quality.noReview',
    'Aucun paiement SaaS à afficher dans votre périmètre.',
    'No SaaS payment is available in your scope.',
    'لا توجد مدفوعات اشتراك للعرض ضمن نطاق صلاحياتك.',
  ],
  [
    'quality.proofStage',
    'Justificatif déposé',
    'Evidence submitted',
    'إيداع وثيقة الدفع',
  ],
  [
    'quality.fundsStage',
    'Fonds vérifiés',
    'Funds verified',
    'التحقق من استلام الأموال',
  ],
  [
    'quality.activationStage',
    'Abonnement activé',
    'Subscription activated',
    'تفعيل الاشتراك',
  ],
  ['quality.notConfirmed', 'Non confirmé', 'Not confirmed', 'غير مؤكّد'],
  [
    'quality.confirmed',
    'Confirmé par le service',
    'Confirmed by the service',
    'مؤكّد من الخدمة',
  ],
  [
    'quality.activationNotExposed',
    'Consultez l’abonnement : le statut du paiement ne prouve pas à lui seul que la période est active aujourd’hui.',
    'Check the subscription: payment status alone does not prove the period is active today.',
    'راجع الاشتراك؛ فحالة الدفع وحدها لا تثبت أن فترة الخدمة نشطة اليوم.',
  ],
  [
    'quality.currencyHelp',
    'La devise est celle de l’offre ; aucune conversion automatique.',
    'Use the offer currency; no automatic conversion.',
    'استعمل عملة العرض؛ لا يوجد تحويل تلقائي للعملات.',
  ],
  [
    'quality.receiptHelp',
    'PDF, PNG ou JPEG, 2 Mo maximum. Ce dépôt ne confirme pas la réception des fonds.',
    'PDF, PNG or JPEG, up to 2 MB. Uploading does not confirm funds were received.',
    'ملف PDF أو PNG أو JPEG بحجم لا يتجاوز 2 ميغابايت. رفع الوثيقة لا يؤكد استلام الأموال.',
  ],
  ['quality.oldOffer', 'Offre conservée', 'Retained offer', 'العرض المحفوظ'],
  [
    'quality.newOffer',
    'Nouvelle offre à confirmer',
    'New offer to confirm',
    'العرض الجديد المطلوب تأكيده',
  ],
  [
    'quality.noAutomaticFunds',
    'Le justificatif, la vérification des fonds et l’activation sont des étapes distinctes. Aucun virement bancaire réel n’est exécuté ici.',
    'Evidence, funds verification and activation are separate steps. No real bank transfer is performed here.',
    'وثيقة الدفع والتحقق من الأموال وتفعيل الاشتراك مراحل منفصلة. لا يُنفَّذ هنا أي تحويل بنكي حقيقي.',
  ],
  [
    'quality.subscription.active',
    'Période active',
    'Active period',
    'فترة خدمة نشطة',
  ],
  [
    'quality.subscription.scheduled',
    'Période confirmée à venir',
    'Confirmed future period',
    'فترة خدمة مؤكدة قادمة',
  ],
  [
    'quality.subscription.pending',
    'Activation en attente',
    'Activation pending',
    'في انتظار التفعيل',
  ],
  [
    'quality.subscription.expired',
    'Période expirée',
    'Expired period',
    'فترة خدمة منتهية',
  ],
  [
    'quality.trialWait',
    'L’essai est encore en cours. La finalisation payante n’est pas disponible avant sa fin.',
    'The trial is still running. Paid finalization is unavailable until it ends.',
    'الفترة التجريبية لم تنتهِ بعد. لا يمكن إتمام الاشتراك المدفوع قبل انتهائها.',
  ],
  [
    'quality.periodUTC',
    'Période de service — UTC',
    'Service period — UTC',
    'فترة الخدمة — التوقيت العالمي UTC',
  ],
  ['quality.cart', 'Votre panier', 'Your basket', 'سلة طلبك'],
  ['quality.unitPrice', 'Prix unitaire', 'Unit price', 'سعر الوحدة'],
  [
    'quality.finalizedAt',
    'Finalisée le — UTC',
    'Finalized on — UTC',
    'تاريخ اعتماد الفاتورة — التوقيت العالمي UTC',
  ],
  [
    'quality.printDetailedInvoice',
    'Imprimer cette facture client',
    'Print this customer invoice',
    'طباعة فاتورة الزبون هذه',
  ],
  [
    'quality.syntheticDocument',
    'Recette locale — données et fonds fictifs — sans valeur comptable.',
    'Local acceptance — fictitious data and funds — no accounting validity.',
    'اختبار محلي — بيانات وأموال وهمية — دون قيمة محاسبية.',
  ],
  [
    'quality.subtotal',
    'Sous-total indicatif',
    'Indicative subtotal',
    'المجموع الفرعي التقديري',
  ],
  [
    'quality.cartReview',
    'Vérifiez les quantités et la devise avant de demander la commande. Le personnel doit encore la valider ; ce panier n’est ni une facture ni un paiement.',
    'Check quantities and currency before requesting an order. Staff must still approve it; this basket is neither an invoice nor a payment.',
    'راجع الكميات والعملة قبل إرسال طلبك. يجب أن يعتمد الموظف الطلب بعد ذلك؛ السلة ليست فاتورة ولا إثبات دفع.',
  ],
  [
    'quality.printInvoice',
    'Imprimer ce récapitulatif client',
    'Print this customer summary',
    'طباعة ملخص حساب الزبون',
  ],
  [
    'quality.invoiceSummary',
    'Récapitulatif des montants consultables, sans valeur de facture détaillée : les lignes figées et la date d’émission ne sont pas exposées par ce contrat.',
    'Summary of accessible amounts, not a detailed invoice: snapshot lines and issue date are not exposed by this contract.',
    'هذا ملخّص للمبالغ المتاحة وليس فاتورة تفصيلية؛ عقد القراءة الحالي لا يعرض بنود الفاتورة المثبّتة أو تاريخ إصدارها.',
  ],
] as const;
export const interfaceQuality = Object.fromEntries(
  ['fr', 'en', 'ar'].map((language, index) => [
    language,
    Object.fromEntries(entries.map((row) => [row[0], row[index + 1]])),
  ]),
) as Record<'fr' | 'en' | 'ar', Record<string, string>>;
