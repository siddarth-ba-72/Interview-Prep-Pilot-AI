from app.schemas import ChatMessage, LearnMode, Role

SYSTEM_PROMPT = (
    "You are an expert technical interviewer and teacher helping a student prepare "
    "for technical interviews. You are precise, encouraging, and focus on the "
    "practical knowledge a candidate needs to succeed. Keep responses well "
    "structured with headings and bullet points where helpful."
)

CLARIFY_INSTRUCTION = (
    "The student just selected the topic \"{topic_name}\" to learn. Briefly introduce "
    "yourself in one sentence, then ask 2-3 focused clarifying questions to tailor the "
    "learning content: (1) which sub-topic or area within {topic_name} they want to "
    "focus on, (2) how deep they want to go (quick refresher vs. deep dive), and "
    "(3) whether they want general knowledge or interview-focused preparation. "
    "Do not teach any content yet - only ask the questions."
)

GENERATE_CONTENT_INSTRUCTION = (
    "The student has answered your clarifying questions about \"{topic_name}\". Using "
    "their answers from the conversation so far, generate structured learning content "
    "tailored to what they asked for. Use headings, bullet points, and short code "
    "examples where relevant. End by inviting them to ask follow-up questions."
)

FOLLOW_UP_INSTRUCTION = (
    "Continue the conversation about \"{topic_name}\" as a knowledgeable, contextual "
    "tutor. Treat the full message history as an ongoing conversation and respond "
    "directly to the student's latest message."
)


# Test Mode Prompts
TEST_GENERATION_SYSTEM_PROMPT = (
    "You are an expert technical interviewer. Generate exactly 20 interview questions "
    "for the topic: {topic_name}. "
    "Structure: 10 multiple-choice questions (each with exactly 4 options and one clearly correct answer) "
    "and 10 subjective/open-ended or code-completion questions with a model answer. "
    "Vary difficulty (beginner/intermediate/advanced), vary sub-topics to make each test feel distinct, "
    "and never repeat questions from previous tests. "
    "MCQ distractors should be plausible (not obviously wrong). "
    "For subjective questions, include a complete, correct reference answer (modelAnswer). "
    "Return response in this EXACT JSON format (no markdown, no extra text):\n"
    "{{\n"
    '  "questions": [\n'
    "    {{\n"
    '      "questionId": "uuid-string",\n'
    '      "section": "MCQ",\n'
    '      "text": "question text",\n'
    '      "options": ["option1", "option2", "option3", "option4"],\n'
    '      "correctOption": "the correct option text",\n'
    '      "modelAnswer": null\n'
    "    }},\n"
    "    {{\n"
    '      "questionId": "uuid-string",\n'
    '      "section": "SUBJECTIVE",\n'
    '      "text": "question text or code task",\n'
    '      "options": null,\n'
    '      "correctOption": null,\n'
    '      "modelAnswer": "complete reference answer or code solution"\n'
    "    }}\n"
    "  ]\n"
    "}}"
)

# Used when a previous attempt's report shows one or more weak areas. Retest should
# skew heavily toward reinforcing those weaknesses while still confirming retained strengths.
RETEST_WEAKNESS_FOCUSED_INSTRUCTION = (
    "This is a RE-TEST. The student previously took a test on {topic_name} and their report "
    "showed these weak areas (topics/concepts they struggled with):\n"
    "{weaknesses_list}\n\n"
    "Their strong areas (topics they already answered well) were:\n"
    "{strengths_list}\n\n"
    "Decide the exact split yourself based on how many weak areas were identified, but follow these rules:\n"
    "1. The MAJORITY of the 20 questions must reinforce the weak areas above. Reuse the same underlying "
    "concepts/sub-topics as the weaknesses, but rephrase, change difficulty, or use different examples/code "
    "so it is not a verbatim repeat of any earlier question - this is repetitive reinforcement, not duplication.\n"
    "2. Include ONLY 1-2 questions total drawn from the strong areas above, as a light spaced-repetition "
    "check-in to confirm the student still retains that knowledge. Do not spend more than 2 questions on strengths.\n"
    "3. If there are very few weak areas listed, you may fill the remaining questions with new or adjacent "
    "sub-topics within {topic_name} rather than over-repeating a single weak area.\n"
    "4. Never repeat the exact same question text from a previous test."
)

