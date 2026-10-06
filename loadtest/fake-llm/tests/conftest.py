import os
import random
import sys
from pathlib import Path

import pytest

FAKE_LLM_DIR = Path(__file__).resolve().parents[1]
AI_SERVICE_DIR = FAKE_LLM_DIR.parents[1] / "ai-service"

# Nothing here may reach the real OpenAI API: ai-service's client is replaced with one wired to
# the fake in-process, and these values make any client that slips through fail instead.
os.environ["OPENAI_API_KEY"] = "sk-fake-test-not-a-real-key"
os.environ["OPENAI_BASE_URL"] = "http://openai.invalid/v1"
os.environ["FAKE_LLM_LATENCY_SCALE"] = "0"

sys.path.insert(0, str(FAKE_LLM_DIR))
sys.path.insert(0, str(AI_SERVICE_DIR))

from fake_llm import main as fake  # noqa: E402
from fake_llm.config import Settings  # noqa: E402


@pytest.fixture(autouse=True)
def instant_fake_llm():
    """Every test starts with no delays, no injected failures and fixed random choices."""
    fake.settings = Settings(latency_scale=0, slow_rate=0, seed=7)
    fake.rng = random.Random(7)
    fake.stats.reset()
    yield fake
