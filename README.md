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
