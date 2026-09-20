import logging

from app.llm import call_llm

logger = logging.getLogger(__name__)

OUT_OF_SCOPE_MESSAGE = (
    "I'm specifically designed to help with technical interview preparation and "
    "engineering topics. I can't generate content for {topic}. "
    "Please choose a programming language, framework, data structure, algorithm, "
    "system design area, or other technical interview topic instead!"
)

SCOPE_CLASSIFIER_PROMPT = (
    "You are a content scope classifier for a technical interview preparation platform. "
    "Decide whether the given topic is something a candidate could plausibly study or be "
    "interviewed on in a software engineering / technical interview context - for example a "
    "programming language, framework, library, database, algorithm, data structure, system "
    "design area, cloud/DevOps technology, or general engineering practice. "
    'Respond with exactly one word: "YES" if it is in scope, or "NO" if it is not '
    "(for example topics like sports, politics, cooking, celebrities, or relationships)."
)


async def validate_topic_scope(topic_name: str) -> tuple[bool, str | None]:
    """
    Ask the model whether a topic is technical/interview-prep related. Used as a
    pre-check before generating structured content (test questions, interview plans)
    where there is no conversational turn for the model to decline within itself.

    Lenient on classifier failure - a broken validation call should never block a
    legitimate request, so any error here allows the topic through.

    Returns (is_valid, error_message_or_none).
    """
    if not topic_name or not topic_name.strip():
        return False, OUT_OF_SCOPE_MESSAGE.format(topic='""')

    try:
        messages = [
            {"role": "system", "content": SCOPE_CLASSIFIER_PROMPT},
            {"role": "user", "content": f"Topic: {topic_name}"},
        ]
        response = await call_llm(messages)
        is_in_scope = "YES" in response.upper()
    except Exception as e:
        logger.warning("Scope classification failed for topic '%s': %s; allowing through", topic_name, e)
        return True, None

    if not is_in_scope:
        return False, OUT_OF_SCOPE_MESSAGE.format(topic=f'"{topic_name}"')
    return True, None
