"""Hardcoded response banks for the fake LLM.

Every template is generic and gets the topic (and sometimes a theme or a quote from the user)
filled in, so any technical topic gets a plausible answer. Variety comes from picking among
several variants, not from generating text.

Placeholders are filled with `fill()`, not `str.format`, because the code samples contain braces.
"""

from dataclasses import dataclass


def fill(template: str, **values: str) -> str:
    for key, value in values.items():
        template = template.replace("{" + key + "}", value)
    return template


# --------------------------------------------------------------------------------------------
# Scope checks
# --------------------------------------------------------------------------------------------

# Words that make a topic or a Learn message off-topic, the way the real model declines
# "cricket" or "pasta recipes". Matched as whole words.
OFF_TOPIC_WORDS = (
    "cricket", "football", "soccer", "basketball", "tennis", "recipe", "recipes", "cooking",
    "cook", "baking", "movie", "movies", "celebrity", "celebrities", "politics", "election",
    "dating", "relationship", "relationships", "horoscope", "astrology", "gossip", "fashion",
)

DECLINES = [
    "I can only help with technical interview preparation, so I can't help with that one. "
    "I'd be happy to cover something like {topic} concepts, data structures and algorithms, or "
    "system design instead - just tell me where you'd like to start.",
    "That's outside what I can help with: I focus on technical interview preparation and software "
    "engineering. If you like, we can work through {topic} fundamentals or practise a few "
    "interview-style questions instead.",
]


# --------------------------------------------------------------------------------------------
# Learn Mode
# --------------------------------------------------------------------------------------------

CLARIFY = [
    """Hi! I'm your PrepPilot tutor, and I'll help you get interview-ready on **{topic}**.

Before we dive in, a few quick questions so I can tailor this to you:

1. **Focus area:** Is there a particular part of {topic} you want to concentrate on - for example the core concepts, common patterns, or the trickier edge cases?
2. **Depth:** Would you like a quick refresher of the essentials, or a deep dive with examples and trade-offs?
3. **Goal:** Are you preparing for a specific interview soon, or building general knowledge of {topic}?""",
    """Hello! I'll be your guide for **{topic}** today.

To pitch this at the right level, could you tell me:

1. Which areas of {topic} feel weakest to you right now, or which sub-topic should we start with?
2. Do you want a **quick refresher** (about ten minutes of essentials) or a **deep dive** with code and design trade-offs?
3. Is this for an upcoming interview? If so, what kind of role and level is it for?""",
    """Welcome! Let's get you confident with **{topic}**.

A couple of questions first, so the material fits what you need:

1. **Where should we focus?** The fundamentals, real-world usage, or the questions interviewers love to ask?
2. **How deep should we go?** A fast overview, or a thorough walkthrough with examples?
3. **What's the goal?** General understanding, or targeted prep for an interview?""",
]

STUDENT_CLARIFY = [
    """Hi! I'm your PrepPilot tutor, and I'll help you prepare **{topic}** for your campus placements.

A few quick questions so I can plan this for you:

1. **How soon are your placements?** That decides whether we do a fast revision or build up slowly.
2. **Which parts of {topic} feel hardest?** For example definitions, output-prediction questions, or coding problems.
3. **What does your target company's process look like?** An online assessment, a technical interview, or both?""",
    """Hello! Let's get **{topic}** placement-ready.

Before we start, tell me:

1. Have you studied {topic} in your coursework, or are we starting from the basics?
2. Would you like **short notes for revision** or a **step-by-step explanation** with small examples you can run?
3. Are you preparing for online assessments, technical interviews, or both?""",
]

CONTENT_REFRESHER = [
    """Great, here's a quick refresher on **{topic}** focused on what matters most in interviews.

## The essentials

- **What it is:** {topic} gives you a structured way to solve a recurring class of engineering problems.
- **Why it matters:** it makes code easier to reason about, test and change as a system grows.
- **The trade-off:** you accept some upfront structure in exchange for long-term maintainability.

## Three things interviewers check

1. **Fundamentals** - can you explain the core idea simply, without jargon?
2. **Application** - can you use it to solve a small, concrete problem?
3. **Judgement** - do you know when *not* to use it?

## Quick example

```python
def first_unique(items):
    counts = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    for item in items:
        if counts[item] == 1:
            return item
    return None
```

Two passes over the input, so O(n) time and O(n) extra space. Being able to state the complexity like this is something interviewers look for.

## Before your interview

- Practise explaining {topic} out loud in two minutes.
- Prepare one example where it helped and one where it was the wrong tool.

Want me to quiz you on this, or go deeper into any of these points?""",
]

