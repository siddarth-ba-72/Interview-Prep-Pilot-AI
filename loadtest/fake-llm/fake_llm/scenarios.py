"""Works out which ai-service call a chat request belongs to, and builds the reply.

Detection keys off phrases in the prompts that ai-service/app/prompts.py (and scope_validator.py)
send. If those prompts are reworded, update the markers below; unknown prompts get a generic
reply and are counted as `unknown` in /stats, so a drift shows up there.
"""

import json
import random
import re
import uuid
from dataclasses import dataclass

from fake_llm import content
from fake_llm.content import fill


@dataclass
class Reply:
    scenario: str
    text: str
    is_json: bool = False


# Marker phrase -> scenario, checked against the first system message.
_SYSTEM_MARKERS = (
    ("content scope classifier", "scope_check"),
    ("Generate exactly 20 interview questions", "test_generate"),
    ("evaluating a student's test answers", "test_evaluate"),
    ("designing the structure of a mock interview", "interview_plan"),
    ("conducting a live, spoken-style technical interview", "interview_turn"),
    ("writing the final report for a completed mock interview", "interview_report"),
)

# Learn Mode puts its per-turn instruction in the last system message.
_LEARN_MARKERS = (
    ("just selected the topic", "learn_clarify"),
    ("has answered your clarifying questions", "learn_content"),
    ("Continue the conversation about", "learn_follow_up"),
)


def respond(messages: list[dict], rng: random.Random, json_mode: bool = False) -> Reply:
    system_messages = [_text(m) for m in messages if m.get("role") == "system"]
    first_system = system_messages[0] if system_messages else ""

    for marker, scenario in _SYSTEM_MARKERS:
        if marker in first_system:
            return _HANDLERS[scenario](messages, first_system, rng)

    last_system = system_messages[-1] if system_messages else ""
    for marker, scenario in _LEARN_MARKERS:
        if marker in last_system:
            return _learn(scenario, messages, first_system, last_system, rng)

    if json_mode:
        return Reply("unknown", json.dumps({"result": "This is a placeholder response from the fake LLM."}), True)
    return Reply("unknown", "This is a placeholder response from the fake LLM. It did not recognise this prompt.")


# --------------------------------------------------------------------------------------------
# Scope check (ai-service/app/scope_validator.py)
# --------------------------------------------------------------------------------------------

def _scope_check(messages: list[dict], system: str, rng: random.Random) -> Reply:
    topic = _search(r"Topic: (.+)", _last_user(messages)) or ""
    return Reply("scope_check", "NO" if _is_off_topic(topic) else "YES")


# --------------------------------------------------------------------------------------------
# Learn Mode
# --------------------------------------------------------------------------------------------

def _learn(scenario: str, messages: list[dict], system: str, instruction: str, rng: random.Random) -> Reply:
    topic = _search(r'is "(.+?)" - and the student', instruction) or "this topic"
    student = "college student preparing for campus placements" in system
    latest = _last_user(messages)

    if _is_off_topic(topic) or (scenario != "learn_clarify" and _is_off_topic(latest)):
        safe_topic = "programming languages" if _is_off_topic(topic) else topic
        return Reply("learn_decline", fill(rng.choice(content.DECLINES), topic=safe_topic))

    if scenario == "learn_clarify":
        bank = content.STUDENT_CLARIFY if student else content.CLARIFY
        return Reply(scenario, fill(rng.choice(bank), topic=topic))

    if scenario == "learn_content":
        wants_short = _contains_any(latest.lower(), ("quick", "refresher", "brief", "short", "overview", "summary"))
        bank = content.CONTENT_REFRESHER if wants_short else content.CONTENT_DEEP_DIVE
        return Reply(scenario, fill(rng.choice(bank), topic=topic))

    intent = next(
        (name for name, words in content.FOLLOW_UP_INTENTS if _contains_any(f" {latest.lower()} ", words)),
        "default",
    )
    quote = f'"{_shorten(latest, 70)}"' if latest else topic
    return Reply(scenario, fill(rng.choice(content.FOLLOW_UP[intent]), topic=topic, quote=quote))


# --------------------------------------------------------------------------------------------
# Test Mode
# --------------------------------------------------------------------------------------------

