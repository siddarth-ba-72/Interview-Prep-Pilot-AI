# PrepPilot - AI-Powered Interview Preparation Platform

> An intelligent, personalized interview preparation platform that leverages AI to help users master technical topics and ace their interviews.

## Overview

**PrepPilot** is a comprehensive interview preparation application designed to help technical professionals prepare for their interviews in any domain. Whether you're preparing for a role in Spring Boot, Python, DevOps, Generative AI, or any other technology stack, PrepPilot provides an AI-powered personalized learning experience.

Users can create topics they want to prepare for (e.g., "Spring Boot Transactions", "Python Decorators", "Kubernetes Deployments") and interact with the content through three distinct learning modes, each tailored for different preparation styles.

### Key Features

#### 1. **Learn Mode** 🎓
An interactive chat-based learning experience where users can:
- Ask the AI to explain topics with customizable learning styles (basic, interview-focused, deep-dive, etc.)
- Have persistent chat conversations per topic
- Ask follow-up questions and get clarifications
- Build a comprehensive understanding of the topic through guided dialogue

#### 2. **Test Mode** 📝
Assess your knowledge with AI-generated interview questions:
- Multiple question formats: MCQs, descriptive questions, scenario-based challenges
- Automatically graded answers with detailed feedback
- Comprehensive test reports highlighting strengths and weak areas
- Option to revisit weak areas with targeted learning content
- All reports are persisted for future reference

#### 3. **Mock Interview Mode** 🎤
Simulate real interview conditions with AI evaluation:
- Questions asked one at a time, requiring detailed text responses
- Real-time evaluation of each answer
- Identification of strong and weak areas
- Comprehensive interview report with actionable feedback
- Option to revisit and strengthen weak areas

### Core Benefits
- **Personalized Learning**: AI adapts to your learning style and pace
- **Comprehensive Feedback**: Detailed insights into your strengths and improvement areas
- **Persistent Records**: All chat histories and reports are saved for future review
- **Data Privacy**: Users only see their own topics and progress
- **Flexible Preparation**: Multiple modes cater to different learning preferences

---

## Technology Stack

### Frontend
- **React 18+** - Modern UI framework with functional components and hooks
- **TypeScript** - Type-safe JavaScript for reliability
- **Redux Toolkit** - Global state management for auth and UI state
- **React Query (TanStack Query)** - Server state management with intelligent caching
- **Axios** - HTTP client with JWT token management
- **React Router** - Client-side navigation
- **Vite** - Lightning-fast build tool with native TypeScript support

### Backend Services
- **API Gateway** - Spring Cloud Gateway
  - Routes all client traffic
  - JWT validation and token-based authentication
  - CORS handling and rate limiting
  
- **User Service** - Spring Boot 4.x with Java 21
  - User registration and login (email/password)
  - Google OAuth 2.0 integration
  - JWT token management and refresh tokens
  
- **Topic Service** - Spring Boot 4.x with Java 21
  - Topic management and CRUD operations
  - Chat session persistence (Learn mode)
  - Test and interview session management
  - Report generation and storage
  
- **AI Service** - FastAPI (Python)
  - Stateless AI orchestration
  - LLM integration (GPT-4o by default)
  - Streaming responses via Server-Sent Events (SSE)
  - Dual authentication (internal service key + JWT)

### Database
- **MongoDB 7.0** - Document database with two logical databases
  - `users_db` - User profiles, authentication data
  - `topics_db` - Topics, chat messages, sessions, reports

### Infrastructure
- **Docker & Docker Compose** - Containerization and local orchestration
- **Gradle** - Build tool for Java services (with Kotlin DSL)
- **NGINX** - Web server for frontend in production

---

## System Architecture

