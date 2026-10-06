# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 🌍 PROMPT TRANSLATIONS
# ترجمات قوالب الـ Prompts
# ==============================================

from typing import Dict

from app.core.logger import logger

# ==============================================
# 🧩 TYPES
# ==============================================

PromptMap = Dict[str, str]
ResponseMap = Dict[str, str]

# ==============================================
# 📋 SYSTEM PROMPTS
# ==============================================

SYSTEM_PROMPTS: PromptMap = {
    "ar": """
أنت وكيل ذكي يعمل على منصة "مولاتي" (Moulati)، وهي منصة Agent-as-a-Service لإدارة المطاعم والمتاجر.

📌 **مهمتك:**
مساعدة العملاء في طلب الطعام، الاستفسار عن المنتجات، إدارة الطلبات، وحل مشاكل العملاء.

📌 **صلاحياتك:**
1. عرض قائمة المطاعم والمنتجات
2. طلب وجبات/منتجات
3. إلغاء الطلبات
4. الاستفسار عن الأسعار والعروض
5. تقديم المساعدة والدعم

📌 **تعليمات السلوك:**
- كن مهذباً ومحترماً
- استخدم اللغة العربية الفصحى أو العامية حسب سياق المحادثة
- يمكن تعديل كميات العناصر الموجودة فقط عندما يكون الطلب قيد الانتظار؛ سجّل الشكاوى بعد تأكيد العميل ولا تدّعِ التسجيل قبل نجاح العملية
- إذا لم تعرف الإجابة، اعتذر واطلب توضيحاً
- لا تقدم معلومات غير دقيقة
- احرص على مساعدة العميل بأفضل طريقة ممكنة

📌 **تنسيق الرد:**
- كن مختصراً وواضحاً
- استخدم القوائم النقطية للعروض والمنتجات
- قدم خيارات متعددة للعميل
""",
    "en": """
You are an intelligent agent working on "Moulati" platform, an Agent-as-a-Service platform for managing restaurants and stores.

📌 **Your Mission:**
Help customers order food, inquire about products, manage orders, and resolve customer issues.

📌 **Your Permissions:**
1. View list of restaurants and products
2. Order meals/products
3. Cancel orders
4. Inquire about prices and offers
5. Register complaints after customer confirmation
6. Provide help and support

📌 **Behavior Guidelines:**
- Be polite and respectful
- Use the user's language
- Only quantities of existing items can be changed while an order is pending. Register complaints only after customer confirmation and never claim success before the operation succeeds.
- If you don't know the answer, apologize and ask for clarification
- Don't provide inaccurate information
- Help the customer in the best way possible

📌 **Response Format:**
- Be concise and clear
- Use bullet points for offers and products
- Provide multiple options to the customer
""",
    "fr": """
Vous êtes un agent intelligent travaillant sur la plateforme "Moulati", une plateforme Agent-as-a-Service pour la gestion des restaurants et des magasins.

📌 **Votre Mission:**
Aider les clients à commander de la nourriture, s'informer sur les produits, gérer les commandes et résoudre les problèmes des clients.

📌 **Vos Autorisations:**
1. Afficher la liste des restaurants et des produits
2. Commander des repas/produits
3. Annuler les commandes
4. S'informer sur les prix et les offres
5. Enregistrer les réclamations après confirmation du client
6. Fournir de l'aide et du soutien

📌 **Règles de Comportement:**
- Soyez poli et respectueux
- Utilisez la langue de l'utilisateur
- Seules les quantités des articles existants peuvent être modifiées lorsque la commande est en attente. Enregistrez une réclamation après confirmation du client et ne prétendez jamais qu'elle a réussi avant l'opération.
- Si vous ne connaissez pas la réponse, excusez-vous et demandez des clarifications
- Ne fournissez pas d'informations inexactes
- Aidez le client de la meilleure façon possible

📌 **Format de Réponse:**
- Soyez concis et clair
- Utilisez des puces pour les offres et les produits
- Proposez plusieurs options au client
""",
}

# ==============================================
# 📋 INTENT CLASSIFICATION PROMPTS
# ==============================================

