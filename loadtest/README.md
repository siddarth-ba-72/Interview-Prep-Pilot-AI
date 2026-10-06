# Load testing PrepPilot

This folder runs the whole PrepPilot stack locally with a **fake LLM** in place of OpenAI. Load tests and end-to-end tests then exercise every service (frontend, gateway, user-service, topic-service, ai-service, MongoDB) without spending a single OpenAI token.

| Path | What it is |
|---|---|
| `docker-compose.yml` | The isolated stack: its own MongoDB, test-only secrets, raised usage limits, and `fake-llm` |
| `fake-llm/` | An OpenAI-compatible server that answers every PrepPilot prompt like a real model |
| `../e2e/` | Playwright tests: functional end-to-end tests and browser-based load journeys |

## How it works

```
browser / load tool ──> frontend (nginx) ──> gateway ──> user-service ──┐
                                               └──────> topic-service ──┼──> MongoDB (local container)
                                                            │
                                                            v
                                                       ai-service ──> fake-llm  (instead of api.openai.com)
```

ai-service is unchanged. The OpenAI SDK reads `OPENAI_BASE_URL`, and this stack sets it to `http://fake-llm:8090/v1`, so ai-service's real prompts, JSON parsing, repair retries and SSE streaming all stay in the path. Only the model is replaced.

### Safety

- **No real OpenAI calls.** ai-service gets a dummy `OPENAI_API_KEY`, and its image is built without `ai-service/.env`. If the base URL were ever wrong, OpenAI would answer 401 and nothing would be billed.
- **No shared database.** The stack has its own MongoDB container and volume. None of your `.env` files are read, and those point at the Atlas cluster.
- **Local ports only.** Everything binds to `127.0.0.1`.
- **Load runs stay local.** The Playwright load project refuses non-localhost targets unless you set `E2E_ALLOW_REMOTE=1`.

## Running a load test

One command does everything: it starts Docker and the stack (rebuilt from your current code), configures the fake LLM, runs the browser journeys, and saves the results.

```bash
loadtest/run.sh                 # standard: 10 users x 3 sessions each, ~5 min
loadtest/run.sh smoke           # 3 users, one of each journey, ~2 min: checks everything works
loadtest/run.sh stress          # 20 users with short pauses: where does it start to slow down?
loadtest/run.sh soak            # 5 users x 30 sessions, ~40 min: leaks and slow degradation
loadtest/run.sh chaos           # AI errors, 429s, dropped streams and bad JSON: what do users see?
loadtest/run.sh --help          # all options
```

Options can override any profile:

```bash
loadtest/run.sh --users 15 --rounds 2 --think 1000      # custom load
loadtest/run.sh --journey learn                          # only Learn Mode sessions
loadtest/run.sh --ai-speed 0.1                           # AI 10x faster than real, to stress the backend itself
loadtest/run.sh --max-p95 learn.first_token=2000 --max-p95 interview.turn=5000   # fail if slower
loadtest/run.sh --no-build                               # skip the rebuild (tests the last build)
loadtest/run.sh --fresh --down                           # empty database first, stop the stack after
```

It prints the timing table and a summary, and exits with 0 if every session passed and every `--max-p95` check held, so it also works in CI:

```
==> Summary
    sessions     3 of 3 passed
    AI calls     17 (ok 17), peak 3 at once, 7052 tokens generated
    errors       0 ERROR lines in the backend logs during the run (backend-errors.log)
    peak usage   CPU and memory per container (sampled every ~5s):
                 ai-service            7%         56 MiB
                 gateway              30%        280 MiB
                 mongodb              23%        473 MiB
                 topic-service        24%        316 MiB
                 ...
==> Checks
    ok   learn.first_token: p95 1166ms (limit 3000ms)
```

Each run gets its own folder, `loadtest/results/<date>-<time>-<profile>/` (gitignored):