### High-Level Overview
```
┌─────────────────────────────────────────────────────────┐
│                    Browser (React SPA)                  │
│                   Port: 3000 / Port: 5173               │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS / SSE
         ┌───────────────▼───────────────┐
         │   API Gateway (Port: 8080)    │
         │   Spring Cloud Gateway        │
         │  - JWT Validation             │
         │  - Request Routing            │
         │  - CORS & Rate Limiting       │
         └───┬──────────────┬────────┬───┘
             │              │        │
   ┌─────────▼──────┐ ┌────▼──────────┐ ┌──────────┐
   │ User Service   │ │ Topic Service  │ │ AI Svc   │
   │  Port: 8081    │ │  Port: 8082    │ │ P: 8000  │
   │  - Auth        │ │  - Topics      │ │(Internal)│
   │  - User Mgmt   │ │  - Sessions    │ │- LLM     │
   │  - OAuth       │ │  - Reports     │ │- Streams │
   └────────┬───────┘ └────┬──────────┘ └──────────┘
            │              │  (internal API key)
            └──────┬───────┘
                   │
         ┌─────────▼──────────────┐
         │  MongoDB (Port 27017)  │
         │  - users_db            │
         │  - topics_db           │
         └────────────────────────┘
```

### Request Flow Diagrams

#### Authentication Flow
```mermaid
sequenceDiagram
    participant Browser
    participant Gateway
    participant UserService
    participant Database

    Browser->>UserService: POST /auth/login (email/password)
    UserService->>Database: Verify credentials
    UserService->>Browser: Access Token + Refresh Token (HTTP-only cookie)
    
    Browser->>Gateway: Request + Authorization: Bearer {token}
    Gateway->>Gateway: Validate JWT signature & expiry
    Gateway->>Gateway: Extract userId from JWT
    Gateway->>Gateway: Add X-User-Id header
    Gateway->>+UserService: Forwarded request + X-User-Id
    UserService->>-Gateway: Response (user-scoped data only)
```

#### Learn Mode Chat Flow
```mermaid
sequenceDiagram
    participant Browser
    participant Gateway
    participant TopicService
    participant Database
    participant AIService
    participant LLM

    Browser->>Gateway: POST /api/v1/sessions/{id}/messages
    Gateway->>TopicService: Forward + X-User-Id header
    
    TopicService->>Database: Load chat history & topic context
    TopicService->>AIService: POST /api/ai/chat (with context + history)
    AIService->>AIService: Build prompt from template
    AIService->>LLM: Stream completion request
    LLM-->>AIService: Token by token (streaming)
    AIService-->>TopicService: SSE stream
    TopicService-->>Gateway: SSE stream forward
    Gateway-->>Browser: SSE stream (real-time)
    
    rect rgb(200, 150, 255)
        Browser->>Browser: Display streamed response
    end
    
    rect rgb(150, 200, 255)
        Note over TopicService,Database: After stream completes
        TopicService->>Database: Persist complete message
    end
```

#### Service-to-Service Communication
```mermaid
graph LR
    A["Topic Service"] -->|X-Internal-Api-Key| B["AI Service"]
    B -->|Stateless| C["LLM Provider"]
    A -->|CRUD + SSE| D["MongoDB"]
    style B fill:#ffcccc
    style A fill:#ccffcc
    style D fill:#ccccff
```

---

## Prerequisites

### System Requirements
- **Docker** (version 20.10+) and **Docker Compose** (version 2.0+)
- **Node.js** (version 18+) for frontend development
- **Java 21** for backend development
- **Python 3.10+** for AI service development
- **Git** for version control

### Required API Keys & Accounts
- **OpenAI API Key** - For LLM integration (default: GPT-4o)
- **Google OAuth Credentials** - For Google sign-in
- **MongoDB Connection URI** - MongoDB Atlas or local MongoDB

---

## Environment Setup

Each service requires a `.env` file with configuration. Copy the `.env.example` file in each directory and fill in the values.

### 1. Root-Level Environment (`.env`)
```bash
# MongoDB credentials (used by docker-compose)
MONGO_ROOT_USER=admin
MONGO_ROOT_PASSWORD=securepassword123
```

