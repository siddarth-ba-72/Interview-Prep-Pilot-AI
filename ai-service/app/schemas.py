from enum import Enum

from pydantic import BaseModel, Field


class Role(str, Enum):
    USER = "USER"
    AI = "AI"


class ChatMessage(BaseModel):
    role: Role
    content: str


class LearnMode(str, Enum):
    CLARIFY = "CLARIFY"
    GENERATE_CONTENT = "GENERATE_CONTENT"
    FOLLOW_UP = "FOLLOW_UP"


class LearnStreamRequest(BaseModel):
    topic_name: str = Field(alias="topicName")
    mode: LearnMode
    messages: list[ChatMessage] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


# Test Mode Schemas

class Section(str, Enum):
    MCQ = "MCQ"
    SUBJECTIVE = "SUBJECTIVE"


class TestQuestion(BaseModel):
    question_id: str = Field(alias="questionId")
    section: Section
    text: str
    options: list[str] | None = None  # MCQ only
    correct_option: str | None = Field(default=None, alias="correctOption")  # MCQ only
    model_answer: str | None = Field(default=None, alias="modelAnswer")  # SUBJECTIVE only

    model_config = {"populate_by_name": True}


class GenerateTestQuestionsRequest(BaseModel):
    topic_name: str = Field(alias="topicName")
    strengths: list[str] | None = Field(default=None)  # from previous attempt's report
    weaknesses: list[str] | None = Field(default=None)  # from previous attempt's report

    model_config = {"populate_by_name": True}


class GenerateTestQuestionsResponse(BaseModel):
    questions: list[TestQuestion]


class AnswerForEvaluation(BaseModel):
    question_id: str = Field(alias="questionId")
    section: Section
    question: str
    correct_answer: str = Field(alias="correctAnswer")
    user_answer: str | None = Field(default=None, alias="userAnswer")

    model_config = {"populate_by_name": True}


class EvaluateAnswersRequest(BaseModel):
    topic_name: str = Field(alias="topicName")
    answers: list[AnswerForEvaluation]

    model_config = {"populate_by_name": True}


class QuestionEvaluation(BaseModel):
    question_id: str = Field(alias="questionId")
    is_correct: bool = Field(alias="isCorrect")
    evaluation: str

    model_config = {"populate_by_name": True}


class EvaluateAnswersResponse(BaseModel):
    per_question: list[QuestionEvaluation] = Field(alias="perQuestion")
    strengths: list[str]
    weaknesses: list[str]

    model_config = {"populate_by_name": True}


# Mock Interview Schemas
class InterviewPlanRequest(BaseModel):
    topic_name: str = Field(alias="topicName")
    experience_level: str = Field(alias="experienceLevel")
    difficulty: str
    duration_minutes: int = Field(alias="durationMinutes")

    model_config = {"populate_by_name": True}


class InterviewPlanResponse(BaseModel):
    themes: list[str]


class InterviewNextTurnExchange(BaseModel):
    question: str
    user_answer: str | None = Field(default=None, alias="userAnswer")
    theme: str
    is_follow_up: bool = Field(default=False, alias="isFollowUp")
    rating: str | None = None

    model_config = {"populate_by_name": True}


class InterviewCurrentQuestion(BaseModel):
    """The question `lastAnswer` is answering. Without this the model has to guess which
    question it is grading, which is the main source of nonsense evaluations."""

    question: str
    theme: str | None = None
    is_follow_up: bool = Field(default=False, alias="isFollowUp")

    model_config = {"populate_by_name": True}


class InterviewNextTurnRequest(BaseModel):
    topic_name: str = Field(alias="topicName")
    experience_level: str = Field(alias="experienceLevel")
    difficulty: str
    theme_plan: list[str] = Field(default_factory=list, alias="themePlan")
    current_theme_index: int = Field(default=0, alias="currentThemeIndex")
    current_follow_up_count: int = Field(default=0, alias="currentFollowUpCount")
    remaining_seconds: int | None = Field(default=None, alias="remainingSeconds")
    prior_exchanges: list[InterviewNextTurnExchange] = Field(default_factory=list, alias="priorExchanges")
    last_answer: str | None = Field(default=None, alias="lastAnswer")
    current_question: InterviewCurrentQuestion | None = Field(default=None, alias="currentQuestion")
    must_advance_theme: bool = Field(default=False, alias="mustAdvanceTheme")
    max_follow_ups: int = Field(default=4, alias="maxFollowUps")

    model_config = {"populate_by_name": True}


class InterviewEvaluation(BaseModel):
    rating: str
    feedback: str


class InterviewNextTurnQuestion(BaseModel):
    question: str
    theme: str
    is_follow_up: bool = Field(alias="isFollowUp")
    advance_theme: bool = Field(alias="advanceTheme")

    model_config = {"populate_by_name": True}


class InterviewNextTurnResponse(BaseModel):
    evaluation: InterviewEvaluation | None = None
    next: InterviewNextTurnQuestion


class GenerateInterviewReportExchange(BaseModel):
    question: str
    user_answer: str | None = Field(default=None, alias="userAnswer")
    theme: str
    rating: str | None = None

    model_config = {"populate_by_name": True}


class GenerateInterviewReportRequest(BaseModel):
    topic_name: str = Field(alias="topicName")
    experience_level: str = Field(alias="experienceLevel")
    difficulty: str
    exchanges: list[GenerateInterviewReportExchange]

    model_config = {"populate_by_name": True}


class InterviewImprovementSuggestion(BaseModel):
    question: str
    user_answer: str | None = Field(default=None, alias="userAnswer")
    theme: str | None = None
    better_answer: str = Field(alias="betterAnswer")

    model_config = {"populate_by_name": True}


class GenerateInterviewReportResponse(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    overall_summary: str = Field(default="", alias="overallSummary")
    improvement_suggestions: list[InterviewImprovementSuggestion] = Field(
        default_factory=list, alias="improvementSuggestions"
    )

    model_config = {"populate_by_name": True}

