// MoulAI™ — descriptions of actual choices; never an authorization policy.
import type { Locale } from '../../access/contracts';
type Copy = readonly [string, string, string];
const index = { fr: 0, en: 1, ar: 2 } as const;
export const readCopy = (copy: Copy, locale: Locale): string =>
  copy[index[locale]];
const descriptions: Record<string, Copy> = {
  zone: [
    'Zone : regroupe les tables dans un espace de service. Ne remplace pas les horaires ni les contrôles de disponibilité.',
    'Zone: groups tables in a service space. Does not replace opening hours or availability checks.',
    'المنطقة تجمع طاولات مساحة خدمة واحدة ولا تحل محل المواعيد أو التحقق من التوفر.',
  ],
  location: [
    'Emplacement : décrit la localisation d’une table ; aucun droit n’en découle.',
    'Location: describes where a table is; grants no permission.',
    'الموقع يصف مكان الطاولة ولا يمنح صلاحيات.',
  ],
  shape: [
    'Forme : géométrie descriptive de la table, sans modifier sa capacité déclarée.',
    'Shape: describes table geometry without changing its declared capacity.',
    'الشكل يصف هيئة الطاولة ولا يغيّر سعتها المحددة.',
  ],
  category: [
    'Catégorie : classe les tables selon le référentiel local. La sélection exprime un critère, pas une confirmation de réservation.',
    'Category: classifies tables using the local reference. A criterion, not a reservation confirmation.',
    'الفئة تصنّف الطاولات حسب مرجع المطعم. اختيارها معيار وليس تأكيد حجز.',
  ],
  view: [
    'Vue : caractéristique descriptive et préférence de recherche.',
    'View: descriptive feature and search preference.',
    'الإطلالة وصف للطاولة وتفضيل في البحث.',
  ],
  proximity: [
    'Proximité : indique un point d’intérêt proche de la table.',
    'Proximity: identifies a nearby point of interest.',
    'القرب يحدد موقعًا أو مرفقًا قريبًا من الطاولة.',
  ],
  feature: [
    'Équipement ou caractéristique : complète la description et les critères de recherche.',
    'Feature: adds descriptive and search criteria.',
    'التجهيز أو الخاصية يكمّل الوصف ومعايير البحث.',
  ],
  event: [
    'Événement : précise le contexte demandé. Un tarif applicable et les accords restent nécessaires si le devis en dépend.',
    'Event: describes the requested occasion. Applicable pricing and agreements remain required where the quote depends on them.',
    'المناسبة تحدد سياق الطلب. يبقى السعر المعتمد والموافقات ضروريين إذا اعتمد عليهما العرض.',
  ],
  weekly: [
    'Horaire hebdomadaire : répète les plages du jour choisi chaque semaine.',
    'Weekly hours: repeats the chosen weekday’s service windows.',
    'الجدول الأسبوعي يكرر فترات العمل في اليوم المحدد كل أسبوع.',
  ],
  dated: [
    'Horaire daté : exception pour la date choisie, prioritaire sur le programme hebdomadaire de ce jour.',
    'Dated hours: an exception for the selected date, overriding that day’s weekly schedule.',
    'جدول تاريخ محدد يستبدل البرنامج الأسبوعي لذلك اليوم.',
  ],
  per_hour: [
    'Par heure : unité utilisée par le calcul tarifaire ; vérifier la période et la règle du devis.',
    'Per hour: pricing calculation unit; check the period and quote rules.',
    'بالساعة: وحدة حساب السعر؛ راجع المدة وقواعد العرض.',
  ],
  flat: [
    'Forfait : montant fixe de la composante, selon le tarif applicable.',
    'Flat: fixed component amount under the applicable tariff.',
    'مبلغ ثابت للمكوّن حسب التعريفة المطبقة.',
  ],
  per_person: [
    'Par personne : le calcul dépend du nombre de convives enregistré.',
    'Per person: calculation depends on the recorded party size.',
    'للفرد: يعتمد الحساب على عدد الضيوف المسجّل.',
  ],
  per_item: [
    'Par article : prix multiplié par la quantité du menu enregistrée.',
    'Per item: price multiplied by the recorded menu quantity.',
    'للعنصر: السعر مضروب في كمية الوجبة المسجّلة.',
  ],
  available: [
    'Disponible physiquement : ne prouve pas qu’un créneau est réservable et ne remplace pas la validation humaine.',
    'Physically available: does not prove a slot is bookable or replace human approval.',
    'متاحة فعليًا: لا يعني ذلك توفر موعد للحجز ولا يغني عن التحقق البشري.',
  ],
  maintenance: [
    'Maintenance : indisponibilité physique à motiver. Les réservations et autres blocages restent distincts.',
    'Maintenance: a physical unavailability requiring a reason. Reservations and other blocks remain separate.',
    'الصيانة حالة عدم توفر فعلي تستلزم سببًا، وتبقى منفصلة عن الحجوزات والمنع الآخر.',
  ],
  out_of_service: [
    'Hors service : retire la table du service physique ; ne supprime pas les réservations existantes.',
    'Out of service: removes the table from physical service; does not delete existing reservations.',
    'خارج الخدمة: يوقف استعمال الطاولة فعليًا ولا يحذف الحجوزات القائمة.',
  ],
  active: [
    'Actif : permet les opérations prévues par les droits actuels ; ne restaure pas des droits révoqués.',
    'Active: permits actions under current grants; does not restore revoked grants.',
    'نشط: يسمح بالإجراءات وفق الصلاحيات الحالية ولا يعيد الصلاحيات المسحوبة.',
  ],
  suspended: [
    'Suspendu : bloque temporairement l’accès du rattachement. Réactivation et droits sont contrôlés séparément.',
    'Suspended: temporarily blocks membership access. Reactivation and grants are checked separately.',
    'معلّق: يوقف وصول العضو مؤقتًا. يُتحقق من إعادة التفعيل والصلاحيات كلٌّ على حدة.',
  ],
  revoked: [
    'Révoqué : retire l’accès du rattachement et ses droits ; une reprise nécessite le parcours autorisé.',
    'Revoked: removes membership access and grants; return requires the authorized process.',
    'ملغى: يسحب وصول العضو وصلاحياته، والعودة تستلزم المسار المعتمد.',
  ],
  human: [
    'Personne : action attribuée à une identité humaine habilitée. La sélection seule ne constitue pas une preuve d’accord.',
    'Human: action attributed to an authorized human identity. Selection alone is not proof of consent.',
    'شخص: يُنسب الإجراء لهوية بشرية مخوّلة. الاختيار وحده ليس دليل موافقة.',
  ],
  assistant: [
    'Assistant : acteur automatisé soumis à des restrictions ; ne remplace pas une validation humaine requise.',
    'Assistant: restricted automated actor; cannot replace required human approval.',
    'مساعد آلي مقيّد لا يحل محل الموافقة البشرية المطلوبة.',
  ],
  customer: [
    'Client : origine de la demande, sans autorisation automatique d’exécuter l’action métier.',
    'Customer: request origin, not automatic authority to execute the business action.',
    'الزبون مصدر الطلب، دون تفويض تلقائي لتنفيذ الإجراء.',
  ],
  cash: [
    'Espèces : mode de réception déclaré ; seul un encaissement validé et tracé prouve la réception.',
    'Cash: declared receipt method; only validated, audited collection proves receipt.',
    'نقدًا: وسيلة التحصيل المعلنة؛ الاستلام المعتمد والمسجّل وحده يثبت الدفع.',
  ],
  ccp: [
    'CCP : utiliser les instructions configurées ; une déclaration ne valide pas la réception.',
    'CCP: follow configured instructions; a declaration does not validate receipt.',
    'CCP: اتبع التعليمات المضبوطة؛ التصريح وحده لا يثبت الاستلام.',
  ],
  baridimob: [
    'BaridiMob : utiliser les instructions configurées ; vérification humaine requise, sans passerelle réelle.',
    'BaridiMob: configured instructions and human verification, no real gateway.',
    'بريدي موب: تعليمات مضبوطة وتحقق بشري، دون بوابة دفع حقيقية.',
  ],
  issue: [
    'Émettre : prépare un document public contrôlé pour la ressource choisie. Autorisation d’émission nécessaire.',
    'Issue: prepares a controlled public document for the chosen resource. Issuing permission required.',
    'إصدار مستند عمومي مضبوط للمورد المحدد؛ يتطلب صلاحية الإصدار.',
  ],
  rotate: [
    'Renouveler le lien : remplace le jeton du document et invalide l’ancien lien.',
    'Rotate link: replaces the document token and invalidates the old link.',
    'تجديد الرابط يستبدل رمز المستند ويُلغي صلاحية الرابط السابق.',
  ],
  disable: [
    'Désactiver : invalide le lien public ; ne supprime pas l’historique métier.',
    'Disable: invalidates the public link without deleting business history.',
    'التعطيل يُبطل الرابط العمومي دون حذف السجل المهني.',
  ],
};
const capabilities: Record<string, Copy> = {
  read: [
    'Consulter le périmètre opérationnel autorisé, sans droit financier implicite.',
    'Read authorized operational scope, without implicit finance access.',
    'الاطلاع على النطاق التشغيلي المسموح دون صلاحية مالية ضمنية.',
  ],
  service: [
    'Gérer les étapes de service autorisées et la confirmation humaine de disponibilité. Ne donne pas le nettoyage ni l’encaissement.',
    'Manage allowed service steps and human availability confirmation; not cleaning or collection.',
    'إدارة خطوات الخدمة والتأكيد البشري للتوفر؛ لا يمنح التنظيف أو التحصيل.',
  ],
  clean: [
    'Effectuer les transitions physiques de nettoyage permises, sans confirmer une réservation.',
    'Perform permitted physical cleaning transitions, not reservation confirmation.',
    'تنفيذ انتقالات التنظيف المسموح بها دون تأكيد الحجز.',
  ],
  collect: [
    'Enregistrer une avance réellement reçue, avec montant, devise et preuve ; aucune passerelle automatique.',
    'Record a received advance with amount, currency and evidence; no automatic gateway.',
    'تسجيل تسبيق مستلم بمبلغه وعملته ودليله، دون بوابة آلية.',
  ],
  'finance.read': [
    'Consulter les montants autorisés sans créer ni finaliser une facture.',
    'Read permitted amounts without creating or finalizing invoices.',
    'عرض المبالغ المسموح بها دون إنشاء الفواتير أو اعتمادها.',
  ],
  'invoices.create': [
    'Préparer une facture à partir des commandes rapprochées et de sources vérifiées.',
    'Prepare an invoice from reconciled orders and verified sources.',
    'إعداد فاتورة من الطلبات المطابقة والمصادر المتحقق منها.',
  ],
  'invoices.finalize': [
    'Finaliser la facture après ses contrôles ; les montants et lignes deviennent un instantané stable.',
    'Finalize after invoice checks; amounts and lines become a stable snapshot.',
    'اعتماد الفاتورة بعد التحقق، لتبقى مبالغها وبنودها محفوظة كما اعتُمدت.',
  ],
  'advances.allocate': [
    'Affecter une avance validée de même devise au solde d’une facture, sans double affectation.',
    'Allocate a validated same-currency advance to an invoice balance without double allocation.',
    'تخصيص تسبيق معتمد بالعملة نفسها لرصيد فاتورة دون ازدواج.',
  ],
  'reservations.cancel_before_arrival': [
    'Annuler avant arrivée et facturation avec motif ; conserve la preuve d’avance, sans remboursement automatique.',
    'Cancel before arrival/invoicing with a reason; retain advance evidence, no automatic refund.',
    'الإلغاء قبل الوصول والفوترة مع السبب؛ يبقى إثبات التسبيق دون استرجاع آلي.',
  ],
  'orders.read': [
    'Consulter les commandes autorisées.',
    'Read authorized orders.',
    'الاطلاع على الطلبات المسموح بها.',
  ],
  'orders.approve': [
    'Valider une commande en attente pour la faire passer à confirmée.',
    'Approve a pending order to confirmed.',
    'اعتماد طلب قيد الانتظار ليصبح مؤكدًا.',
  ],
  'orders.prepare': [
    'Passer une commande confirmée en préparation, puis la marquer prête.',
    'Move a confirmed order to preparing, then ready.',
    'نقل الطلب المؤكد إلى التحضير ثم تحديده جاهزًا.',
  ],
  'orders.complete': [
    'Confirmer le service d’une commande prête et la terminer.',
    'Confirm service of a ready order and complete it.',
    'تأكيد تقديم الطلب الجاهز للزبون وإنهاؤه.',
  ],
  'documents.issue': [
    'Émettre, renouveler ou désactiver les documents autorisés.',
    'Issue, rotate or disable authorized documents.',
    'إصدار المستندات المسموح بها أو تجديدها أو تعطيلها.',
  ],
  assistant: descriptions.assistant!,
};
const records: Record<string, Copy> = {
  branch: [
    'Le changement recharge le périmètre de cette succursale et ses droits. Aucun droit sur une autre succursale n’est ajouté.',
    'Changing branch reloads its scope and grants. No other branch access is added.',
    'تغيير الفرع يعيد تحميل نطاقه وصلاحياته ولا يمنح الوصول إلى فرع آخر.',
  ],
  request: [
    'Cible cette demande ou réservation pour la procédure courante. Vérifier son état et ses accords ; la sélection ne la confirme pas.',
    'Targets this request or reservation for the current procedure. Check its state and agreements; selection does not confirm it.',
    'يحدد هذا الطلب أو الحجز للإجراء الحالي. راجع حالته وموافقاته؛ الاختيار لا يؤكده.',
  ],
  quote: [
    'Cible cette version de devis. Sa validité, ses accords et sa devise sont vérifiés lors de l’opération.',
    'Targets this quote version. Validity, agreements and currency are checked when operating.',
    'يحدد نسخة العرض هذه؛ تُراجع صلاحيتها وموافقاتها وعملتها عند التنفيذ.',
  ],
  receipt: [
    'Cible une preuve d’avance reçue. Le service contrôle le périmètre, la devise et le reliquat avant toute affectation.',
    'Targets received advance evidence. Scope, currency and remainder are checked before allocation.',
    'يحدد إثبات تسبيق مستلم. يُراجع النطاق والعملة والمتبقي قبل التخصيص.',
  ],
  invoice: [
    'Cible cette facture et son état courant ; seules les opérations permises par cet état et les droits sont admises.',
    'Targets this invoice and its current state; only state- and permission-allowed operations are accepted.',
    'يحدد الفاتورة وحالتها الحالية؛ لا يُقبل إلا الإجراء المتوافق مع الحالة والصلاحية.',
  ],
  occupation: [
    'Cible une installation existante. Une fin prévue ne libère pas automatiquement la table.',
    'Targets an existing seating. An expected end never releases the table automatically.',
    'يحدد جلسة قائمة. نهاية الوقت المتوقع لا تُحرر الطاولة تلقائيًا.',
  ],
  table: [
    'Cible cette table du périmètre courant ; état physique, planning et autorisation de réservation restent séparés.',
    'Targets this scoped table; physical state, schedule and reservation approval remain separate.',
    'يحدد الطاولة ضمن النطاق؛ حالتها الفعلية وجدولها والموافقة على حجزها أمور منفصلة.',
  ],
  person: [
    'Cible ce rattachement du personnel. Une fonction descriptive n’attribue aucun droit automatiquement.',
    'Targets this staff membership. A descriptive function grants no automatic permissions.',
    'يحدد ارتباط الموظف؛ الوظيفة الوصفية لا تمنح صلاحيات تلقائيًا.',
  ],
  function: [
    'Associe cette fonction descriptive au membre ; les habilitations se règlent séparément.',
    'Assigns this descriptive function to the member; permissions are managed separately.',
    'يربط الوظيفة الوصفية بالعضو؛ تُدار الصلاحيات بصورة منفصلة.',
  ],
  currency: [
    'Fixe la devise du calcul. Aucun prix ni paiement d’une autre devise n’est converti implicitement.',
    'Sets the calculation currency. No implicit conversion of other-currency prices or payments.',
    'يحدد عملة الحساب دون تحويل ضمني لأسعار أو مدفوعات بعملة أخرى.',
  ],
  editOrCreate: [
    'Charge cet enregistrement pour modification. Le choix vide conserve le parcours de création ; rien n’est enregistré avant validation.',
    'Loads this record for editing. Empty selection uses creation; nothing is saved before submission.',
    'يحمّل السجل للتعديل. الخيار الفارغ مخصص للإنشاء؛ لا يُحفظ شيء قبل الاعتماد.',
  ],
};
Object.assign(records, {
  document_resource: [
    'Cible le document pour la ressource sélectionnée dans le périmètre autorisé. Le choix du type détermine la liste ; aucune donnée publique n’est publiée par la seule sélection.',
    'Targets the document for the selected authorized resource. Document type determines the list; selection alone publishes no data.',
    'يحدد مورد المستند ضمن النطاق المسموح. يحدد نوع المستند القائمة؛ الاختيار وحده لا ينشر بيانات.',
  ],
  visit_order: [
    'Cible cette commande liée à une visite active pour la transition choisie. État courant et habilitation sont revérifiés côté serveur.',
    'Targets this active-visit order for the chosen transition. Current state and grant are rechecked server-side.',
    'يحدد طلب جلسة نشطة للانتقال المختار. يعيد الخادم التحقق من الحالة والصلاحية.',
  ],
  presence: [
    'Sélectionne un signal de présence à vérifier avant installation ; un scan seul ne confirme pas l’installation.',
    'Selects a presence signal to verify before seating; a scan alone never confirms seating.',
    'يختار إشارة حضور للتحقق قبل الإجلاس؛ المسح وحده لا يؤكد الإجلاس.',
  ],
  product: [
    'Ajoute cet article autorisé au menu demandé, avec la quantité saisie. Le devis exige une référence tarifaire valide ; aucune commande n’est créée par ce choix.',
    'Adds this authorized item to the requested menu with its entered quantity. A quote requires valid pricing; selection creates no order.',
    'يضيف الصنف المسموح إلى القائمة المطلوبة بالكمية المدخلة. يتطلب العرض سعرًا صالحًا؛ الاختيار لا ينشئ طلبًا.',
  ],
});
const special: Record<string, Record<string, Copy>> = {
  code: Object.fromEntries(
    ['round', 'rectangular', 'square', 'oval'].map((shape) => [
      shape,
      [
        'Forme descriptive de la table ; ne change pas la capacité ni les droits.',
        'Descriptive table shape; changes neither capacity nor permissions.',
        'شكل وصفي للطاولة لا يغيّر السعة أو الصلاحيات.',
      ] as Copy,
    ]),
  ),
  component: {
    table: [
      'Tarif de la table pour la période demandée.',
      'Table price for the requested period.',
      'سعر الطاولة للفترة المطلوبة.',
    ],
    preparation: [
      'Tarif des préparatifs demandés ; nécessite une référence applicable.',
      'Price of requested preparations; requires an applicable reference.',
      'سعر التجهيزات المطلوبة، مع مرجع تعريفة صالح.',
    ],
    menu: [
      'Tarif du menu ou des articles demandés ; quantités et référence doivent correspondre.',
      'Price of requested menu/items; quantities and reference must match.',
      'سعر القائمة أو الأطباق المطلوبة؛ يجب تطابق الكميات والمرجع.',
    ],
  },
  blockKind: {
    closure: [
      'Fermeture planifiée empêchant la réservation sur la période ciblée.',
      'Planned closure blocks booking in the targeted period.',
      'إغلاق مبرمج يمنع الحجز خلال الفترة المحددة.',
    ],
    maintenance: [
      'Maintenance planifiée sur la période ciblée, indépendante de l’état physique observé.',
      'Planned maintenance in the targeted period, separate from observed physical state.',
      'صيانة مبرمجة للفترة المحددة، منفصلة عن الحالة الفعلية المرصودة.',
    ],
    preparation: [
      'Réserve la période aux préparatifs et la rend indisponible à la réservation.',
      'Reserves the period for preparation and prevents booking.',
      'يخصص الفترة للتجهيز ويمنع الحجز خلالها.',
    ],
    cleaning: [
      'Réserve une période de nettoyage ; ne déclare pas le nettoyage réellement terminé.',
      'Reserves a cleaning period; does not declare cleaning actually complete.',
      'يخصص فترة للتنظيف ولا يثبت اكتمال التنظيف فعليًا.',
    ],
  },
  blockTarget: {
    branch: [
      'Applique le blocage aux tables de cette succursale.',
      'Applies the block to this branch’s tables.',
      'يطبق المنع على طاولات هذا الفرع.',
    ],
    zone: [
      'Applique le blocage à la zone sélectionnée.',
      'Applies the block to the selected zone.',
      'يطبق المنع على المنطقة المختارة.',
    ],
    table: [
      'Applique le blocage à la seule table sélectionnée.',
      'Applies the block only to the selected table.',
      'يطبق المنع على الطاولة المختارة فقط.',
    ],
  },
  signalKind: {
    customer_departure: [
      'Signale le départ déclaré du client ; ne libère pas automatiquement la table.',
      'Signals reported customer departure; does not release the table automatically.',
      'يبلّغ عن مغادرة الزبون دون تحرير الطاولة تلقائيًا.',
    ],
    customer_cancellation_requested: [
      'Transmet une demande d’annulation ; une personne disposant du droit dédié doit agir.',
      'Passes on a cancellation request; a person with the dedicated grant must act.',
      'ينقل طلب إلغاء لينفذه شخص يملك الصلاحية المخصصة.',
    ],
    late_arrival: [
      'Signale un retard nécessitant l’attention du service, sans annuler automatiquement.',
      'Flags late arrival for service attention, without automatic cancellation.',
      'ينبّه إلى تأخر الوصول ليتدخل مسؤول الخدمة، دون إلغاء آلي.',
    ],
    expected_end_passed: [
      'Signale le dépassement de fin prévue ; la table reste occupée jusqu’à une action autorisée.',
      'Flags an expected-end overrun; table remains occupied until an authorized action.',
      'ينبّه إلى تجاوز النهاية المتوقعة، وتظل الطاولة مشغولة حتى إجراء مخوّل.',
    ],
  },
  documentKind: {
    table: [
      'Document de table avec accès QR contrôlé au menu ; ne confirme aucune installation.',
      'Table document with controlled QR menu access; does not confirm seating.',
      'مستند طاولة برمز وصول مضبوط للقائمة؛ لا يؤكد إجلاس الزبون.',
    ],
    reservation: [
      'Confirmation consultable de la réservation choisie, sous les contrôles de validité.',
      'Viewable confirmation of the chosen reservation, subject to validity checks.',
      'تأكيد قابل للاطلاع للحجز المختار، وفق ضوابط الصلاحية.',
    ],
    food_invoice: [
      'Document de facture alimentaire autorisée ; ne reçoit aucun paiement.',
      'Authorized food invoice document; does not receive payment.',
      'مستند فاتورة طعام مخوّلة؛ لا يستلم أي دفع.',
    ],
    receipt: [
      'Document d’une avance enregistrée ; l’émission ne crée pas un nouvel encaissement.',
      'Document of a recorded advance; issuing creates no new collection.',
      'مستند تسبيق مسجّل؛ إصداره لا ينشئ تحصيلًا جديدًا.',
    ],
  },
  visit_action: {
    approve: capabilities['orders.approve']!,
    prepare: capabilities['orders.prepare']!,
    ready: [
      'Marque prête une commande en préparation ; ne la déclare pas servie.',
      'Marks a preparing order ready; does not mark it served.',
      'يحدد الطلب قيد التحضير جاهزًا دون اعتباره مقدمًا للزبون.',
    ],
    served: capabilities['orders.complete']!,
  },
};
/** Resolve only documented enum meaning or the exact relationship selected by a record field. */
export function optionExplanation(
  name: string,
  label: string,
  value: string,
  locale: Locale,
): string | null {
  const specific = special[name]?.[value] ?? special[label]?.[value];
  if (specific) return readCopy(specific, locale);
  if (name.endsWith('_fold') || label === 'fold' || label.endsWith('Fold'))
    return readCopy(
      value === '0'
        ? [
            'Première occurrence de cette heure répétée lors du changement d’heure.',
            'First occurrence of this repeated wall time during a clock change.',
            'الظهور الأول لهذه الساعة المكررة عند تغيير التوقيت.',
          ]
        : [
            'Seconde occurrence de cette heure répétée lors du changement d’heure.',
            'Second occurrence of this repeated wall time during a clock change.',
            'الظهور الثاني لهذه الساعة المكررة عند تغيير التوقيت.',
          ],
      locale,
    );
  if (label === 'capability')
    return capabilities[value] ? readCopy(capabilities[value], locale) : null;
  const aliases: Record<string, string> = {
    proposal: 'quote',
    verifiedReceipt: 'receipt',
    reservation: 'request',
    reservationOptional: 'request',
    zoneOptional: 'zone',
    categoryOptional: 'category',
    presenceSignal: 'presence',
    authorizedBranch: 'branch',
    tableOptional: 'table',
    requestOptional: 'request',
    staffMember: 'person',
    staffFunction: 'function',
    documentResource: 'document_resource',
    presence: 'occupation',
    sourceOrders: 'visit_order',
  };
  const recordKey = aliases[label] ?? label;
  const record = records[recordKey] ?? records[name];
  if (record) return readCopy(record, locale);
  if (recordKey !== label && descriptions[recordKey])
    return readCopy(descriptions[recordKey], locale);
  if (
    [
      'referenceKind',
      'initialPhysical',
      'physicalState',
      'staffState',
      'calendarKind',
      'unit',
      'actorKind',
      'origin',
      'mode',
      'documentAction',
      'zone',
      'category',
      'location',
      'view',
      'event',
      'proximity',
    ].includes(label) &&
    descriptions[value]
  )
    return readCopy(descriptions[value], locale);
  if (label === 'weekday')
    return readCopy(
      [
        'Applique les plages à ce jour de semaine. Vérifiez les exceptions datées.',
        'Applies windows to this weekday. Check dated exceptions.',
        'يطبق الفترات على يوم الأسبوع هذا. راجع استثناءات التواريخ.',
      ],
      locale,
    );
  if (
    [
      'zone',
      'category',
      'location',
      'shape',
      'view',
      'event',
      'proximity',
      'feature',
    ].includes(label) &&
    descriptions[label]
  )
    return readCopy(descriptions[label], locale);
  return null;
}
