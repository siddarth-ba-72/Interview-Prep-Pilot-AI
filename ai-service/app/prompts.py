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