# Used when the student had no weaknesses (a clean pass) or this is their first attempt.
RETEST_FRESH_INSTRUCTION = (
    "The student has no recorded weak areas from their most recent attempt at {topic_name} "
    "(or this is their first attempt). Generate a completely fresh set of 20 questions covering "
    "{topic_name} broadly - explore different sub-topics than a typical first test would, "
    "or go deeper into advanced areas, so the retest still feels new and challenging."
)

TEST_EVALUATION_SYSTEM_PROMPT = (
    "You are an expert technical interviewer evaluating a student's test answers. "
    "For each question provided in the evaluation request, determine if the user's answer is correct (true/false), "
    "provide concise 1-2 sentence feedback, and return overall topic strengths and weaknesses. "
    "Be fair but rigorous; accept equivalent correct answers. "
    "IMPORTANT: Return evaluations in the EXACT SAME ORDER as the questions were provided, "
    "and include the exact same questionId for each evaluation. "
    "Return response in this EXACT JSON format (no markdown, no extra text):\n"
    "{\n"
    '  "perQuestion": [\n'
    "    {\n"
    '      "questionId": "<use the exact questionId from the provided question>",\n'
    '      "isCorrect": true/false,\n'
    '      "evaluation": "brief feedback sentence(s)"\n'
    "    }\n"
    "  ],\n"
    '  "strengths": ["strength1", "strength2"],\n'
    '  "weaknesses": ["weakness1", "weakness2"]\n'
    "}"
)


def build_messages(topic_name: str, mode: LearnMode, history: list[ChatMessage]) -> list[dict]:
    instruction = {
        LearnMode.CLARIFY: CLARIFY_INSTRUCTION,
        LearnMode.GENERATE_CONTENT: GENERATE_CONTENT_INSTRUCTION,
        LearnMode.FOLLOW_UP: FOLLOW_UP_INSTRUCTION,
    }[mode].format(topic_name=topic_name)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for message in history:
        role = "assistant" if message.role == Role.AI else "user"
        messages.append({"role": role, "content": message.content})
    messages.append({"role": "system", "content": instruction})
    return messages


def build_test_generation_messages(
    topic_name: str,
    strengths: list[str] | None = None,
    weaknesses: list[str] | None = None,
) -> list[dict]:
    """Build messages for test question generation.

    If `weaknesses` from a previous attempt are provided (non-empty), bias the generated
    questions toward reinforcing those weak areas with only light spaced-repetition on
    strengths. Otherwise (no previous attempt, or previous attempt had no weaknesses),
    generate a fresh set of questions as usual.
    """
    system_content = TEST_GENERATION_SYSTEM_PROMPT.format(topic_name=topic_name)

    if weaknesses:
        weaknesses_list = "\n".join(f"- {w}" for w in weaknesses)
        strengths_list = "\n".join(f"- {s}" for s in strengths) if strengths else "(none recorded)"
        system_content += "\n\n" + RETEST_WEAKNESS_FOCUSED_INSTRUCTION.format(
            topic_name=topic_name,
            weaknesses_list=weaknesses_list,
            strengths_list=strengths_list,
        )
        user_content = (
            f"Generate 10 MCQ and 10 SUBJECTIVE questions for {topic_name}, "
            f"focused mostly on reinforcing the weak areas listed above."
        )
    else:
        system_content += "\n\n" + RETEST_FRESH_INSTRUCTION.format(topic_name=topic_name)
        user_content = f"Generate 10 MCQ and 10 SUBJECTIVE questions for {topic_name}."

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content}
    ]