def _test_generate(messages: list[dict], system: str, rng: random.Random) -> Reply:
    topic = _search(r"for the topic: (.+?)\. Structure", system) or "this topic"
    weaknesses = _bullets_after(system, "showed these weak areas") if "This is a RE-TEST" in system else []

    questions = []
    for item in rng.sample(content.MCQ_BANK, 10):
        correct = fill(item.options[item.correct], topic=topic)
        options = [fill(option, topic=topic) for option in item.options]
        rng.shuffle(options)
        questions.append({
            "questionId": _uuid(rng),
            "section": "MCQ",
            "text": fill(item.text, topic=topic),
            "options": options,
            "correctOption": correct,
            "modelAnswer": None,
        })

    subjective = []
    # A re-test spends most of its subjective questions on last attempt's weak areas.
    for weakness in weaknesses[:6]:
        subjective.append((
            fill(content.RETEST_TEXT, weakness=weakness, topic=topic),
            fill(content.RETEST_MODEL_ANSWER, weakness=weakness, topic=topic),
        ))
    for item in rng.sample(content.SUBJECTIVE_BANK, 10 - len(subjective)):
        subjective.append((fill(item.text, topic=topic), fill(item.model_answer, topic=topic)))

    for text, model_answer in subjective:
        questions.append({
            "questionId": _uuid(rng),
            "section": "SUBJECTIVE",
            "text": text,
            "options": None,
            "correctOption": None,
            "modelAnswer": model_answer,
        })

    return Reply("test_generate", json.dumps({"questions": questions}, indent=2), is_json=True)


_ANSWER_BLOCK = re.compile(
    r"QuestionId: (?P<id>.*?)\nSection: (?P<section>\w+)\nQuestion: (?P<question>.*?)\n"
    r"  Correct: (?P<correct>.*?)\n  User: (?P<user>.*?)(?=\n+QuestionId: |\s*\Z)",
    re.S,
)


def _test_evaluate(messages: list[dict], system: str, rng: random.Random) -> Reply:
    user = _last_user(messages)
    topic = _search(r"Topic: (.+)", user) or "this topic"
    student = "college student preparing for campus placements" in system
    concepts = _concept_index(topic)

    per_question, strengths, weaknesses = [], [], []
    for block in _ANSWER_BLOCK.finditer(user):
        question = block["question"].strip()
        correct = block["correct"].strip()
        answer = block["user"].strip()
        answered = answer and answer != "Not answered"
        concept = _concept_for(question, concepts, topic)
        hint = _first_sentence(correct)

        if block["section"] == "MCQ":
            is_correct = answered and answer.lower() == correct.lower()
            template = content.EVAL_MCQ_CORRECT if is_correct else content.EVAL_MCQ_WRONG
            evaluation = fill(rng.choice(template), correct=correct, concept=concept.lower())
        else:
            is_correct = answered and _subjective_is_correct(answer, correct, student)
            if not answered:
                evaluation = fill(content.EVAL_NOT_ANSWERED, hint=hint)
            else:
                template = content.EVAL_SUBJECTIVE_CORRECT if is_correct else content.EVAL_SUBJECTIVE_WRONG
                evaluation = fill(rng.choice(template), hint=hint, concept=concept.lower())

        per_question.append({"questionId": block["id"].strip(), "isCorrect": bool(is_correct), "evaluation": evaluation})
        (strengths if is_correct else weaknesses).append(concept)

    return Reply(
        "test_evaluate",
        json.dumps({
            "perQuestion": per_question,
            "strengths": _unique(strengths)[:4],
            "weaknesses": _unique(weaknesses)[:4],
        }, indent=2),
        is_json=True,
    )


def _subjective_is_correct(answer: str, reference: str, student: bool) -> bool:
    words = answer.split()
    if len(words) >= (25 if student else 40):
        return True
    reference_terms = {w for w in re.findall(r"[a-z]{5,}", reference.lower())}
    overlap = reference_terms & set(re.findall(r"[a-z]{5,}", answer.lower()))
    return len(words) >= (8 if student else 12) and len(overlap) >= 2


def _concept_index(topic: str) -> dict[str, str]:
    index = {fill(item.text, topic=topic): item.concept for item in content.MCQ_BANK}
    index.update({fill(item.text, topic=topic): item.concept for item in content.SUBJECTIVE_BANK})
    return index


def _concept_for(question: str, index: dict[str, str], topic: str) -> str:
    if question in index:
        return index[question]
    weakness = _search(r"^Revisiting (.+?): explain", question)
    return weakness or f"{topic} fundamentals"


# --------------------------------------------------------------------------------------------
# Mock Interview
# --------------------------------------------------------------------------------------------

def _interview_plan(messages: list[dict], system: str, rng: random.Random) -> Reply:
    topic = _search(r"mock interview on (.+?) for a \S+ candidate", system) or "this topic"
    count = int(_search(r"Produce exactly (\d+) themes", system) or 4)
    student = "college student with no professional experience" in system
    bank = content.STUDENT_THEMES if student else content.THEMES
    themes = [fill(theme, topic=topic) for theme in bank[:count]]
    return Reply("interview_plan", json.dumps({"themes": themes}, indent=2), is_json=True)


