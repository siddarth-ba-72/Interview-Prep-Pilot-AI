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
