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

**API Gateway**
```
Spring Cloud Gateway   Route traffic, JWT validation, CORS, rate limiting
Spring Boot 3.3+       Foundation framework
Java 21                Language version
Spring Security        JWT token validation
```

**User Service**
```
Spring Boot 4.x        Framework
Java 21                Language version
Spring Security OAuth2 Google OAuth 2.0 integration
Spring Data MongoDB    Database access
BCrypt                 Password hashing
JJWT (jjwt 0.12+)      JWT token creation and validation
```

**Topic Service**
```
Spring Boot 4.x        Framework
Java 21                Language version
Spring Data MongoDB    Database access
Spring Web             REST API
```

**AI Service**
```
FastAPI 0.111+         Python async web framework
Python 3.9+            Language version
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
Gradle 8.8+            Build tool for Java services (Kotlin DSL)
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
├── preppilot-backend/                  # All Java microservices (monorepo)
│   ├── gateway/                        # Spring Cloud Gateway
│   │   ├── src/main/java/com/preppilot/gateway/
│   │   │   ├── config/                 # Gateway configuration, JWT filter, CORS
│   │   │   ├── filter/                 # Custom gateway filters
│   │   │   └── Application.java        # Main entry point
│   │   ├── build.gradle.kts            # Gradle build config
│   │   ├── Dockerfile                  # Container image
│   │   └── .env.example                # Environment variables template
│   │
│   ├── user-service/                   # User authentication & profile management
│   │   ├── src/main/java/com/preppilot/userservice/
│   │   │   ├── config/                 # Security, MongoDB config
│   │   │   ├── controller/             # REST endpoints (/auth/**, /users/**)
│   │   │   ├── service/                # Business logic (AuthService, UserService)
│   │   │   ├── model/                  # User, RefreshToken entities
│   │   │   ├── repository/             # MongoDB repositories
│   │   │   └── Application.java        # Main entry point
│   │   ├── build.gradle.kts
│   │   ├── Dockerfile
│   │   └── .env.example
│   │
│   ├── topic-service/                  # Topics, sessions, reports, AI orchestration
│   │   ├── src/main/java/com/preppilot/topicservice/
│   │   │   ├── config/                 # MongoDB config, WebClient config
│   │   │   ├── controller/             # REST endpoints (/topics/**, /sessions/**)
│   │   │   ├── service/                # Business logic (TopicService, SessionService, AIClient)
│   │   │   ├── model/                  # Topic, ChatSession, TestSession, InterviewSession, Report entities
│   │   │   ├── repository/             # MongoDB repositories
│   │   │   └── Application.java
│   │   ├── build.gradle.kts
│   │   ├── Dockerfile
│   │   └── .env.example
│   │
│   ├── cache-service/                  # (Optional) Caching layer for frequent queries
│   │   ├── src/
│   │   ├── build.gradle.kts
│   │   └── Dockerfile
│   │
│   ├── gradle/                         # Gradle wrapper
│   ├── gradlew / gradlew.bat            # Gradle executable
│   ├── settings.gradle.kts             # Root Gradle settings (lists subprojects)
│   └── build.gradle.kts                # Root Gradle build config
│
├── ai-service/                         # FastAPI stateless AI service
│   ├── app/
│   │   ├── routers/
│   │   │   ├── learn.py                # Learn mode prompt/response handling
│   │   │   ├── test.py                 # Test mode question generation, evaluation
│   │   │   ├── mock_interview.py       # Mock interview orchestration
│   │   │   └── health.py               # Health check endpoint
│   │   ├── auth.py                     # Internal-key auth (X-Internal-Api-Key only)
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
├── docker-compose.yml                  # Local development orchestration
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
```bash
# Start all services with MongoDB
docker-compose up --build

# Start without rebuilding images (faster iteration)
docker-compose up

# Tear down all services
docker-compose down

# View logs from all services
docker-compose logs -f

# View logs from specific service
docker-compose logs -f gateway
docker-compose logs -f ai-service
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

### Java Backend Services (Gateway, User Service, Topic Service)
From each service directory (`preppilot-backend/gateway/`, `preppilot-backend/user-service/`, `preppilot-backend/topic-service/`):

```bash
# Build and run tests
./gradlew build

# Run Spring Boot application locally (with auto-reload)
./gradlew bootRun

# Run only test suite
./gradlew test

# Run a specific test class
./gradlew test --tests "com.preppilot.topicservice.TopicServiceTest"

# Build JAR only (no tests)
./gradlew build -x test

# Clean build artifacts
./gradlew clean
```

