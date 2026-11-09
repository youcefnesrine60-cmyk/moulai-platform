// MoulAI™ — versioned operational documentation, reviewed against D1d services.
import type { Locale } from '../../access/contracts';
export const GUIDE_VERSION = 'O2-help-2026-11-08.1';
export type Topic =
  | 'start'
  | 'configuration'
  | 'staff'
  | 'reservations'
  | 'walkin'
  | 'qr'
  | 'orders'
  | 'finance'
  | 'cleaning'
  | 'history'
  | 'concepts';
export interface ProcedureCopy {
  title: string;
  who: string;
  requires: string;
  steps: readonly string[];
  result: string;
  blocked: string;
}
export interface Procedure {
  id: Topic;
  section: string;
  operations: readonly string[];
  capabilities: readonly string[];
  copy: Record<Locale, ProcedureCopy>;
}
export const procedures: readonly Procedure[] = [
  {
    id: 'start',
    section: 'planning',
    operations: ['choose_scope'],
    capabilities: [],
    copy: {
      fr: {
        title: 'Démarrer dans la bonne succursale',
        who: 'Compte déjà rattaché et habilité à cet établissement. Le sélecteur de profils est réservé à la recette locale.',
        requires:
          'Une identité autorisée et une succursale accessible ; aucune authentification réelle n’est créée ici.',
        steps: [
          'Choisir le profil de recette et ouvrir la session.',
          'Choisir explicitement le restaurant et la succursale autorisés.',
          'Vérifier le contexte affiché et la présence de règles de gestion.',
          'Passer à la configuration puis aux habilitations selon vos droits.',
        ],
        result:
          'Le bon contexte est affiché ; aucune table, réservation ou somme n’est créée par cette sélection.',
        blocked:
          'Sans contexte ou droit, demander le rattachement au propriétaire. Une identité simulée ne prouve pas une connexion Keycloak réelle.',
      },
      en: {
        title: 'Start in the correct branch',
        who: 'An account already attached and authorized for this establishment. The profile selector is local rehearsal only.',
        requires:
          'An authorized identity and accessible branch; no real authentication is created here.',
        steps: [
          'Choose the rehearsal profile and sign in.',
          'Explicitly select the authorized restaurant and branch.',
          'Check the displayed context and management policy.',
          'Continue to configuration and permissions according to your rights.',
        ],
        result:
          'The correct context is displayed; selecting it creates no table, booking or funds.',
        blocked:
          'If scope or permission is missing, ask the owner for membership. A simulated identity does not prove real Keycloak login.',
      },
      ar: {
        title: 'البدء في المطعم والفرع الصحيحين',
        who: 'المستخدم الذي لديه حساب مرتبط بالمطعم وصلاحية للعمل في الفرع. اختيار الحسابات هنا مخصص للتجربة المحلية.',
        requires: 'يجب أن يكون حسابك مرتبطًا بالمطعم والفرع المطلوبين.',
        steps: [
          'اختر حساب التجربة ثم اضغط زر فتح الجلسة.',
          'حدد المطعم والفرع من القائمة المسموح لك باستخدامها.',
          'راجع السياق المعروض قبل إدخال البيانات.',
          'ابدأ بإعداد الطاولات وأوقات العمل، ثم راجع صلاحيات الموظفين.',
        ],
        result:
          'يظهر سياق العمل الصحيح دون إنشاء حجز أو تسجيل مبلغ بمجرد الاختيار.',
        blocked:
          'إذا لم يظهر الفرع المطلوب، اطلب من المالك التحقق من ربط حسابك وصلاحياته. الحسابات المعروضة محاكاة للاختبار وليست دخولًا إلى حساب حقيقي.',
      },
    },
  },
  {
    id: 'configuration',
    section: 'configuration',
    operations: [
      'reference',
      'table',
      'policy',
      'calendar',
      'tariff',
      'grant',
      'combination',
      'blackout',
    ],
    capabilities: ['configure'],
    copy: {
      fr: {
        title: 'Configurer espaces et tables',
        who: 'Le propriétaire ou une personne disposant des droits de gestion prévus pour cet établissement.',
        requires:
          'Établissement et succursale choisis ; valeurs commerciales approuvées et devise explicite.',
        steps: [
          'Configurer le fuseau et les règles de gestion, sans inventer les paramètres manquants.',
          'Créer formes, catégories, zones, emplacements et autres référentiels nécessaires.',
          'Créer les tables avec capacités, localisation, état initial et références de tarif.',
          'Configurer les horaires et indisponibilités ; examiner les conflits signalés avant confirmation.',
          'Publier uniquement des tarifs exacts explicitement approuvés.',
        ],
        result:
          'Les configurations sont persistées localement ; chaque nouvelle table reçoit son QR, avec état physique privé par défaut.',
        blocked:
          'Une configuration absente bloque les opérations qui en dépendent. Ne remplacez pas un tarif manquant par zéro ni une devise par une autre.',
      },
      en: {
        title: 'Configure spaces and tables',
        who: 'The owner or a person with the established management permissions for this establishment.',
        requires:
          'Restaurant and branch selected; approved commercial values and explicit currency.',
        steps: [
          'Configure timezone and management rules without inventing missing settings.',
          'Create required shapes, categories, zones, locations and references.',
          'Create tables with capacities, location, initial state and tariff references.',
          'Configure opening hours and unavailability; review reported conflicts before confirming.',
          'Publish only explicitly approved exact tariffs.',
        ],
        result:
          'Configuration is persisted locally; each new table receives its QR with physical state private by default.',
        blocked:
          'Missing settings block dependent operations. Never replace a missing tariff with zero or substitute another currency.',
      },
      ar: {
        title: 'إعداد المساحات والطاولات وأوقات العمل',
        who: 'مالك المطعم أو من تسمح له الصلاحيات الحالية بإدارة الإعدادات.',
        requires:
          'اختر المطعم والفرع أولًا، واستعمل القواعد والأسعار المعتمدة فقط.',
        steps: [
          'اضبط توقيت الفرع وقواعد إدارة الحجوزات والخدمة.',
          'أضف مناطق الجلوس والقاعات والأشكال والفئات اللازمة.',
          'أضف الطاولات مع أرقامها وسعتها ومكانها وحالتها عند الإنشاء.',
          'حدد أوقات العمل والصيانة وعدم التوفر، وراجع تعارضها مع الحجوزات.',
          'أدخل الأسعار المعتمدة بعملتها وفترة سريانها، ولا تستعمل أسعار التجربة كأسعار تجارية.',
        ],
        result:
          'تُحفظ إعدادات الفرع وتُستخدم في التحقق من العمليات اللاحقة. إعداد الطاولة لا يؤكد حجزها.',
        blocked:
          'إذا رُفض الحفظ، راجع الحقول والتعارضات المعروضة. لا تتجاوز شرطًا تجاريًا غير محدد، ولا تغيّر حالة طاولة مشغولة دون الإجراء المسموح.',
      },
    },
  },
  {
    id: 'staff',
    section: 'staff',
    operations: [
      'staff_invite',
      'staff_profile',
      'staff_function',
      'staff_assignment',
      'staff_status',
    ],
    capabilities: ['configure'],
    copy: {
      fr: {
        title: 'Personnel, fonctions et autorisations',
        who: 'Le propriétaire gère le rattachement ; la personne concernée accepte elle-même son invitation.',
        requires:
          'Un compte OIDC déjà enregistré, la bonne succursale et les droits du propriétaire.',
        steps: [
          'Inviter le compte existant par son émetteur et sujet exacts, sans mot de passe dans la fiche.',
          'La personne accepte son rattachement depuis sa propre session.',
          'Le propriétaire active ensuite le rattachement.',
          'Créer les fonctions et tâches descriptives, puis leurs affectations.',
          'Accorder séparément chaque habilitation et son périmètre dans Habilitations.',
        ],
        result:
          'Le membre peut cumuler des fonctions ; seuls les droits effectivement accordés permettent les actions.',
        blocked:
          'Sans acceptation, activation refusée. Suspendre ou révoquer retire les droits concernés ; réactiver ne les restaure pas automatiquement. Le rôle de service seul n’accorde pas l’annulation avant arrivée.',
      },
      en: {
        title: 'Staff, functions and permissions',
        who: 'The owner manages membership; the invited person accepts their own invitation.',
        requires:
          'An existing registered OIDC account, correct branch and owner authority.',
        steps: [
          'Invite the existing account using its exact issuer and subject; store no password in the profile.',
          'The person accepts membership from their own session.',
          'The owner then activates membership.',
          'Create descriptive functions, tasks and assignments.',
          'Separately grant each capability and scope under Permissions.',
        ],
        result:
          'A member may hold several functions; only explicitly granted capabilities permit actions.',
        blocked:
          'Activation without acceptance is refused. Suspension or revocation removes applicable grants; reactivation does not restore them. Service alone does not grant cancellation before arrival.',
      },
      ar: {
        title: 'إدارة الموظفين والوظائف والصلاحيات',
        who: 'المالك يدير ربط الموظف بالمطعم، والموظف يقبل دعوة الانضمام من جلسته.',
        requires:
          'يلزم حساب مسجل للموظف وصلاحية المالك في المطعم والفرع الصحيحين.',
        steps: [
          'ادعُ الحساب الموجود ببيانات تعريفه، دون طلب كلمة مروره.',
          'يقبل الموظف دعوة الانضمام من حسابه.',
          'يُفعّل المالك الارتباط بعد قبول الدعوة.',
          'أنشئ الوظائف ومهامها، ثم أسندها إلى الموظفين.',
          'امنح كل صلاحية لازمة بشكل مستقل وفي نطاق المطعم والفرع المطلوبين.',
        ],
        result:
          'يمكن للموظف الجمع بين وظائف متعددة، لكن الإجراءات المتاحة تعتمد على صلاحياته الفعلية.',
        blocked:
          'لا يمكن التفعيل قبل قبول الدعوة. إيقاف الارتباط أو إلغاؤه يسحب الصلاحيات المعنية؛ إعادة التفعيل لا تعيدها تلقائيًا. مسؤول الخدمة لا يملك حق إلغاء الحجز لمجرد وظيفته.',
      },
    },
  },
  {
    id: 'reservations',
    section: 'requests',
    operations: [
      'request',
      'select_tables',
      'quote',
      'restaurant_consent',
      'customer_consent',
      'human_proof',
      'hold',
      'confirm_human',
      'confirm_assistant',
      'cancel_before_arrival',
      'signal',
      'customer_cancellation',
    ],
    capabilities: ['service'],
    copy: {
      fr: {
        title: 'Réserver et confirmer',
        who: 'Service habilité pour les décisions humaines ; client et établissement pour leurs accords respectifs. Annulation avant arrivée : permission dédiée.',
        requires:
          'Règles, horaires et tarifs applicables ; demande, tables et devis cohérents.',
        steps: [
          'Enregistrer la demande et proposer les tables sans certifier leur disponibilité.',
          'Préparer le devis, puis enregistrer les accords de l’établissement et du client sur cette version.',
          'Faire vérifier humainement la disponibilité et enregistrer le blocage temporaire valide.',
          'Faire enregistrer l’avance effectivement reçue par une personne habilitée à encaisser.',
          'Confirmer avec le devis courant, le reçu vérifié et la preuve humaine encore valides.',
          'Consulter le justificatif ; vérifier son statut après une éventuelle annulation.',
        ],
        result:
          'Une réservation confirmée et son document vérifiable ; aucune disponibilité ni réception d’argent n’est déduite d’une simple demande.',
        blocked:
          'Blocage expiré, devis remplacé, accord invalidé ou reçu non vérifié empêchent la confirmation. L’avance nulle reste bloquée sans politique explicite. Le transport simulé n’établit pas une notification réelle ; ce parcours ne rend pas un agent IA opérationnel.',
      },
      en: {
        title: 'Book and confirm',
        who: 'Authorized service staff make human decisions; customer and establishment provide their own consent. Before-arrival cancellation requires its dedicated permission.',
        requires:
          'Applicable policy, hours and tariffs; consistent request, tables and quote.',
        steps: [
          'Record the request and proposed tables without certifying availability.',
          'Prepare a quote and record establishment/customer acceptance of that version.',
          'Obtain a human availability check and a valid temporary hold.',
          'Have an authorized collector record funds actually received.',
          'Confirm with the current quote, verified receipt and still-valid human proof.',
          'Consult the document and verify its state after any cancellation.',
        ],
        result:
          'A confirmed booking and verifiable document; a mere request proves neither availability nor received funds.',
        blocked:
          'Expired holds, replaced quotes, invalid consent or unverified receipts block confirmation. Zero advance remains blocked without explicit policy. Simulated transport proves no real notification; this flow does not make an AI agent operational.',
      },
      ar: {
        title: 'معالجة طلب الحجز وتأكيده',
        who: 'الموظف المخول يستقبل الطلب، ومسؤول الخدمة يتحقق من التوفر، والمحصل يعتمد استلام الأموال، والزبون يوافق على عرضه من حسابه.',
        requires:
          'يلزم تحديد الموعد والطاولات والعملة، مع قواعد وأسعار معتمدة وموافقات الأطراف المطلوبة.',
        steps: [
          'سجل طلب الحجز وعدد الأشخاص والموعد المطلوب.',
          'اختر الطاولات المقترحة وأعد عرض السعر واحصل على الموافقات.',
          'احجز الفترة مؤقتًا وتابع موعد انتهاء الحجز المؤقت.',
          'يتحقق مسؤول الخدمة من التوفر فعلًا ويسجل موافقته.',
          'يسجل المحصل الأموال المستلمة؛ الإيصال الذي ينتظر المراجعة لا يكفي للتأكيد.',
          'أكد الحجز بعد اكتمال الشروط، ثم اعرض وثيقة التأكيد أو اطبعها.',
        ],
        result:
          'يُحفظ حجز مؤكد ويمكن التحقق من صلاحية وثيقته. عرض السعر أو الحجز المؤقت وحده لا يكفي.',
        blocked:
          'إذا انتهى الحجز المؤقت أو تغير العرض أو غابت موافقة أو لم يُعتمد الإيصال، راجع الخطوة المعنية. سياسة الحجز دون عربون غير معتمدة هنا. الإلغاء قبل الوصول يتطلب صلاحية خاصة ولا يعيد الأموال تلقائيًا.',
      },
    },
  },
  {
    id: 'walkin',
    section: 'planning',
    operations: ['arrival', 'extend', 'physical_state'],
    capabilities: ['service'],
    copy: {
      fr: {
        title: 'Installer un client',
        who: 'Personne humaine disposant de l’habilitation service ; nettoyage et observation de disponibilité restent distincts.',
        requires:
          'Table sélectionnée et physiquement disponible, capacité, règles, créneau et fin prévue valides. Pour une réservation : affectation confirmée correspondante.',
        steps: [
          'Préciser s’il s’agit d’un client sans réservation ou d’une réservation confirmée.',
          'Choisir les tables autorisées et vérifier leur état physique chargé.',
          'Renseigner le nombre réel de personnes et une fin prévue postérieure à l’arrivée.',
          'Le service observe et confirme l’installation réelle ; ne cochez pas une observation non réalisée.',
        ],
        result:
          'Une occupation réelle est enregistrée et reste liée à ses tables. Une fin prévue n’enregistre jamais le départ automatiquement.',
        blocked:
          'Une table à nettoyer, occupée, en maintenance ou hors service ne peut pas être présentée comme disponible. Sinon, contrôler les conflits, capacités et affectations ; un état disponible seul ne garantit pas la réussite. L’arrivée anticipée reste bloquée sans politique explicite.',
      },
      en: {
        title: 'Seat a guest',
        who: 'A human with the service capability; cleaning and availability confirmation remain distinct.',
        requires:
          'Selected physically available table, valid capacity, policy, slot and planned end. For a booking, its corresponding confirmed assignment.',
        steps: [
          'Specify walk-in or confirmed booking.',
          'Select authorized tables and check their loaded physical state.',
          'Enter actual party size and a planned end after arrival.',
          'Service staff observe and confirm actual seating; never attest an unobserved fact.',
        ],
        result:
          'An actual occupation is recorded and linked to its tables. A planned end never records departure automatically.',
        blocked:
          'A dirty, occupied, maintained or out-of-service table cannot be represented as physically available. Otherwise check conflicts, capacity and assignments; available state alone does not guarantee success. Early arrival is blocked without explicit policy.',
      },
      ar: {
        title: 'تسجيل جلوس الزبون',
        who: 'موظف لديه صلاحية الخدمة والتحقق من الجلوس. صلاحية التنظيف وحدها لا تكفي.',
        requires:
          'حدد طاولة متاحة فعليًا وعدد الأشخاص وموعد المغادرة المتوقع. إذا كان للزبون حجز، فيجب أن يكون مؤكدًا ومطابقًا للطاولات.',
        steps: [
          'حدد هل جاء الزبون بحجز أم دون حجز.',
          'اختر الطاولات وتحقق من حالتها وسعتها والمواعيد الأخرى.',
          'أدخل عدد الأشخاص وموعد المغادرة المتوقع بعد وقت الوصول.',
          'عاين الجلوس الفعلي، ثم سجله بالإجراء المسموح لك.',
        ],
        result:
          'يُسجل إشغال الطاولة وتبدأ زيارة الزبون. موعد المغادرة المتوقع لا يسجل مغادرته تلقائيًا.',
        blocked:
          'لا يمكن الجلوس على طاولة بحاجة إلى تنظيف أو مشغولة أو قيد الصيانة أو خارج الخدمة. حتى الطاولة المتاحة قد تكون محجوزة في الموعد المطلوب. الوصول المبكر يحتاج إلى سياسة معتمدة غير متاحة حاليًا.',
      },
    },
  },
  {
    id: 'qr',
    section: 'visits',
    operations: ['public_link', 'install_presence'],
    capabilities: ['configure', 'service'],
    copy: {
      fr: {
        title: 'QR, signalement et visite',
        who: 'Client pour consulter et signaler ; service humain pour installer ; propriétaire pour gérer le QR de table.',
        requires:
          'Lien actif, table en service et tarif public exact configuré pour commander.',
        steps: [
          'Scanner ouvre le menu dans le navigateur sans enregistrer une présence.',
          'Le client choisit de signaler « Nous sommes installés ».',
          'Le personnel habilité observe la situation et confirme l’installation correspondante.',
          'La visite peut ensuite demander une commande ; le scan seul ne l’autorise pas.',
          'Consulter, imprimer ou renouveler le QR uniquement avec les droits de gestion requis.',
        ],
        result:
          'Une visite contrôlée est liée à l’occupation réelle. L’ancien accès ne permet plus de commander après le départ constaté.',
        blocked:
          'Lien invalide, table désactivée ou signal expiré : vérifier le bon QR et solliciter le service. Une lecture ne valide ni réservation, disponibilité ni paiement. Les liens 127.0.0.1 de recette ne sont pas accessibles depuis un autre téléphone.',
      },
      en: {
        title: 'QR, presence signal and visit',
        who: 'Customers consult and signal; human service staff seat; the owner manages table QR links.',
        requires:
          'Active link, in-service table and an exact configured public tariff to order.',
        steps: [
          'Scanning opens the menu in the browser without recording presence.',
          'The customer chooses to signal that they are seated.',
          'Authorized staff observe and confirm the corresponding actual seating.',
          'The controlled visit may then request an order; scanning alone grants no ordering authority.',
          'Read, print or rotate table QR links only with required management permissions.',
        ],
        result:
          'A controlled visit is linked to the actual occupation. Its old credential cannot order after recorded departure.',
        blocked:
          'For invalid links, inactive tables or expired signals, check the QR and ask service staff. Reading validates no booking, availability or payment. Rehearsal loopback links are not accessible from another phone.',
      },
      ar: {
        title: 'استخدام رمز QR وزيارة الزبون',
        who: 'الزبون يعرض القائمة ويبلغ عن جلوسه. مسؤول الخدمة يتحقق من الجلوس، والموظف المخول يدير رموز الطاولات.',
        requires:
          'يلزم رابط QR نشط وطاولة صالحة للخدمة. إرسال طلب وجبة يحتاج إلى أسعار سارية وزيارة معتمدة.',
        steps: [
          'يمسح الزبون الرمز لعرض القائمة؛ المسح وحده لا يسجل وصوله.',
          'يستطيع الزبون الإبلاغ بأنه جالس على الطاولة.',
          'يعاين مسؤول الخدمة الوضع ويسجل الجلوس الفعلي.',
          'بعد اعتماد الزيارة، يمكن للزبون إرسال طلب وجبة.',
          'اعرض الرمز أو اطبعه أو جدده فقط بالصلاحية المناسبة.',
        ],
        result:
          'ترتبط الزيارة بالجلوس المسجل. بعد تسجيل المغادرة، لا تسمح الزيارة القديمة بإرسال طلبات جديدة.',
        blocked:
          'إذا أُلغي الرابط أو كانت الطاولة خارج الخدمة أو انتهت صلاحية البلاغ، اطلب من مسؤول الخدمة التحقق. الرمز لا يمنح حق تأكيد حجز أو دفع. روابط التجربة المحلية لا تعمل من هاتف آخر دون إعداد وصول مناسب.',
      },
    },
  },
  {
    id: 'orders',
    section: 'visits',
    operations: ['visit_order_transition'],
    capabilities: [
      'orders.read',
      'orders.approve',
      'orders.prepare',
      'orders.complete',
    ],
    copy: {
      fr: {
        title: 'De la commande au service',
        who: 'Client de la visite pour demander ; service pour autoriser ; cuisine pour préparer ; service pour constater la remise. Chaque permission est distincte.',
        requires:
          'Visite active, occupation réelle, devise choisie et produits avec tarifs publics valides.',
        steps: [
          'Le client prépare et envoie sa demande de commande.',
          'Une personne autorisée approuve l’envoi de la commande en cuisine.',
          'La cuisine enregistre le début de la préparation, puis la disponibilité du plat.',
          'Le service constate la remise effective du plat au client.',
          'Consulter les événements autorisés de chaque responsabilité.',
        ],
        result:
          'Les étapes sont persistées localement et la commande reste rattachée à sa visite. Aucune étape ne vaut encaissement.',
        blocked:
          'Une permission ou un tarif manquant, une visite terminée ou un menu modifié bloque l’étape concernée. Ne recréez pas une demande pour contourner une réponse inconnue ; actualisez et vérifiez. Aucun envoi réel n’est activé.',
      },
      en: {
        title: 'From order request to service',
        who: 'The visit customer requests; service approves; kitchen prepares; service records delivery to the table. Every capability is separate.',
        requires:
          'Active visit, actual occupation, chosen currency and products with valid public tariffs.',
        steps: [
          'The customer prepares and submits the order request.',
          'An authorized staff member approves sending the order to the kitchen.',
          'Kitchen staff record preparation and mark the meal ready.',
          'Service staff confirm actual delivery to the customer.',
          'Read events authorized for each responsibility.',
        ],
        result:
          'Steps persist locally and the order stays linked to its visit. No step records collection.',
        blocked:
          'Missing permission/tariff, ended visits or a changed menu block the affected step. Do not recreate a request to bypass an unknown result; refresh and verify. No real transport is active.',
      },
      ar: {
        title: 'من تسجيل الطلب إلى تقديمه للزبون',
        who: 'الزبون يرسل الطلب. الموظف المخول يوافق على إرساله للمطبخ. المطبخ يسجل التحضير والجاهزية، وموظف الخدمة يؤكد التقديم. لكل خطوة صلاحية مستقلة.',
        requires:
          'يجب أن تكون الزيارة نشطة والجلوس مسجلًا، وأن تكون الأصناف متاحة بأسعار سارية وعملة محددة.',
        steps: [
          'يختار الزبون الأصناف ويرسل طلبه.',
          'يراجع الموظف المخول الطلب ويوافق على إرساله إلى المطبخ.',
          'يسجل موظف المطبخ بدء التحضير، ثم جاهزية الوجبة عند اكتمالها.',
          'بعد تقديم الوجبة فعلًا، يسجل موظف الخدمة إتمام التقديم.',
          'يمكن للمخولين مراجعة سجل كل خطوة ومن نفذها.',
        ],
        result:
          'تُحفظ مراحل الطلب وتبقى مرتبطة بزيارة الزبون. تقديم الوجبة لا يعني تحصيل ثمنها.',
        blocked:
          'إذا غابت الصلاحية أو السعر أو انتهت الزيارة أو تغيرت القائمة، راجع السبب. عند غياب نتيجة واضحة، حدّث البيانات ولا تنشئ طلبًا آخر لتجاوز المشكلة. لا تُرسل إشعارات حقيقية في التجربة.',
      },
    },
  },
  {
    id: 'finance',
    section: 'finance',
    operations: ['receipt', 'invoice', 'finalize_invoice', 'allocate'],
    capabilities: [
      'finance.read',
      'collect',
      'invoices.create',
      'invoices.finalize',
      'advances.allocate',
    ],
    copy: {
      fr: {
        title: 'Encaisser et facturer au restaurant',
        who: 'La personne habilitée à encaisser enregistre les fonds reçus. La consultation financière, la préparation et la finalisation des factures et l’affectation d’une avance exigent des droits distincts.',
        requires:
          'Réception réelle observée, demande/devis cohérents, devise et montants exacts. Aucun prestataire de paiement n’est connecté par cette aide.',
        steps: [
          'Le collecteur enregistre seulement les fonds effectivement reçus avec date et référence.',
          'Vérifier le statut du reçu ; revue manuelle n’est pas réception vérifiée.',
          'Préparer la facture de réservation ou d’occupation à partir de ses commandes et instantanés.',
          'Une personne distinctement habilitée finalise le brouillon après examen.',
          'Affecter l’avance éligible sans double utilisation ; elle réduit le solde, pas les ventes.',
        ],
        result:
          'Une facture et des faits d’encaissement traçables. Le flux n’exécute ni paiement externe ni remboursement automatique.',
        blocked:
          'Devise/montant divergents, précision historique non établie, source manquante ou excédent exigent un traitement humain. Une facture finalisée n’est pas une preuve de paiement. Les abonnements SaaS sont un parcours distinct.',
      },
      en: {
        title: 'Restaurant collection and invoicing',
        who: 'Authorized collectors record received funds. Financial viewing, invoice preparation, invoice finalization and advance allocation each require separate permissions.',
        requires:
          'Actual observed receipt, consistent request/quote, explicit currency and exact amounts. This help connects no payment provider.',
        steps: [
          'The collector records only funds actually received, with date and reference.',
          'Check receipt status; manual review is not verified receipt.',
          'Prepare the reservation or occupation invoice from its orders and snapshots.',
          'A separately authorized person reviews and finalizes the draft.',
          'Allocate eligible advances without reuse; they reduce the balance, not sales.',
        ],
        result:
          'A traceable invoice and collection facts. The flow executes neither external payment nor automatic refund.',
        blocked:
          'Currency/amount mismatch, uncertain historical precision, missing source or excess requires human handling. A finalized invoice does not prove payment. SaaS subscriptions are a separate flow.',
      },
      ar: {
        title: 'تسجيل الأموال المستلمة وإعداد الفاتورة',
        who: 'المحصل يسجل الأموال التي استلمها فعلًا. الاطلاع المالي وإعداد الفاتورة واعتمادها وتخصيص العربون تحتاج إلى صلاحيات مستقلة.',
        requires:
          'تحقق من الاستلام ومطابقة الطلب وعرض السعر والمبلغ والعملة. لا توجد بوابة دفع حقيقية متصلة بهذا الدليل.',
        steps: [
          'سجل المبلغ المستلم فعلًا مع التاريخ ومرجع الاستلام.',
          'راجع حالة الإيصال؛ الإيصال الذي ينتظر المراجعة لم يُعتمد بعد.',
          'أعد مسودة الفاتورة من الطلبات المرتبطة بالحجز أو الجلوس والأسعار المحفوظة.',
          'يراجع الموظف المخول الفاتورة ثم يعتمدها.',
          'خصص العربون المؤهل مرة واحدة؛ يخفض المبلغ المتبقي ولا يغيّر إجمالي المبيعات.',
        ],
        result:
          'تُحفظ الفاتورة وسجلات الاستلام دون دفع خارجي أو استرجاع تلقائي للأموال.',
        blocked:
          'عند اختلاف العملة أو المبلغ أو غياب مصدر موثوق للسعر أو وجود فائض عربون، اطلب مراجعة مالية. اعتماد الفاتورة لا يثبت الدفع. اشتراك المطعم في المنصة له مسار منفصل.',
      },
    },
  },
  {
    id: 'cleaning',
    section: 'planning',
    operations: ['physical'],
    capabilities: ['clean'],
    copy: {
      fr: {
        title: 'Départ et nettoyage',
        who: 'Personne disposant de l’habilitation de nettoyage pour les transitions physiques autorisées. La validation de disponibilité d’une réservation demande le service.',
        requires:
          'Une occupation réelle et l’observation du départ ou de l’étape de nettoyage ; droits toujours valides.',
        steps: [
          'Constater le départ réel dans le formulaire de départ/nettoyage.',
          'Commencer le nettoyage quand il commence effectivement.',
          'Terminer le nettoyage après son achèvement réel.',
          'Consulter séparément les réservations, maintenances et blocages futurs.',
        ],
        result:
          'Trois actions physiques distinctes et tracées. Le départ met fin aux autorisations de commande de la visite.',
        blocked:
          'Une fin prévue ne libère jamais une table. Un nettoyage terminé ne supprime pas les réservations ou maintenances. Même avec cumul des rôles, le nettoyage et la validation humaine d’une réservation restent deux actions.',
      },
      en: {
        title: 'Departure and cleaning',
        who: 'A human with cleaning capability performs authorized physical transitions. Booking availability confirmation requires service.',
        requires:
          'An actual occupation and observation of departure/cleaning; still-valid permissions.',
        steps: [
          'Record actual departure in the departure/cleaning form.',
          'Start cleaning when it actually starts.',
          'Finish cleaning only after completion.',
          'Separately consult future bookings, maintenance and blocks.',
        ],
        result:
          'Three distinct traceable physical actions. Departure ends visit ordering authority.',
        blocked:
          'A planned end never frees a table. Completed cleaning removes no future booking or maintenance. Holding both roles still requires separate cleaning and human availability-confirmation actions.',
      },
      ar: {
        title: 'تسجيل المغادرة والتنظيف',
        who: 'الموظف الذي يملك صلاحية التنظيف ينفذ الإجراءات الفعلية المسموح بها. تأكيد توفر الحجز يحتاج أيضًا إلى مسؤول الخدمة.',
        requires:
          'تحقق من المغادرة أو بدء التنظيف أو انتهائه فعلًا، مع صلاحية مناسبة ما زالت سارية.',
        steps: [
          'سجل المغادرة بعد ملاحظتها فعلًا.',
          'سجل بدء التنظيف عندما يبدأ العمل.',
          'أكد انتهاء التنظيف بعد إتمامه.',
          'راجع الحجوزات والصيانة وفترات عدم التوفر بصورة مستقلة.',
        ],
        result:
          'تُسجل المغادرة وبدء التنظيف وانتهاؤه كإجراءات منفصلة. المغادرة تنهي حق الزيارة في إرسال طلبات جديدة.',
        blocked:
          'موعد المغادرة المتوقع لا يحرر الطاولة تلقائيًا. انتهاء التنظيف لا يلغي الحجوزات المقبلة أو الصيانة. حتى من يجمع الوظيفتين ينفذ التنظيف وتأكيد توفر الحجز كإجراءين منفصلين.',
      },
    },
  },
  {
    id: 'history',
    section: 'history',
    operations: [],
    capabilities: [
      'service',
      'assistant',
      'collect',
      'finance.read',
      'configure',
      'reservations.cancel_before_arrival',
    ],
    copy: {
      fr: {
        title: 'Lire le journal des événements',
        who: 'Lecteurs du journal déjà autorisés pour cette succursale ; les droits restent contrôlés côté serveur.',
        requires:
          'Le bon périmètre et un accès courant. Les noms professionnels ne sont affichés que s’ils sont autorisés.',
        steps: [
          'Choisir éventuellement des dates locales inclusives, un type et un auteur.',
          'Filtrer et parcourir les pages ; actualiser pour inclure de nouveaux événements.',
          'Lire l’action, la cible, l’auteur et la date.',
          'Déplier les détails pour le code conservé et les valeurs effectivement enregistrées.',
        ],
        result:
          'Une lecture bornée et fidèle du journal append-only, sans modifier ses enregistrements.',
        blocked:
          'Un motif absent est explicitement non renseigné. Ne déduisez pas d’anciennes valeurs depuis la configuration actuelle. Les noms affichés peuvent être les noms professionnels actuels, pas des noms figés à la date de l’événement.',
      },
      en: {
        title: 'Read the event journal',
        who: 'Existing authorized history readers for this branch; the server still checks access.',
        requires:
          'Correct scope and current access. Professional names appear only when authorized.',
        steps: [
          'Optionally select inclusive local dates, type and actor.',
          'Apply filters and page through results; refresh for new events.',
          'Read action, target, actor and date.',
          'Expand details for the retained code and actually recorded values.',
        ],
        result:
          'A bounded, faithful read of the append-only journal without changing records.',
        blocked:
          'An absent reason is explicitly unrecorded. Do not infer past values from current configuration. Displayed names may be current professional labels, not historical snapshots.',
      },
      ar: {
        title: 'مراجعة سجل الأحداث',
        who: 'المستخدم المخول بالاطلاع على سجل هذا الفرع. يتحقق النظام من هذا الحق عند كل طلب.',
        requires:
          'اختر المطعم والفرع الصحيحين. الأسماء والمعلومات المالية لا تظهر إلا لمن تسمح صلاحياته بذلك.',
        steps: [
          'اختر الفترة ونوع الحدث ومن نفذه عند الحاجة.',
          'اضغط تصفية وتنقل بين الصفحات. حدّث القائمة لعرض الأحداث الجديدة.',
          'اقرأ ما حدث، والعنصر المعني، ومن نفذ الإجراء ومتى.',
          'افتح التغيير المسجل لعرض القيم السابقة والجديدة، أو التفاصيل التقنية لعرض الرمز الأصلي.',
        ],
        result: 'يمكنك مراجعة السجل دون تعديله أو حذف أحداثه.',
        blocked:
          'إذا لم يُسجل سبب أو اسم أو قيمة قديمة، يوضح الدليل ذلك ولا يخمنها. قد يكون الاسم المعروض هو الاسم المهني الحالي، وليس الاسم وقت الحدث.',
      },
    },
  },
  {
    id: 'concepts',
    section: 'planning',
    operations: [],
    capabilities: [],
    copy: {
      fr: {
        title: 'Comprendre les états et les objets',
        who: 'Tout lecteur autorisé peut consulter ces définitions ; elles n’accordent aucune permission.',
        requires:
          'Distinguer un fait physique, une demande et une décision autorisée.',
        steps: [
          'État physique : situation observée de la table maintenant. Planning : créneaux réservés, bloqués ou fermés à une date.',
          'Demande : intention à traiter. Réservation : engagement confirmé selon les validations du parcours.',
          'Visite : contexte contrôlé d’un client installé et de ses commandes. Document : version émise dont on vérifie le statut actuel.',
          'Fonction : description du travail. Permission : droit précis avec périmètre et contrôle serveur.',
        ],
        result:
          'Une table disponible physiquement peut être entièrement réservée. Un QR ou un document ne confère aucun droit administratif.',
        blocked:
          'En cas d’ambiguïté, préciser l’objet et l’étape avant d’agir. L’assistant documentaire ne certifie pas la disponibilité ni la réception d’argent.',
      },
      en: {
        title: 'Understand states and objects',
        who: 'Any authorized reader can consult these definitions; they grant no permission.',
        requires:
          'Separate a physical fact, a request and an authorized decision.',
        steps: [
          'Physical state: the observed table condition now. Schedule: booked, held or closed slots on a date.',
          'Request: an intention to process. Booking: a commitment confirmed through the required checks.',
          'Visit: a controlled context for an actually seated customer and orders. Document: an issued version with a currently verifiable status.',
          'Function: work description. Permission: a specific scoped right checked by the server.',
        ],
        result:
          'A physically available table may be fully booked. A QR or document grants no administrative authority.',
        blocked:
          'If ambiguous, clarify the object and step before acting. The documentation assistant certifies neither availability nor received funds.',
      },
      ar: {
        title: 'فهم حالة الطاولة والحجز والزيارة والصلاحيات',
        who: 'كل مستخدم مخول يمكنه قراءة هذه التعريفات، دون أن تمنحه صلاحية جديدة.',
        requires:
          'ميّز بين ما يحدث فعليًا في القاعة والمواعيد المسجلة والموافقات المطلوبة.',
        steps: [
          'حالة الطاولة تصف وضعها الآن. جدول الحجوزات يصف المواعيد المحجوزة أو غير المتاحة في يوم محدد.',
          'طلب الحجز يحتاج إلى معالجة. الحجز المؤكد يعني اكتمال التحققات والموافقات المطلوبة.',
          'الزيارة تربط الزبون الجالس بطاولته وطلباته. وثيقة التأكيد نسخة صادرة يجب التحقق من صلاحيتها.',
          'الوظيفة تصف مهام الموظف. الصلاحية تحدد الإجراء المسموح له وفي أي مطعم وفرع.',
        ],
        result:
          'قد تكون الطاولة متاحة الآن، لكن لا يوجد وقت لحجزها اليوم. الرمز أو الوثيقة لا يمنحان صلاحيات إدارية.',
        blocked:
          'إذا لم يكن المقصود واضحًا، حدد الطاولة أو الطلب والخطوة المطلوبة. الدليل لا يضمن توفر موعد أو استلام مبلغ.',
      },
    },
  },
];
const operationalStart: Record<Locale, ProcedureCopy> = {
  fr: {
    title: 'Accéder à sa succursale avec son compte',
    who: 'Compte réellement authentifié auprès du Keycloak local et rattaché par le propriétaire.',
    requires:
      'Une session active, une invitation acceptée si nécessaire, une activation et les permissions explicitement accordées.',
    steps: [
      'Se connecter depuis /access avec son compte personnel. Aucun profil de recette à choisir.',
      'Sélectionner son entreprise puis son restaurant dans la navigation principale.',
      'Ouvrir Tables et réservations, puis choisir explicitement une succursale autorisée.',
      'Vérifier le contexte et configurer les paramètres manquants si vos permissions le permettent.',
    ],
    result:
      'La même session permet de consulter et de modifier les données locales autorisées. Aucune réservation ni somme n’est créée par la sélection.',
    blocked:
      'Sans rattachement, consulter ses invitations et demander au propriétaire leur activation. L’acceptation seule ne donne pas de permission. Une session expirée nécessite une reconnexion ; une suspension ou révocation est appliquée côté serveur.',
  },
  en: {
    title: 'Access your branch with your account',
    who: 'An account genuinely authenticated by local Keycloak and associated by the owner.',
    requires:
      'An active session, accepted invitation when needed, activation and explicitly granted permissions.',
    steps: [
      'Sign in from /access with your personal account. No rehearsal profile is selected.',
      'Select your company and restaurant in the main navigation.',
      'Open Tables and reservations, then explicitly choose an authorized branch.',
      'Check the scope and configure missing settings if your permissions allow it.',
    ],
    result:
      'The same session reads and changes authorized local data. Selecting a branch creates no booking or funds.',
    blocked:
      'Without membership, review your invitations and ask the owner to activate them. Acceptance alone grants no permission. Expired sessions require sign-in; suspension and revocation are enforced server-side.',
  },
  ar: {
    title: 'الدخول إلى الفرع بحسابك الشخصي',
    who: 'مستخدم سجّل الدخول فعليًا عبر Keycloak المحلي وربط المالك حسابه بالمؤسسة.',
    requires:
      'جلسة سارية، وقبول الدعوة عند الحاجة، ثم تفعيل الارتباط ومنح الصلاحيات بشكل صريح.',
    steps: [
      'سجّل الدخول من /access بحسابك الشخصي دون اختيار شخصية اختبار.',
      'اختر المؤسسة ثم المطعم من التنقل الرئيسي.',
      'افتح الطاولات والحجوزات ثم اختر فرعًا مسموحًا لك.',
      'راجع سياق العمل وأكمل الإعدادات الناقصة إذا كانت لديك الصلاحية.',
    ],
    result:
      'تتيح الجلسة نفسها قراءة البيانات المحلية المسموح بها وتعديلها. اختيار الفرع لا ينشئ حجزًا أو مبلغًا.',
    blocked:
      'إذا لم يظهر ارتباطك، راجع دعواتك واطلب من المالك تفعيله. قبول الدعوة وحده لا يمنح صلاحية. أعد تسجيل الدخول عند انتهاء الجلسة؛ يطبّق الخادم التعليق وإلغاء الوصول.',
  },
};
export function procedure(id: Topic, operational = false): Procedure {
  const found = procedures.find((item) => item.id === id);
  if (!found) throw new Error('Unknown documentation topic');
  if (operational && id==='finance') {
    const additions: Record<Locale,{step:string;blocked:string}> = {
      fr:{step:'Après finalisation, une personne habilitée à l’encaissement peut enregistrer le solde exact vérifié, avec devise, date et référence de reçu. Ce formulaire est disponible dans le parcours opérationnel local.',blocked:'Ce circuit ne traite ni paiement partiel, ni conversion, ni remboursement automatique. En recette, les fonds déclarés restent explicitement fictifs. Le client consulte sa propre facture avec sa preuve de visite ; une session du personnel ne la remplace pas.'},
      en:{step:'After finalization, an explicitly authorized collector can record the exact verified balance, currency, date and receipt reference. This form is available in the integrated local flow.',blocked:'This path provides no partial payment, conversion or automatic refund. Rehearsal funds remain explicitly fictional. A customer reads their own invoice using their visit proof; a staff session cannot replace it.'},
      ar:{step:'بعد تثبيت الفاتورة، يستطيع شخص مخوّل بالتحصيل تسجيل المبلغ المتبقي كاملًا بعد التحقق منه، مع العملة والتاريخ ومرجع الوصل. هذا النموذج متاح في المسار المحلي المدمج.',blocked:'لا يشمل هذا المسار الدفع الجزئي أو تحويل العملة أو الاسترداد الآلي. تبقى أموال التجربة وهمية ومعلنة. يطّلع الزبون على فاتورته بإثبات زيارته، ولا تعوّضه جلسة أحد العاملين.'},
    };
    const copy=(locale:Locale):ProcedureCopy=>({...found.copy[locale],steps:[...found.copy[locale].steps,additions[locale].step],blocked:found.copy[locale].blocked+' '+additions[locale].blocked});
    return {...found,operations:[...found.operations,'settlement'],copy:{fr:copy('fr'),en:copy('en'),ar:copy('ar')}};
  }
  return operational && id === 'start'
    ? { ...found, copy: operationalStart }
    : found;
}
export function topicForOperation(operation: string): Topic {
  if(operation==='settlement')return 'finance';
  return (
    procedures.find((item) => item.operations.includes(operation))?.id ??
    'concepts'
  );
}
export function topicForSection(section: string): Topic {
  return (
    (
      {
        planning: 'walkin',
        configuration: 'configuration',
        staff: 'staff',
        requests: 'reservations',
        visits: 'qr',
        finance: 'finance',
        history: 'history',
      } as Record<string, Topic>
    )[section] ?? 'start'
  );
}