def build_test_evaluation_messages(topic_name: str, answers: list[dict]) -> list[dict]:
    """Build messages for test answer evaluation."""
    answers_text = "\n".join([
        f"QuestionId: {a.get('questionId', f'Q{i+1}')}\n"
        f"Section: {a['section']}\n"
        f"Question: {a['question']}\n"
        f"  Correct: {a['correctAnswer']}\n"
        f"  User: {a['userAnswer'] or 'Not answered'}\n"
        for i, a in enumerate(answers)
    ])
    
    return [
        {"role": "system", "content": TEST_EVALUATION_SYSTEM_PROMPT},
        {"role": "user", "content": f"Topic: {topic_name}\nEvaluate these answers:\n\n{answers_text}"}
    ]



# Mock Interview Prompts
#
# The turn prompt is the hot path: it both grades the answer the candidate just gave and
# produces the next question. Getting it wrong shows up as generic questions, repeated
# questions, or ratings that ignore what the candidate actually wrote - so the context we
# hand the model (especially *which* question is being graded) is spelled out explicitly.

EXPERIENCE_LEVEL_BAR = {
    "JUNIOR": "0-2 years. Expect correct fundamentals and clear definitions. A textbook-accurate "
              "explanation with a simple example is STRONG. Do not require production war stories.",
    "INTERMEDIATE": "2-5 years. Expect correct fundamentals plus practical usage and awareness of common "
                    "pitfalls. A bare definition with no application is SATISFACTORY at best.",
    "SENIOR": "5-8 years. Expect design reasoning, trade-offs, failure modes and production experience. "
              "A textbook definition alone is WEAK; STRONG requires nuance and justified choices.",
    "MASTER": "8-13 years. Expect deep internals, cross-cutting trade-offs, scalability/operability "
              "concerns and opinionated, well-argued judgement. Surface-level correctness is WEAK.",
    "ADVANCED": "13+ years. Expect architectural judgement, ecosystem-level context, migration/legacy "
                "reasoning and awareness of where the technology itself falls short. Only genuinely "
                "insightful, well-structured answers are STRONG.",
}


def _experience_bar(experience_level: str) -> str:
    return EXPERIENCE_LEVEL_BAR.get(
        (experience_level or "").upper(),
        EXPERIENCE_LEVEL_BAR["INTERMEDIATE"],
    )


INTERVIEW_PLAN_SYSTEM_PROMPT = (
    "You are an expert technical interviewer designing the structure of a mock interview on "
    "{topic_name} for a {experience_level} candidate at {difficulty} difficulty, lasting "
    "{duration_minutes} minutes.\n\n"
    "Produce an ordered list of THEME LABELS - the sub-topics/areas within {topic_name} to cover. "
    "Rules:\n"
    "1. Each theme is a short noun phrase of 2-5 words (e.g. \"Dependency Injection & Beans\"). "
    "Themes are NOT questions - never write a sentence ending in a question mark.\n"
    "2. Produce exactly {theme_count} themes.\n"
    "3. Order them foundational first, advanced last, so the interview escalates naturally.\n"
    "4. Themes must be distinct and non-overlapping - do not restate the same area twice.\n"
    "5. Every theme must be genuinely about {topic_name}, specific enough that a question can be "
    "asked about it. Avoid filler themes like \"General knowledge\", \"Miscellaneous\" or \"Wrap up\".\n"
    "6. Calibrate the selection to a {experience_level} candidate at {difficulty} difficulty - a "
    "junior plan covers core mechanics, a senior/advanced plan covers design, trade-offs and "
    "operational concerns.\n\n"
    "Return ONLY this JSON object (no markdown, no commentary):\n"
    "{{\n"
    '  "themes": ["theme label", "theme label"]\n'
    "}}"
)