CONTENT_DEEP_DIVE = [
    """Thanks, that helps. Here's a structured deep dive into **{topic}**, aimed at the questions interviewers actually ask.

## 1. The mental model

Start with *why* {topic} exists. Interviewers want to hear the problem first, then the solution:

- **The problem:** as systems grow, ad-hoc solutions become hard to reason about, test and change.
- **The idea:** {topic} gives you a small set of well-defined building blocks with clear responsibilities.
- **The payoff:** code that is easier to read, test and evolve, at the cost of some upfront structure.

## 2. Core building blocks

| Concept | What it is | Why interviewers care |
|---|---|---|
| Abstractions | Stable interfaces that hide details | Shows you can design for change |
| State | The data a component owns | Most bugs live here |
| Boundaries | Where your code meets I/O | Where errors and latency show up |

## 3. A small example

```python
def word_counts(lines: list[str]) -> dict[str, int]:
    \"\"\"Count words, ignoring blanks - the kind of task used to probe fundamentals.\"\"\"
    counts: dict[str, int] = {}
    for line in lines:
        for word in line.split():
            key = word.strip(".,!?").lower()
            if key:
                counts[key] = counts.get(key, 0) + 1
    return counts
```

Walk through it out loud: input handling, the data structure choice (a hash map gives O(1) average lookups) and the overall O(n) complexity in the number of words.

## 4. Common pitfalls

1. **Skipping the "why".** Jumping into syntax before explaining the problem being solved.
2. **Ignoring failure modes.** What happens on bad input, timeouts or partial failures?
3. **Premature optimisation.** Measure first, then optimise the real bottleneck.

## 5. How this comes up in interviews

- *"Explain {topic} to a junior engineer."* Use the mental model above.
- *"What are the trade-offs?"* Name one benefit and one cost, each with an example.
- *"How would you test it?"* Unit tests for the logic, integration tests at the boundaries.

---

What would you like to explore next? I can go deeper into any section, give you practice questions, or quiz you on what we just covered.""",
    """Perfect - let's do a proper deep dive into **{topic}**.

## Why {topic} matters

Most interview questions about {topic} are really testing three things: whether you understand the **problem** it solves, whether you can **apply** it, and whether you know its **limits**. We'll cover each one.

## Core concepts

### Separation of concerns
Each part of a {topic} solution should have one clear job. When responsibilities blur, changes ripple across the codebase and bugs hide in the gaps.

### Explicit contracts
Define what goes in and what comes out. Clear contracts make components easy to test in isolation and easy to replace later.

### Failure handling
Real systems fail: networks time out, inputs are malformed, dependencies go down. A strong answer always says what happens when things go wrong.

## Worked example

Suppose you need to fetch data that is slow to compute. A simple cache is a classic interview discussion:

```python
import time

class TTLCache:
    def __init__(self, ttl_seconds: float):
        self.ttl = ttl_seconds
        self.store = {}

    def get(self, key, compute):
        hit = self.store.get(key)
        if hit and time.monotonic() - hit[1] < self.ttl:
            return hit[0]
        value = compute()
        self.store[key] = (value, time.monotonic())
        return value
```

Discussion points interviewers expect:
- **Staleness:** values can be up to `ttl` seconds old. Is that acceptable for this data?
- **Memory:** the store grows without bound; you'd add a maximum size and an eviction policy such as LRU.
- **Concurrency:** two callers can compute the same key at once (a "thundering herd").

## Trade-offs to mention

| Choice | Benefit | Cost |
|---|---|---|
| More abstraction | Flexibility, testability | Indirection, more code to read |
| Caching | Speed | Staleness, memory, invalidation |
| Strict validation | Fewer bad states | More upfront work |

## Interview tips

1. Lead with the problem, then the solution.
2. Use one concrete example rather than three vague ones.
3. Always close with a trade-off; it signals seniority.

Shall we continue with practice questions, or would you like me to expand on one of these sections?""",
]

