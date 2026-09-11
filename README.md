# 🚀 MoulAI™ Platform - Agent-as-a-Service

[![License: CC BY-NC-ND 4.0](https://img.shields.io/badge/License-CC_BY--NC--ND_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-nd/4.0/)
[![Python 3.14+](https://img.shields.io/badge/Python-3.14+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-red.svg)](https://redis.io/)
[![Tests](https://img.shields.io/badge/Tests-16%2F16%20passed-brightgreen.svg)]()
[![Pydantic](https://img.shields.io/badge/Pydantic%20V2-0%20warnings-brightgreen.svg)]()

---

## 📖 Description

**MoulAI** is an ambitious personal project to build a multi-sector **Agent-as-a-Service** platform. It enables businesses (restaurants, pharmacies, clinics, retail stores) to seamlessly integrate intelligent AI assistants into their operations, automating customer interactions and business management.

> 🇫🇷 **MoulAI** est un projet personnel ambitieux visant à construire une plateforme **Agent-as-a-Service** multisectorielle. Elle permet aux entreprises d'intégrer facilement des assistants IA intelligents dans leurs opérations.

> 🇩🇿 **مولاي** هو مشروع شخصي طموح لبناء منصة **الوكيل كخدمة** متعددة القطاعات، تمكن الشركات من دمج مساعدين أذكياء يعملون بالذكاء الاصطناعي في عملياتهم بسهولة.

This project demonstrates my expertise in designing and implementing a complete, scalable, and secure architecture using modern technologies.

---

## 🛠️ Technologies Used

| Category | Technologies |
|----------|--------------|
| **Backend** | Python 3.14+, FastAPI, SQLAlchemy, Pydantic V2 |
| **Database** | PostgreSQL 16+, Alembic Migrations |
| **Caching** | Redis 7.0+ |
| **AI/ML** | OpenAI API, DeepSeek API |
| **Containerization** | Docker, Docker Compose |
| **Deployment** | Render |
| **Version Control** | Git, GitHub |
| **Testing** | Pytest, Pytest-Asyncio, Pytest-Cov |

---

## ✨ Key Features

### 🏗️ Core Platform
- **Multi-tenant architecture** with strict data isolation
- **Complete RESTful APIs** (14 endpoints)
- **Comprehensive database** (34 tables, 22 models)
- **Production-ready deployment** on Render
- **Clean code** with **0 Pydantic warnings** (fully migrated to Pydantic V2)

### 🤖 AI Agent Core
- **Multilingual language detection** (Arabic, English, French)
- **13 intent types** (order, menu, restaurants, modify, cancel, track, price, offers, complaint, help, greeting, goodbye)
- **10 entity types** (products, quantities, prices, order IDs, phone numbers, addresses, dates, times, units, customer names)
- **12 executable actions** with confirmation system
- **Memory management** (sessions, context, conversation history)
- **AI-powered classification** with fallback pattern matching

### 🔐 Security & Performance
- **JWT authentication** and session management
- **Password hashing** (bcrypt)
- **Rate limiting** and abuse prevention
- **Redis caching** for performance optimization

---

## 📊 Project Status

| Component | Completion | Status |
|-----------|------------|--------|
| Infrastructure | 100% | Complete |
| Database | 100% | Complete |
| Repositories | 100% | Complete |
| Services | 100% | Complete |
| API Endpoints | 100% | Complete |
| Schemas | 100% | Complete (0 warnings) |
| AI Agent Core | 100% | Complete |
| Restaurant Tests | 100% | Complete (16/16) |
| Channels | 0% | Pending |
| Dashboard | 0% | Pending |
| Subscriptions | 80% | In Progress |
| Verticals | 20% | In Progress |

### Overall Progress: 85%

```
┌─────────────────────────────────────────────────────────────────┐
│  🎯 Overall Completion: 85%                                    │
├─────────────────────────────────────────────────────────────────┤
│  ████████████████████████████████████████████████ 100%  Infrastructure │
│  ████████████████████████████████████████████████ 100%  Database        │
│  ████████████████████████████████████████████████ 100%  Repositories    │
│  ████████████████████████████████████████████████ 100%  Services        │
│  ████████████████████████████████████████████████ 100%  API Endpoints   │
│  ████████████████████████████████████████████████ 100%  Schemas         │
│  ████████████████████████████████████████████████ 100%  AI Agent Core   │
│  ████████████████████████████████████████████████ 100%  Restaurant Tests│
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   0%  Channels        │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   0%  Dashboard       │
│  ████████████████████████████████████░░░░░░░░░░  80%  Subscriptions   │
│  ██████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  20%  Verticals       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗺️ Roadmap

### Phase 1: Foundation ✅ Complete
- Project setup and architecture design
- Database schema and models
- Core infrastructure (FastAPI, SQLAlchemy, PostgreSQL)

### Phase 2: Business Logic ✅ Complete
- Repository layer (data access)
- Service layer (business logic)
- Complete RESTful APIs
- Pydantic schemas

### Phase 3: AI Agent Core ✅ Complete
- Multilingual language detection
- Intent classification (13 intents)
- Entity extraction (10 entity types)
- Action execution (12 actions)
- Memory management
- AI integration (OpenAI/DeepSeek)
- Comprehensive testing

### Phase 4: Restaurant API & Tests ✅ Complete
- Restaurant CRUD operations
- Restaurant Groups management
- Restaurant Branches management
- Restaurant Metrics tracking
- Order Counter management
- Payment Settings management
- 16/16 tests passing ✅

### Phase 5: Pydantic V2 Migration ✅ Complete
- Migrated all schemas to Pydantic V2
- Replaced `example=` with `json_schema_extra`
- Replaced `class Config` with `ConfigDict`
- 0 warnings remaining ✅

### Phase 6: Channels 🔄 Next
- [ ] Telegram Bot integration
- [ ] Web Chat integration
- [ ] WhatsApp integration

### Phase 7: Dashboard ⏳ Pending
- [ ] Restaurant management interface
- [ ] Order management interface
- [ ] Analytics and reporting

### Phase 8: Subscriptions ⏳ Pending
- [ ] Payment gateways (Stripe, PayPal)
- [ ] Plan management (Basic, Pro, Enterprise)
- [ ] Billing and invoicing

### Phase 9: Verticals ⏳ Pending
- [ ] Restaurant template ✅ Complete
- [ ] Pharmacy template
- [ ] Clinic template

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app

# Run specific test suite
pytest tests/api/v1/restaurant/test_restaurants.py -v

# Current test results:
# ✅ 16/16 passed for Restaurant API
# ✅ 0 Pydantic warnings
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.14+
- PostgreSQL 16+
- Redis 7.0+
- Docker (optional)

### Installation

```bash
# Clone the repository
git clone https://github.com/youcefnesrine60-cmyk/dzeatery-bot.git
cd dzeatery-bot

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

### Environment Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db

# Redis
REDIS_URL=redis://localhost:6379/0

# AI
OPENAI_API_KEY=My-api-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
AI_MODEL=deepseek-chat

# Security
SECRET_KEY=your-secret-key

# Telegram
BOT_TOKEN=your-telegram-bot-token
```

---

## 📁 Project Structure

```
MoulAI Platform/
├── app/
│   ├── agent/          # AI Agent Core
│   │   ├── language/   # Language Detection
│   │   ├── nlu/        # Natural Language Understanding
│   │   ├── executor/   # Action Execution
│   │   ├── memory/     # Memory Management
│   │   └── prompts/    # Prompt Templates
│   ├── api/            # API Endpoints (14 endpoints)
│   │   └── v1/
│   │       └── restaurant/  # Restaurant API
│   │           ├── restaurants/     # CRUD operations
│   │           ├── groups/          # Groups management
│   │           ├── branches/        # Branches management
│   │           ├── metrics/         # Metrics tracking
│   │           ├── order_counter/   # Order counter
│   │           └── payment_setting/ # Payment settings
│   ├── core/           # Core Components
│   ├── models/         # Database Models (22 models)
│   ├── repositories/   # Data Access Layer
│   ├── schemas/        # Pydantic Schemas (100% V2 compliant)
│   └── services/       # Business Logic (17 services)
├── tests/              # Tests
│   └── api/
│       └── v1/
│           └── restaurant/  # Restaurant tests (16/16 passed)
├── alembic/            # Database Migrations
├── README.md           # Documentation
└── LICENSE             # License
```

---

## 👩‍💻 Author

**Youcef Nesrine**

- GitHub: [youcefnesrine60-cmyk](https://github.com/youcefnesrine60-cmyk)
- Email: youcefnesrine60@gmail.com
- LinkedIn: [linkedin.com/in/youcef-nesrine-66a92a431](http://www.linkedin.com/in/youcef-nesrine-66a92a431)

---

## 📄 License

This project is licensed under the **Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International License**.

- ✅ You are free to **view, fork, and study** the code.
- ❌ You may **NOT** use it for **commercial purposes**.
- ❌ You may **NOT** modify or create derivative works.

For more details, see the full [LICENSE](LICENSE) file.

---

## 🙏 Acknowledgments

- **FastAPI** - For the amazing web framework
- **SQLAlchemy** - For the powerful ORM
- **Pydantic** - For the robust data validation
- **OpenAI/DeepSeek** - For the AI capabilities

---

## 📬 Contact

If you have any questions or would like to discuss this project, feel free to reach out!

---

*Made with ❤️ by Youcef Nesrine*