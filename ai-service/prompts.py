from schemas import ChatMessage, LearnMode, Role

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


def build_test_generation_messages(topic_name: str) -> list[dict]:
    """Build messages for test question generation."""
    return [
        {"role": "system", "content": TEST_GENERATION_SYSTEM_PROMPT.format(topic_name=topic_name)},
        {"role": "user", "content": f"Generate 10 MCQ and 10 SUBJECTIVE questions for {topic_name}."}
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