FOLLOW_UP = {
    "example": [
        """Sure! Here's a concrete example related to your question about {quote}.

```python
from dataclasses import dataclass

@dataclass
class Order:
    id: str
    amount: float
    status: str = "PENDING"

def apply_discount(order: Order, percent: float) -> Order:
    if not 0 <= percent <= 100:
        raise ValueError("percent must be between 0 and 100")
    discounted = round(order.amount * (1 - percent / 100), 2)
    return Order(order.id, discounted, order.status)
```

What to point out when you walk an interviewer through it:

- **Validation first:** bad input fails fast with a clear error instead of corrupting data.
- **Immutability:** we return a new `Order` instead of mutating the original, which makes the function easy to test and safe to reuse.
- **Small surface:** one function, one job - the same principle applies throughout {topic}.

Would you like me to add tests for this, or show how it changes as the requirements grow?""",
        """Good idea - examples make {topic} much easier to remember. Here's one you can adapt:

```python
def retry(operation, attempts: int = 3, delay: float = 0.5):
    import time
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except TimeoutError as error:
            last_error = error
            time.sleep(delay * attempt)  # simple linear backoff
    raise last_error
```

How this connects to {quote}:

1. It isolates a cross-cutting concern (retrying) from the business logic.
2. It makes the failure policy explicit: three attempts with increasing delays.
3. It only retries errors that are worth retrying. Retrying a validation error would just fail three times.

In an interview, mention **idempotency**: retries are only safe if repeating the operation has the same effect as running it once.""",
    ],
    "compare": [
        """Good question - comparisons like {quote} come up a lot in interviews. Here's a side-by-side view:

| Aspect | Option A (simpler approach) | Option B (more structured approach) |
|---|---|---|
| Learning curve | Low | Moderate |
| Flexibility | Limited | High |
| Performance | Usually fine for small workloads | Better at scale, with tuning |
| Testability | Harder once it grows | Designed for it |
| Best for | Prototypes and small scripts | Long-lived production systems |

**How to answer this in an interview:** don't declare a winner. Say *"it depends on..."* and name the deciding factors - team size, expected scale, how long the code will live - then pick one for a concrete scenario and justify it.

Want me to walk through a scenario where each option is the right call in {topic}?""",
    ],
    "interview": [
        """Here are questions about {topic} that come up often in interviews, with what a strong answer covers:

1. **"Explain {topic} in simple terms."**
   Lead with the problem it solves, then the core idea, then one example.

2. **"What are the trade-offs?"**
   Name a concrete benefit and a concrete cost. Interviewers listen for balanced judgement.

3. **"Tell me about a bug you hit with {topic}."**
   Use a short story: symptom, how you investigated, root cause, fix, and what you changed afterwards.

4. **"How would you test it?"**
   Unit tests for logic, integration tests for boundaries, and one sentence on what you would monitor in production.

5. **"How does it behave under load?"**
   Talk about bottlenecks, measuring before optimising, and caching or batching where they make sense.

Would you like to practise one of these? Give me your answer and I'll give you feedback.""",
    ],
    "explain": [
        """Let me explain that step by step, since {quote} is a common point of confusion.

**The short version:** {topic} works by splitting a problem into well-defined pieces with clear responsibilities, so each piece can be understood, tested and changed on its own.

**Step by step:**

1. **Identify the responsibility.** What is this component *for*? If you can't say it in one sentence, it is probably doing too much.
2. **Define the contract.** What does it accept, what does it return, and what errors can it raise?
3. **Handle the edges.** Empty input, very large input, slow dependencies, concurrent callers.
4. **Verify it.** A test that pins down the behaviour, so a later change can't silently break it.

**Why it works:** each step reduces the number of things you have to keep in your head at once. That's really the whole point of good engineering practice in {topic}.

Does that clear it up? I can give you an example or a quick exercise to check your understanding.""",
        """Great question. The key idea behind {quote} is about **managing complexity**.

- At small scale almost any approach works, because you can keep the whole system in your head.
- As the codebase and the team grow, you need structure: clear boundaries, explicit contracts and predictable behaviour.
- {topic} provides that structure, at the cost of some extra upfront design.

A useful way to remember it: *structure is a loan* - you pay a little now so that every future change is cheaper.

In an interview, follow this explanation with a concrete example from a project, even a university or side project. Concrete beats abstract every time.""",
    ],
    "quiz": [
        """Let's test your understanding of {topic}. Try to answer these before scrolling down:

1. In one sentence, what problem does {topic} solve?
2. Name one situation where you would **not** use it.
3. What is the time complexity of looking up a key in a hash map, on average and in the worst case?
4. Why should a retried operation be idempotent?

---

Take your time, then reply with your answers and I'll give you feedback on each one.""",
    ],
    "default": [
        """Good question. Regarding {quote}, here's how I'd think about it in the context of {topic}:

- **Start from the requirement.** What exactly needs to happen, and what would count as "correct"?
- **Choose the simplest design that meets it.** Extra flexibility you don't need yet is a cost, not a feature.
- **Plan for failure.** Decide what happens on bad input, timeouts and partial failures.
- **Make it observable.** Logs and metrics turn a 3 a.m. mystery into a five-minute fix.

If you bring this structure to an interview answer - requirement, design, failure handling, observability - you'll come across as someone who has built real systems.

Would you like an example, or shall we move on to the next sub-topic?""",
        """That's a good point to dig into. For {quote}, the most important things to understand are:

1. **The core principle:** keep each part of your solution focused on one responsibility.
2. **The practical rule:** make the common case simple and the edge cases explicit.
3. **The interview angle:** explain your reasoning, not just the answer - interviewers grade the *how* as much as the *what*.

A common mistake is to over-engineer early. In {topic}, start simple, measure, and add structure when the code tells you it needs it.

What would you like to look at next?""",
    ],
}

