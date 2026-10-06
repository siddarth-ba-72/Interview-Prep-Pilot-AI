# CLAUDE.md — PrepPilot

**PrepPilot** is an AI-powered interview preparation platform that helps technical professionals master interview topics through three interactive learning modes: Learn (persistent chat), Test (AI-generated questions with reports), and Mock Interview (sequential Q&A with real-time evaluation).

---

## Project Overview & Features

### Core Application Modes

**1. Learn Mode (Chat-Based)**
- Interactive AI chat for personalized topic exploration
- AI asks clarifying questions about learning style and depth
- Users ask follow-up questions within a persistent chat session
- One chat per topic per user, resumable across sessions

**2. Test Mode (Knowledge Assessment)**
- AI generates mixed question sets (MCQs, descriptive, scenario-based)
- Users submit answers; AI evaluates in real-time
- Comprehensive test reports showing:
  - Areas of strength
  - Areas needing improvement
  - Actionable feedback
- Reports persisted and viewable from dashboard
- "Revisit" option redirects to Learn Mode chat for focused study

**3. Mock Interview Mode (Realistic Practice)**
- Sequential interview questions asked one at a time
- Users type detailed text responses
- Real-time AI evaluation of each answer
- Per-answer feedback identifying strengths and weaknesses
- Comprehensive interview report after completion
- "Revisit" option for targeted learning on weak areas

### User-Centric Features
- **User Data Isolation**: Each user sees only their own topics and progress
- **Persistent History**: All chats, test reports, and interview reports are saved
- **Flexible Access**: Users can revisit any previous conversation or report at any time
- **Google OAuth**: Sign up/login via Google or traditional email/password

---

## Technology Stack

### Frontend
```
React 18+              JavaScript UI framework with hooks
TypeScript 5.4+        Type-safe development
Redux Toolkit 2.2+     Global state (auth, UI mode, active topic)
React Query 5.4+       Server state (topics, reports, chat history)
React Router 6.2+      Client-side navigation
Axios 1.7+             HTTP client with JWT interceptor
Tailwind CSS 4.3+      Utility-first CSS framework
Vite 5.3+              Fast build tool with native TypeScript support
```

### Backend Services

All four services are Python 3.12 / FastAPI, each in its own folder at the repository root. They are plain async
FastAPI apps with Pydantic models and no ODM (raw PyMongo `AsyncMongoClient`), deliberately compatible with the
documents the legacy Spring services wrote.

**API Gateway** (`gateway/`)
```
FastAPI + httpx        Streaming reverse proxy (SSE-safe), CORS, route table
PyJWT                  JWT verification (HS256/384/512); injects X-User-Id / X-User-Email
```

**User Service** (`user-service/`)
```
FastAPI + PyMongo      Async REST API and MongoDB access
bcrypt (cost 12)       Password hashing (72-byte truncation, run in a threadpool)
PyJWT                  Access-token creation (claims: userId, email, iat, exp)
httpx                  Hand-rolled Google OAuth 2.0 authorization-code flow
```

**Topic Service** (`topic-service/`)
```
FastAPI + PyMongo      Async REST API and MongoDB access
httpx                  Client for the AI service (SSE stream + request/response calls)
```

**AI Service**
```
FastAPI 0.111+         Python async web framework
Python 3.12            Language version
Uvicorn 0.29+          ASGI server
OpenAI SDK 1.30+       LLM integration (GPT-4o by default)
Pydantic 2.7+          Data validation and settings
```

### Database
```
MongoDB 7.0            Document database
Users DB               User profiles, authentication data
Topics DB              Topics, chat sessions, test reports, interview reports
```

### Infrastructure & DevOps
```
Docker                 Container runtime
Docker Compose         Local multi-service orchestration
pytest + ruff          Tests and linting (per service)
Gradle 8.8+            Legacy Java services only (preppilot-backend/, removed in migration Phase 9)
NGINX                  Frontend web server (production)
GitHub Actions         CI/CD pipeline
```

---

## Folder Structure

