// ==============================================
// MoulAI™ Platform - Agent-as-a-Service
// Author: Youcef Nesrine
// License: CC BY-NC-ND 4.0
// Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
// ==============================================

import type { intelligenceFr } from './intelligence.fr';

export const intelligenceAr: Record<keyof typeof intelligenceFr, string> = {
  'intelligence.boundary':
    'مراجعة محلية: وكلاء وقنوات ومحادثات اصطناعية. لا يوجد مزود متصل. تُمسح بيانات هذه الوحدة عند مغادرة النطاق.',
  'intelligence.agentIntro':
    'اطّلع على وكلاء المطعم المحدد وإعداداتهم الوصفية.',
  'intelligence.channelIntro':
    'القنوات التابعة لوكلاء هذا المطعم. تصف المؤشرات سجلات المراجعة وليس اتصالًا فعليًا.',
  'intelligence.conversationIntro':
    'اطّلع على المحادثات ضمن النطاق المحدد. لا تُحدّث هذه الواجهة في الوقت الحقيقي.',
  'intelligence.name': 'الاسم',
  'intelligence.description': 'الوصف',
  'intelligence.language': 'لغة الوكيل',
  'intelligence.tone': 'أسلوب الخطاب',
  'intelligence.tone.professional': 'مهني',
  'intelligence.tone.casual': 'عفوي',
  'intelligence.tone.friendly': 'ودّي',
  'intelligence.status': 'الحالة',
  'intelligence.all': 'الكل',
  'intelligence.search': 'بحث',
  'intelligence.agent': 'الوكيل',
  'intelligence.channelType': 'نوع القناة',
  'intelligence.channel.telegram': 'تيليغرام',
  'intelligence.channel.whatsapp': 'واتساب',
  'intelligence.channel.web': 'الويب',
  'intelligence.channel.messenger': 'ماسنجر',
  'intelligence.channel.api': 'واجهة برمجية',
  'intelligence.status.active': 'نشطة',
  'intelligence.status.closed': 'مغلقة',
  'intelligence.status.suspended': 'معلقة',
  'intelligence.openAgent': 'عرض الوكيل',
  'intelligence.openChannel': 'عرض القناة',
  'intelligence.openConversation': 'عرض المحادثة',
  'intelligence.created': 'تاريخ الإنشاء',
  'intelligence.updated': 'آخر تحديث',
  'intelligence.notProvided': 'غير محدد',
  'intelligence.configure': 'إعداد ضمن المراجعة المحلية',
  'intelligence.closeEditor': 'إغلاق النموذج',
  'intelligence.safeConfig':
    'لم يُعتمد عقد عام آمن لإعدادات JSON المتقدمة ومعاملات الذكاء الاصطناعي. أُجّل ربطها ولا يتوفر تفعيل هنا.',
  'intelligence.channelBoundary':
    'لا تُعرض إعدادات المزود أو بيانات الدخول أو الرموز أو الويب هوك. ينتظر ربط القنوات وعملياتها مرحلة التكامل الوظيفي.',
  'intelligence.editNotice':
    'تعديلات وصفية اصطناعية فقط. دون حفظ عن بعد أو تفعيل حقيقي.',
  'intelligence.confirmTitle': 'مراجعة التعديل المحلي',
  'intelligence.backEdit': 'العودة إلى النموذج',
  'intelligence.applyReview': 'تطبيق على المراجعة المحلية',
  'intelligence.preview': 'مراجعة التعديل',
  'intelligence.invalid': 'تحقق من هذا الحقل وحدوده.',
  'intelligence.stale':
    'تغيرت بيانات المراجعة. أغلق النموذج وأعد تحميل المعلومات.',
  'intelligence.failed':
    'لم يُطبق التعديل. تحقق من النطاق قبل المحاولة مجددًا.',
  'intelligence.pagination': 'ترقيم الصفحات',
  'intelligence.previous': 'السابق',
  'intelligence.next': 'التالي',
  'intelligence.pageCount': 'الصفحة {{page}} / {{pages}} · {{count}} عناصر',
  'intelligence.visitor': 'زائر غير محدد الاسم',
  'intelligence.participant': 'معرّف المشارك',
  'intelligence.messages': 'الرسائل',
  'intelligence.emptyMessages': 'لا تحتوي هذه المحادثة على رسائل.',
  'intelligence.role.user': 'العميل',
  'intelligence.role.assistant': 'المساعد',
  'intelligence.role.system': 'النظام',
  'intelligence.mediaBoundary': 'يُعرض محتوى الوسائط كنص فقط',
  'intelligence.media.image': 'صورة',
  'intelligence.media.audio': 'صوت',
  'intelligence.media.video': 'فيديو',
  'intelligence.media.file': 'ملف',
  'intelligence.readOnly':
    'للاطلاع فقط. ينتظر الإرسال والتحديث الفوري وتغيير الحالات مرحلة التكامل الوظيفي.',
};