### 2. Gateway (`.env`)
Located in `preppilot-backend/gateway/.env`
```bash
# Core gateway config
JWT_SECRET=your-super-secret-key-change-this-in-prod
FRONTEND_ORIGIN=http://localhost:3000

# Downstream service URLs
USER_SERVICE_URL=http://user-service:8081
TOPIC_SERVICE_URL=http://topic-service:8082
AI_SERVICE_URL=http://ai-service:8000

# Spring Boot config
SERVER_PORT=8080
```

### 3. User Service (`.env`)
Located in `preppilot-backend/user-service/.env`
```bash
# Database
MONGODB_URI=mongodb://admin:securepassword123@mongodb:27017/users_db?authSource=admin

# Authentication
JWT_SECRET=your-super-secret-key-change-this-in-prod
FRONTEND_ORIGIN=http://localhost:3000

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Spring Boot config
SERVER_PORT=8081
```

### 4. Topic Service (`.env`)
Located in `preppilot-backend/topic-service/.env`
```bash
# Database
MONGODB_URI=mongodb://admin:securepassword123@mongodb:27017/topics_db?authSource=admin

# AI Service communication
INTERNAL_API_KEY=your-internal-api-secret-key
AI_SERVICE_URL=http://ai-service:8000

# Spring Boot config
SERVER_PORT=8082
```

### 5. AI Service (`.env`)
Located in `ai-service/.env`
```bash
# LLM Configuration
LLM_API_KEY=sk-your-openai-api-key
LLM_MODEL=gpt-4o
LLM_MAX_TOKENS=2000

# Service-to-service authentication
INTERNAL_API_KEY=your-internal-api-secret-key

# Server config
SERVER_PORT=8000
```

### 6. Frontend (`.env`)
Located in `frontend/.env`
```bash
# API Gateway URL
VITE_API_BASE_URL=http://localhost:8080
```

**Important**: All `.env` files are in `.gitignore`. Never commit real secrets to the repository.

---

## Getting Started

### Option 1: Docker Compose (Recommended - Full Stack)

**Best for:** Testing all services together, end-to-end testing

```bash
# From project root

# 1. Set up all .env files (see Environment Setup section)

# 2. Build and start all services
docker-compose up --build

# 3. Access the application
# Frontend:    http://localhost:3000
# API Gateway: http://localhost:8080
# MongoDB:     mongodb://localhost:27017 (if exposed)
```

**Useful Docker Compose commands:**
```bash
# Stop all services
docker-compose down

# View logs from all services
docker-compose logs -f

# View logs from specific service
docker-compose logs -f frontend

# Rebuild without cache
docker-compose up --build --no-cache

# Remove volumes (fresh database)
docker-compose down -v
```

---

### Option 2: Local Development (Individual Services)

**Best for:** Focused development on specific services with hot-reload

#### Frontend Development
```bash
cd frontend

# Install dependencies
npm install

# Start dev server (Port 5173 with hot-reload)
npm run dev

# Build for production
npm run build

# Type checking
npm run type-check

# Linting
npm run lint

# Format code
npm run format
```

#### Java Services (Gateway, User Service, Topic Service)
```bash
cd preppilot-backend/gateway  # or user-service or topic-service

# Build the service
./gradlew build

# Run locally
./gradlew bootRun

# Run tests
./gradlew test

# Run specific test
./gradlew test --tests "com.preppilot.gateway.SomeTest"

# Clean build
./gradlew clean build
```

#### AI Service
```bash
cd ai-service

# Create virtual environment (if not already done)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server (Port 8000 with auto-reload)
uvicorn main:app --reload

# Run tests
pytest

# Format code
black .
```

---

## Development Workflow

### Starting Fresh Local Setup

```bash
# 1. Clone and navigate to project
git clone <repo-url>
cd int-prep-ai

# 2. Set up environment files
cp preppilot-backend/gateway/.env.example preppilot-backend/gateway/.env
cp preppilot-backend/user-service/.env.example preppilot-backend/user-service/.env
cp preppilot-backend/topic-service/.env.example preppilot-backend/topic-service/.env
cp ai-service/.env.example ai-service/.env
cp frontend/.env.example frontend/.env

# 3. Fill in real values in .env files (API keys, secrets, etc.)

# 4. Start the full stack
docker-compose up --build

# 5. Access at http://localhost:3000
```