def _interview_turn(messages: list[dict], system: str, rng: random.Random) -> Reply:
    # The turn prompt is the first user message; a duplicate-question retry appends another one.
    prompt = next((_text(m) for m in messages if m.get("role") == "user"), "")
    retrying = any("has already been asked" in _text(m) for m in messages[2:])
    student = "This candidate is a college student" in system

    topic = _line_value(prompt, "TOPIC") or "this topic"
    current_theme = _line_value(prompt, "CURRENT THEME") or f"{topic} Fundamentals"
    must_advance = _line_value(prompt, "MUST ADVANCE TO NEXT THEME") == "YES"
    follow_ups = re.search(r"FOLLOW-UPS USED ON THIS THEME: (\d+) of (\d+)", prompt)
    used, budget = (int(follow_ups[1]), int(follow_ups[2])) if follow_ups else (0, 4)
    plan, current_index = _theme_plan(prompt)
    asked = {_normalize(q) for q in _bullets_after(prompt, "QUESTIONS ALREADY ASKED")}

    if "THIS IS THE OPENING TURN" in prompt:
        theme = current_theme if not current_theme.startswith("(") else (plan[0] if plan else f"{topic} Fundamentals")
        question = _pick_question(content.STUDENT_OPENERS if student else content.OPENERS, theme, topic, asked, rng, retrying)
        turn = {"evaluation": None, "next": {"question": question, "theme": theme, "isFollowUp": False, "advanceTheme": False}}
        return Reply("interview_turn", json.dumps(turn, indent=2), is_json=True)

    answer = _search(r"<<<ANSWER\n(.*?)\nANSWER>>>", prompt, re.S) or ""
    graded_theme = _search(r"THE QUESTION THE CANDIDATE JUST ANSWERED.*?\n  theme: ([^\n]+)", prompt, re.S) or current_theme
    rating = _rate(answer, student)
    quote = _shorten(answer, 60) if answer and not answer.startswith("(the candidate") else "your answer"
    feedback = fill(rng.choice(content.FEEDBACK[rating]), quote=quote, theme=graded_theme)

    if rating == "STRONG" and not must_advance and used < budget:
        theme = current_theme if not current_theme.startswith("(") else graded_theme
        bank = content.STUDENT_FOLLOW_UPS if student else content.FOLLOW_UPS
        question = _pick_question(bank, theme, topic, asked, rng, retrying)
        next_turn = {"question": question, "theme": theme, "isFollowUp": True, "advanceTheme": False}
    else:
        theme = _next_theme(plan, current_index, asked_themes=_transcript_themes(prompt), rng=rng)
        bank = content.STUDENT_OPENERS if student else content.OPENERS
        question = _pick_question(bank, theme, topic, asked, rng, retrying)
        next_turn = {"question": question, "theme": theme, "isFollowUp": False, "advanceTheme": True}

    turn = {"evaluation": {"rating": rating, "feedback": feedback}, "next": next_turn}
    return Reply("interview_turn", json.dumps(turn, indent=2), is_json=True)


def _rate(answer: str, student: bool) -> str:
    text = answer.strip()
    if not text or text.startswith("(the candidate submitted nothing)"):
        return "WEAK"
    words = len(text.split())
    if words < 6 or (words < 20 and _contains_any(text.lower(), content.NON_ANSWERS)):
        return "WEAK"
    if words < (25 if student else 35):
        return "SATISFACTORY"
    return "STRONG"


def _theme_plan(prompt: str) -> tuple[list[str], int]:
    block = _search(r"THEME PLAN:\n(.*?)\nCURRENT THEME:", prompt, re.S) or ""
    plan, current = [], len(block.splitlines())
    for line in block.splitlines():
        match = re.match(r"^(->| {2}) (\d+)\. (.+)$", line)
        if match:
            if match[1] == "->":
                current = len(plan)
            plan.append(match[3].strip())
    return plan, current


def _next_theme(plan: list[str], current_index: int, asked_themes: set[str], rng: random.Random) -> str:
    if 0 <= current_index + 1 < len(plan):
        return plan[current_index + 1]
    fresh = [t for t in content.EXTRA_THEMES if t not in asked_themes and t not in plan]
    return fresh[0] if fresh else rng.choice(content.EXTRA_THEMES)


def _transcript_themes(prompt: str) -> set[str]:
    return set(re.findall(r"^\[\d+\] theme: (.+)$", prompt, re.M))


def _pick_question(bank, theme: str, topic: str, asked: set[str], rng: random.Random, retrying: bool) -> str:
    candidates = [fill(q, theme=theme, topic=topic) for q in bank]
    fresh = [q for q in candidates if _normalize(q) not in asked]
    if retrying and len(fresh) > 1:
        fresh = fresh[1:]
    if fresh:
        return rng.choice(fresh)
    # Every template was used on this theme already; vary the wording so it is still new.
    return f"Thinking about {theme} in {topic} once more: what would you do differently on your next project, and why? (#{len(asked) + 1})"


