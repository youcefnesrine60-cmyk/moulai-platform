# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🤖 AGENT MODEL
# نظام الوكيل الذكي - قلب المنصة
# يدير الوكلاء والقنوات والمحادثات والرسائل
# ==============================================

from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .base import BaseModel

# ==============================================
# 🧩 TYPES
# ==============================================

JSONDict = Dict[str, Any]

# ==============================================
# 🤖 AGENT
# ==============================================

class Agent(BaseModel):
    """
    نموذج الوكيل الذكي - قلب المنصة
    
    يدير:
        - إعدادات الوكيل الأساسية (الاسم، اللغة، النبرة)
        - إعدادات الذكاء الاصطناعي (النموذج، درجة الحرارة)
        - حالة النشاط
        - العلاقات مع المطعم والقنوات والمحادثات
    
    Attributes:
        restaurant_id: معرف المطعم (ForeignKey)
        name: اسم الوكيل
        description: وصف الوكيل
        language: اللغة (ar, fr, en)
        tone: النبرة (professional, casual, friendly)
        is_active: حالة النشاط
        config: إعدادات الوكيل (JSON)
        ai_config: إعدادات الذكاء الاصطناعي (JSON)
        restaurant: علاقة مع نموذج Restaurant
        channels: قائمة القنوات
        conversations: قائمة المحادثات
    """
    __tablename__ = "agents"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    restaurant_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف المطعم",
    )
    name = Column(
        String(100),
        nullable=False,
        default="My Assistant",
        comment="اسم الوكيل",
    )
    description = Column(
        Text,
        comment="وصف الوكيل",
    )
    language = Column(
        String(10),
        default="ar",
        comment="اللغة: ar, fr, en",
    )
    tone = Column(
        String(50),
        default="professional",
        comment="النبرة: professional, casual, friendly",
    )
    is_active = Column(
        Boolean,
        default=True,
        comment="حالة النشاط",
    )
    
    # ==========================================
    # ⚙️ CONFIGURATIONS
    # ==========================================
    
    config = Column(
        JSON,
        default={
            "auto_reply": True,
            "upselling_enabled": True,
            "max_conversation_turns": 50,
            "fallback_response": "عذراً، لم أفهم طلبك. هل يمكنك إعادة الصياغة؟",
            "greeting_message": "مرحباً! كيف يمكنني مساعدتك اليوم؟",
        },
        comment="إعدادات الوكيل",
    )
    ai_config = Column(
        JSON,
        default={
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 500,
            "system_prompt": "أنت مساعد ذكي لمطعم...",
        },
        comment="إعدادات الذكاء الاصطناعي",
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    restaurant = relationship(
        "Restaurant",
        back_populates="agents",
        lazy="selectin",
        # comment="المطعم",
    )
    channels = relationship(
        "Channel",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة القنوات",
    )
    conversations = relationship(
        "Conversation",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة المحادثات",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على المعرف والاسم ومعرف المطعم
        """
        return f"<Agent(id={self.id}, name={self.name}, restaurant_id={self.restaurant_id})>"


# ==============================================
# 📡 CHANNEL
# ==============================================

class Channel(BaseModel):
    """
    نموذج القناة - للتواصل مع العملاء
    
    يدير:
        - نوع القناة (telegram, whatsapp, web, messenger, api)
        - إعدادات القناة (webhook, token, phone)
        - حالة النشاط
        - العلاقات مع الوكيل والمحادثات
    
    Attributes:
        agent_id: معرف الوكيل (ForeignKey)
        type: نوع القناة
        name: اسم القناة
        is_active: حالة النشاط
        config: إعدادات القناة (JSON)
        agent: علاقة مع نموذج Agent
        conversations: قائمة المحادثات
    """
    __tablename__ = "channels"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    agent_id = Column(
        Integer,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف الوكيل",
    )
    type = Column(
        String(50),
        nullable=False,
        comment="نوع القناة: telegram, whatsapp, web, messenger, api",
    )
    name = Column(
        String(100),
        nullable=False,
        comment="اسم القناة",
    )
    is_active = Column(
        Boolean,
        default=True,
        comment="حالة النشاط",
    )
    
    # ==========================================
    # ⚙️ CONFIGURATIONS
    # ==========================================
    
    config = Column(
        JSON,
        default={
            "webhook_url": None,
            "api_token": None,
            "phone_number": None,
        },
        comment="إعدادات القناة",
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    agent = relationship(
        "Agent",
        back_populates="channels",
        lazy="selectin",
        # comment="الوكيل",
    )
    conversations = relationship(
        "Conversation",
        back_populates="channel",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة المحادثات",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على المعرف والنوع ومعرف الوكيل
        """
        return f"<Channel(id={self.id}, type={self.type}, agent_id={self.agent_id})>"


# ==============================================
# 💬 CONVERSATION
# ==============================================

class Conversation(BaseModel):
    """
    نموذج المحادثة - تتبع التفاعلات
    
    يدير:
        - بيانات المستخدم (user_id, user_name)
        - سياق المحادثة (الطلب الحالي، الخطوة، النوايا)
        - حالة النشاط
        - العلاقات مع الوكيل والقناة والرسائل
    
    Attributes:
        agent_id: معرف الوكيل (ForeignKey)
        channel_id: معرف القناة (ForeignKey)
        user_id: معرف المستخدم من القناة
        user_name: اسم المستخدم
        is_active: حالة النشاط
        context: سياق المحادثة (JSON)
        agent: علاقة مع نموذج Agent
        channel: علاقة مع نموذج Channel
        messages: قائمة الرسائل
    """
    __tablename__ = "conversations"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    agent_id = Column(
        Integer,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف الوكيل",
    )
    channel_id = Column(
        Integer,
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف القناة",
    )
    user_id = Column(
        String(255),
        nullable=False,
        comment="معرف المستخدم من القناة (chat_id)",
    )
    user_name = Column(
        String(255),
        comment="اسم المستخدم",
    )
    is_active = Column(
        Boolean,
        default=True,
        comment="حالة النشاط",
    )
    
    # ==========================================
    # 📊 CONTEXT
    # ==========================================
    
    context = Column(
        JSON,
        default={
            "current_order": None,
            "current_step": None,
            "intent_history": [],
            "last_intent": None,
            "entities": {},
        },
        comment="سياق المحادثة",
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    agent = relationship(
        "Agent",
        back_populates="conversations",
        lazy="selectin",
        # comment="الوكيل",
    )
    channel = relationship(
        "Channel",
        back_populates="conversations",
        lazy="selectin",
        # comment="القناة",
    )
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة الرسائل",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على المعرف ومعرف المستخدم ومعرف الوكيل
        """
        return f"<Conversation(id={self.id}, user_id={self.user_id}, agent_id={self.agent_id})>"


# ==============================================
# 💬 MESSAGE
# ==============================================

class Message(BaseModel):
    """
    نموذج الرسالة - تتبع كل رسالة
    
    يدير:
        - محتوى الرسالة ودور المرسل (user, assistant, system)
        - تحليل الرسالة (النوايا، الثقة، الكيانات)
        - البيانات الوصفية
        - العلاقة مع المحادثة
    
    Attributes:
        conversation_id: معرف المحادثة (ForeignKey)
        role: دور المرسل (user, assistant, system)
        content: محتوى الرسالة
        intent: نية الرسالة
        confidence: درجة الثقة
        entities: الكيانات المستخرجة (JSON)
        meta_data: بيانات وصفية (JSON)
        conversation: علاقة مع نموذج Conversation
    """
    __tablename__ = "messages"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف المحادثة",
    )
    role = Column(
        String(20),
        nullable=False,
        comment="دور المرسل: user, assistant, system",
    )
    content = Column(
        Text,
        nullable=False,
        comment="محتوى الرسالة",
    )
    
    # ==========================================
    # 🧠 ANALYSIS
    # ==========================================
    
    intent = Column(
        String(100),
        comment="نية الرسالة",
    )
    confidence = Column(
        Float,
        comment="درجة الثقة",
    )
    entities = Column(
        JSON,
        default={},
        comment="الكيانات المستخرجة",
    )
    
    # ==========================================
    # 📊 meta_data
    # ==========================================
    
    meta_data = Column(
        JSON,
        default={},
        comment="بيانات وصفية",
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    conversation = relationship(
        "Conversation",
        back_populates="messages",
        lazy="selectin",
        # comment="المحادثة",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على المعرف والدور والنية
        """
        return f"<Message(id={self.id}, role={self.role}, intent={self.intent})>"