### Debugging

#### View service logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f topic-service
docker-compose logs -f ai-service

# Follow new logs only
docker-compose logs -f --tail=50
```

#### Database inspection
```bash
# Connect to MongoDB from your local machine
mongodb://admin:securepassword123@localhost:27017/?authSource=admin

# Common tools
# - MongoDB Compass (GUI)
# - mongosh (CLI)
# - Visual Studio Code MongoDB extension
```

#### Test a single endpoint
```bash
# Example: Get topics for authenticated user
curl -H "Authorization: Bearer <your-jwt-token>" \
     http://localhost:8080/api/v1/topics
```

---

## Key Design Principles

### Security
- **User ID Trust**: Only derived from JWT via `X-User-Id` header injected by Gateway
- **Token Storage**: JWT stored in memory (not localStorage) to prevent XSS; refresh token in HTTP-only cookie
- **Access Control**: Users only see their own topics and reports
- **AI Service Not Publicly Exposed**: All traffic routed through Gateway; AI service has no public network access

### Scalability
- **Stateless Services**: Each service can be scaled independently
- **AI Service Stateless**: No database; all context passed per-request
- **SSE Streaming**: Enables real-time responses without long polling

### Reliability
- **Persistent Chat & Reports**: All user data persisted to MongoDB immediately after generation
- **Service Health Checks**: Each service exposes `/actuator/health` or `/health`
- **Error Consistency**: Standardized error response format across all services

### Development Experience
- **Docker Compose**: Single command to spin up entire stack locally
- **Hot-Reload**: Frontend and AI service support live development
- **Type Safety**: TypeScript frontend + Kotlin DSL Gradle scripts + Java generics

---

## Troubleshooting

### Port Already in Use
```bash
# Find process using port (e.g., 8080)
lsof -i :8080

# Kill process
kill -9 <PID>
```

### Docker Container Issues
```bash
# Remove all containers and volumes
docker-compose down -v

# Rebuild from scratch
docker-compose up --build

# Check for disk space (Docker can run out of space)
docker system prune -a
```

### MongoDB Connection Errors
```bash
# Verify MongoDB is running
docker-compose ps mongodb

# Check logs
docker-compose logs mongodb

# Reset database
docker-compose down -v
docker-compose up mongodb
```

### Frontend Can't Connect to API
- Ensure `VITE_API_BASE_URL` in `frontend/.env` matches Gateway URL
- Ensure Gateway is running: `curl http://localhost:8080/actuator/health`
- Check browser console for CORS errors

### AI Service Not Responding
- Verify `LLM_API_KEY` is correct in `ai-service/.env`
- Check OpenAI API quota and billing
- Review AI service logs: `docker-compose logs -f ai-service`

---

## CI/CD & Production Deployment (Backend Services)

`gateway`, `user-service`, and `topic-service` are each deployed independently
to their own AWS EC2 instance via GitHub Actions. `cache-service` is a shared
library module (no `bootJar`) consumed by the other three — it is never
deployed on its own, but changes to it trigger all three deploy pipelines
since they depend on it.

### Pipeline overview

| Workflow | Trigger | What it does |
|---|---|---|
| `.github/workflows/deploy-gateway.yml` | push to `main` touching `preppilot-backend/gateway/**` or `cache-service/**` | test → bootJar → deploy to gateway's EC2 instance |
| `.github/workflows/deploy-user-service.yml` | push to `main` touching `preppilot-backend/user-service/**` or `cache-service/**` | test → bootJar → deploy to user-service's EC2 instance |
| `.github/workflows/deploy-topic-service.yml` | push to `main` touching `preppilot-backend/topic-service/**` or `cache-service/**` | test → bootJar → deploy to topic-service's EC2 instance |
| `.github/workflows/_deploy-service-reusable.yml` | called by the 3 workflows above | shared test/build/deploy logic (not run directly) |
| `.github/workflows/rollback-service.yml` | manual (`workflow_dispatch`), pick a service | restores the last backup jar on that service's EC2 instance and restarts it |

