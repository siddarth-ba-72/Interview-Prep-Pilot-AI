# Contract tests

Black-box API tests that run through the gateway, so the same suite can check the legacy Spring Boot stack and the
Python rewrite. See `specs/Python-Backend-Migration-Plan.md` (Phase 0) for the background.

## Run

```bash
cd contract-tests
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# start a stack first (legacy):
#   docker compose up --build -d
# or the Python one:
#   docker compose -f docker-compose.python.yml up --build -d

BACKEND=java   pytest -m "not ai"     # no LLM calls
BACKEND=java   pytest -m ai           # needs a valid OPENAI_API_KEY in ai-service/.env
BACKEND=python pytest                 # everything, including the deliberate deviations
```

| Env var | Default | Meaning |
|---|---|---|
| `BASE_URL` | `http://localhost:8080` | Gateway URL |
| `BACKEND` | `java` | `python` also runs tests marked `python_only` (deliberate deviations D1/D3/D4) |
| `FRONTEND_ORIGIN` | `http://localhost:3000` | Origin used in CORS assertions |

Each module registers fresh `contract+<uuid>@example.com` users, so runs don't collide. Shapes are asserted with exact
key sets, so a missing or renamed field fails the test.