```
int-prep-ai/
├── frontend/                           # React TypeScript SPA
│   ├── src/
│   │   ├── api/                        # API client and interceptors
│   │   │   ├── axiosInstance.ts        # Axios client with JWT interceptor
│   │   │   └── endpoints.ts            # API endpoint constants
│   │   ├── components/                 # Reusable React components
│   │   ├── features/                   # Feature-specific state/logic
│   │   ├── pages/                      # Page components (Dashboard, Learn, Test, Mock Interview, Reports)
│   │   ├── App.tsx                     # Root component with routing
│   │   ├── store.ts                    # Redux store configuration
│   │   └── index.css                   # Global styles
│   ├── package.json                    # Dependencies
│   ├── vite.config.ts                  # Vite configuration
│   └── tsconfig.json                   # TypeScript configuration
│
├── gateway/                            # FastAPI API gateway (:8080)
│   ├── app/
│   │   ├── main.py                     # create_app(): CORS, health, catch-all proxy handler
│   │   ├── routes.py                   # Route table, public-path whitelist, dot-segment check
│   │   ├── auth.py                     # JWT verification
│   │   ├── proxy.py                    # Streaming reverse proxy, header stripping/injection
│   │   ├── config.py, errors.py, logging_config.py
│   ├── tests/unit/                     # respx-mocked upstreams + live-uvicorn SSE tests
│   ├── Dockerfile, requirements*.txt, pyproject.toml, .env.example
│
├── user-service/                       # FastAPI auth service (:8081)
│   ├── app/
│   │   ├── routers/                    # auth.py, oauth.py, users.py, cookies.py
│   │   ├── services/                   # auth_service, jwt_service, passwords, google_oauth, user_service
│   │   ├── models/, repositories/      # Mongo documents and collections (users, refresh_tokens)
│   │   ├── schemas/                    # camelCase API DTOs and explicit validation
│   │   ├── main.py (lifespan, indexes), db.py, deps.py, timeutil.py, config.py, errors.py, logging_config.py
│   ├── tests/{unit,integration}/       # integration tests use a real MongoDB
│   ├── Dockerfile, requirements*.txt, pyproject.toml, .env.example
│
├── topic-service/                      # FastAPI topics / chat / tests / interviews (:8082)
│   ├── app/
│   │   ├── routers/                    # topics.py, chat.py (SSE), tests.py, interviews.py
│   │   ├── services/                   # topic_service, chat_service, test_service, mock_interview_service
│   │   ├── clients/                    # ai_client.py (+ ai_schemas.py): the only caller of ai-service
│   │   ├── models/, repositories/, schemas/
│   │   ├── main.py (lifespan, indexes), db.py, deps.py, timeutil.py, config.py, errors.py, logging_config.py
│   ├── tests/{unit,integration}/       # AI mocked with respx, MongoDB real
│   ├── Dockerfile, requirements*.txt, pyproject.toml, .env.example
│
├── contract-tests/                     # Black-box API tests through the gateway (BACKEND=java|python)
│
├── preppilot-backend/                  # LEGACY Spring Boot implementation, kept until Phase 9 of
│                                       # specs/Python-Backend-Migration-Plan.md; do not extend it
│
├── ai-service/                         # FastAPI stateless AI service
│   ├── app/
│   │   ├── routers/
│   │   │   ├── learn.py                # Learn mode prompt/response handling
│   │   │   ├── test.py                 # Test mode question generation, evaluation
│   │   │   ├── mock_interview.py       # Mock interview orchestration
│   │   │   └── health.py               # Health check endpoint
│   │   ├── middleware/                 # Dual-auth middleware (X-Internal-Api-Key + X-User-Id)
│   │   ├── config.py                   # Settings, LLM configuration
│   │   └── __init__.py
│   ├── main.py                         # FastAPI app initialization
│   ├── requirements.txt                # Python dependencies
│   ├── Dockerfile                      # Container image
│   └── .env.example
│
├── specs/                              # Architecture & design documentation
│   ├── User-story.md                   # Feature requirements
│   ├── Tech-Decisions.md               # Architecture, service breakdown, tech rationale
│   ├── Rollout-Plan.md                 # 6-phase implementation roadmap
│   ├── Tech-Phase-1-*.md
│   ├── Tech-Phase-2-*.md
│   ├── Tech-Phase-3-*.md
│   ├── Tech-Phase-4-*.md
│   ├── Tech-Phase-5-*.md
│   ├── Tech-Phase-6-*.md
│   └── Phase-2-Implementation-Plan.md  # Detailed phase 2 tasks
│
├── deploy/                             # Deployment & DevOps
│   ├── systemd/                        # Systemd service files for EC2 deployment
│   └── [CI/CD scripts and configs]
│
├── docs/                               # Additional documentation
│
├── docker-compose.python.yml           # Local orchestration of the Python stack (use this one)
├── docker-compose.yml                  # LEGACY Java stack (same ports; run only one stack at a time)
├── .env.example                        # Root environment variables template
├── .github/
│   └── workflows/                      # GitHub Actions CI/CD pipelines
│
├── CLAUDE.md                           # This file
├── README.md                           # Project overview & quick start
└── .gitignore                          # Git ignore rules
```

