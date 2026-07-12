# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: PrepPilot

AI-powered interview preparation platform. Users create topics (e.g., "Spring Boot", "Python"), then study via three modes: Learn (persistent AI chat), Test (AI-generated questions + report), and Mock Interview (sequential Q&A with real-time evaluation). The full spec lives in `specs/`.

## Commands

### Full stack (recommended for integration work)
```bash
docker-compose up --build      # start all services + MongoDB
docker-compose up              # start without rebuilding images
docker-compose down
```

### Frontend (`frontend/`)
```bash
npm run dev        # dev server on :5173
npm run build      # tsc + vite build
npm run lint       # eslint on .ts/.tsx
```

### Java services (run from each service directory: `gateway/`, `user-service/`, `topic-service/`)
```bash
./gradlew build            # compile + test
./gradlew bootRun          # run locally
./gradlew test             # run tests only
./gradlew test --tests "com.preppilot.userservice.SomeTest"  # single test
```

### AI service (`ai-service/`)
```bash
pip install -r requirements.txt
uvicorn main:app --reload     # dev server
```

## Environment setup

Each service requires a `.env` file (gitignored). Copy `.env.example` in each directory and fill in real values. Required variables per service:

| Service | Key variables |
|---|---|
| `gateway/` | `JWT_SECRET`, `USER_SERVICE_URL`, `TOPIC_SERVICE_URL`, `AI_SERVICE_URL`, `FRONTEND_ORIGIN` |
| `user-service/` | `MONGODB_URI`, `JWT_SECRET`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `FRONTEND_ORIGIN` |
| `topic-service/` | `MONGODB_URI`, `INTERNAL_API_KEY`, `AI_SERVICE_URL` |
| `ai-service/` | `LLM_API_KEY`, `LLM_MODEL`, `INTERNAL_API_KEY` |
| `frontend/` | `VITE_API_BASE_URL` |

`JWT_SECRET` must be identical across `gateway/` and `user-service/`. `INTERNAL_API_KEY` must be identical across `topic-service/` and `ai-service/`.

## Architecture

```
Browser (React SPA)
    ↓ HTTPS / SSE
API Gateway :8080  (Spring Cloud Gateway)
    ├── /api/v1/auth/**  → User Service :8081
    ├── /api/v1/users/** → User Service :8081
    ├── /api/v1/topics,sessions,reports/**  → Topic Service :8082
    └── /api/v1/ai/**    → AI Service (JWT required)

Topic Service → AI Service  (X-Internal-Api-Key)
```

**Gateway** (`gateway/`) validates JWT on every request except `/api/v1/auth/**`, `/oauth2/**`, `/login/oauth2/**`, and `/actuator/health`. On success it injects `X-User-Id` and `X-User-Email` headers for downstream services.

**User Service** (`user-service/`) owns all auth: email/password registration and login, Google OAuth2 via Spring Security, JWT issuance and refresh token management. Refresh tokens are stored in MongoDB and sent as HTTP-only cookies.

**Topic Service** (`topic-service/`) owns all domain logic: topic CRUD, Learn Mode chat sessions, Test Mode, Mock Interview sessions, and reports. It calls the AI Service over internal HTTP using `X-Internal-Api-Key`.

**AI Service** (`ai-service/`) is fully stateless — no database. It accepts structured prompt requests and streams responses via SSE. Authenticates callers via dual-auth middleware: `X-Internal-Api-Key` for topic-service calls, or `X-User-Id` (injected by Gateway) for direct user calls.

**MongoDB** uses two logical databases on one instance: `users_db` (User Service) and `topics_db` (Topic Service).

## Key design invariants

- **User ID trust**: downstream services must only read `X-User-Id` from the request header injected by the Gateway — never from the client request body or URL path for security-sensitive operations.
- **Access token storage**: stored in Redux state (in-memory), never localStorage. The Axios interceptor in `frontend/src/api/axiosInstance.ts` attaches it as `Authorization: Bearer`. On 401, it silently calls `/api/v1/auth/refresh` (which sends the HTTP-only refresh cookie) to get a new token.
- **AI Service stateless**: all context (chat history, topic name, user ID) must be passed in each request from Topic Service. No session state on the AI layer.
- **SSE streaming**: Topic Service proxies the AI Service's SSE stream to the frontend via Gateway. Once the stream ends, the complete message is persisted to MongoDB.
- **AI Service not publicly exposed**: in Docker Compose there is no `ports:` mapping on the AI Service container. All external traffic must enter through the Gateway.

## Current build phase

Phase 1 (Foundation & Auth) — infrastructure scaffold, user auth, and basic topic CRUD. See `specs/Rollout-Plan.md` for the full 6-phase roadmap and `specs/Tech-Decisions.md` for detailed architecture rationale.