All three deploy workflows can also be triggered manually from the Actions
tab (`workflow_dispatch`) without needing a code change.

### What happens on each deploy

1. `./gradlew :<service>:test` — fails the pipeline if tests fail, nothing is deployed.
2. `./gradlew :<service>:bootJar` — builds the runnable Spring Boot jar.
3. The jar is uploaded as a GitHub Actions build artifact, then `scp`'d to
   `/preppilot/<service>/webapp/app.jar.new` on that service's EC2 instance.
4. Over SSH, the instance:
   - stops the systemd service,
   - copies the **currently running** `webapp/app.jar` into `backup/app.jar` (so there's always exactly one previous good version on disk),
   - promotes `app.jar.new` to `webapp/app.jar`,
   - restarts the systemd service and prints its status.

### EC2 instance layout (one per service)

```
/preppilot/<service>/webapp/app.jar   <- currently running jar
/preppilot/<service>/backup/app.jar   <- previous jar (for rollback)
/preppilot/<service>/.env             <- real runtime secrets, never committed
/etc/systemd/system/<service>.service <- systemd unit, Restart=always
```

### One-time EC2 setup (per instance, done manually before first deploy)

The `deploy/` folder at the repo root holds the assets for this manual
bootstrap step. **GitHub Actions never reads from `deploy/`** — it only
exists so you (a human) can provision each EC2 box once, after which all
future deploys/rollbacks go entirely through the Actions workflows.

```bash
# from your local machine, for each service + its EC2 host:
scp deploy/systemd/<service>.service deploy/systemd/setup-ec2.sh ec2-user@<host>:/tmp/
ssh ec2-user@<host>
cd /tmp && sudo ./setup-ec2.sh <service>
# then fill in real secrets:
sudo nano /preppilot/<service>/.env
```

`setup-ec2.sh <service>` creates the `preppilot` system user, the
`webapp`/`backup` directories, an empty `.env`, and installs + enables the
`<service>.service` systemd unit. Repeat for `gateway`, `user-service`, and
`topic-service` on their respective instances.

Also required once per instance: add the GitHub Actions deploy SSH **public**
key to that instance's `~/.ssh/authorized_keys` (the matching **private** key
goes into GitHub, see below — never committed to the repo).

### Required GitHub configuration

Create 3 GitHub **Environments**, each scoping its own secrets so the shared
reusable workflow resolves `secrets.EC2_HOST` etc. to the right instance:

| Environment | Secrets |
|---|---|
| `production-gateway` | `EC2_HOST`, `EC2_USERNAME`, `EC2_SSH_KEY` |
| `production-user-service` | `EC2_HOST`, `EC2_USERNAME`, `EC2_SSH_KEY` |
| `production-topic-service` | `EC2_HOST`, `EC2_USERNAME`, `EC2_SSH_KEY` |

Environments also let you add required reviewers / manual approval gates per
service before it deploys to production.

### Emergency rollback

Actions tab → **Rollback - Backend Service** → Run workflow → choose the
service. This copies `backup/app.jar` back over `webapp/app.jar` and
restarts the systemd service — no rebuild required.

See `deploy/README.md` for the full reference.

---

## Contributing

### Code Standards
- **Frontend**: TypeScript, ESLint, Prettier
- **Java Services**: Google Java Style Guide, Gradle formatted
- **Python**: Black formatting, mypy type checking
- **Git Commits**: Write clear, descriptive commit messages

### Pull Request Process
1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and commit with clear messages
3. Ensure tests pass: `npm test` (frontend), `./gradlew test` (Java), `pytest` (Python)
4. Push and create pull request
5. Address review feedback
6. Merge to main

---

**Happy Learning! 🚀**

PrepPilot makes interview preparation intelligent, personalized, and effective. Start by creating your first topic and choosing your preferred learning mode!