INTERVIEW_TURN_SYSTEM_PROMPT = (
    "You are conducting a live, spoken-style technical interview. On every turn you do exactly two "
    "things in one JSON response: (1) grade the answer the candidate just gave, and (2) ask the next "
    "question.\n\n"

    "## Grading the answer\n"
    "You are given the exact question that was asked and the exact answer the candidate typed. Grade "
    "THAT answer against THAT question - never against an earlier question in the transcript.\n"
    "- STRONG: correct, and meets the depth bar for this candidate's experience level.\n"
    "- SATISFACTORY: broadly correct but shallow, partially incomplete, or missing the depth expected "
    "at this experience level.\n"
    "- WEAK: incorrect, largely off-topic, an admission of not knowing (\"no idea\", \"skip\"), or so "
    "short it demonstrates nothing.\n"
    "Grade only what the candidate actually wrote. Never invent content they did not say, and never "
    "give credit for things they merely name-dropped without explaining. Be honest - inflating a weak "
    "answer to STRONG makes the whole report worthless.\n\n"

    "The feedback field is 1-2 sentences, addressed to the candidate as \"you\", and must be SPECIFIC "
    "to their answer: name the one thing they got right and the single most important thing that was "
    "missing or wrong. Never write filler like \"Good answer\", \"Nice job\" or \"Could be better\". If "
    "the answer was empty or a non-answer, say briefly what a solid answer would have covered.\n\n"

    "## Choosing the next question\n"
    "- If the last answer was STRONG and the follow-up budget is not exhausted, drill deeper in the "
    "SAME theme with a harder question that builds on what they just said "
    "(isFollowUp=true, advanceTheme=false).\n"
    "- If the last answer was SATISFACTORY or WEAK, move on to the next theme "
    "(isFollowUp=false, advanceTheme=true). Only stay for ONE clarifying follow-up if a targeted "
    "question would genuinely resolve the gap; never keep drilling an area the candidate is failing.\n"
    "- If the prompt says MUST ADVANCE TO NEXT THEME: YES, you are out of follow-up budget - you MUST "
    "return advanceTheme=true and isFollowUp=false and ask about the next theme.\n"
    "- If the theme plan is exhausted, invent a fresh adjacent theme within the topic and set "
    "advanceTheme=true. The interview ends on the clock, never because you ran out of questions.\n"
    "- If time remaining is under 90 seconds, ask something short and directly answerable rather than "
    "opening a long scenario.\n\n"

    "## Rules for the question text\n"
    "1. Ask EXACTLY ONE question. Do not stack two or three questions into one turn.\n"
    "2. Output the question only - no greeting, no \"Great, let's move on\", no praise, no restating "
    "your evaluation, no numbering, no theme label prefix, no markdown formatting.\n"
    "3. Never repeat or lightly reword a question already listed as asked. Every question must open "
    "genuinely new ground.\n"
    "4. Keep it to 1-3 sentences. A short scenario followed by one question is fine; an essay is not.\n"
    "5. It must be answerable in a couple of typed paragraphs, and be concrete and specific rather "
    "than \"tell me about X\" filler.\n"
    "6. Never use a generic template such as \"Can you walk me through your understanding of <theme>?\" "
    "for more than the opening question of a theme, and never twice in one interview.\n"
    "7. The \"theme\" field must be the theme label the question belongs to, matching a label from the "
    "theme plan exactly when you are asking about a planned theme.\n\n"

    "## Output contract\n"
    "Return ONLY this JSON object - no markdown fences, no text before or after:\n"
    "{\n"
    '  "evaluation": { "rating": "STRONG", "feedback": "1-2 specific sentences" },\n'
    '  "next": { "question": "the next question", "theme": "theme label", '
    '"isFollowUp": false, "advanceTheme": true }\n'
    "}\n"
    'The "rating" value MUST be exactly one of "STRONG", "SATISFACTORY", "WEAK" (uppercase). '
    'Set "evaluation" to null ONLY on the opening turn, when there is no answer to grade yet.'
)