def _interview_report(messages: list[dict], system: str, rng: random.Random) -> Reply:
    prompt = _last_user(messages)
    topic = _line_value(prompt, "TOPIC") or "this topic"
    student = "This candidate is a college student" in system
    exchanges = [
        {
            "theme": match["theme"].strip(),
            "rating": match["rating"].strip().upper(),
            "question": match["question"].strip(),
            "answer": match["answer"].strip(),
        }
        for match in re.finditer(
            r"^\[\d+\] theme: (?P<theme>.*?) \| rating: (?P<rating>\S+)\n    Q: (?P<question>.*?)\n    A: (?P<answer>.*?)"
            r"(?=\n\[\d+\] theme: |\n\nWrite the report|\Z)",
            prompt,
            re.S | re.M,
        )
    ]

    if not exchanges:
        report = {
            "strengths": [],
            "weaknesses": [],
            "overallSummary": (
                "You ended the interview before answering any questions, so there is nothing to assess yet. "
                "Start a new interview and answer at least a few questions to get meaningful feedback."
            ),
            "improvementSuggestions": [],
        }
        return Reply("interview_report", json.dumps(report, indent=2), is_json=True)

    by_theme: dict[str, list[str]] = {}
    for exchange in exchanges:
        by_theme.setdefault(exchange["theme"], []).append(exchange["rating"])
    strengths = [t for t, ratings in by_theme.items() if ratings.count("STRONG") * 2 > len(ratings)]
    weaknesses = [t for t in by_theme if t not in strengths]

    strong = sum(1 for e in exchanges if e["rating"] == "STRONG")
    summary = [f"You answered {len(exchanges)} question{'s' if len(exchanges) != 1 else ''} across {len(by_theme)} theme{'s' if len(by_theme) != 1 else ''} on {topic}."]
    if strengths:
        summary.append(f"Your strongest area was {strengths[0]}, where your answers were specific and well structured.")
    else:
        summary.append("None of the themes reached a consistently strong level yet.")
    if weaknesses:
        summary.append(f"Answers on {', '.join(weaknesses[:3])} stayed general; concrete examples and trade-offs would lift them.")
    if strong * 2 >= len(exchanges):
        summary.append("Overall this was a solid performance - keep practising explaining your reasoning out loud.")
    else:
        summary.append("Focus your next study session on the weaker themes, then try another interview to measure progress.")

    better = content.STUDENT_BETTER_ANSWER if student else content.BETTER_ANSWER
    suggestions = [
        {
            "question": e["question"],
            "userAnswer": None if e["answer"] == "(no answer given)" else e["answer"],
            "theme": e["theme"],
            "betterAnswer": fill(better, theme=e["theme"], topic=topic),
        }
        for e in exchanges
        if e["rating"] in ("WEAK", "SATISFACTORY", "UNRATED")
    ]
    report = {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "overallSummary": " ".join(summary),
        "improvementSuggestions": suggestions,
    }
    return Reply("interview_report", json.dumps(report, indent=2), is_json=True)


_HANDLERS = {
    "scope_check": _scope_check,
    "test_generate": _test_generate,
    "test_evaluate": _test_evaluate,
    "interview_plan": _interview_plan,
    "interview_turn": _interview_turn,
    "interview_report": _interview_report,
}


# --------------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------------

def _text(message: dict) -> str:
    value = message.get("content") or ""
    if isinstance(value, list):  # content parts: [{"type": "text", "text": "..."}]
        return "".join(part.get("text", "") for part in value if isinstance(part, dict))
    return str(value)


def _last_user(messages: list[dict]) -> str:
    return next((_text(m) for m in reversed(messages) if m.get("role") == "user"), "")


def _search(pattern: str, text: str, flags: int = 0) -> str | None:
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else None


def _line_value(text: str, label: str) -> str | None:
    return _search(rf"^{re.escape(label)}: (.+)$", text, re.M)


def _bullets_after(text: str, heading: str) -> list[str]:
    """The "- item" lines that follow the line containing `heading`."""
    start = text.find(heading)
    if start == -1:
        return []
    items = []
    for line in text[start:].splitlines()[1:]:
        if line.startswith("- "):
            items.append(line[2:].strip())
        elif items or line.strip():
            break
    return [item for item in items if item and item != "(none recorded)"]


def _is_off_topic(text: str) -> bool:
    words = set(re.findall(r"[a-z]+", text.lower()))
    return any(word in words for word in content.OFF_TOPIC_WORDS)


def _contains_any(text: str, needles) -> bool:
    return any(needle in text for needle in needles)


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _shorten(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 3].rsplit(" ", 1)[0] + "..."


def _first_sentence(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    match = re.match(r"(.+?[.!?])(\s|$)", text)
    return match.group(1) if match else _shorten(text, 160)


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _uuid(rng: random.Random) -> str:
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))
