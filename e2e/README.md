# PrepPilot end-to-end tests (Playwright)

Browser tests for every user flow, plus browser-based load journeys. They run against the isolated stack in `loadtest/`, where the AI is a fake LLM, so a run costs no OpenAI tokens.

```bash
# from the repo root: start the stack
docker compose -f loadtest/docker-compose.yml up --build -d --wait

cd e2e
npm install
npm run install-browsers   # once: downloads Chromium

npm test                   # functional tests (project "e2e")
npm run test:headed        # the same, with the browser visible
npm run load -- --workers=10 --repeat-each=3   # load journeys directly; usually run them via loadtest/run.sh
npm run report             # open the HTML report of the last run
```

| Folder | Contents |
|---|---|
| `tests/` | Functional specs: auth, dashboard, Learn Mode, Test Mode, Mock Interview |
| `load/` | Load journeys that record timings through the `metrics` fixture |
| `support/` | Fixtures (one onboarded account per worker), UI helpers, the timing reporter |

### Configuration

| Env var | Default | Effect |
|---|---|---|
| `E2E_BASE_URL` | `http://localhost:3000` | The frontend to test |
| `E2E_AI_TIMEOUT_MS` | `120000` | Ceiling for steps that wait on the AI |
| `LOAD_THINK_TIME_MS` | `2000` | Average pause between user actions in load journeys |
| `E2E_ALLOW_REMOTE` | unset | Set to `1` to allow load journeys against a non-local host |

AI steps run at realistic speed by default; generating a test takes 30-50 seconds. For faster functional runs, start the stack with `FAKE_LLM_LATENCY_SCALE=0.1`.

Each worker registers its own account (`e2e-…@example.com`) through the API, and each test signs in through the real login form. Topic names get a random suffix, so tests can run in parallel and against a database that already has data.

The tests use roles, labels and visible text where possible. Chat bubbles and the interview question have no accessible name, so they carry `data-testid` attributes (`chat-message-ai`, `chat-message-user`, `chat-message-streaming`, `interview-question`).

See `loadtest/README.md` for the fake LLM, its failure-injection knobs, and what to watch during a load test.
