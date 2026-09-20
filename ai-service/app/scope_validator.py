import logging
from app.llm import call_llm

logger = logging.getLogger(__name__)

TECH_KEYWORDS = {
    # Programming languages and frameworks
    "python", "java", "javascript", "typescript", "golang", "go", "rust", "c++", "c#", "csharp",
    "kotlin", "swift", "ruby", "php", "scala", "clojure", "haskell", "perl",
    "react", "vue", "angular", "svelte", "ember", "nextjs", "nuxt", "gatsby",
    "spring", "springboot", "django", "flask", "fastapi", "express", "nestjs",
    "spring boot", "node.js", "nodejs", "rails", "laravel", "asp.net", "asp", "dotnet",

    # Databases
    "sql", "mysql", "postgresql", "postgres", "mongodb", "cassandra", "redis",
    "elasticsearch", "dynamodb", "firebase", "neo4j", "graphql", "rest",
    "database", "orm", "nosql", "relational", "query",

    # Concepts and technologies
    "algorithm", "data structure", "tree", "graph", "array", "linked list", "hash table",
    "binary search", "sorting", "dynamic programming", "recursion", "graph traversal",
    "design pattern", "solid", "microservice", "kubernetes", "docker", "devops",
    "ci/cd", "git", "version control", "agile", "scrum", "linux", "unix", "aws", "gcp", "azure",
    "machine learning", "deep learning", "neural network", "ai", "nlp", "computer vision",
    "distributed system", "scaling", "caching", "load balancing", "authentication", "oauth",
    "jwt", "rest api", "graphql", "websocket", "http", "tcp", "networking",
    "testing", "unit test", "integration test", "tdd", "mock", "stub",
    "debugging", "profiling", "performance", "optimization", "security", "encryption",
    "api design", "system design", "architecture", "refactoring", "clean code",
    "container", "orchestration", "deployment", "infrastructure", "cloud",
    "concurrency", "threading", "async", "promise", "callback",
    "monolithic", "serverless", "faas", "saas", "paas", "iaas",
    "message queue", "kafka", "rabbitmq", "event streaming",
    "blockchain", "web3", "smart contract", "ethereum",

    # Interview and preparation related
    "interview", "coding interview", "technical interview", "leetcode",
    "behavioral", "system design", "whiteboard", "hiring", "oop", "object-oriented",
    "functional programming", "declarative", "imperative",

    # DevOps and Infrastructure
    "terraform", "ansible", "jenkins", "gitlab", "github", "docker", "container",
    "kubernetes", "helm", "prometheus", "grafana", "monitoring", "logging",
    "cloud", "aws", "gcp", "azure", "serverless", "lambda",
}

OUT_OF_SCOPE_MESSAGE = (
    "I'm specifically designed to help with technical interview preparation and "
    "engineering topics. I cannot answer questions about {topic}. "
    "Please ask me about programming languages, data structures, algorithms, "
    "system design, or other technical interview topics instead!"
)

BLOCKED_TOPICS = {
    "politics", "religion", "sports", "entertainment", "music", "movies",
    "celebrities", "news", "gossip", "dating", "relationships", "philosophy",
    "history", "literature", "art", "cooking", "travel", "fashion", "weather",
    "astrology", "numerology", "horoscope", "magic", "conspiracy",
}


def _is_tech_related(text: str) -> bool:
    """Quick keyword-based check for tech relevance."""
    if not text:
        return False

    text_lower = text.lower()

    # Check if blocked topics are mentioned
    for blocked in BLOCKED_TOPICS:
        if blocked in text_lower:
            return False

    # Check for tech keywords
    for keyword in TECH_KEYWORDS:
        if keyword in text_lower:
            return True

    return False


async def validate_topic_scope(topic_name: str) -> tuple[bool, str | None]:
    """
    Validate if a topic is tech/interview related.
    Returns (is_valid, error_message_or_none)
    """
    if _is_tech_related(topic_name):
        return True, None

    return False, OUT_OF_SCOPE_MESSAGE.format(topic=f'"{topic_name}"')


async def validate_user_message_scope(topic_name: str, user_message: str) -> tuple[bool, str | None]:
    """
    Validate if a user message is relevant to tech/interview preparation.
    Uses keyword check first, then LLM validation if needed.
    Returns (is_valid, error_message_or_none)
    """
    if not user_message or not user_message.strip():
        return True, None

    # Quick keyword check
    if _is_tech_related(user_message):
        return True, None

    # LLM-based validation for edge cases
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a content scope validator. Determine if a user message is related to "
                    "technical interview preparation and software engineering. Respond with exactly "
                    'one word: "YES" if the message is tech/interview related, or "NO" if it is off-topic. '
                    "Examples of on-topic: algorithms, data structures, programming languages, system design, "
                    "coding interviews, databases, DevOps, cloud platforms, software architecture. "
                    "Examples of off-topic: politics, sports, entertainment, cooking, relationships, philosophy."
                )
            },
            {
                "role": "user",
                "content": f"Topic context: {topic_name}\n\nUser message: {user_message}"
            }
        ]

        response = await call_llm(messages)
        is_on_topic = "YES" in response.upper()

        if not is_on_topic:
            return False, OUT_OF_SCOPE_MESSAGE.format(topic=f'this topic')

        return True, None

    except Exception as e:
        logger.warning(f"LLM validation failed: {e}, allowing message through")
        # Be lenient on validation errors - don't block the user
        return True, None