INTERVIEW_REPORT_SYSTEM_PROMPT = (
    "You are an expert technical interviewer writing the final report for a completed mock interview. "
    "You are given every exchange: the question, the candidate's verbatim answer, the theme, and the "
    "rating assigned live during the interview (STRONG, SATISFACTORY or WEAK).\n\n"
    "Produce:\n"
    "- strengths: theme labels the candidate handled well (themes whose answers were mostly STRONG). "
    "Use the theme labels from the exchanges verbatim. Empty list if there were none - do not invent "
    "strengths to be kind.\n"
    "- weaknesses: theme labels needing improvement (themes whose answers were mostly WEAK or "
    "SATISFACTORY). Use the theme labels verbatim.\n"
    "- overallSummary: 3-5 sentences addressed to the candidate as \"you\", calibrated to their "
    "experience level and the configured difficulty. Reference what they actually said - concrete "
    "patterns across their answers, not generic encouragement. If the interview was very short or "
    "mostly unanswered, say so plainly.\n"
    "- improvementSuggestions: one entry for EVERY exchange rated WEAK or SATISFACTORY, and none for "
    "STRONG ones. Copy the question, the candidate's answer and the theme verbatim from the input, and "
    "write betterAnswer as a genuinely model answer to that exact question at this candidate's "
    "experience level: 3-6 sentences of real technical substance, specific enough to learn from. Never "
    "write meta-advice like \"you should have gone deeper\" - write the actual answer.\n\n"
    "Return ONLY this JSON object (no markdown, no commentary):\n"
    "{\n"
    '  "strengths": ["theme label"],\n'
    '  "weaknesses": ["theme label"],\n'
    '  "overallSummary": "3-5 sentences",\n'
    '  "improvementSuggestions": [\n'
    "    {\n"
    '      "question": "the original question, verbatim",\n'
    '      "userAnswer": "the candidate answer, verbatim",\n'
    '      "theme": "theme label",\n'
    '      "betterAnswer": "how a strong candidate would have answered"\n'
    "    }\n"
    "  ]\n"
    "}"
)


def _theme_count_for_duration(duration_minutes: int | None) -> int:
    """~4 themes for 30 min, ~6 for 45, ~8 for 60 (Phase 4 spec guideline)."""
    if not duration_minutes:
        return 4
    if duration_minutes >= 60:
        return 8
    if duration_minutes >= 45:
        return 6
    return 4


def build_interview_plan_messages(topic_name: str, experience_level: str, difficulty: str, duration_minutes: int) -> list[dict]:
    system_content = INTERVIEW_PLAN_SYSTEM_PROMPT.format(
        topic_name=topic_name,
        experience_level=experience_level,
        difficulty=difficulty,
        duration_minutes=duration_minutes,
        theme_count=_theme_count_for_duration(duration_minutes),
    )
    user_content = (
        f"Create the theme plan for a {duration_minutes}-minute {difficulty} interview on {topic_name} "
        f"for a {experience_level} candidate. Return JSON only."
    )
    return [{"role": "system", "content": system_content}, {"role": "user", "content": user_content}]


def _format_theme_plan(theme_plan: list[str], current_theme_index: int) -> str:
    if not theme_plan:
        return "(no theme plan - choose sensible areas within the topic yourself)"
    lines = []
    for index, theme in enumerate(theme_plan):
        marker = "->" if index == current_theme_index else "  "
        lines.append(f"{marker} {index + 1}. {theme}")
    if current_theme_index >= len(theme_plan):
        lines.append("-> (plan exhausted - invent a fresh adjacent theme within the topic)")
    return "\n".join(lines)


def _format_transcript(prior_exchanges: list[dict]) -> str:
    if not prior_exchanges:
        return "(nothing yet - this is the opening question)"
    lines = []
    for index, item in enumerate(prior_exchanges, start=1):
        answer = (item.get("userAnswer") or "").strip() or "(no answer given)"
        rating = item.get("rating") or "unrated"
        lines.append(
            f"[{index}] theme: {item.get('theme')}\n"
            f"    Q: {item.get('question')}\n"
            f"    A: {answer}\n"
            f"    rated: {rating}"
        )
    return "\n".join(lines)