| File | Contents |
|---|---|
| `run.txt` | The settings and the git commit that was tested |
| `summary.json` | p50/p90/p95/max per step, outcomes, failures grouped by reason |
| `playwright.log` | The full test output |
| `fake-llm-stats.json` | AI calls per scenario and outcome, peak concurrency, tokens |
| `docker-stats.csv`, `resources.txt` | CPU and memory of every container over the run, and the peaks |
| `backend-errors.log` | ERROR lines from gateway, user-service, topic-service and ai-service |
| `compose.log` | Output of building and starting the stack |

The stack keeps running after a run, so the next one starts in seconds. The fake LLM's settings are put back as they were, so a chaos run doesn't affect the next `npm test`. Stop the stack with `docker compose -f loadtest/docker-compose.yml down`, adding `-v` to also delete the test database.

The stack uses ports 3000, 8080, 8090 and 27019. The first two clash with the regular `docker-compose.yml` and with `npm run dev`; the script tells you if something is in the way.

### Running the pieces by hand

```bash
docker compose -f loadtest/docker-compose.yml up --build -d --wait   # start the stack
open http://localhost:3000                                            # use the app; the AI is fake-llm
cd e2e && npm test                                                    # functional end-to-end tests
npm run load -- --workers=10 --repeat-each=3                          # the load journeys directly
```

## The fake LLM

### What it answers

It recognises each prompt that ai-service sends and replies in the format ai-service expects. Content comes from hardcoded banks in `fake-llm/fake_llm/content.py`, with the topic filled in and variants picked at random:

| Scenario | Triggered by | Reply |
|---|---|---|
| `scope_check` | Topic classifier | `YES`, or `NO` for topics like "cricket" or "recipes" |
| `learn_clarify` | First Learn message | 2-3 clarifying questions (placement-focused for students) |
| `learn_content` | Reply to the clarifying questions | A structured lesson with headings, a table and code. Shorter if the user asked for a "quick refresher" |
| `learn_follow_up` | Later Learn messages | An answer matched to the question: example (code), comparison (table), interview questions, explanation, quiz |
| `learn_decline` | Off-topic Learn message | A polite refusal, as the real scope guard does |
| `test_generate` | Start a test | Exactly 10 MCQs and 10 subjective questions. A re-test targets the previous weaknesses |
| `test_evaluate` | Submit a test | MCQs graded exactly; subjective answers graded by length and overlap with the model answer; strengths and weaknesses by concept |
| `interview_plan` | Start an interview | The requested number of themes, from fundamentals to advanced |
| `interview_turn` | Each answer | Rating by answer quality (very short or "no idea" = WEAK, long = STRONG), feedback that quotes the answer, a follow-up after a STRONG answer, otherwise the next theme. Never repeats a question |
| `interview_report` | End an interview | Strengths and weaknesses by theme, a summary, and model answers for weak exchanges |

`GET http://localhost:8090/stats` shows request counts per scenario. If `unknown` shows up, ai-service sent a prompt the fake doesn't recognise, most likely because a prompt in `ai-service/app/prompts.py` was reworded. Update the marker phrases at the top of `fake-llm/fake_llm/scenarios.py`.

### Timing

By default it answers at roughly gpt-4o-mini speed:

