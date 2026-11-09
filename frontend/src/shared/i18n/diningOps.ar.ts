// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

export const diningOpsAr = {
  'ops.planningLabel': 'التخطيط',
  'ops.observationDetails': 'تفاصيل المعاينة',

  'ops.board': 'حالة الطاولات والتخطيط',
  'ops.currentPhysical': 'الحالة الفعلية الحالية',
  'ops.observedAt': 'بيانات أعيدت قراءتها في',
  'ops.observationTimeMissing': 'وقت الرصد غير متوفر — بيانات مراجعة',
  'ops.planningDate': 'تخطيط التاريخ المحدد',
  'ops.separationNote':
    'الحالة الفعلية لا تؤكد توفر الحجز. الأوقات المتوقعة لا تحرر الطاولة تلقائيًا.',
  'ops.filterPhysical': 'تصفية الحالة الفعلية الحالية',
  'ops.all': 'الكل',
  'ops.reset': 'إعادة ضبط التصفية',
  'ops.legend': 'دليل الحالات والتخطيط',
  'ops.results': 'الطاولات المعروضة: {{visible}} من {{total}}',
  'ops.available': 'متاحة',
  'ops.occupied': 'مشغولة',
  'ops.dirty': 'بحاجة إلى التنظيف',
  'ops.maintenance': 'قيد الصيانة',
  'ops.out_of_service': 'خارج الخدمة',
  'ops.unknown': 'حالة غير معروفة — يلزم التحقق',
  'ops.full': 'محجوزة بالكامل خلال ساعات الفتح',
  'ops.confirmed': 'حجز مؤكد',
  'ops.hold': 'حجز مؤقت',
  'ops.holdExpired': 'انتهى الحجز المؤقت — يلزم التدخل',
  'ops.paymentPending': 'بانتظار الدفع',
  'ops.paymentReview': 'الدفع غير معتمد',
  'ops.humanPending': 'بانتظار الموافقة البشرية على الطلب',
  'ops.closed': 'فترة غير متاحة في التخطيط',
  'ops.planningUnknown': 'التخطيط غير متاح — يلزم التحقق',
  'ops.planningOccupation': 'إشغال مسجل في التخطيط',
  'ops.nextReservation': 'الحجز القادم',
  'ops.noRegisteredClaim':
    'لا حجز مؤقت أو مؤكد مسجل لهذا التاريخ. لا يزال التوفر يتطلب التأكيد.',
  'ops.recordedPeriods': 'عرض الفترات المسجلة ({{count}})',
  'ops.expires': 'انتهاء الحجز المؤقت',
  'ops.blockReason': 'سبب المنع المرتبط',
  'ops.notRecorded': 'غير مسجل',
  'ops.locationMissing': 'الموقع غير مسجل',
  'ops.capacity': 'السعة',
  'ops.arrivalActual': 'الإجلاس الفعلي',
  'ops.endExpected': 'النهاية المتوقعة',
  'ops.cleanStartExpected': 'بداية التنظيف المتوقعة',
  'ops.cleanEndExpected': 'نهاية التنظيف المتوقعة',
  'ops.cleanStartActual': 'بداية التنظيف الفعلية',
  'ops.cleanEndActual': 'نهاية التنظيف الفعلية',
  'ops.unavailableFrom': 'غير متاحة منذ',
  'ops.unavailableUntil': 'نهاية عدم التوفر المسجلة',
  'ops.occupationLate':
    'تجاوز وقت النهاية المتوقع — الطاولة ما زالت مشغولة ويلزم التدخل.',
  'ops.cleaningLate': 'تجاوز وقت نهاية التنظيف المتوقع — يلزم التدخل.',
  'ops.planningConflict': 'يتداخل الحجز مع فترة عدم توفر — تلزم مراجعة بشرية.',
  'ops.manualReview': 'يلزم تدخل بشري',
  'ops.requests': 'طلبات مرتبطة بهذا التاريخ',
  'ops.readOnly': 'للاطلاع — لا إجراء فعلي مخوّل هنا',
  'ops.authorizedActions': 'عرض الإجراءات المصرح بها',
  'ops.noMatch':
    'لا طاولة تطابق هذه الحالة الفعلية. أعد ضبط التصفية لعرض جميع الطاولات.',
  'ops.noTables': 'لا طاولات متاحة للاطلاع في هذا النطاق.',
  'ops.legend_available': 'حالة فعلية دون موافقة على الحجز.',
  'ops.legend_occupied': 'إشغال فعلي مستقل عن النهاية المتوقعة.',
  'ops.legend_dirty': 'تنظيف مطلوب أو جارٍ؛ التحرير بإجراء بشري فقط.',
  'ops.legend_maintenance': 'الصيانة مستقلة عن الحجوزات.',
  'ops.legend_out_of_service': 'مسحوبة من الخدمة؛ المدة مجهولة ما لم تسجل.',
  'ops.legendPlanning':
    'الأزرق: حجز أو تخطيط ممتلئ. الكهرماني: حجز مؤقت أو انتظار دفع بتسميات وأيقونات مختلفة. الساعة المحايدة: موافقة بشرية. الأحمر: تدخل مطلوب.',
  'ops.localNotice':
    'مراجعة محلية: PostgreSQL مؤقت · هويات وأموال وهمية · دون إرسال حقيقي.',
  'ops.environmentDetails': 'تفاصيل البيئة المحلية',
  'ops.sessionSettings': 'هوية ومؤسسة المراجعة',
  'ops.tablePlanning': 'تخطيط الطاولة {{table}}',
} as const;