From the root `preppilot-backend/` directory:
```bash
# Build all services at once
./gradlew build

# Run all tests across services
./gradlew test
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
- **Java 21** - For building Spring Boot services locally
- **Python 3.9+** - For AI service development
- **Node.js 18+** - For frontend development
- **MongoDB 7.0** - Included in docker-compose

### Configuration Files

Each service requires a `.env` file (gitignored). Copy `.env.example` in each directory and fill in real values:

| Service | Location | Key Variables |
|---|---|---|
| **Gateway** | `preppilot-backend/gateway/.env` | `JWT_SECRET`, `USER_SERVICE_URL`, `TOPIC_SERVICE_URL`, `AI_SERVICE_URL`, `FRONTEND_ORIGIN` |
| **User Service** | `preppilot-backend/user-service/.env` | `MONGODB_URI`, `JWT_SECRET`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `FRONTEND_ORIGIN`, `REFRESH_TOKEN_EXPIRY` |
| **Topic Service** | `preppilot-backend/topic-service/.env` | `MONGODB_URI`, `JWT_SECRET`, `INTERNAL_API_KEY`, `AI_SERVICE_URL`, `GATEWAY_URL` |
| **AI Service** | `ai-service/.env` | `LLM_API_KEY`, `LLM_MODEL`, `INTERNAL_API_KEY`, `OPENAI_API_KEY` |
| **Frontend** | `frontend/.env` | `VITE_API_BASE_URL` |
| **MongoDB** | Root `.env` | `MONGO_ROOT_USER`, `MONGO_ROOT_PASSWORD` |

### Critical Invariants

⚠️ **These values MUST match across services:**
- `JWT_SECRET` must be identical in `gateway/.env`, `user-service/.env` and `topic-service/.env` (all three verify access tokens)
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
   cd preppilot-backend/gateway && cp .env.example .env && cd ../../..
   
   # User Service
   cd preppilot-backend/user-service && cp .env.example .env && cd ../../..
   
   # Topic Service
   cd preppilot-backend/topic-service && cp .env.example .env && cd ../../..
   
   # AI Service
   cd ai-service && cp .env.example .env && cd ..
   ```

3. **Fill in real values** (see `.env.example` files for what's needed)

4. **Start the stack:**
   ```bash
   docker-compose up --build
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
         │  Spring Cloud Gateway    │
         │       Port 8080          │
         │  - JWT Validation        │
         │  - Route to services     │
         │  - CORS handling         │
         │  - Rate limiting         │
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
| **AI Service** | 8000 | Stateless LLM orchestration, prompt engineering, SSE streaming; only Topic Service may call it (X-Internal-Api-Key) |
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
- Google sign-in handled by User Service using Spring Security OAuth2 Client
- On successful Google auth, User Service issues same JWT/refresh token pair as email/password flow
- Frontend stores access token in Redux, never in localStorage (prevents XSS)

### User ID Trust
- **Critical invariant:** the user's identity always comes from a verified access token, never from a header or body the caller controls
- Gateway extracts userId from validated JWT and adds it as `X-User-Id` header
- User Service (`/api/v1/users/**`) and Topic Service have public URLs, so each also verifies the `Authorization: Bearer` token itself (`config/JwtAuthFilter.java`) and overwrites `X-User-Id`, `X-User-Email` and `X-User-Experience` from its claims. Controllers keep reading those headers.
- Never accept userId from request body or URL path for security-sensitive operations

### AI Service Security (Internal Key Only)
Only Topic Service may call the AI Service; every request must carry the shared `X-Internal-Api-Key`, otherwise 401. A bare `X-User-Id` is not accepted: the AI Service has a public URL and every call spends LLM tokens. Users reach the AI only through Topic Service, which checks their token and usage limits first.

### Usage Limits
Topic Service limits AI-backed actions per user (`UsageLimitService`, configured under `usage-limits` in its `application.yml`). The tier comes from the `experienceLevel` token claim: `STUDENT` gets the student tier, everyone else the standard tier.

| Tier | Topics | Learn messages | Tests | Mock interviews |
|---|---|---|---|---|
| Student | 2 | 30 | 2 | 1 |
| Standard | no limit | 50 | 3 | 2 |

- Actions are counted over a sliding 24h window. The use that reaches the limit locks the action until 24h after that use; then the full limit is back.
- What costs a use: sending a Learn message, starting a new test, starting a new mock interview. Resuming, submitting a test, answering and ending an interview, and the first Learn chat reply are free.
- A use whose AI call fails is refunded. Over the limit returns `429 USAGE_LIMIT_REACHED` with `retryAt`; the topic limit returns `403 TOPIC_LIMIT_REACHED`.
- State lives in the `usage_windows` collection (one document per user and action, TTL-cleaned), updated atomically so concurrent requests cannot both take the last slot. `GET /api/v1/usage` returns what is left.

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
| **Spring Cloud Gateway** | Native Spring integration, declarative routing, JWT validation centralized |
| **MongoDB** | Document-shaped data (chat messages, reports) with schema flexibility; two logical databases for isolation |
| **Stateless AI Service** | Enables horizontal scaling; no session state to manage; all context passed per request |
| **JWT in-memory + refresh token in HTTP-only cookie** | Prevents XSS (no localStorage) and CSRF (access token not in cookie) |
| **SSE Streaming** | Real-time user experience; responses appear as they're generated, not after full completion |
| **Gradle (Kotlin DSL)** | Faster incremental builds, type-safe build scripts, modern Spring standard |
| **Internal-key-only AI Service** | Its URL is public and every call costs LLM tokens, so only Topic Service (X-Internal-Api-Key) may call it; usage limits are enforced there |

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
- Docker Compose logs can be viewed with `docker-compose logs -f`
- Health check endpoints: `/actuator/health` (Spring Boot) or `/health` (FastAPI)

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
