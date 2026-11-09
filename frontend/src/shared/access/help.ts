// MoulAI™ — versioned access documentation derived from the disconnected and review adapters.
import type { Locale } from './contracts';
type Copy = readonly [string, string, string];
export const ACCESS_HELP_VERSION = 'access-help-2026-11-07.1';
const index = { fr: 0, en: 1, ar: 2 } as const;
const copy = (text: Copy, locale: Locale) => text[index[locale]];
export const accessScenarios: Record<string, Copy> = {
  owner: [
    'Revue synthétique : propriétaire de deux entreprises fictives, avec accès à leurs restaurants. Ne crée aucune identité réelle.',
    'Synthetic review: owner of two fictional companies and their restaurants. Creates no real identity.',
    'مراجعة مصطنعة: مالك مؤسستين وهميتين ومطاعمهما. لا تنشئ هوية حقيقية.',
  ],
  manager: [
    'Revue synthétique : responsable de l’entreprise A, avec accès explicite au restaurant Alger Centre. Ne dispose pas des opérations réservées au propriétaire.',
    'Synthetic review: company A manager, explicitly scoped to Algiers Centre. No owner-only operations.',
    'مراجعة مصطنعة: مسؤول المؤسسة أ مع وصول صريح إلى مطعم الجزائر الوسط، دون إجراءات المالك الحصرية.',
  ],
  employee: [
    'Revue synthétique : membre du personnel avec accès de consultation au restaurant Alger Les Jardins. Aucun droit de gestion implicite.',
    'Synthetic review: staff reader scoped to Algiers Les Jardins. No implicit management rights.',
    'مراجعة مصطنعة: موظف للاطلاع على مطعم الجزائر الحدائق، دون صلاحيات إدارة ضمنية.',
  ],
  empty: [
    'Contrôle : membre associé à l’entreprise mais sans restaurant accordé. Demander au propriétaire un rattachement autorisé ; ne pas changer de profil pour contourner ce manque.',
    'Control: company member without a granted restaurant. Ask the owner for authorized access; do not switch profiles to bypass it.',
    'اختبار: عضو مرتبط بالمؤسسة دون مطعم مسموح. اطلب من المالك الربط المناسب ولا تغيّر الملف لتجاوز المنع.',
  ],
  admin: [
    'Revue synthétique : espace plateforme, avec gestion des administrateurs, des restaurants et revue des paiements fictifs. Distinct du rôle propriétaire.',
    'Synthetic review: platform area with admin/restaurant management and fictional payment review. Separate from owner.',
    'مراجعة مصطنعة: فضاء المنصة لإدارة المسؤولين والمطاعم ومراجعة مدفوعات وهمية، منفصل عن دور المالك.',
  ],
  unlinked: [
    'Contrôle : identité sans association active. Demander une invitation ou un rattachement vérifié ; aucun établissement ne doit être deviné.',
    'Control: identity with no active association. Request a verified invitation or membership; never guess an establishment.',
    'اختبار: هوية دون ارتباط نشط. اطلب دعوة أو ربطًا متحققًا منه؛ لا يُفترض لها مطعم.',
  ],
  suspended: [
    'Contrôle : accès suspendu. Contacter le propriétaire ou un responsable habilité ; aucune réactivation automatique.',
    'Control: suspended access. Contact the owner or authorized administrator; no automatic reactivation.',
    'اختبار: وصول معلّق. اتصل بالمالك أو المسؤول المخوّل؛ لا إعادة تفعيل تلقائية.',
  ],
  error: [
    'Contrôle : erreur temporaire de chargement. Réessayer par l’action proposée sans modifier les droits ; contacter l’assistance si elle persiste.',
    'Control: temporary loading error. Use the offered retry without changing permissions; contact support if it persists.',
    'اختبار: خطأ مؤقت في التحميل. أعد المحاولة بالإجراء المعروض دون تغيير الصلاحيات، واطلب الدعم إن استمر.',
  ],
};
const sections: readonly { title: Copy; body: Copy }[] = [
  {
    title: ['Accéder à son espace', 'Access your space', 'الوصول إلى فضائك'],
    body: [
      'La connexion réelle n’est pas raccordée dans cette revue. En utilisation réelle, l’identité authentifiée détermine les rôles et les accès ; le choix d’un scénario ne constitue jamais une connexion. Ici, seuls des comptes synthétiques en mémoire sont proposés.',
      'Real login is not connected in this review. In real use, authenticated identity determines roles and access; choosing a scenario is never authentication. Only in-memory synthetic accounts are offered here.',
      'تسجيل الدخول الحقيقي غير مربوط بهذه المراجعة. تحدد الهوية الموثقة الأدوار والوصول في الاستخدام الحقيقي؛ اختيار سيناريو ليس تسجيل دخول. المتاح هنا حسابات مصطنعة في الذاكرة فقط.',
    ],
  },
  {
    title: [
      'Entreprise, restaurant et succursale',
      'Company, restaurant and branch',
      'المؤسسة والمطعم والفرع',
    ],
    body: [
      'Choisir d’abord son entreprise autorisée, puis le restaurant et la succursale accessibles. Un nom de fonction ne donne pas de droits. Le propriétaire organise les rattachements ; le serveur doit vérifier chaque opération lors de l’intégration réelle.',
      'Choose an authorized company, then an accessible restaurant and branch. A function title grants no rights. The owner manages memberships; the server must verify every operation during real integration.',
      'اختر المؤسسة المسموح بها ثم المطعم والفرع المتاحين. اسم الوظيفة لا يمنح صلاحيات. يدير المالك الارتباطات، ويتحقق الخادم من كل إجراء عند الربط الحقيقي.',
    ],
  },
  {
    title: [
      'Si aucun espace n’est accessible',
      'If no space is accessible',
      'إذا لم يتوفر فضاء',
    ],
    body: [
      'Sans établissement attribué : demander un accès au propriétaire. Sans association : demander une invitation vérifiée. Accès suspendu : contacter la personne habilitée à le rétablir. Erreur temporaire : utiliser Réessayer ; si elle persiste, demander assistance sans transmettre de mot de passe ni de jeton. Aucun canal de notification réel n’est activé ici.',
      'No assigned establishment: ask the owner for access. No association: request a verified invitation. Suspended: contact an authorized administrator. Temporary error: retry; if persistent, ask for support without passwords or tokens. No real notification channel is enabled here.',
      'دون مؤسسة مسندة: اطلب الوصول من المالك. دون ارتباط: اطلب دعوة متحققًا منها. وصول معلّق: راجع المخوّل بإعادته. خطأ مؤقت: أعد المحاولة واطلب الدعم إن استمر، دون إرسال كلمة مرور أو رمز دخول. لا قناة إشعار حقيقية مفعلة هنا.',
    ],
  },
  {
    title: [
      'Profils métier et contrôles de recette',
      'Business profiles and review checks',
      'الملفات المهنية وسيناريوهات التحقق',
    ],
    body: [
      'Les profils propriétaire, responsable et personnel, ainsi que l’administration, illustrent des droits synthétiques. Les autres choix provoquent volontairement des états sans accès ou d’erreur. Aucun choix ne modifie les permissions d’un compte réel.',
      'Owner, manager, staff and platform administration profiles illustrate synthetic grants. Other choices deliberately exercise no-access or error states. No choice changes a real account’s permissions.',
      'تعرض ملفات المالك والمسؤول والموظف وإدارة المنصة صلاحيات مصطنعة. بقية الخيارات تختبر عمدًا حالات منع الوصول أو الخطأ. لا يغيّر أي خيار صلاحيات حساب حقيقي.',
    ],
  },
];
export const scenarioExplanation = (scenario: string, locale: Locale) =>
  accessScenarios[scenario] ? copy(accessScenarios[scenario], locale) : null;