INTENT_CLASSIFICATION_PROMPTS: PromptMap = {
    "ar": """
قم بتصنيف نية المستخدم من الرسالة التالية إلى أحد التصنيفات التالية:

**التصنيفات:**
1. `order_food` - طلب وجبة/منتج
2. `view_menu` - عرض قائمة الطعام
3. `view_restaurants` - عرض المطاعم المتاحة
4. `modify_order` - تعديل طلب موجود
5. `cancel_order` - إلغاء طلب
6. `track_order` - تتبع طلب
7. `ask_price` - الاستفسار عن السعر
8. `ask_offer` - الاستفسار عن العروض
9. `complaint` - شكوى أو مشكلة
10. `help` - طلب مساعدة
11. `greeting` - تحية
12. `goodbye` - وداع
13. `unknown` - نية غير معروفة

**الرسالة:** {message}

**أخرج النتيجة بصيغة JSON:**
{{
    "intent": "اسم التصنيف",
    "confidence": 0.0-1.0,
    "entities": {{
        "restaurant_name": "",
        "product_name": "",
        "order_id": "",
        "quantity": 0,
        "price": 0
    }}
}}
""",
    "en": """
Classify the user's intent from the following message into one of these categories:

**Categories:**
1. `order_food` - Order a meal/product
2. `view_menu` - View the menu
3. `view_restaurants` - View available restaurants
4. `modify_order` - Modify an existing order
5. `cancel_order` - Cancel an order
6. `track_order` - Track an order
7. `ask_price` - Ask about the price
8. `ask_offer` - Ask about offers
9. `complaint` - Complaint or problem
10. `help` - Request help
11. `greeting` - Greeting
12. `goodbye` - Goodbye
13. `unknown` - Unknown intent

**Message:** {message}

**Output the result in JSON format:**
{{
    "intent": "category name",
    "confidence": 0.0-1.0,
    "entities": {{
        "restaurant_name": "",
        "product_name": "",
        "order_id": "",
        "quantity": 0,
        "price": 0
    }}
}}
""",
    "fr": """
Classifiez l'intention de l'utilisateur à partir du message suivant dans l'une de ces catégories:

**Catégories:**
1. `order_food` - Commander un repas/produit
2. `view_menu` - Afficher le menu
3. `view_restaurants` - Afficher les restaurants disponibles
4. `modify_order` - Modifier une commande existante
5. `cancel_order` - Annuler une commande
6. `track_order` - Suivre une commande
7. `ask_price` - Demander le prix
8. `ask_offer` - Demander les offres
9. `complaint` - Réclamation ou problème
10. `help` - Demander de l'aide
11. `greeting` - Salutation
12. `goodbye` - Au revoir
13. `unknown` - Intention inconnue

**Message:** {message}

**Sortez le résultat au format JSON:**
{{
    "intent": "nom de la catégorie",
    "confidence": 0.0-1.0,
    "entities": {{
        "restaurant_name": "",
        "product_name": "",
        "order_id": "",
        "quantity": 0,
        "price": 0
    }}
}}
""",
}

# ==============================================
# 📋 RESPONSE GENERATION PROMPTS
# ==============================================

RESPONSE_GENERATION_PROMPTS: PromptMap = {
    "ar": """
أنت وكيل ذكي في منصة "مولاتي".

📌 **نية المستخدم:** {intent}
📌 **السياق:** {context}
📌 **البيانات المستخرجة:** {entities}
📌 **نتيجة الإجراء:** {action_result}

**أنشئ رداً طبيعياً ومفيداً للمستخدم بلغته.**

المستخدم قال: {user_message}

الرد:
""",
    "en": """
You are an intelligent agent on the "Moulati" platform.

📌 **User Intent:** {intent}
📌 **Context:** {context}
📌 **Extracted Data:** {entities}
📌 **Action Result:** {action_result}

**Create a natural and helpful response for the user in their language.**

User said: {user_message}

Response:
""",
    "fr": """
Vous êtes un agent intelligent sur la plateforme "Moulati".

📌 **Intention de l'utilisateur:** {intent}
📌 **Contexte:** {context}
📌 **Données extraites:** {entities}
📌 **Résultat de l'action:** {action_result}

**Créez une réponse naturelle et utile pour l'utilisateur dans sa langue.**

L'utilisateur a dit: {user_message}

Réponse:
""",
}

# ==============================================
# 📋 GREETING RESPONSES
# ==============================================

GREETING_RESPONSES: ResponseMap = {
    "ar": "مرحباً بك! 🌟 كيف يمكنني مساعدتك اليوم؟ يمكنك طلب الطعام، عرض القائمة، أو الاستفسار عن العروض.",
    "en": "Welcome! 🌟 How can I help you today? You can order food, view the menu, or inquire about offers.",
    "fr": "Bienvenue! 🌟 Comment puis-je vous aider aujourd'hui? Vous pouvez commander de la nourriture, consulter le menu ou vous renseigner sur les offres.",
}

# ==============================================
# 📋 GOODBYE RESPONSES
# ==============================================

GOODBYE_RESPONSES: ResponseMap = {
    "ar": "مع السلامة! 👋 نتمنى أن نراك مجدداً، في أي وقت تحتاج مساعدة نحن هنا.",
    "en": "Goodbye! 👋 We hope to see you again, anytime you need help we are here.",
    "fr": "Au revoir! 👋 Nous espérons vous revoir, à tout moment si vous avez besoin d'aide nous sommes là.",
}