---

## Build & Run Commands

### Full Stack (Recommended for Integration Testing)
`docker-compose.python.yml` is the Python stack. The legacy Java stack is `docker-compose.yml` and uses the same ports.
```bash
# Start all services with MongoDB
docker compose -f docker-compose.python.yml up --build

# Start without rebuilding images (faster iteration)
docker compose -f docker-compose.python.yml up

# Tear down all services
docker compose -f docker-compose.python.yml down

# View logs from all services
docker compose -f docker-compose.python.yml logs -f

# View logs from specific service
docker compose -f docker-compose.python.yml logs -f gateway
docker compose -f docker-compose.python.yml logs -f ai-service
```

### Frontend (React + Vite)
```bash
cd frontend/

# Development server (hot reload on :5173)
npm run dev

# Type check and build for production
npm run build

# Preview production build locally
npm run preview

# Lint TypeScript and TSX files
npm run lint
```

### Python Backend Services (Gateway, User Service, Topic Service)
From each service directory (`gateway/`, `user-service/`, `topic-service/`):

```bash
# One-time setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env

# Run with auto-reload (gateway :8080, user-service :8081, topic-service :8082)
uvicorn app.main:app --reload --port 8081

# Lint and test
ruff check .
pytest
pytest tests/unit                      # unit tests only (no MongoDB needed)
pytest tests/unit/test_mock_interview_service.py -k deadline
```
Integration tests (user-service, topic-service) use a real MongoDB via `TEST_MONGODB_URI`
(default `mongodb://root:change_me@localhost:27017/?authSource=admin`) and skip with a message if it is unreachable.
Outbound HTTP (AI service, Google) is always mocked with `respx`; tests never call a real LLM.

### Contract tests (black-box, through the gateway)
```bash
cd contract-tests && pip install -r requirements.txt
BACKEND=python pytest -m "not ai"      # no LLM calls
BACKEND=python pytest -m ai            # calls the real LLM (costs money)
```

### Legacy Java services (preppilot-backend/, until migration Phase 9)
```bash
cd preppilot-backend && ./gradlew build   # or ./gradlew test, ./gradlew :topic-service:bootRun
```

### AI Service (FastAPI + Uvicorn)
```bash
cd ai-service/

# Install dependencies
pip install -r requirements.txt

# Development server with auto-reload (on :8000)
uvicorn main:app --reload

# Production server
uvicorn main:app --host 0.0.0.0 --port 8000

# Run tests (when tests are added)
pytest tests/
```

---

## Environment Setup

### Prerequisites
- **Docker & Docker Compose** - For easy local development
- **Python 3.12** - For the gateway, user, topic and AI services
- **Node.js 18+** - For frontend development
- **MongoDB 7.0** - Included in docker-compose

### Configuration Files

Each service requires a `.env` file (gitignored). Copy `.env.example` in each directory and fill in real values:

