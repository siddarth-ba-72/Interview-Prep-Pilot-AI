# CLAUDE.md — PrepPilot

PrepPilot is an AI-powered interview preparation app. A user adds a topic and practises it in three modes: **Learn** (a saved chat with an AI tutor), **Test** (an AI-written, AI-graded 20-question test) and **Mock Interview** (a timed, one-question-at-a-time interview with a report).

It is a small microservice system: a React frontend, a Spring Cloud Gateway, two Spring Boot services, a FastAPI AI service, and MongoDB.

`README.md` has the product tour, screenshots and architecture diagrams. This file holds what you need to change the code safely.

---

## Rules

These hold everywhere in the repo. Check a change against them before you finish.

1. **Identity comes only from a verified access token.** Never trust a user id, email, role or experience level from a request body, a URL, or a header the caller controls.
2. **Only Topic Service calls the AI Service.** Do not add a path that lets a browser, or any other service, reach it.
3. **Never call a real LLM from a test, a script or a demo.** Use the fake-LLM stack in `loadtest/` for anything that exercises AI flows.
4. **Admins see counts, not content.** Admin pages show profiles, topic names and counts of tests and interviews. No scores, answers, reports or chats, and no admin write actions. Ask before crossing that line.
5. **Mask sensitive UI from analytics.** Any new page or component that shows answers, scores, reports, chats, admin data or a user's name needs `<PageContainer mask>` or `data-clarity-mask="True"`.
6. **Keep secrets out of the repo and out of the docs.** Environment files are gitignored; never commit them. In documentation, do not write keys or secrets, or even their variable and header names. Describe behaviour instead.
7. **Keep documentation lean.** In user-facing docs, include only the commands a reader needs to run the app. Put everything else in prose or tables.

---

## Stack

| Part | Technology |
|---|---|
| Frontend | React 18, TypeScript 5 (strict), Vite 5, Tailwind CSS 4, Redux Toolkit, TanStack Query 5, React Router 6, Axios |
| Gateway | Spring Cloud Gateway 2023.0 on Spring Boot 3.3, Java 21 |
| User Service | Spring Boot 3.3, Spring Security with the Google OAuth2 client, Spring Data MongoDB, JJWT 0.12, BCrypt |
| Topic Service | Spring Boot 3.3 (MVC, plus WebClient for calls to the AI Service), Spring Data MongoDB |
| Shared library | `cache-service`: Caffeine cache auto-configuration, built into the two services. It is not deployed on its own |
| AI Service | FastAPI, Uvicorn, Pydantic 2, OpenAI SDK (OpenAI, or Gemini through its OpenAI-compatible endpoint). Needs Python 3.10 or later |
| Data | MongoDB 7: `users_db` and `topics_db` |
| Build and test | Gradle 8.8 (Kotlin DSL, one multi-project build), Docker Compose, Playwright |

---

## Layout

| Path | Contents |
|---|---|
| `frontend/src/api/` | Axios instance with token refresh, SSE chat stream, one module per backend area |
| `frontend/src/features/` | `auth`, `chat`, `tests`, `interviews`, `prepTrack`, `howItWorks`, `admin`, `analytics`, `theme` |
| `frontend/src/pages/`, `components/` | One page per route (see `App.tsx`), shared components |
| `preppilot-backend/gateway/` | `filter/JwtAuthFilter.java` and the route table in `application.yml` |
| `preppilot-backend/user-service/` | `config`, `controller`, `service`, `model`, `repository`, `dto` |
| `preppilot-backend/topic-service/` | The same packages, plus `exception` and `util`. `service/AiClient.java` is the only caller of the AI Service |
| `preppilot-backend/cache-service/` | The shared cache library |
| `ai-service/app/` | `main.py`, `routers/` (`learn`, `test`, `interview`), `prompts.py`, `llm.py`, `scope_validator.py`, `schemas.py`, `config.py`, `auth.py` |
| `loadtest/` | Isolated Compose stack with a fake LLM, and the load-test runner |
| `e2e/` | Playwright functional tests (`tests/`) and load journeys (`load/`) |
| `deploy/`, `.github/workflows/` | EC2 setup assets; lint, deploy and rollback pipelines |

`specs/` is gitignored and may be missing. Do not link to it from tracked files.

---

## Commands