# Which follow-up bank a Learn message falls into, by the first matching keyword.
FOLLOW_UP_INTENTS = (
    ("quiz", ("quiz", "test me", "practice question", "practise question")),
    ("compare", ("difference", " vs ", " vs.", "versus", "compare", "comparison")),
    ("example", ("example", "show me", "code", "snippet", "sample", "demo")),
    ("interview", ("interview", "asked", "questions")),
    ("explain", ("why", "how ", "explain", "what is", "what are", "understand")),
)


# --------------------------------------------------------------------------------------------
# Test Mode
# --------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Mcq:
    concept: str
    text: str
    options: tuple[str, str, str, str]
    correct: int = 0


@dataclass(frozen=True)
class Subjective:
    concept: str
    text: str
    model_answer: str


MCQ_BANK = (
    Mcq("Core purpose", "Which statement best describes why teams adopt {topic}?", (
        "It solves a recurring engineering problem with a well-understood set of trade-offs",
        "It removes the need for automated testing",
        "It guarantees that no runtime errors reach production",
        "It replaces the need for version control",
    )),
    Mcq("Abstractions", "When working with {topic}, what is the main benefit of a well-designed abstraction?", (
        "It hides implementation details behind a stable interface",
        "It makes every code path run faster",
        "It removes all coupling between modules",
        "It makes documentation unnecessary",
    )),
    Mcq("Error handling", "In {topic}, what is usually the best way to handle an error you cannot recover from locally?", (
        "Propagate it with enough context for a caller to handle or log it",
        "Silently ignore it so the program keeps running",
        "Retry the operation forever until it succeeds",
        "Print it to the console and continue with default values",
    )),
    Mcq("Testing", "Which kind of test gives the fastest feedback when you change a small piece of {topic} logic?", (
        "A focused unit test",
        "A full end-to-end test",
        "A manual exploratory test",
        "A load test",
    )),
    Mcq("Performance tuning", "Before optimising slow {topic} code, what should you do first?", (
        "Measure and profile to find the actual bottleneck",
        "Rewrite the code in a lower-level language",
        "Add caching to every function",
        "Double the server's memory",
    )),
    Mcq("Concurrency", "Two requests update the same shared state in a {topic} application at the same time. What is the most likely risk?", (
        "A race condition that leaves the state inconsistent",
        "A compile-time type error",
        "A memory leak in the garbage collector",
        "A DNS resolution failure",
    )),
    Mcq("Algorithmic complexity", "Code in a {topic} project loops over n items and, for each item, loops over all n items again. What is its time complexity?", (
        "O(n^2)",
        "O(n)",
        "O(log n)",
        "O(n log n)",
    )),
    Mcq("Configuration and secrets", "Where should secrets such as API keys used by a {topic} service be stored?", (
        "In environment variables or a secrets manager, outside source control",
        "Hard-coded in the source code",
        "In the README so the whole team can find them",
        "In client-side JavaScript bundles",
    )),
    Mcq("Caching", "What is the main trade-off of adding a cache in front of a {topic} component?", (
        "Faster reads at the cost of possibly serving stale data",
        "Lower memory use at the cost of slower reads",
        "Stronger consistency at the cost of availability",
        "Simpler code at the cost of more network calls",
    )),
    Mcq("Observability", "Which practice makes a production issue in a {topic} system easiest to diagnose?", (
        "Structured logs with request IDs and meaningful context",
        "Logging only when the application starts",
        "Turning logging off to improve performance",
        "Showing stack traces to end users",
    )),
    Mcq("Idempotency", "Why should a retried operation in a {topic} system ideally be idempotent?", (
        "So repeating it has the same effect as running it once",
        "So it always runs faster the second time",
        "So it never needs to be logged",
        "So it can skip input validation",
    )),
    Mcq("Design principles", "Which principle says that a {topic} module should have only one reason to change?", (
        "Single Responsibility Principle",
        "Liskov Substitution Principle",
        "Don't Repeat Yourself",
        "You Aren't Gonna Need It",
    )),
    Mcq("Data structures", "You need fast lookups by key in a {topic} program. Which data structure is usually the best fit?", (
        "A hash map",
        "A linked list",
        "A stack",
        "An unsorted array",
    )),
    Mcq("API versioning", "You need to change a public {topic} API that other teams depend on. What is the safest approach?", (
        "Version the API and deprecate the old behaviour gradually",
        "Change it in place and announce it afterwards",
        "Delete the old API immediately",
        "Ask consumers to pin an old build forever",
    )),
)

