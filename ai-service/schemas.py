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

