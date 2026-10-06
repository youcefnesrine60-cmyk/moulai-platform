# MoulAI Platform — Agent-as-a-Service

[![License: CC BY-NC-ND 4.0](https://img.shields.io/badge/License-CC_BY--NC--ND_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-nd/4.0/)
[![Python 3.14+](https://img.shields.io/badge/Python-3.14+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-red.svg)](https://redis.io/)
[![Tests](https://img.shields.io/badge/Tests-45%2F45%20passed-brightgreen.svg)](https://github.com/youcefnesrine60-cmyk/moulai-platform)

## Overview

**MoulAI** is a personal SaaS project focused on **Agent-as-a-Service** and the practical integration of AI agents into business workflows.

The platform is being developed as a multi-tenant architecture intended to support multiple business domains, including restaurants, pharmacies, clinics and retail.

The project explores backend engineering, API design, database architecture, multilingual natural language processing, AI agent integration, automated testing and SaaS architecture.

> **Project status:** MoulAI is under active development. The repository documents the current implementation and ongoing engineering work.

## Technology Stack

| Area | Technologies |
| --- | --- |
| Backend | Python 3.14+, FastAPI, SQLAlchemy, Pydantic V2 |
| Database | PostgreSQL 16+, Alembic |
| Caching | Redis 7.0+ |
| AI integration | OpenAI API, DeepSeek API |
| Containerization | Docker, Docker Compose |
| Deployment | Render |
| Testing | Pytest, Pytest-Asyncio, Pytest-Cov |
| Version control | Git, GitHub |

## Architecture and Current Capabilities

### Multi-tenant platform

- Multi-tenant architecture with data isolation
- RESTful API layer
- Database architecture based on PostgreSQL and SQLAlchemy
- Repository and service layers
- Authentication and session management
- Redis-based caching
- Database migrations with Alembic

### AI Agent Core

- Multilingual language detection for Arabic, English and French
- 13 intent types
- 10 entity types
- 12 registered action handlers with confirmation handling
- `modify_order` supports changing the quantity of an existing item on pending orders; `complaint` creates an open, restaurant-scoped ticket linked to the customer and optionally to one of their orders, after confirmation
- Session, context and conversation-history management
- AI-assisted classification with fallback pattern matching
- Integration with OpenAI and DeepSeek APIs

Intent recognition does not imply full workflow support. Modify Order is limited to quantities of existing items on pending orders; complaint tickets are persisted as open records and still need a restaurant-side review/handling workflow.

### Security

- JWT authentication
- Password hashing with bcrypt
- Rate limiting and abuse-prevention mechanisms
- Session management
- Redis-backed application services

## Testing

The repository currently includes a restaurant API test suite with **45/45 tests passing**.

Test suites include:

- Restaurant operations: 16 tests
- Restaurant groups: 4 tests
- Restaurant branches: 12 tests
- Restaurant metrics: 5 tests
- Order counter: 4 tests
- Payment settings: 4 tests

### Running tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app

# Run the restaurant test suite
pytest tests/api/v1/restaurant/test_restaurants.py -v
```

## Project Structure

```
moulai-platform/
├── app/
│   ├── agent/          # AI Agent Core
│   │   ├── language/   # Language Detection
│   │   ├── nlu/        # Natural Language Understanding
│   │   ├── executor/   # Action Execution
│   │   ├── memory/     # Memory Management
│   │   └── prompts/    # Prompt Templates
│   ├── api/            # API Endpoints
│   │   └── v1/
│   ├── core/           # Core Components
│   ├── models/         # Database Models
│   ├── repositories/   # Data Access Layer
│   ├── schemas/        # Pydantic Schemas
│   └── services/       # Business Logic
├── tests/              # Automated Tests
├── alembic/            # Database Migrations
├── README.md
└── LICENSE
```

## Project Metrics

The current implementation includes:

| Metric | Current value |
| --- | ---: |
| SQLAlchemy models | 33 |
| Database tables | 41 |
| Services | 17+ |
| API endpoints | 14+ |
| Pydantic schema files | 23+ |
| Automated tests | 45 |
| Database migrations | 17+ |
| Supported languages | 3 |

These figures describe the current repository state and may change as development continues.

## Development Roadmap

### Current foundation

- Core project architecture
- Database schema and models
- Repository and service layers
- REST API layer
- Pydantic schemas
- AI Agent Core
- Restaurant API
- Automated testing

### In progress and planned

- Telegram integration
- Web chat integration
- WhatsApp integration
- Management dashboard
- Analytics and reporting
- Subscription and billing capabilities
- Additional business verticals
- Performance monitoring and optimization

## Quick Start

### Prerequisites

- Python 3.14+
- PostgreSQL 16+
- Redis 7.0+
- Docker (optional)

### Installation

```bash
# Clone the repository
git clone https://github.com/youcefnesrine60-cmyk/moulai-platform.git
cd moulai-platform

# Create a virtual environment
python -m venv .venv

# Activate it
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Apply database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload
```

### Environment configuration

Create a local `.env` file from `.env.example` and provide your own configuration values.

Example structure:

```env
DATABASE_URL=your-database-url
REDIS_URL=your-redis-url

OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=your-ai-base-url
AI_MODEL=your-ai-model

SECRET_KEY=your-secret-key
BOT_TOKEN=your-telegram-bot-token
```

Do not commit secrets, API keys, tokens or private configuration files to the repository.

## Author

**Nesrine YOUCEF**

- GitHub: https://github.com/youcefnesrine60-cmyk
- LinkedIn: https://linkedin.com/in/nesrine-youcef-data-engineer

## License

This project is licensed under the **Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International License**.

- You may view, fork and study the code under the terms of the license.
- Commercial use is not permitted under this license.
- Derivative works are not permitted under this license.

See [LICENSE](LICENSE) for the complete terms.

## Acknowledgments

MoulAI is built with and benefits from the following technologies and projects:

- FastAPI
- SQLAlchemy
- Pydantic
- PostgreSQL
- Redis
- OpenAI API
- DeepSeek API

---

*MoulAI is a personal project under active development.*
