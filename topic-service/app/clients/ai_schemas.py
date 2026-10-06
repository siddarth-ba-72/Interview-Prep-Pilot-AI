"""What ai-service sends back. Parsing is lenient: unknown fields are ignored and every field is optional, so a
response that does not fit is caught by the caller and treated as an AI failure rather than blowing up here."""
from app.schemas.base import CamelModel


class AiQuestion(CamelModel):
    question_id: str | None = None
    section: str | None = None
    text: str | None = None
    options: list[str] | None = None
    correct_option: str | None = None
    model_answer: str | None = None


class GenerateTestResponse(CamelModel):
    questions: list[AiQuestion] | None = None


class AiQuestionEvaluation(CamelModel):
    question_id: str | None = None
    is_correct: bool | None = None
    evaluation: str | None = None


class EvaluateAnswersResponse(CamelModel):
    per_question: list[AiQuestionEvaluation] | None = None
    strengths: list[str] | None = None
    weaknesses: list[str] | None = None


# ---------- Mock Interview: requests (dumped by alias, nulls included, as Jackson did) ----------

class PlanInterviewRequest(CamelModel):
    topic_name: str
    experience_level: str
    difficulty: str
    duration_minutes: int


class NextTurnExchange(CamelModel):
    question: str | None = None
    user_answer: str | None = None
    theme: str | None = None
    is_follow_up: bool = False
    rating: str | None = None


class NextTurnQuestionContext(CamelModel):
    """The question `last_answer` responds to, so the AI grades the right one instead of inferring it."""

    question: str | None = None
    theme: str | None = None
    is_follow_up: bool = False


class NextTurnRequest(CamelModel):
    topic_name: str
    experience_level: str
    difficulty: str
    theme_plan: list[str]
    current_theme_index: int
    current_follow_up_count: int
    remaining_seconds: int
    prior_exchanges: list[NextTurnExchange]
    last_answer: str | None = None
    current_question: NextTurnQuestionContext | None = None
    must_advance_theme: bool
    max_follow_ups: int


class ReportExchange(CamelModel):
    question: str | None = None
    user_answer: str | None = None
    theme: str | None = None
    rating: str | None = None


class GenerateInterviewReportRequest(CamelModel):
    topic_name: str
    experience_level: str
    difficulty: str
    exchanges: list[ReportExchange]


# ---------- Mock Interview: responses (lenient) ----------

class PlanInterviewResponse(CamelModel):
    themes: list[str] | None = None


class NextTurnEvaluation(CamelModel):
    rating: str | None = None
    feedback: str | None = None


class NextTurnNext(CamelModel):
    question: str | None = None
    theme: str | None = None
    is_follow_up: bool = False
    advance_theme: bool = False


class NextTurnResponse(CamelModel):
    evaluation: NextTurnEvaluation | None = None
    next: NextTurnNext | None = None


class AiImprovementSuggestion(CamelModel):
    question: str | None = None
    user_answer: str | None = None
    theme: str | None = None
    better_answer: str | None = None


class GenerateInterviewReportResponse(CamelModel):
    strengths: list[str] | None = None
    weaknesses: list[str] | None = None
    overall_summary: str | None = None
    improvement_suggestions: list[AiImprovementSuggestion] | None = None