SUBJECTIVE_BANK = (
    Subjective(
        "Core concepts",
        "Explain the core idea behind {topic} to a teammate who has never used it. What problem does it solve?",
        "{topic} gives developers a structured way to solve a recurring class of problems. A good explanation "
        "names the problem first - code that becomes hard to reason about, test and change as it grows - then "
        "describes the key building blocks and how they interact, and finishes with a small concrete example. "
        "It should also mention one limitation, because no tool fits every situation.",
    ),
    Subjective(
        "Trade-offs",
        "Describe a situation where {topic} would NOT be a good choice, and what you would use instead.",
        "{topic} adds structure and indirection, which pays off for long-lived systems maintained by a team. For a "
        "small throwaway script, a prototype, or a performance-critical hot path where the overhead matters, a "
        "simpler approach is better. A strong answer names the specific cost (complexity, latency, learning curve), "
        "the alternative, and the signal that would make you switch back.",
    ),
    Subjective(
        "Debugging",
        "Walk through how you would debug an intermittent failure in a {topic} application that only happens in production.",
        "Start by collecting evidence: logs, metrics and traces around the failures, plus anything that differs from "
        "test environments (data volume, concurrency, configuration). Form a hypothesis, such as a race condition or "
        "a timeout under load, and try to reproduce it with production-like data or load. Add targeted logging if the "
        "evidence is thin. Fix the root cause, add a regression test, and add monitoring so a recurrence is caught early.",
    ),
    Subjective(
        "Testing",
        "How would you structure the tests for a new feature built with {topic}? Mention at least two kinds of tests.",
        "Use a test pyramid: many fast unit tests for the core logic and edge cases, fewer integration tests that "
        "exercise real boundaries such as the database or external APIs, and a handful of end-to-end tests for the "
        "critical user journeys. Tests should be deterministic, independent of each other, and run in CI on every change.",
    ),
    Subjective(
        "Performance tuning",
        "A {topic} endpoint has become slow as the data grew. Describe the steps you would take to find and fix the cause.",
        "Measure first: check latency percentiles and profile the endpoint to see where time goes. Common causes are "
        "missing database indexes, N+1 queries, unbounded result sets and repeated expensive computation. Fix the "
        "biggest bottleneck - add an index, paginate, batch queries or cache results - then measure again to confirm "
        "the improvement, and add a performance test or alert to catch regressions.",
    ),
    Subjective(
        "Algorithms",
        "Write a function `find_duplicates(items)` that returns the values appearing more than once in a list, in the order they first repeat. State its time complexity. (Use any language.)",
        "def find_duplicates(items):\n    seen, reported, result = set(), set(), []\n    for item in items:\n"
        "        if item in seen and item not in reported:\n            result.append(item)\n            reported.add(item)\n"
        "        seen.add(item)\n    return result\n\n# O(n) time and O(n) extra space, using hash sets for O(1) average lookups.",
    ),
    Subjective(
        "Error handling",
        "How should errors be handled and surfaced in a {topic} codebase? Give an example of a good and a bad practice.",
        "Errors should be handled at the level that can do something useful about them, and otherwise propagated with "
        "context. Good practice: validate input at the boundary and return a clear error message, while logging the "
        "details with a request ID. Bad practice: catching every exception and ignoring it, which hides bugs and leaves "
        "the system in an inconsistent state.",
    ),
    Subjective(
        "Concurrency",
        "Explain how you would prevent two concurrent updates from corrupting shared state in a {topic} system.",
        "Make the update atomic. Options include database transactions, optimistic locking with a version field (retry "
        "on conflict), pessimistic locks for short critical sections, or designing the operation as a single atomic "
        "statement. The right choice depends on contention: optimistic locking suits rare conflicts, locks suit frequent ones.",
    ),
    Subjective(
        "System design",
        "Design a simple rate limiter that a {topic} service could use to allow at most N requests per user per minute. Describe the data structure and algorithm.",
        "Use a sliding window or a token bucket per user. For a sliding window, store the timestamps of each user's "
        "recent requests (for example in a sorted set in Redis), drop entries older than 60 seconds, and reject the "
        "request if N remain. A token bucket stores a token count and last-refill time per user and refills at N per "
        "minute. Updates must be atomic so concurrent requests cannot both take the last slot.",
    ),
    Subjective(
        "Best practices",
        "List three best practices you follow when writing production-quality {topic} code and explain why each matters.",
        "1) Small, focused units with clear names - easier to read, test and change. 2) Automated tests in CI - catch "
        "regressions before users do. 3) Structured logging and metrics - make production behaviour observable. Other "
        "good answers include code review, explicit error handling and keeping dependencies up to date.",
    ),
    Subjective(
        "Caching",
        "Write a function `memoize(fn)` that caches the results of a pure function by its arguments. When would memoization be a bad idea?",
        "def memoize(fn):\n    cache = {}\n    def wrapper(*args):\n        if args not in cache:\n"
        "            cache[args] = fn(*args)\n        return cache[args]\n    return wrapper\n\n"
        "Memoization is a bad idea for impure functions (results depend on time or external state), for functions with "
        "huge argument spaces (the cache grows without bound), and when results must always be fresh.",
    ),
    Subjective(
        "Security",
        "What are the most common security mistakes developers make with {topic}, and how do you avoid them?",
        "Common mistakes: trusting user input (leading to injection attacks), hard-coding secrets, overly broad "
        "permissions, and leaking internal details in error messages. Avoid them with input validation and "
        "parameterised queries, a secrets manager, least-privilege access, generic user-facing errors with detailed "
        "server-side logs, and regular dependency updates.",
    ),
)

