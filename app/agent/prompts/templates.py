# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 📝 PROMPT TEMPLATES
# قوالب الـ Prompts للوكيل الذكي (متعددة اللغات)
# ==============================================

from typing import (
    Any,
    Dict,
    Optional,
)

from app.core.logger import logger

# ==============================================
# 🧩 TYPES
# ==============================================

PromptMap = Dict[str, str]
MultiLangPromptMap = Dict[str, Dict[str, str]]
LanguageCode = str

# ==============================================
# 🌍 SUPPORTED LANGUAGES
# ==============================================

SUPPORTED_LANGUAGES: Dict[LanguageCode, str] = {
    "ar": "العربية",
    "en": "English",
    "fr": "Français",
}

DEFAULT_LANGUAGE: LanguageCode = "ar"

# ==============================================
# 🧠 SYSTEM PROMPTS (متعددة اللغات)
# ==============================================

SYSTEM_PROMPTS: PromptMap = {
    "ar": """
أنت وكيل ذكي يعمل على منصة "مولاي" (MoulAI)، وهي منصة Agent-as-a-Service لإدارة المطاعم والمتاجر.

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
- تعديل الطلبات وتسجيل الشكاوى غير متاحين حالياً؛ لا تدّعِ إتمامهما أو إنشاء بلاغ، وأخبر العميل بذلك بوضوح
- إذا لم تعرف الإجابة، اعتذر واطلب توضيحاً
- لا تقدم معلومات غير دقيقة
- احرص على مساعدة العميل بأفضل طريقة ممكنة

📌 **تنسيق الرد:**
- كن مختصراً وواضحاً
- استخدم القوائم النقطية للعروض والمنتجات
- قدم خيارات متعددة للعميل
""",
    "en": """
You are an intelligent agent working on the "MoulAI" platform, an Agent-as-a-Service platform for managing restaurants and stores.

📌 **Your Mission:**
Help customers order food, inquire about products, manage orders, and resolve customer issues.

📌 **Your Permissions:**
1. View the list of restaurants and products
2. Order meals/products
3. Cancel orders
4. Inquire about prices and offers
5. Provide help and support

📌 **Behavior Guidelines:**
- Be polite and respectful
- Use the user's language
- Order modifications and complaint ticket creation are not available yet; never claim they were completed, and tell the customer clearly
- If you don't know the answer, apologize and ask for clarification
- Don't provide inaccurate information
- Help the customer in the best way possible

📌 **Response Format:**
- Be concise and clear
- Use bullet points for offers and products
- Provide multiple options to the customer
""",
    "fr": """
Vous êtes un agent intelligent travaillant sur la plateforme "MoulAI", une plateforme Agent-as-a-Service pour la gestion des restaurants et des magasins.

📌 **Votre Mission:**
Aider les clients à commander de la nourriture, s'informer sur les produits, gérer les commandes et résoudre les problèmes des clients.

📌 **Vos Autorisations:**
1. Afficher la liste des restaurants et des produits
2. Commander des repas/produits
3. Annuler des commandes
4. S'informer sur les prix et les offres
5. Fournir de l'aide et du soutien

📌 **Règles de Comportement:**
- Soyez poli et respectueux
- Utilisez la langue de l'utilisateur
- La modification des commandes et la création de tickets de réclamation ne sont pas encore disponibles ; ne prétendez jamais qu'elles ont été effectuées et informez clairement le client
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
# 🎯 INTENT CLASSIFICATION PROMPTS (متعددة اللغات)
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
# 💬 RESPONSE GENERATION PROMPTS (متعددة اللغات)
# ==============================================

RESPONSE_GENERATION_PROMPTS: PromptMap = {
    "ar": """
أنت وكيل ذكي في منصة "مولاي" (MoulAI).

📌 **نية المستخدم:** {intent}
📌 **السياق:** {context}
📌 **البيانات المستخرجة:** {entities}
📌 **نتيجة الإجراء:** {action_result}

**أنشئ رداً طبيعياً ومفيداً للمستخدم بلغته.**

المستخدم قال: {user_message}

الرد:
""",
    "en": """
You are an intelligent agent on the "MoulAI" platform.

📌 **User Intent:** {intent}
📌 **Context:** {context}
📌 **Extracted Data:** {entities}
📌 **Action Result:** {action_result}

**Create a natural and helpful response for the user in their language.**

User said: {user_message}

Response:
""",
    "fr": """
Vous êtes un agent intelligent sur la plateforme "MoulAI".

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
# 🔍 ENTITY EXTRACTION PROMPTS (متعددة اللغات)
# ==============================================

ENTITY_EXTRACTION_PROMPTS: PromptMap = {
    "ar": """
استخرج الكيانات التالية من النص:
- product_name: اسم المنتج أو الطبق
- quantity: الكمية (رقم)
- unit: وحدة القياس (kg, g, piece, etc.)
- price: السعر (رقم)
- order_id: رقم الطلب
- customer_name: اسم العميل
- customer_phone: رقم الهاتف
- delivery_address: عنوان التوصيل
- date: التاريخ
- time: الوقت

**النص:** {text}
**اللغة:** {language}

أخرج النتيجة بصيغة JSON:
[
    {{
        "type": "product_name",
        "value": "بيتزا مارغريتا",
        "confidence": 0.95
    }},
    {{
        "type": "quantity",
        "value": 2,
        "confidence": 0.9
    }}
]
""",
    "en": """
Extract the following entities from the text:
- product_name: Product or dish name
- quantity: Quantity (number)
- unit: Unit of measurement (kg, g, piece, etc.)
- price: Price (number)
- order_id: Order number
- customer_name: Customer name
- customer_phone: Phone number
- delivery_address: Delivery address
- date: Date
- time: Time

**Text:** {text}
**Language:** {language}

Output the result in JSON format:
[
    {{
        "type": "product_name",
        "value": "Margherita Pizza",
        "confidence": 0.95
    }},
    {{
        "type": "quantity",
        "value": 2,
        "confidence": 0.9
    }}
]
""",
    "fr": """
Extrayez les entités suivantes du texte:
- product_name: Nom du produit ou du plat
- quantity: Quantité (nombre)
- unit: Unité de mesure (kg, g, pièce, etc.)
- price: Prix (nombre)
- order_id: Numéro de commande
- customer_name: Nom du client
- customer_phone: Numéro de téléphone
- delivery_address: Adresse de livraison
- date: Date
- time: Heure

**Texte:** {text}
**Langue:** {language}

Sortez le résultat au format JSON:
[
    {{
        "type": "product_name",
        "value": "Pizza Margherita",
        "confidence": 0.95
    }},
    {{
        "type": "quantity",
        "value": 2,
        "confidence": 0.9
    }}
]
""",
}

# ==============================================
# 📋 CONFIRMATION PROMPTS (متعددة اللغات)
# ==============================================

CONFIRMATION_PROMPTS: PromptMap = {
    "ar": """
📋 **تأكيد {action_name}**

{details}

هل تريد تأكيد العملية؟ (نعم/لا)
""",
    "en": """
📋 **Confirm {action_name}**

{details}

Do you want to confirm? (Yes/No)
""",
    "fr": """
📋 **Confirmation de {action_name}**

{details}

Voulez-vous confirmer ? (Oui/Non)
""",
}

# ==============================================
# ❌ ERROR PROMPTS (متعددة اللغات)
# ==============================================

ERROR_PROMPTS: MultiLangPromptMap = {
    "unknown_intent": {
        "ar": "آسف، لم أفهم طلبك. يمكنك كتابة 'مساعدة' لمعرفة الخدمات المتاحة.",
        "en": "Sorry, I didn't understand your request. You can type 'help' to see available services.",
        "fr": "Désolé, je n'ai pas compris votre demande. Vous pouvez taper 'aide' pour voir les services disponibles.",
    },
    "action_failed": {
        "ar": "حدث خطأ أثناء تنفيذ الطلب. يرجى المحاولة مرة أخرى.",
        "en": "An error occurred while executing the request. Please try again.",
        "fr": "Une erreur est survenue lors de l'exécution de la demande. Veuillez réessayer.",
    },
    "order_modification_not_supported": {
        "ar": "تعديل الطلبات عبر المحادثة غير متاح حالياً. لم يتم تغيير الطلب.",
        "en": "Order modifications are not available yet. The order was not changed.",
        "fr": "La modification des commandes n'est pas encore disponible. La commande n'a pas été modifiée.",
    },
    "complaint_registration_not_supported": {
        "ar": "تسجيل الشكاوى غير متاح حالياً. لم يتم إنشاء بلاغ.",
        "en": "Complaint registration is not available yet. No ticket was created.",
        "fr": "L'enregistrement des réclamations n'est pas encore disponible. Aucun ticket n'a été créé.",
    },
    "not_found": {
        "ar": "عذراً، لم نتمكن من العثور على ما تبحث عنه.",
        "en": "Sorry, we couldn't find what you're looking for.",
        "fr": "Désolé, nous n'avons pas trouvé ce que vous cherchez.",
    },
    "invalid_input": {
        "ar": "البيانات التي أدخلتها غير صحيحة. يرجى التحقق والمحاولة مرة أخرى.",
        "en": "The data you entered is invalid. Please check and try again.",
        "fr": "Les données que vous avez saisies sont invalides. Veuillez vérifier et réessayer.",
    },
    "unauthorized": {
        "ar": "ليس لديك صلاحية للقيام بهذا الإجراء.",
        "en": "You don't have permission to perform this action.",
        "fr": "Vous n'avez pas la permission d'effectuer cette action.",
    },
    "timeout": {
        "ar": "انتهت مهلة الطلب. يرجى المحاولة مرة أخرى.",
        "en": "Request timed out. Please try again.",
        "fr": "La demande a expiré. Veuillez réessayer.",
    },
}

# ==============================================
# 🎉 SUCCESS PROMPTS (متعددة اللغات)
# ==============================================

SUCCESS_PROMPTS: MultiLangPromptMap = {
    "order_created": {
        "ar": "✅ تم إنشاء طلبك بنجاح! رقم الطلب: {order_id}",
        "en": "✅ Your order has been created successfully! Order ID: {order_id}",
        "fr": "✅ Votre commande a été créée avec succès! ID de commande: {order_id}",
    },
    "order_cancelled": {
        "ar": "❌ تم إلغاء طلبك بنجاح.",
        "en": "❌ Your order has been cancelled successfully.",
        "fr": "❌ Votre commande a été annulée avec succès.",
    },
    "order_tracked": {
        "ar": "📦 حالة طلبك: {status}",
        "en": "📦 Your order status: {status}",
        "fr": "📦 Statut de votre commande: {status}",
    },
    "price_found": {
        "ar": "💰 سعر {product_name}: {price} دج",
        "en": "💰 Price of {product_name}: {price} DA",
        "fr": "💰 Prix de {product_name}: {price} DA",
    },
    "offers_found": {
        "ar": "🎁 العروض المتاحة: {offers}",
        "en": "🎁 Available offers: {offers}",
        "fr": "🎁 Offres disponibles: {offers}",
    },
}

# ==============================================
# 📝 HELPER FUNCTIONS
# ==============================================

# ==============================================
# GET SYSTEM PROMPT
# ==============================================

def get_system_prompt(
    language: LanguageCode = "ar",
) -> str:
    """
    الحصول على System Prompt باللغة المطلوبة.
    
    Args:
        language: رمز اللغة (ar, en, fr)
        
    Returns:
        System Prompt
    """
    logger.debug(
        "get_system_prompt_called",
        extra={"language": language},
    )

    return SYSTEM_PROMPTS.get(language, SYSTEM_PROMPTS["ar"])


# ==============================================
# GET INTENT CLASSIFICATION PROMPT
# ==============================================

def get_intent_classification_prompt(
    language: LanguageCode = "ar",
) -> str:
    """
    الحصول على Intent Classification Prompt باللغة المطلوبة.
    
    Args:
        language: رمز اللغة (ar, en, fr)
        
    Returns:
        Intent Classification Prompt
    """
    logger.debug(
        "get_intent_classification_prompt_called",
        extra={"language": language},
    )

    return INTENT_CLASSIFICATION_PROMPTS.get(
        language,
        INTENT_CLASSIFICATION_PROMPTS["ar"],
    )


# ==============================================
# GET RESPONSE GENERATION PROMPT
# ==============================================

def get_response_generation_prompt(
    language: LanguageCode = "ar",
) -> str:
    """
    الحصول على Response Generation Prompt باللغة المطلوبة.
    
    Args:
        language: رمز اللغة (ar, en, fr)
        
    Returns:
        Response Generation Prompt
    """
    logger.debug(
        "get_response_generation_prompt_called",
        extra={"language": language},
    )

    return RESPONSE_GENERATION_PROMPTS.get(
        language,
        RESPONSE_GENERATION_PROMPTS["ar"],
    )


# ==============================================
# GET ENTITY EXTRACTION PROMPT
# ==============================================

def get_entity_extraction_prompt(
    language: LanguageCode = "ar",
) -> str:
    """
    الحصول على Entity Extraction Prompt باللغة المطلوبة.
    
    Args:
        language: رمز اللغة (ar, en, fr)
        
    Returns:
        Entity Extraction Prompt
    """
    logger.debug(
        "get_entity_extraction_prompt_called",
        extra={"language": language},
    )

    return ENTITY_EXTRACTION_PROMPTS.get(
        language,
        ENTITY_EXTRACTION_PROMPTS["ar"],
    )


# ==============================================
# GET CONFIRMATION PROMPT
# ==============================================

def get_confirmation_prompt(
    language: LanguageCode = "ar",
) -> str:
    """
    الحصول على Confirmation Prompt باللغة المطلوبة.
    
    Args:
        language: رمز اللغة (ar, en, fr)
        
    Returns:
        Confirmation Prompt
    """
    logger.debug(
        "get_confirmation_prompt_called",
        extra={"language": language},
    )

    return CONFIRMATION_PROMPTS.get(
        language,
        CONFIRMATION_PROMPTS["ar"],
    )


# ==============================================
# GET ERROR PROMPT
# ==============================================

def get_error_prompt(
    error_type: str,
    language: LanguageCode = "ar",
    **kwargs,
) -> str:
    """
    الحصول على Error Prompt باللغة المطلوبة.
    
    Args:
        error_type: نوع الخطأ
        language: رمز اللغة (ar, en, fr)
        **kwargs: المعاملات للتنسيق
        
    Returns:
        رسالة الخطأ المنسقة
    """
    logger.debug(
        "get_error_prompt_called",
        extra={
            "error_type": error_type,
            "language": language,
        },
    )

    error_dict = ERROR_PROMPTS.get(
        error_type,
        ERROR_PROMPTS["unknown_intent"],
    )
    template = error_dict.get(language, error_dict["ar"])

    return template.format(**kwargs) if kwargs else template


# ==============================================
# GET SUCCESS PROMPT
# ==============================================

def get_success_prompt(
    success_type: str,
    language: LanguageCode = "ar",
    **kwargs,
) -> str:
    """
    الحصول على Success Prompt باللغة المطلوبة.
    
    Args:
        success_type: نوع النجاح
        language: رمز اللغة (ar, en, fr)
        **kwargs: المعاملات للتنسيق
        
    Returns:
        رسالة النجاح المنسقة
    """
    logger.debug(
        "get_success_prompt_called",
        extra={
            "success_type": success_type,
            "language": language,
        },
    )

    success_dict = SUCCESS_PROMPTS.get(success_type)
    if success_dict is None:
        logger.warning(
            "unknown_success_prompt_type",
            extra={"success_type": success_type, "language": language},
        )
        return get_error_prompt("action_failed", language)

    template = success_dict.get(language, success_dict["ar"])

    return template.format(**kwargs) if kwargs else template


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [

    # Languages
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGUAGE",

    # System
    "SYSTEM_PROMPTS",
    "get_system_prompt",

    # Classification
    "INTENT_CLASSIFICATION_PROMPTS",
    "get_intent_classification_prompt",

    # Response
    "RESPONSE_GENERATION_PROMPTS",
    "get_response_generation_prompt",

    # Entity Extraction
    "ENTITY_EXTRACTION_PROMPTS",
    "get_entity_extraction_prompt",

    # Confirmation
    "CONFIRMATION_PROMPTS",
    "get_confirmation_prompt",

    # Error
    "ERROR_PROMPTS",
    "get_error_prompt",

    # Success
    "SUCCESS_PROMPTS",
    "get_success_prompt",
]