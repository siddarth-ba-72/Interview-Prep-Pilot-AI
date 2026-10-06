"""Port of MockInterviewServiceTest.java: the same 15 tests, in the same order, with snake_case names.
Everything after the ported block is additional coverage."""
from datetime import timedelta

import pytest

from app.errors import ApiError
from app.models.mock_interview import QuestionState
from app.schemas.interviews import AnswerInterviewRequest, StartInterviewRequest
from app.services.mock_interview_service import MAX_FOLLOW_UPS_PER_THEME, calculate_score
from tests.unit.fakes_interview import (
    Interviews,
    exchange,
    report_response,
    turn,
)


@pytest.fixture
def w():
    return Interviews()


def answer(w, text):
    return w.service.answer("user-1", "topic-1", "session-1", AnswerInterviewRequest(answer=text))


def start(w, level="JUNIOR", difficulty="MEDIUM", minutes=30):
    return w.service.start(
        "user-1", "topic-1",
        StartInterviewRequest(experience_level=level, difficulty=difficulty, duration_minutes=minutes),
    )


# =============================== ported from MockInterviewServiceTest.java ===============================

def test_calculate_score_uses_mean_of_exchange_points():
    score = calculate_score([
        exchange("q1", "theme-1", False, "answer-1", "STRONG", 100, "Great"),
        exchange("q2", "theme-1", True, "answer-2", "SATISFACTORY", 60, "Okay"),
        exchange("q3", "theme-2", False, "answer-3", "WEAK", 20, "Needs work"),
    ])
    assert score == 60


async def test_start_interview_falls_back_when_ai_service_is_unavailable(w):
    w.ai.plan_error = RuntimeError("AI service unavailable")

    response = await start(w, "JUNIOR", "MEDIUM", 30)

    assert response.current_question is not None
    assert response.resumed is False
    assert response.theme_progress.current_theme_index == 1
    assert response.theme_progress.total_themes == 4


async def test_start_interview_rejects_an_unknown_experience_level(w):
    with pytest.raises(ApiError) as exc:
        await start(w, "WIZARD", "MEDIUM", 30)
    assert (exc.value.status_code, exc.value.code) == (400, "INVALID_INTERVIEW_CONFIG")


async def test_start_interview_rejects_an_unsupported_duration(w):
    with pytest.raises(ApiError) as exc:
        await start(w, "SENIOR", "HARD", 25)
    assert (exc.value.status_code, exc.value.code) == (400, "INVALID_INTERVIEW_CONFIG")


async def test_start_interview_resumes_an_in_progress_session_instead_of_creating_a_new_one(w):
    w.in_progress_session("Explain bean scopes.", "Core IoC & Beans")

    response = await start(w, "JUNIOR", "EASY", 60)

    assert response.resumed is True
    assert response.current_question.question == "Explain bean scopes."
    # Config from the request is ignored on resume: the original session config wins.
    assert response.config.experience_level == "SENIOR"
    assert response.config.duration_minutes == 30
    assert len(w.sessions.items) == 1


async def test_answer_sends_the_question_being_graded_to_the_ai_service(w):
    w.in_progress_session("Explain bean scopes.", "Core IoC & Beans")
    w.ai.turn_result = turn("STRONG", "How would singleton scope break with stateful beans?", "Core IoC & Beans",
                            True, False)

    await answer(w, "Singleton, prototype, request, session.")

    assert len(w.ai.turn_requests) == 1
    sent = w.ai.turn_requests[0]
    assert sent.current_question is not None, "the graded question must be sent to the AI service"
    assert sent.current_question.question == "Explain bean scopes."
    assert sent.last_answer == "Singleton, prototype, request, session."
    assert sent.must_advance_theme is False


async def test_strong_answer_follow_up_stays_on_the_same_theme_and_increments_the_budget(w):
    session = w.in_progress_session("Explain bean scopes.", "Core IoC & Beans")
    w.ai.turn_result = turn("STRONG", "Where does prototype scope surprise people?", "Core IoC & Beans", True, False)

    response = await answer(w, "A thorough answer.")

    assert response.evaluation.rating == "STRONG"
    assert response.evaluation.points == 100
    assert session.current_theme_index == 0
    assert session.current_follow_up_count == 1
    assert response.theme_progress.current_theme_index == 1