Run Gradle commands from `preppilot-backend/`, npm commands from the folder named, and the rest from the repository root.

| Goal | Command |
|---|---|
| Run the whole app with a fake LLM | `docker compose -f loadtest/docker-compose.yml up --build -d --wait` |
| Stop it | `docker compose -f loadtest/docker-compose.yml down` |
| Run the whole app with a real LLM | `docker compose up --build` (needs each service's environment file) |
| Frontend dev server | `npm run dev` in `frontend/` |
| Frontend checks | `npm run lint` and `npm run build` in `frontend/` |
| Build all Java modules | `./gradlew build` |
| Test one Java module | `./gradlew :topic-service:test` |
| Run one Java test class | `./gradlew :topic-service:test --tests "com.preppilot.topicservice.service.MockInterviewServiceTest"` |
| Run one Java service from source | `./gradlew :gateway:bootRun --args='--spring.profiles.active=dev'` |
| AI Service from source | `uvicorn app.main:app --reload --port 8000` in `ai-service/` |
| End-to-end tests | `npm test` in `e2e/`, with the fake-LLM stack running |
| Load test | `loadtest/run.sh smoke` |

Ports: frontend 3000, gateway 8080, User Service 8081, Topic Service 8082, AI Service 8000. The fake-LLM stack also uses 8090 (fake LLM) and 27019 (its own MongoDB), and it clashes with the regular Compose stack on 3000 and 8080.

---

## Architecture

| Service | Role |
|---|---|
| **Gateway** | The only public entry point for the browser. Verifies the access token, sets the identity headers, routes by path, handles CORS, and returns 403 for non-admins on `/api/v1/admin/**` |
| **User Service** | Registration, login, Google OAuth, refresh-token rotation, profile and onboarding answers, feedback, admin user list |
| **Topic Service** | Topics, Learn chats, tests, mock interviews, reports, admin activity counts |
| **AI Service** | Stateless. Builds prompts, checks topic scope, calls the LLM, streams tokens |

**Gateway routes.** `/api/v1/auth/**`, `/api/v1/users/**`, `/api/v1/admin/users/**`, `/api/v1/admin/feedback/**`, `/oauth2/**` and `/login/oauth2/**` go to User Service. `/api/v1/topics/**` and `/api/v1/admin/activity/**` go to Topic Service. When you add a controller path, add it to the gateway's route table too. The table also has three entries that no controller serves: `/api/v1/sessions/**`, `/api/v1/reports/**` and `/api/v1/ai/**`.

**API map.**

| Service | Endpoints |
|---|---|
| User Service | `/api/v1/auth/` `register`, `login`, `refresh`, `logout`, `google`. `/api/v1/users/me`, `/me/profile`, `/me/feedback`. `/api/v1/admin/users` (paged, `?q=` search), `/{userId}`, `/stats`. `/api/v1/admin/feedback` |
| Topic Service | `/api/v1/topics` and `/{topicId}`. Under a topic: `/chat`, `/chat/messages`, `/tests`, `/tests/{testId}`, `/submit`, `/report`, `/interviews`, `/interviews/{sessionId}`, `/answer`, `/end`, `/report`. `/api/v1/admin/activity/` `summary`, `users?ids=`, `users/{id}` |
| AI Service | `/ai/learn/stream`, `/ai/test/generate`, `/ai/test/evaluate`, `/ai/interview/plan`, `/ai/interview/next-turn`, `/ai/interview/generate-report`, `/health` |

The `{topicId}` in a URL is the topic's `publicId`, not its MongoDB id.

**Data.** `users_db` holds `users`, `refresh_tokens` and `feedback`. `topics_db` holds `topics`, `chat_sessions`, `test_sessions`, `test_reports`, `mock_interview_sessions` and `mock_interview_reports`. The two databases are linked only by the user id string.

**Errors.** Topic Service returns `{ "error": { "code", "message" } }`, with codes from `exception/ErrorCode.java`. Add a code there instead of returning ad-hoc messages.

**Caching.** `TopicService.list` caches a user's topics and evicts only when a topic is created or deleted. Code that changes a topic's fields elsewhere, such as the average score after a test, must evict or update that entry or the dashboard shows stale data. User Service caches user profiles and updates the entry on every profile change.

---

## Authentication

- **Access token.** A 30-minute JWT with the claims `userId`, `email`, `role` and, after onboarding, `experienceLevel`. The frontend keeps it in Redux memory, never in `localStorage`.
- **Refresh token.** Valid for 30 days, sent as an `HttpOnly`, `Secure` cookie scoped to `/api/v1/auth/refresh`, stored hashed, and rotated on every use. The old token stays valid for a short grace window so that a lost response does not sign the user out.
- **Gateway.** Lets `/api/v1/auth/`, `/oauth2/`, `/login/oauth2/` and `/actuator/health` through without a token. For everything else it verifies the token and sets `X-User-Id`, `X-User-Email` and `X-User-Experience` from its claims.
- **Services verify again.** User Service (for `/api/v1/users/**`) and Topic Service each have a `config/JwtAuthFilter.java` that verifies the same token and overwrites those headers. Controllers read the headers.
- **Admin access.** `config/AdminAccessInterceptor.java` in each service reads the role from the verified token. Grant admin by hand: set `role` to `ADMIN` on the user's document in `users_db.users`, then sign in again. A missing role means `USER`. There is no API for it.
- **Google sign-in.** `/oauth2/authorization/google`, then Google redirects to `/login/oauth2/code/google`, then User Service sets the refresh cookie and redirects to `/auth/callback` with the access token in the URL fragment.
- **Frontend.** `api/axiosInstance.ts` attaches the token and, on a 401, refreshes once and retries. Concurrent callers share one refresh request, because the server rotates the token.

**Two shared settings must stay identical wherever they appear**, or every request fails with 401: the one that signs and verifies access tokens (gateway, User Service, Topic Service), and the one Topic Service uses to authenticate to the AI Service (Topic Service, AI Service). The first must be at least 32 bytes long or the Java services fail at startup. Their names are in each service's `application.yml` and in `ai-service/app/config.py`.

---

## Domain rules the code enforces

**Learn Mode**
- One chat per user and topic. The user's message is saved before the stream starts; the AI reply is saved when the stream completes.
- `POST .../chat/messages` answers as Server-Sent Events: `{"token": ...}` per token, then `[DONE]`. On failure a single `{"error": ...}` event ends the stream and no reply is saved.
- Topic Service sends the full history to the AI Service, not just the visible page.

**Test Mode**
- 10 multiple-choice and 10 written questions. Multiple-choice scores +1 or −1, written +5 or −5, blank 0. Maximum 60, pass at 36.
- Starting a test returns the existing in-progress test if there is one.
- Correct options and model answers are stripped from responses until the test is completed.
- A new test is biased towards the weak areas of the last report for that topic.

**Mock Interview**
- Durations 30, 45 or 60 minutes. Levels `STUDENT`, `JUNIOR`, `INTERMEDIATE`, `SENIOR`, `MASTER`, `ADVANCED`. Difficulty `EASY`, `MEDIUM`, `HARD`.
- A user whose profile says `STUDENT` always gets a student-level, easy interview, whatever the request says.
- At most 4 follow-ups per theme. Topic Service enforces this, not the AI.
- Ratings map to points: `STRONG` 100, `SATISFACTORY` 60, `WEAK` 20, blank 0. The report score is out of 100 and the pass mark is 75.
- The clock never pauses. A session past its deadline stays `IN_PROGRESS` in the database until the user returns, so treat it as completed when counting.
- If an AI call fails mid-interview, Topic Service asks a built-in fallback question. The report is generated on first request and regenerated if that failed.

**Experience tracks**
- The onboarding answer travels as the `experienceLevel` claim. `STUDENT` gets the placement track; every other answer gets the professional track.
- The copy in `frontend/src/features/prepTrack/tracks.ts` must stay in step with the student instructions in `ai-service/app/prompts.py`.

**Other**
- There are no per-user usage limits. An old `usage_windows` collection in `topics_db` is unused.
- Deleting a topic keeps its sessions. They still count in admin totals and show as "Deleted topics".

---

## AI Service

- All prompts live in `app/prompts.py`. `app/llm.py` wraps the OpenAI SDK; `LLM_PROVIDER` switches between OpenAI and Gemini. Model names come only from the environment, so the code does not reveal them.
- Learn Mode keeps the model on topic through the prompt itself (`SCOPE_GUARD`). Test and interview generation run `validate_topic_scope()` first. `GUARDRAILS.md` describes an older keyword-based design.
- The LLM call times out after 60 seconds; Topic Service waits up to 90 seconds for the AI Service. Generating a full test is close to that limit.
- **If you reword a prompt, update the fake LLM.** It recognises prompts by marker phrases in `loadtest/fake-llm/fake_llm/scenarios.py`. Its contract test fails when they drift.
- `test_guardrails.py` is a manual script that calls the real model. Do not run it.

---

## Frontend

- Redux Toolkit holds auth and UI state. TanStack Query holds server data.
- `@/` is an alias for `src/`. Styling is Tailwind 4 with theme tokens in `index.css`. Icons come from `lucide-react`.
- The dev server runs on port 3000 and proxies `/api`, `/oauth2` and `/login/oauth2` to `localhost:8080`. With `VITE_API_BASE_URL` unset, requests stay relative, which is also how the nginx image and Vercel serve the app.
- Admin pages are lazy-loaded chunks. Hiding a page is not access control; the admin APIs check the role themselves.
- The end-to-end tests rely on four `data-testid` values: `chat-message-ai`, `chat-message-user`, `chat-message-streaming` and `interview-question`. Keep them.
- **Analytics.** Microsoft Clarity runs only when `VITE_CLARITY_PROJECT_ID` is set at build time, which is production only. It receives the user id plus `experience` and `role` tags, never the name or email. Send events through `trackEvent` in `features/analytics/clarity.ts`. Current events: `topic_created`, `learn_message_sent`, `test_started`, `test_submitted`, `interview_started`, `interview_completed`, `feedback_sent`.
- **Feedback.** The header's Feedback button posts to `/api/v1/users/me/feedback` (up to 2000 characters). Only admins read it, at `/admin/feedback`.

---

## Configuration

- Each service reads a gitignored environment file from its own folder. The `.env.example` templates are gitignored too, so they do not reach a fresh clone. Record a new non-secret setting in this file.
- Service URLs and the allowed frontend origin come from the Spring profile, in `application-dev.yml` and `application-prod.yml`, not from the environment.
- The `dev` profile uses Docker hostnames. To run a Java service directly on your machine, pass the profile and the URLs as arguments: `--spring.profiles.active=dev`, plus `--prep-pilot.user-service-url`, `--prep-pilot.topic-service-url` and `--prep-pilot.ai-service-url` for the gateway, or `--ai-service.url` for Topic Service. Under `bootRun` the profile is not picked up from the environment file.
- Developer environment files may point at a shared database. Run tests and experiments against the `loadtest/` stack, which has its own MongoDB.

---

## Testing

- **Java.** JUnit tests in each module. Integration tests are skipped unless a throwaway MongoDB is configured; each test's Javadoc says how.
- **End to end.** Playwright specs in `e2e/tests/` cover sign-in, the dashboard, Learn, Test, Mock Interview and feedback. They run against the fake-LLM stack. See `e2e/README.md`.
- **Load.** `loadtest/run.sh` runs browser journeys with `smoke`, `stress`, `soak` and `chaos` profiles. See `loadtest/README.md`.
- **CI.** Pull requests to `main` run ESLint and `tsc` for the frontend, a Gradle build for each Java module, and non-blocking flake8 and pylint for the AI Service.

---

## Deployment

- **Gateway, User Service and Topic Service run on AWS EC2**, one instance each, as a jar under systemd. `deploy-<service>.yml` runs on a push to `main` that touches that module or `cache-service`, and calls `_deploy-service-reusable.yml`: test, build the jar, copy it over, back up the running jar, restart. `rollback-service.yml` restores the backup. Setup is in `deploy/README.md`.
- **The frontend runs on Vercel.** `frontend/vercel.json` rewrites API and OAuth paths to the gateway.
- **The AI Service runs on Vercel** through `ai-service/api/index.py`.
- **MongoDB runs on Atlas.**
- Production uses the `prod` Spring profile. When a service moves host, update the hostnames in `application-prod.yml` and `frontend/vercel.json` together.

---

## Status

All three modes, onboarding with experience tracks, test and interview history, the read-only admin pages, user feedback and analytics are built and live. There is no phase plan to follow; treat the code as the source of truth.