| Service | Location | Key Variables |
|---|---|---|
| **Gateway** | `gateway/.env` | `JWT_SECRET`, `USER_SERVICE_URL`, `TOPIC_SERVICE_URL`, `FRONTEND_ORIGIN`, `UPSTREAM_READ_TIMEOUT_SECONDS`, `LOG_LEVEL` |
| **User Service** | `user-service/.env` | `MONGODB_URI`, `MONGODB_DB`, `JWT_SECRET`, `ACCESS_TOKEN_EXPIRY_SECONDS`, `REFRESH_TOKEN_EXPIRY_DAYS`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `FRONTEND_ORIGIN`, `COOKIE_SECURE` |
| **Topic Service** | `topic-service/.env` | `MONGODB_URI`, `MONGODB_DB`, `INTERNAL_API_KEY`, `AI_SERVICE_URL` |
| **AI Service** | `ai-service/.env` | `LLM_API_KEY`, `LLM_MODEL`, `INTERNAL_API_KEY`, `OPENAI_API_KEY` |
| **Frontend** | `frontend/.env` | `VITE_API_BASE_URL` |
| **MongoDB** | Root `.env` | `MONGO_ROOT_USER`, `MONGO_ROOT_PASSWORD` |

### Critical Invariants

⚠️ **These values MUST match across services:**
- `JWT_SECRET` must be identical in `gateway/.env` and `user-service/.env` (and at least 32 bytes; the services refuse to start otherwise)
- `INTERNAL_API_KEY` must be identical in `topic-service/.env` and `ai-service/.env`

### Quick Start (Docker Compose)

1. **Clone and navigate to the project:**
   ```bash
   cd int-prep-ai
   ```

2. **Create `.env` files from examples:**
   ```bash
   # Root environment
   cp .env.example .env
   
   # Frontend
   cd frontend && cp .env.example .env && cd ..
   
   # Gateway
   cd gateway && cp .env.example .env && cd ..
   
   # User Service
   cd user-service && cp .env.example .env && cd ..
   
   # Topic Service
   cd topic-service && cp .env.example .env && cd ..
   
   # AI Service
   cd ai-service && cp .env.example .env && cd ..
   ```