async def test_follow_up_cap_forces_the_theme_to_advance_even_if_the_ai_wants_to_stay(w):
    session = w.in_progress_session("Yet another follow-up.", "Core IoC & Beans")
    session.current_follow_up_count = MAX_FOLLOW_UPS_PER_THEME
    # The AI tries to keep drilling the same theme.
    w.ai.turn_result = turn("STRONG", "One more on beans?", "Core IoC & Beans", True, False)

    await answer(w, "Another good answer.")

    assert w.ai.turn_requests[0].must_advance_theme is True, "the cap must be signalled to the AI service"
    assert session.current_theme_index == 1, "the theme must advance regardless of the AI response"
    assert session.current_follow_up_count == 0


async def test_blank_answer_scores_zero_without_trusting_the_ai_rating(w):
    session = w.in_progress_session("Explain bean scopes.", "Core IoC & Beans")
    w.ai.turn_result = turn("STRONG", "Let's talk auto-configuration.", "Auto-configuration", False, True)

    response = await answer(w, "   ")

    assert response.evaluation.rating == "WEAK"
    assert response.evaluation.points == 0
    assert session.exchanges[0].points == 0
    assert session.current_theme_index == 1


async def test_theme_plan_grows_when_the_ai_invents_an_adjacent_theme_after_the_plan_is_exhausted(w):
    session = w.in_progress_session("Last planned question.", "Auto-configuration")
    session.current_theme_index = 1  # on the final planned theme
    w.ai.turn_result = turn("SATISFACTORY", "How do you approach observability?", "Actuator & Observability",
                            False, True)

    response = await answer(w, "A partial answer.")

    assert len(session.theme_plan) == 3, "an invented theme should extend the plan"
    assert session.theme_plan[2] == "Actuator & Observability"
    assert response.theme_progress.current_theme_index == 3
    assert response.theme_progress.total_themes == 3, "progress must never exceed its own total"


async def test_answer_after_the_deadline_finalizes_instead_of_recording_the_answer(w):
    session = w.in_progress_session("Explain bean scopes.", "Core IoC & Beans")
    session.deadline_at = w.clock() - timedelta(seconds=60)

    response = await answer(w, "Too late.")

    assert response.is_complete is True
    assert session.status == "COMPLETED"
    assert session.completion_reason == "TIME_EXPIRED"
    assert session.exchanges == [], "a late answer must not be recorded"


async def test_resuming_an_expired_session_finalizes_it_and_returns_the_report(w):
    session = w.in_progress_session("Explain bean scopes.", "Core IoC & Beans")
    session.deadline_at = w.clock() - timedelta(seconds=30)
    session.exchanges = [exchange("q1", "Core IoC & Beans", False, "a1", "STRONG", 100, "Good")]
    w.ai.report_error = RuntimeError("AI service unavailable")

    state = await w.service.get("user-1", "topic-1", "session-1")

    assert state.is_complete is True
    assert state.completion_reason == "TIME_EXPIRED"
    assert state.report is not None, "an expired session must still produce a report"
    assert state.report.score == 100
    assert state.report.passed is True


async def test_end_interview_with_no_answers_scores_zero_and_fails(w):
    w.in_progress_session("Explain bean scopes.", "Core IoC & Beans")
    w.ai.report_result = report_response(summary="You ended early.", strengths=(), weaknesses=())

    report = await w.service.end("user-1", "topic-1", "session-1")

    assert report.score == 0
    assert report.passed is False
    assert report.pass_threshold == 75


async def test_interview_survives_an_ai_failure_with_a_real_next_question(w):
    session = w.in_progress_session("Explain bean scopes.", "Core IoC & Beans")
    w.ai.turn_error = RuntimeError("AI service unavailable")

    response = await answer(w, "Some answer.")

    assert response.is_complete is False, "an AI hiccup must not end the interview"
    assert response.next_question is not None
    assert len(session.exchanges) == 1
    assert response.evaluation.rating == "SATISFACTORY"


async def test_consecutive_ai_failures_do_not_repeat_the_same_fallback_question(w):
    session = w.in_progress_session("Explain bean scopes.", "Core IoC & Beans")
    w.ai.turn_error = RuntimeError("AI service unavailable")

    first = (await answer(w, "answer one")).next_question.question
    session.current_question = QuestionState(question=first, theme="theme", is_follow_up=False)
    second = (await answer(w, "answer two")).next_question.question

    assert first != second, "repeating the same fallback is what makes the interview feel stuck"