- 350-1200 ms before the first token, a little more for long prompts
- 60-110 tokens per second (token counts are within ~10% of gpt-4o's real tokenizer)
- 2% of requests 3-8x slower to start, like a slow moment at the provider

Streaming sends one SSE event per token, like OpenAI, so ai-service and topic-service do the same per-token work as in production. Generating a 20-question test (about 3,000 tokens) takes 30-50 seconds, as it does with the real model.

### Knobs

Set them as environment variables when starting the stack, or change them while it runs:

```bash
FAKE_LLM_LATENCY_SCALE=0.1 docker compose -f loadtest/docker-compose.yml up -d   # 10x faster AI, for quick functional runs

curl -X PATCH localhost:8090/admin/config -H 'content-type: application/json' \
     -d '{"error_rate": 0.05, "slow_rate": 0.2}'    # chaos mid-test: 5% errors, 20% slow starts
curl localhost:8090/admin/config                     # current values
curl -X POST localhost:8090/admin/reset-stats        # zero the counters before a run
```

| Env var | Default | Effect |
|---|---|---|
| `FAKE_LLM_LATENCY_SCALE` | `1.0` | Multiplies every delay. `0` = instant |
| `FAKE_LLM_TTFT_MIN_MS` / `_MAX_MS` | `350` / `1200` | Time to first token range |
| `FAKE_LLM_TOKENS_PER_SEC_MIN` / `_MAX` | `60` / `110` | Output speed range |
| `FAKE_LLM_SLOW_RATE` | `0.02` | Share of requests with a 3-8x slower start |
| `FAKE_LLM_ERROR_RATE` | `0` | Share answered with an OpenAI-style 500 |
| `FAKE_LLM_RATE_LIMIT_RATE` | `0` | Share answered with an OpenAI-style 429 |
| `FAKE_LLM_STREAM_DROP_RATE` | `0` | Share of streams cut off halfway |
| `FAKE_LLM_BAD_JSON_RATE` | `0` | Share of JSON replies wrapped in prose or truncated, as real models sometimes do |
| `FAKE_LLM_SEED` | unset | Fixes the random choices for reproducible runs |

The OpenAI SDK in ai-service retries 429s and 5xx twice. An injected error rate of 10% therefore only fails about 0.1% of AI calls for good, which is how real provider errors behave too.

### Capacity

One fake-llm process held 300 concurrent streams at the configured timing in a local test. Past roughly 500 it adds latency of its own. Check `GET /stats` (`in_flight`, `peak_in_flight`) if you suspect it. ai-service is also a single Python process and is likely to saturate first, and that is part of what a load test should find.

### Tests

```bash
cd loadtest/fake-llm
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

`tests/test_ai_service_contract.py` runs ai-service's real endpoints in-process against the fake, so a change to ai-service's prompts or parsing that breaks the fake fails here. These tests never call OpenAI.

## How the load test works

### Browser journeys (Playwright)

`e2e/load/journeys.spec.ts` has three realistic sessions: studying in Learn Mode, taking a test, and doing a mock interview. Each one includes pauses for reading and typing. Every Playwright worker is one concurrent user with its own account.

At the end it prints p50/p90/p95/max for each step and writes `summary.json` (into the run's results folder when `run.sh` started it, otherwise `e2e/load-results/`):

```
Timings over 85s with 4 worker(s); tests: {"passed":6}
metric              count      p50      p90      p95      max
-----------------   -----   ------   ------   ------   ------
auth.sign_in            6    497ms    504ms    504ms    504ms
interview.report        2   5385ms   5903ms   5903ms   5903ms
interview.start         2   3936ms   6958ms   6958ms   6958ms
interview.turn          6   2365ms   3357ms   3357ms   3357ms
learn.first_token       8    999ms   1164ms   1164ms   1164ms
learn.full_reply        8   3822ms    10.4s    10.4s    10.4s
learn.open              2   2866ms   3377ms   3377ms   3377ms
test.generate           2    42.2s    48.7s    48.7s    48.7s
test.grade              2    17.7s    22.3s    22.3s    22.3s
topic.create            6     98ms    101ms    101ms    101ms
```

(From a short run with 4 users.)

These timings are what users see, measured in a real browser: time until the first token appears on screen, until the reply is complete, until the test is generated.

A browser uses about 100-300 MB, so one machine runs tens of users, not thousands. For more volume, run a protocol-level tool (Locust or k6) against `http://localhost:8080` at the same time, and use the Playwright journeys to see what users experience under that load.

### What to watch live

`run.sh` saves all of this per run. To watch while a test is running:

- `docker stats` for CPU and memory of each container
- `curl localhost:8090/stats` for AI calls per scenario, in-flight streams and injected failures
- `docker compose -f loadtest/docker-compose.yml logs -f topic-service ai-service` for errors
- MongoDB at `mongodb://root:loadtest@localhost:27019/?authSource=admin` (mongosh or Compass)

### Usage limits

The stack raises all usage limits to 100,000 through `SPRING_APPLICATION_JSON` on topic-service, so virtual users aren't stopped by `429 USAGE_LIMIT_REACHED`. To test the real limits, remove that variable and restart topic-service.
