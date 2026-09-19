import logging
import re

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_internal_api_key_or_user_id
from app.llm import call_llm_json
from app.prompts import (
    build_interview_plan_messages,
    build_interview_next_turn_messages,
    build_interview_report_messages,
)
from app.schemas import (
    GenerateInterviewReportRequest,
    GenerateInterviewReportResponse,
    InterviewImprovementSuggestion,
    InterviewPlanRequest,
    InterviewPlanResponse,
    InterviewNextTurnRequest,
    InterviewNextTurnResponse,
    InterviewNextTurnQuestion,
    InterviewEvaluation,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/interview", tags=["interview"])

VALID_RATINGS = {"STRONG", "SATISFACTORY", "WEAK"}

# Openers the model reaches for when it has nothing better to say. They are the tell-tale
# sign of a degenerate turn, so we detect them and ask for a real question instead.
# An acknowledgement opener must be followed by punctuation to count, so a real question
# that merely starts with one of these words ("Good practices for caching - ...") survives.
_ACK_OPENER_RE = re.compile(
    r"^(?:"
    r"(?:great|good|nice|excellent|perfect|solid|strong)\s*(?:answer|job|point|explanation|work|start)?\s*[,!.:;]+"
    r"|(?:thanks|thank you)(?:\s+for\s+that)?\s*[,!.:;]+"
    r"|that'?s\s+(?:right|correct|helpful|a\s+good\s+point)\s*[,!.:;]+"
    r"|(?:okay|ok|alright|sure|understood|got it|makes sense|fair enough)\s*[,!.:;]+"
    r"|(?:let'?s\s+move\s+on|lets\s+move\s+on|moving\s+on|let'?s\s+continue)\s*[,!.:;\-–—]+"
    r")\s*",
    re.I,
)

_LABEL_PREFIX_RE = re.compile(r"^(?:next\s+)?question\s*[:.\-–—]\s*", re.I)


def _normalize_rating(raw: str | None, answer: str | None = None) -> str:
    """Normalize to the exact enum the downstream Java service expects. When the model
    gives us nothing usable, fall back on the length of the answer rather than blindly
    handing out SATISFACTORY - an empty box is not a satisfactory answer."""
    candidate = (raw or "").strip().upper()
    if candidate in VALID_RATINGS:
        return candidate
    if not (answer or "").strip():
        return "WEAK"
    return "SATISFACTORY"


def _normalize_for_compare(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _clean_question(raw: str | None) -> str:
    """Strip the conversational packaging models like to wrap questions in, so the UI
    renders a clean interview question rather than 'Great answer! Next question: ...'.

    A filler opener can hide another one behind it, so stripping repeats until stable.
    """
    text = (raw or "").strip()
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    for _ in range(6):
        before = text
        text = text.strip().strip('"').strip()
        text = re.sub(r"^#{1,6}\s+", "", text)
        text = re.sub(r"^[-*•>]\s+", "", text)
        text = re.sub(r"^\d+[.)]\s+", "", text)
        text = re.sub(r"^\*\*(.+?)\*\*", r"\1", text)
        text = _ACK_OPENER_RE.sub("", text)
        text = _LABEL_PREFIX_RE.sub("", text)
        if text == before:
            break

    return re.sub(r"\s+", " ", text).strip()


def _clean_theme(raw: str | None, fallback: str) -> str:
    theme = re.sub(r"\s+", " ", (raw or "").strip()).strip('"').rstrip("?").strip()
    return theme or fallback


def _sanitize_themes(raw_themes: list, topic_name: str) -> list[str]:
    """Drop blanks, questions-masquerading-as-themes and case-insensitive duplicates."""
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in raw_themes or []:
        if not isinstance(item, str):
            continue
        theme = re.sub(r"\s+", " ", item.strip()).strip('"').strip()
        if not theme or theme.endswith("?") or len(theme) > 80:
            continue
        key = _normalize_for_compare(theme)
        if not key or key in seen:
            continue
        seen.add(key)
        cleaned.append(theme)
    return cleaned


def _default_themes(topic_name: str) -> list[str]:
    return [
        f"{topic_name} fundamentals",
        f"{topic_name} in practice",
        f"Design and trade-offs in {topic_name}",
        f"Debugging and testing {topic_name}",
    ]


def _asked_questions(request: InterviewNextTurnRequest) -> list[str]:
    asked = [exchange.question for exchange in request.prior_exchanges if exchange.question]
    if request.current_question and request.current_question.question:
        asked.append(request.current_question.question)
    return asked


@router.post("/plan", response_model=InterviewPlanResponse)
async def plan_interview(request: InterviewPlanRequest, _=Depends(require_internal_api_key_or_user_id)):
    try:
        messages = build_interview_plan_messages(
            request.topic_name, request.experience_level, request.difficulty, request.duration_minutes
        )
        data = await call_llm_json(messages, temperature=0.7)
        themes = _sanitize_themes(data.get("themes", []), request.topic_name)
        if not themes:
            logger.warning("Interview plan for %s produced no usable themes; using defaults", request.topic_name)
            themes = _default_themes(request.topic_name)
        return InterviewPlanResponse(themes=themes)
    except Exception as exc:
        logger.exception("Failed to plan interview for topic %s", request.topic_name)
        raise HTTPException(status_code=500, detail=f"Error planning interview: {exc}") from exc


@router.post("/next-turn", response_model=InterviewNextTurnResponse)
async def next_turn(request: InterviewNextTurnRequest, _=Depends(require_internal_api_key_or_user_id)):
    is_opening_turn = request.current_question is None or not request.current_question.question
    asked = _asked_questions(request)
    already_asked = {_normalize_for_compare(question) for question in asked}

    fallback_theme = (
        request.theme_plan[request.current_theme_index]
        if 0 <= request.current_theme_index < len(request.theme_plan)
        else request.topic_name
    )

    def build_messages(extra_instruction: str | None = None) -> list[dict]:
        messages = build_interview_next_turn_messages(
            request.topic_name,
            request.experience_level,
            request.difficulty,
            request.theme_plan,
            request.current_theme_index,
            request.current_follow_up_count,
            request.remaining_seconds,
            [exchange.model_dump(by_alias=True) for exchange in request.prior_exchanges],
            request.last_answer,
            current_question=request.current_question.model_dump(by_alias=True) if request.current_question else None,
            must_advance_theme=request.must_advance_theme,
            max_follow_ups=request.max_follow_ups,
            asked_questions=asked,
        )
        if extra_instruction:
            messages.append({"role": "user", "content": extra_instruction})
        return messages

    # The turn call blocks a candidate mid-interview, so it gets fewer repair attempts than
    # the plan/report calls - the caller falls back gracefully, a long stall is worse.
    try:
        data = await call_llm_json(build_messages(), attempts=2, temperature=0.7)
        question_text = _clean_question((data.get("next") or {}).get("question"))

    except Exception as exc:
        logger.exception("Failed to generate the next interview turn for topic %s", request.topic_name)
        raise HTTPException(status_code=500, detail=f"Error generating next interview turn: {exc}") from exc

    # One targeted retry when the model recycles a question it already asked - repeated
    # questions are what make the interview feel stuck. A failure here is not fatal: the
    # duplicate is still a usable question, so we keep the original turn.
    if question_text and _normalize_for_compare(question_text) in already_asked:
        logger.info("Model repeated an already-asked question; requesting a replacement")
        try:
            retry_data = await call_llm_json(
                build_messages(
                    "The question you proposed has already been asked in this interview. Ask a "
                    "different question that covers new ground, and return the JSON object only."
                ),
                attempts=1,
                temperature=0.9,
            )
            retry_question = _clean_question((retry_data.get("next") or {}).get("question"))
            if retry_question and _normalize_for_compare(retry_question) not in already_asked:
                data = retry_data
                question_text = retry_question
        except Exception:
            logger.warning("Replacement question request failed; keeping the original turn", exc_info=True)

    evaluation = None
    if not is_opening_turn:
        raw_evaluation = data.get("evaluation") or {}
        if not isinstance(raw_evaluation, dict):
            raw_evaluation = {}
        feedback = (raw_evaluation.get("feedback") or "").strip()
        evaluation = InterviewEvaluation(
            rating=_normalize_rating(raw_evaluation.get("rating"), request.last_answer),
            feedback=feedback or "This answer was recorded, but no specific feedback was produced for it.",
        )

    next_data = data.get("next") or {}
    if not isinstance(next_data, dict):
        next_data = {}

    if not question_text:
        question_text = f"Let's talk about {fallback_theme}. What is the most important thing to get right there, and why?"

    # The follow-up cap is the service's call, not the model's (Phase 4 spec, section 4).
    advance_theme = bool(next_data.get("advanceTheme", False))
    is_follow_up = bool(next_data.get("isFollowUp", False))
    if request.must_advance_theme:
        advance_theme = True
        is_follow_up = False
    if is_opening_turn:
        advance_theme = False
        is_follow_up = False

    return InterviewNextTurnResponse(
        evaluation=evaluation,
        next=InterviewNextTurnQuestion(
            question=question_text,
            theme=_clean_theme(next_data.get("theme"), fallback_theme),
            is_follow_up=is_follow_up,
            advance_theme=advance_theme,
        ),
    )


@router.post("/generate-report", response_model=GenerateInterviewReportResponse)
async def generate_report(request: GenerateInterviewReportRequest, _=Depends(require_internal_api_key_or_user_id)):
    try:
        messages = build_interview_report_messages(
            request.topic_name, request.experience_level, request.difficulty,
            [exchange.model_dump(by_alias=True) for exchange in request.exchanges],
        )
        data = await call_llm_json(messages, temperature=0.5)
    except Exception as exc:
        logger.exception("Failed to generate the interview report for topic %s", request.topic_name)
        raise HTTPException(status_code=500, detail=f"Error generating interview report: {exc}") from exc

    suggestions: list[InterviewImprovementSuggestion] = []
    for item in data.get("improvementSuggestions") or []:
        if not isinstance(item, dict):
            continue
        better_answer = (item.get("betterAnswer") or "").strip()
        question = (item.get("question") or "").strip()
        if not better_answer or not question:
            continue
        suggestions.append(
            InterviewImprovementSuggestion(
                question=question,
                user_answer=item.get("userAnswer"),
                theme=item.get("theme"),
                better_answer=better_answer,
            )
        )

    def string_list(key: str) -> list[str]:
        return [item.strip() for item in (data.get(key) or []) if isinstance(item, str) and item.strip()]

    return GenerateInterviewReportResponse(
        strengths=string_list("strengths"),
        weaknesses=string_list("weaknesses"),
        overall_summary=(data.get("overallSummary") or "").strip(),
        improvement_suggestions=suggestions,
    )