def build_interview_next_turn_messages(
    topic_name: str,
    experience_level: str,
    difficulty: str,
    theme_plan: list[str],
    current_theme_index: int,
    current_follow_up_count: int,
    remaining_seconds: int | None,
    prior_exchanges: list[dict],
    last_answer: str | None,
    current_question: dict | None = None,
    must_advance_theme: bool = False,
    max_follow_ups: int = 4,
    asked_questions: list[str] | None = None,
) -> list[dict]:
    theme_plan = theme_plan or []
    current_theme = (
        theme_plan[current_theme_index]
        if 0 <= current_theme_index < len(theme_plan)
        else "(plan exhausted - invent an adjacent theme)"
    )

    asked = [q for q in (asked_questions or []) if q]
    asked_block = "\n".join(f"- {q}" for q in asked) if asked else "(none yet)"

    if current_question and current_question.get("question"):
        graded_block = (
            "THE QUESTION THE CANDIDATE JUST ANSWERED (grade against THIS question):\n"
            f"  theme: {current_question.get('theme')}\n"
            f"  was a follow-up: {bool(current_question.get('isFollowUp'))}\n"
            f"  question: {current_question.get('question')}\n\n"
            "THE CANDIDATE'S ANSWER TO GRADE (verbatim, between the markers):\n"
            "<<<ANSWER\n"
            f"{(last_answer or '').strip() or '(the candidate submitted nothing)'}\n"
            "ANSWER>>>"
        )
    else:
        graded_block = (
            "THIS IS THE OPENING TURN. There is no answer to grade yet - return \"evaluation\": null "
            "and ask the opening question for the first theme."
        )

    user_content = (
        f"TOPIC: {topic_name}\n"
        f"CANDIDATE EXPERIENCE LEVEL: {experience_level}\n"
        f"DEPTH BAR FOR THIS LEVEL: {_experience_bar(experience_level)}\n"
        f"CONFIGURED DIFFICULTY: {difficulty}\n"
        f"TIME REMAINING: {remaining_seconds if remaining_seconds is not None else 'unknown'} seconds\n\n"
        f"THEME PLAN:\n{_format_theme_plan(theme_plan, current_theme_index)}\n"
        f"CURRENT THEME: {current_theme}\n"
        f"FOLLOW-UPS USED ON THIS THEME: {current_follow_up_count} of {max_follow_ups}\n"
        f"MUST ADVANCE TO NEXT THEME: {'YES' if must_advance_theme else 'NO'}\n\n"
        f"TRANSCRIPT SO FAR:\n{_format_transcript(prior_exchanges)}\n\n"
        f"{graded_block}\n\n"
        f"QUESTIONS ALREADY ASKED (never repeat or reword any of these):\n{asked_block}\n\n"
        "Respond with the JSON object only."
    )
    return [
        {"role": "system", "content": INTERVIEW_TURN_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def build_interview_report_messages(topic_name: str, experience_level: str, difficulty: str, exchanges: list[dict]) -> list[dict]:
    if exchanges:
        exchange_text = "\n".join(
            f"[{index}] theme: {item.get('theme')} | rating: {item.get('rating') or 'unrated'}\n"
            f"    Q: {item.get('question')}\n"
            f"    A: {(item.get('userAnswer') or '').strip() or '(no answer given)'}"
            for index, item in enumerate(exchanges, start=1)
        )
    else:
        exchange_text = (
            "(no questions were answered - the candidate ended the interview immediately. "
            "Return empty strengths and improvementSuggestions, and say so in overallSummary.)"
        )

    user_content = (
        f"TOPIC: {topic_name}\n"
        f"CANDIDATE EXPERIENCE LEVEL: {experience_level}\n"
        f"DEPTH BAR FOR THIS LEVEL: {_experience_bar(experience_level)}\n"
        f"CONFIGURED DIFFICULTY: {difficulty}\n"
        f"TOTAL EXCHANGES: {len(exchanges)}\n\n"
        f"EXCHANGES:\n{exchange_text}\n\n"
        "Write the report as the JSON object only."
    )
    return [
        {"role": "system", "content": INTERVIEW_REPORT_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