RETEST_TEXT = "Revisiting {weakness}: explain the key idea in your own words and show how it applies in {topic} with a concrete example."
RETEST_MODEL_ANSWER = (
    "A strong answer defines {weakness} precisely, explains why it matters in {topic}, and walks through a concrete "
    "example step by step. It closes with one common mistake related to {weakness} and how to avoid it."
)

EVAL_MCQ_CORRECT = [
    "Correct. \"{correct}\" is the right answer.",
    "Correct - you identified \"{correct}\".",
]
EVAL_MCQ_WRONG = [
    "Not quite. The correct answer is \"{correct}\". Review {concept} to see why.",
    "Incorrect. The right choice was \"{correct}\"; this is a common confusion around {concept}.",
]
EVAL_SUBJECTIVE_CORRECT = [
    "Good answer - you covered the key idea. To make it stronger, add a concrete example or mention a trade-off.",
    "Correct and clearly explained. Mentioning how you would verify this in practice would make it even better.",
]
EVAL_SUBJECTIVE_WRONG = [
    "This misses the core point. A complete answer would explain: {hint}",
    "The answer is too thin to show understanding of {concept}. Key point to cover: {hint}",
]
EVAL_NOT_ANSWERED = "Not answered. A good answer would cover: {hint}"


# --------------------------------------------------------------------------------------------
# Mock Interview
# --------------------------------------------------------------------------------------------

