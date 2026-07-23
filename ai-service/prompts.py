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