const operationalSections: readonly { title: Copy; body: Copy }[] = [
  {
    title: [
      'Connexion authentifiée locale',
      'Authenticated local login',
      'تسجيل دخول محلي موثّق',
    ],
    body: [
      'Utilisez votre compte et mot de passe Keycloak local. La plateforme ne reçoit pas votre mot de passe. La session est restaurée par un cookie sécurisé ; son expiration impose une nouvelle authentification. Déconnectez-vous par le bouton de la plateforme.',
      'Use your local Keycloak account and password. The platform does not receive your password. A secure cookie restores the session; expiration requires authentication again. Use the platform sign-out button.',
      'استخدم حسابك وكلمة مرورك في Keycloak المحلي. لا تستلم المنصة كلمة مرورك. تستعيد الجلسة بملف ارتباط آمن، ويتطلب انتهاء صلاحيتها إعادة التحقق. استخدم زر الخروج من المنصة.',
    ],
  },
  {
    title: [
      'Établissements et habilitations',
      'Establishments and permissions',
      'المؤسسات والصلاحيات',
    ],
    body: [
      'Vos entreprises, restaurants et succursales proviennent des rattachements persistés et sont vérifiés côté serveur. Choisissez explicitement le contexte autorisé. Aucun profil de test ni nom de fonction ne donne des droits. Le propriétaire ne devient pas administrateur MoulAI.',
      'Companies, restaurants and branches come from persisted memberships checked server-side. Explicitly select an authorized context. No test profile or function name grants permission. An owner does not become a MoulAI administrator.',
      'تأتي المؤسسات والمطاعم والفروع من الارتباطات المحفوظة ويتحقق منها الخادم. اختر نطاقًا مسموحًا صراحةً. ملف الاختبار أو اسم الوظيفة لا يمنح صلاحيات، والمالك ليس مسؤولًا عامًا للمنصة.',
    ],
  },
  {
    title: [
      'Sans accès ou invitation en attente',
      'No access or pending invitation',
      'غياب الوصول أو دعوة معلقة',
    ],
    body: [
      'Sans rattachement actif, consultez Mes invitations professionnelles ou demandez une invitation au propriétaire. Votre acceptation ne remplace pas son activation et ses habilitations explicites. En cas de suspension ou révocation, le serveur refuse l’accès. Une erreur temporaire permet de réessayer sans changer d’identité.',
      'Without active membership, check My professional invitations or request an owner invitation. Accepting does not replace owner activation and explicit grants. The server denies suspended or revoked access. Retry a temporary error without switching identity.',
      'دون ارتباط نشط، راجع دعواتك المهنية أو اطلب دعوة من المالك. قبولك لا يغني عن تفعيله ومنحه الصلاحيات صراحةً. يرفض الخادم الوصول المعلّق أو الملغى. أعد محاولة الخطأ المؤقت دون تغيير هويتك.',
    ],
  },
  {
    title: [
      'Périmètre opérationnel disponible',
      'Available operational scope',
      'النطاق التشغيلي المتاح',
    ],
    body: [
      'Le lot 1 raccorde l’identité, les établissements et Tables et réservations. Les tarifs SaaS, l’inscription complète, le parcours client et les autres modules restent suivis dans les lots suivants. Les transports externes et l’IA ne sont pas activés.',
      'Lot 1 connects identity, establishments and Tables and reservations. SaaS pricing, complete enrollment, customer flows and other modules remain in subsequent lots. External transports and AI are not activated.',
      'تربط الدفعة الأولى الهوية والمؤسسات ووحدة الطاولات والحجوزات. التسعير والاشتراك ومسار الزبون وبقية الوحدات ضمن الدفعات التالية. لا خدمات نقل خارجية أو ذكاء اصطناعي مفعّلة.',
    ],
  },
];
export const accessDocumentation = (locale: Locale, operational = false) =>
  (operational ? operationalSections : sections).map((section) => ({
    title: copy(section.title, locale),
    body: copy(section.body, locale),
  }));