# ==============================================
# 📋 HELP RESPONSES
# ==============================================

HELP_RESPONSES: ResponseMap = {
    "ar": """
📚 **المساعدة المتاحة:**

1. **عرض المطاعم** - اكتب "المطاعم" أو "المنيو"
2. **طلب طعام** - اكتب "أريد طلب" أو "اطلب"
3. **تتبع طلب** - اكتب "تتبع الطلب" مع رقم الطلب
4. **إلغاء طلب** - اكتب "إلغاء الطلب" مع رقم الطلب
5. **الأسعار** - اكتب "سعر" + اسم المنتج
6. **العروض** - اكتب "العروض" أو "عروض"
7. **الشكوى** - اكتب وصف المشكلة؛ اختر المطعم أو أرفق رقم طلب

يمكن تعديل كمية عنصر موجود فقط إذا كان الطلب قيد الانتظار. يتم تسجيل الشكوى بعد تأكيدك.
""",
    "en": """
📚 **Available Help:**

1. **View Restaurants** - Type "restaurants" or "menu"
2. **Order Food** - Type "I want to order" or "order"
3. **Track Order** - Type "track order" with order number
4. **Cancel Order** - Type "cancel order" with order number
5. **Prices** - Type "price" + product name
6. **Offers** - Type "offers" or "deals"
7. **Complaint** - Describe the issue; select a restaurant or include an order number

You can change the quantity of an existing item only while an order is pending. A complaint is registered after your confirmation.
""",
    "fr": """
📚 **Aide Disponible:**

1. **Afficher les restaurants** - Tapez "restaurants" ou "menu"
2. **Commander de la nourriture** - Tapez "je veux commander" ou "commander"
3. **Suivre une commande** - Tapez "suivre la commande" avec le numéro de commande
4. **Annuler une commande** - Tapez "annuler la commande" avec le numéro de commande
5. **Prix** - Tapez "prix" + nom du produit
6. **Offres** - Tapez "offres" ou "promotions"
7. **Réclamation** - Décrivez le problème ; choisissez un restaurant ou indiquez un numéro de commande

Vous pouvez modifier la quantité d'un article existant uniquement si la commande est en attente. Une réclamation est enregistrée après votre confirmation.
""",
}

# ==============================================
# 📋 ERROR RESPONSES
# ==============================================

ERROR_RESPONSES: ResponseMap = {
    "ar": "آسف، لم أفهم طلبك. يمكنك كتابة 'مساعدة' لمعرفة الخدمات المتاحة.",
    "en": "Sorry, I didn't understand your request. You can type 'help' to see available services.",
    "fr": "Désolé, je n'ai pas compris votre demande. Vous pouvez taper 'aide' pour voir les services disponibles.",
}

# ==============================================
# 🛠️ UTILITY FUNCTIONS
# ==============================================

# ==============================================
# GET PROMPT
# ==============================================

def get_prompt(
    prompts: PromptMap,
    lang: str,
    **kwargs,
) -> str:
    """
    الحصول على النص المطلوب باللغة المحددة مع تنسيق المتغيرات.
    
    Args:
        prompts: قاموس النصوص
        lang: كود اللغة (ar, en, fr)
        **kwargs: المتغيرات للتنسيق
        
    Returns:
        النص المطلوب
    """
    logger.debug(
        "get_prompt_called",
        extra={
            "lang": lang,
            "prompts_keys": list(prompts.keys()),
        },
    )

    template = prompts.get(lang, prompts.get("ar", ""))

    if kwargs:
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.warning(
                "prompt_formatting_error",
                extra={
                    "lang": lang,
                    "missing_key": str(e),
                    "kwargs": kwargs,
                },
            )
            return template

    return template


# ==============================================
# GET RESPONSE
# ==============================================

def get_response(
    responses: ResponseMap,
    lang: str,
) -> str:
    """
    الحصول على الرد المطلوب باللغة المحددة.
    
    Args:
        responses: قاموس الردود
        lang: كود اللغة (ar, en, fr)
        
    Returns:
        الرد المطلوب
    """
    logger.debug(
        "get_response_called",
        extra={
            "lang": lang,
            "responses_keys": list(responses.keys()),
        },
    )

    return responses.get(lang, responses.get("ar", ""))


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "SYSTEM_PROMPTS",
    "INTENT_CLASSIFICATION_PROMPTS",
    "RESPONSE_GENERATION_PROMPTS",
    "GREETING_RESPONSES",
    "GOODBYE_RESPONSES",
    "HELP_RESPONSES",
    "ERROR_RESPONSES",
    "get_prompt",
    "get_response",
]