3. **Fill in real values** (see `.env.example` files for what's needed)

4. **Start the stack:**
   ```bash
   docker compose -f docker-compose.python.yml up --build
   ```

5. **Access the application:**
   - Frontend: http://localhost:3000
   - Gateway (API): http://localhost:8080
   - MongoDB: localhost:27017

---

## System Architecture

### High-Level Overview

```
┌──────────────────────────────────────────────────────┐
│                 Browser (React SPA)                  │
│                  Port 3000 / 5173                    │
│          Redux + React Query + TypeScript            │
└────────────────────┬─────────────────────────────────┘
                     │ HTTPS / SSE (Server-Sent Events)
         ┌───────────▼──────────────┐
         │    API Gateway           │
         │  FastAPI + httpx proxy   │
         │       Port 8080          │
         │  - JWT Validation        │
         │  - Route to services     │
         │  - CORS handling         │
         │  (no rate limiting yet)  │
         └────┬──────────┬──────────┬─────────────┐
              │          │          │             │
       ┌──────▼──┐ ┌─────▼──────┐  │             │
       │  User   │ │   Topic    │  │    AI       │
       │ Service │ │  Service   │  │  Service    │
       │ :8081   │ │   :8082    │  │   :8000     │
       └──────┬──┘ └─────┬──────┘  │             │
              │          │         │             │
              │ (internal HTTP + X-Internal-Api-Key)
              │          │    ┌────▼──────────────┘
              │          │    │
              │          └────▼─────────────────┐
              │                                │
              └───────────────┬────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   MongoDB 7.0      │
                    │   - users_db       │
                    │   - topics_db      │
                    │   Port 27017       │
                    └────────────────────┘
```

### Service Responsibilities

| Service | Port | Responsibilities |
|---|---|---|
| **API Gateway** | 8080 | Route all traffic, JWT validation, inject X-User-Id header, enforce CORS & rate limits |
| **User Service** | 8081 | User registration/login, Google OAuth, JWT/refresh token management, user profiles |
| **Topic Service** | 8082 | Topic CRUD, Learn Mode chats, Test Mode, Mock Interview sessions, Report generation and storage |
| **AI Service** | 8000 | Stateless LLM orchestration, prompt engineering, SSE streaming, dual-auth (X-Internal-Api-Key + X-User-Id) |
| **MongoDB** | 27017 | Persistent document storage (users_db, topics_db) |

### Data Flow Patterns

**Learn Mode Chat Flow:**
```
User sends message → Gateway (validates JWT, injects X-User-Id)
  → Topic Service receives request
    → Calls AI Service with: topic name, chat history, current message, X-Internal-Api-Key header
      → AI Service streams response via SSE
        ← Topic Service forwards SSE stream to client
  → Topic Service persists complete message to MongoDB after stream ends
```

**Test Mode Flow:**
```
User starts test → Topic Service generates questions via AI Service (SSE streaming)
  → Topic Service stores questions in MongoDB
User submits answers → Topic Service calls AI Service for evaluation per answer
  → AI Service evaluates and provides feedback
← Topic Service aggregates all feedback into a Report
  → Report persisted to MongoDB
```

**Mock Interview Flow:**
```
User starts interview → AI Service asks question 1, streams via SSE
User submits answer 1 → AI Service evaluates and marks strength/weakness
  (repeat for all questions)
After all questions → Topic Service aggregates evaluations into Interview Report
  → Report persisted to MongoDB
```

---

## Authentication & Authorization

### Token Model
- **Access Token**: Short-lived JWT (15–30 minutes), stored in Redux state (in-memory, NOT localStorage)
- **Refresh Token**: Long-lived (7–30 days), stored in HTTP-only cookie, auto-refreshed on 401

### OAuth Flow
- Google sign-in handled by the User Service with a hand-rolled authorization-code flow (httpx); `redirect_uri` is `{FRONTEND_ORIGIN}/login/oauth2/code/google`, proxied to the gateway by nginx/Vite
- On successful Google auth, User Service issues same JWT/refresh token pair as email/password flow
- Frontend stores access token in Redux, never in localStorage (prevents XSS)

### User ID Trust
- **Critical invariant:** Downstream services ONLY trust `X-User-Id` header injected by Gateway
- Never accept userId from request body or URL path for security-sensitive operations
- Gateway extracts userId from validated JWT and adds it as `X-User-Id` header

### AI Service Security (Dual Auth)
The AI Service accepts requests from two types of callers:

1. **Topic Service (Internal)** – validated via `X-Internal-Api-Key` header
2. **Authenticated Users (via Gateway)** – validated via JWT at Gateway, `X-User-Id` forwarded

**Middleware check (every AI request):**
```
Is X-Internal-Api-Key present and valid?
  → YES → Allow (internal service call)
  → NO:
Is X-User-Id header present?
  → YES → Allow (user authenticated via Gateway)
  → NO → 401 Unauthorized
```

---

## Current Implementation Phase

**Phase 1** ✅ **Complete**
- User authentication (email/password + Google OAuth)
- Topic management (create, list, delete)
- Basic dashboard and navigation

**Phase 2** ✅ **In Progress / Complete**
- Learn Mode (persistent chat with AI)
- Chat history persistence
- Follow-up question support

**Phase 3** 🔄 **Planned**
- Test Mode (AI-generated questions, evaluation, reports)
- Report generation and storage

**Phase 4** 🔄 **Planned**
- Mock Interview Mode (sequential Q&A with evaluation)
- Interview reports and performance tracking

**Phase 5** 🔄 **Planned**
- Reporting & History Dashboard
- Multi-report viewing and filtering
- Progress tracking visualization

**Phase 6** 🔄 **Planned**
- Production hardening
- Performance optimization
- Security audit and fixes
- UX polish and accessibility

See `specs/Rollout-Plan.md` and `specs/Tech-Decisions.md` for detailed phase breakdown and architecture rationale.

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Microservices** | Bounded contexts (auth vs. content vs. AI orchestration) cleanly separated; independent scaling |
| **FastAPI gateway** | One streaming reverse proxy: JWT validation centralized, spoofable `X-User-*` / `X-Internal-Api-Key` headers stripped on every route, CORS on its own error responses too |
| **MongoDB** | Document-shaped data (chat messages, reports) with schema flexibility; two logical databases for isolation |
| **Stateless AI Service** | Enables horizontal scaling; no session state to manage; all context passed per request |
| **JWT in-memory + refresh token in HTTP-only cookie** | Prevents XSS (no localStorage) and CSRF (access token not in cookie) |
| **SSE Streaming** | Real-time user experience; responses appear as they're generated, not after full completion |
| **Python end to end** | One language for every backend service; async I/O fits the proxy, SSE and AI calls. Behavioural parity with the old Spring services is pinned by `contract-tests/` |
| **Dual-auth on AI Service** | Supports both internal service calls (X-Internal-Api-Key) and direct user API calls (X-User-Id) |

---

## Python Backend Conventions & Gotchas

These are the behaviours the migration pinned down (full list: `specs/Python-Backend-Migration-Plan.md` §8, local only).

- **Mongo compatibility:** never write `None`-valued fields (omit them; `users.googleId` has a sparse unique index and an explicit null would collide). `_id` is an ObjectId but reference fields (`userId`, `topicId`, `testSessionId`, `mockInterviewSessionId`) are **hex strings**, and `topicId` elsewhere is the topic's `_id` hex, not its `publicId`. Create the client with `tz_aware=True` and use millisecond-truncated UTC (`app/timeutil.py`).
- **Wire format:** camelCase everywhere via `CamelModel`; keep null fields in responses; `isFollowUp` / `isComplete` / `isCorrect` keep their `is` prefix. Errors are always `{"error": {"code", "message"}}`. User-facing validation messages are explicit (not Pydantic's defaults).
- **Downstream apps use `redirect_slashes=False`** (a 307 would point the browser at an internal hostname) and are never published in compose, because they trust `X-User-Id`.
- **SSE:** the gateway streams with `aiter_raw` and must never buffer or gzip. Learn Mode saves the AI answer from a detached `asyncio` task so a closed browser tab does not lose it.
- **Scoring:** Test Mode treats only `None` as unanswered (`""` is an answer). Mock Interview scores round half-up (`math.floor(x + 0.5)`), not Python's `round()`.
- **Time in tests:** `MockInterviewService` takes an injectable `clock`; integration tests move deadlines by rewriting `deadlineAt` in MongoDB instead of waiting.
- **`.gitignore` hazard:** the root `.gitignore` carries broad Python template patterns. Do not name a directory `lib`, `bin`, `scripts`, `build`, `dist`, `env`, `logs`, etc., and check new files with `git status --short` / `git check-ignore -v <path>`. `specs/` and `.env.example` files are ignored on purpose.
- **Known issues left as they were:** logout cannot revoke the refresh token server-side (the cookie `Path` is `/api/v1/auth/refresh`, so the browser never sends it to `/logout`); deleting a topic removes only its chat session, not its tests or interviews; no gateway rate limiting.
- **Never run `ai`-marked contract tests casually:** they call the real LLM and cost money.

---

## Important Notes

### Secrets Management
- All `.env` files are gitignored — never commit real secrets
- On production, secrets are injected via environment manager (AWS Secrets Manager, GCP Secret Manager, etc.)
- Never hardcode API keys or passwords in source code

### Development vs. Production
- **Local development** uses `.env` files and docker-compose
- **CI/CD** (GitHub Actions) uses repository secrets
- **Production** uses cloud secrets manager for secret injection

### Logging & Monitoring
- Each service logs to stdout (JSON-structured logs)
- Docker Compose logs can be viewed with `docker compose -f docker-compose.python.yml logs -f`
- Health check endpoint: `GET /health` on every service (user and topic services also ping MongoDB and return 503 when it is down)

### Testing Strategy
- Unit tests per service (to be expanded in Phase 6)
- Integration tests hit real database (not mocked)
- End-to-end tests via browser automation (planned)

---

## Helpful Resources

- **Architecture & Decisions**: `specs/Tech-Decisions.md`
- **Phase Roadmap**: `specs/Rollout-Plan.md`
- **User Story**: `specs/User-story.md`
- **Phase Details**: `specs/Tech-Phase-*.md`
- **Deployment**: `deploy/` and GitHub Actions workflows (`.github/workflows/`)

---

## Questions?

Refer to the `specs/` directory for detailed architecture decisions, tech rationale, and phase-wise implementation plans. Each phase has dedicated documentation outlining scope, success criteria, and technical details.