THEMES = (
    "{topic} Fundamentals",
    "Core Building Blocks",
    "Error Handling & Debugging",
    "Testing Strategies",
    "Data Modeling & State",
    "Performance Tuning",
    "Concurrency & Consistency",
    "Design Trade-offs",
    "Security Practices",
    "Scaling & Operations",
)

STUDENT_THEMES = (
    "{topic} Basics",
    "Key Terminology",
    "Simple Data Structures",
    "Control Flow & Logic",
    "Common Mistakes",
    "Writing Clean Code",
    "Basic Testing",
    "Small Problem Solving",
)

# Used when the plan runs out - "invent a fresh adjacent theme".
EXTRA_THEMES = (
    "Tooling & Ecosystem",
    "API Design",
    "Observability",
    "Code Review Practices",
    "Migration Strategies",
    "Reliability Engineering",
)

OPENERS = (
    "What is the single most important concept in {theme} for {topic}, and how have you applied it in practice?",
    "Imagine a teammate's change breaks something related to {theme} in a {topic} codebase. How would you track down the cause?",
    "What mistakes do engineers commonly make around {theme} in {topic}, and how do you avoid them?",
    "How would you explain {theme} in {topic} to a junior engineer, using one concrete example?",
    "Describe a decision related to {theme} in {topic} where you had to weigh two reasonable options. Which did you choose and why?",
)

FOLLOW_UPS = (
    "How would that approach hold up if the traffic or data volume grew tenfold?",
    "What would you monitor to know that approach is working correctly in production?",
    "How would you test that behaviour automatically, and what edge cases would you cover?",
    "What is a failure mode of that approach, and how would you mitigate it?",
    "If you had to build it again with half the time, what would you simplify and why?",
)

STUDENT_OPENERS = (
    "In your own words, what does {theme} mean in {topic}? Give a small example.",
    "What is a common mistake students make with {theme} in {topic}, and how would you avoid it?",
    "Can you explain the difference between two basic ideas in {theme} in {topic}, with a short example of each?",
    "If you were teaching {theme} in {topic} to a classmate, which example would you use and why?",
)

STUDENT_FOLLOW_UPS = (
    "What would happen in your example if the input were empty?",
    "How would you check that your example works correctly?",
    "Can you think of a situation where that approach would not work well?",
)

FEEDBACK = {
    "STRONG": [
        "You explained this clearly, starting from \"{quote}\", and backed it with a concrete approach. To go further, quantify the impact or explain how you would verify it in production.",
        "Strong answer: \"{quote}\" set up a well-structured explanation of {theme}. The one thing to add is a trade-off or failure mode, which shows deeper judgement.",
    ],
    "SATISFACTORY": [
        "You covered the basic idea with \"{quote}\", but the answer stayed general. Add a specific example from {theme} and explain the trade-offs you considered.",
        "A reasonable start - \"{quote}\" is on the right track - but it lacks depth for this level. Walk through a concrete scenario and name what could go wrong.",
    ],
    "WEAK": [
        "This answer did not address the question directly. A solid answer would define the key idea in {theme}, give one example, and note a common pitfall.",
        "There wasn't enough here to assess your understanding of {theme}. Next time, start with a one-sentence definition, then add an example, even a simple one.",
    ],
}

NON_ANSWERS = ("no idea", "don't know", "dont know", "do not know", "not sure", "skip", "pass", "idk")

BETTER_ANSWER = (
    "A strong answer would start by defining the core idea behind {theme} in {topic} in one or two sentences. "
    "It would then walk through a concrete example, such as a feature you built or a bug you fixed, explaining each "
    "decision along the way. Next, it would name the main trade-off - for instance simplicity versus flexibility - and "
    "when each side wins. Finally, it would mention how to verify the approach, for example with targeted tests or "
    "production metrics."
)

STUDENT_BETTER_ANSWER = (
    "A strong answer would first explain {theme} in {topic} in simple words, as you would to a classmate. "
    "It would then give a small example - a few lines of code or a step-by-step walkthrough - and say what the "
    "result is. Finally, it would mention one common mistake and how to avoid it."
)
