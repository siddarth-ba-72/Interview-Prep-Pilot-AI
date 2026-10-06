"""Beyond the ported Java tests: rounding, AI contract, every branch of the state machine."""
import asyncio
from datetime import timedelta

import pytest

from app.clients.ai_schemas import (
    GenerateInterviewReportResponse,
    NextTurnExchange,
    NextTurnQuestionContext,
    NextTurnRequest,
    NextTurnResponse,
    PlanInterviewResponse,
)
from app.errors import ApiError
from app.models.mock_interview import MockInterviewSession, QuestionState
from app.schemas.interviews import AnswerInterviewRequest, StartInterviewRequest, ThemeProgressResponse
from app.services.mock_interview_service import (
    FALLBACK_QUESTION_TEMPLATES,
    apply_theme_transition,
    calculate_score,
    dedupe_themes,
    default_summary,
    default_theme_plan,
    fallback_next_question,
    index_of_ignore_case,
    parse_rating,
    points_for_rating,
    remaining_seconds,
    require_enum,
)
from tests.unit.fakes_interview import Clock, Interviews, exchange, report_response, turn

THEME_A, THEME_B = "Core IoC & Beans", "Auto-configuration"


@pytest.fixture
def w():
    return Interviews()


def say(w, text, session_id="session-1"):
    return w.service.answer("user-1", "topic-1", session_id, AnswerInterviewRequest(answer=text))


def start(w, level="SENIOR", difficulty="MEDIUM", minutes=30):
    return w.service.start(
        "user-1", "topic-1",
        StartInterviewRequest(experience_level=level, difficulty=difficulty, duration_minutes=minutes),
    )


def api_error_of(coro_or_fn):
    async def run():
        with pytest.raises(ApiError) as exc:
            await coro_or_fn
        return exc.value
    return run()


# ---------------------------------------------------------------- scoring

def test_score_rounds_half_up_not_half_to_even():
    # mean 2.5: Java's Math.round gives 3; Python's round() gives 2
    exchanges = [exchange(points=20)] + [exchange(points=0) for _ in range(7)]
    assert 20 / 8 == 2.5 and round(2.5) == 2
    assert calculate_score(exchanges) == 3


@pytest.mark.parametrize(
    "points, expected",
    [([], 0), ([100], 100), ([60, 100], 80), ([20, 60], 40), ([100, 60, 20], 60), ([100, 100, 60], 87),
     ([20, 20, 60], 33), ([0], 0), ([0, 100], 50), ([60, 20, 20, 20], 30), ([60, 60, 0], 40), ([1, 0], 1)],
)
def test_score_is_the_rounded_mean(points, expected):
    assert calculate_score([exchange(points=p) for p in points]) == expected


def test_score_treats_missing_points_as_zero_and_handles_none():
    assert calculate_score(None) == 0
    assert calculate_score([exchange(points=None), exchange(points=100)]) == 50


@pytest.mark.parametrize("rating, points", [("STRONG", 100), ("SATISFACTORY", 60), ("WEAK", 20), (None, 0)])
def test_points_for_rating(rating, points):
    assert points_for_rating(rating) == points


@pytest.mark.parametrize(
    "raw, expected",
    [("STRONG", "STRONG"), (" strong ", "STRONG"), ("weak", "WEAK"), ("Satisfactory", "SATISFACTORY"),
     (None, "SATISFACTORY"), ("", "SATISFACTORY"), ("EXCELLENT", "SATISFACTORY")],
)
def test_parse_rating_defaults_to_satisfactory(raw, expected):
    assert parse_rating(raw) == expected


async def test_pass_threshold_is_inclusive_at_75(w):
    session = w.in_progress_session("q", THEME_A)
    session.exchanges = [exchange(points=100), exchange(points=60), exchange(points=60), exchange(points=80)]  # 75.0
    assert (await w.service.end("user-1", "topic-1", "session-1")).passed is True


async def test_74_fails(w):
    session = w.in_progress_session("q", THEME_A)
    session.exchanges = [exchange(points=100), exchange(points=60), exchange(points=60), exchange(points=76)]  # 74
    report = await w.service.end("user-1", "topic-1", "session-1")
    assert (report.score, report.passed, report.max_score) == (74, False, 100)


# ---------------------------------------------------------------- pure helpers

def test_dedupe_themes_trims_drops_blanks_and_ignores_case():
    assert dedupe_themes([" Beans ", "beans", "", "  ", "Security", "BEANS", "security "]) == ["Beans", "Security"]
    assert dedupe_themes(None) == [] and dedupe_themes([]) == []


@pytest.mark.parametrize("minutes, count", [(30, 4), (45, 6), (60, 8), (None, 4), (31, 4), (44, 4)])
def test_default_plan_grows_with_duration(minutes, count):
    plan = default_theme_plan("Kafka", minutes)
    assert len(plan) == count and plan[0] == "Kafka fundamentals" and "Design and trade-offs in Kafka" in plan


def test_default_plan_texts_are_verbatim():
    assert default_theme_plan("X", 60) == [
        "X fundamentals", "X in practice", "Design and trade-offs in X", "Debugging and testing X",
        "Performance and scaling with X", "Real-world X scenarios", "Advanced X internals",
        "Ecosystem and tooling around X",
    ]


@pytest.mark.parametrize(
    "values, candidate, expected",
    [(["A", "B"], "b", 1), (["A", "B"], "  B  ", 1), (["A", "B"], "C", -1), (["A"], None, -1), (["A"], "  ", -1),
     (["a", "A"], "A", 0)],
)
def test_index_of_ignore_case(values, candidate, expected):
    assert index_of_ignore_case(values, candidate) == expected


def test_require_enum_normalises_and_lists_values_in_a_stable_order():
    assert require_enum("  senior ", ("JUNIOR", "SENIOR"), "x") == "SENIOR"
    with pytest.raises(ApiError) as exc:
        require_enum("wizard", ("JUNIOR", "INTERMEDIATE", "SENIOR", "MASTER", "ADVANCED"), "experienceLevel")
    assert exc.value.message == "experienceLevel must be one of [JUNIOR, INTERMEDIATE, SENIOR, MASTER, ADVANCED]"
    with pytest.raises(ApiError):
        require_enum(None, ("EASY",), "difficulty")


@pytest.mark.parametrize("seconds, expected", [(90, 90), (90.9, 90), (0.4, 0), (-5, 0), (0, 0)])
def test_remaining_seconds_truncates_and_never_goes_negative(seconds, expected):
    clock = Clock()
    assert remaining_seconds(clock.now + timedelta(seconds=seconds), clock.now) == expected
    assert remaining_seconds(None, clock.now) == 0


def make_session(plan=("A", "B", "C"), index=0, follow_ups=0, exchanges=0) -> MockInterviewSession:
    return MockInterviewSession(
        topic_id="t", user_id="u", theme_plan=list(plan), current_theme_index=index,
        current_follow_up_count=follow_ups, exchanges=[exchange() for _ in range(exchanges)],
    )


@pytest.mark.parametrize(
    "plan, index, advance, next_theme, want_index, want_plan_len, want_label",
    [
        (("A", "B", "C"), 0, True, "B", 1, 3, "B"),  # the AI named the next planned theme
        (("A", "B", "C"), 0, True, "C", 2, 3, "C"),  # the AI skipped ahead: follow it
        (("A", "B", "C"), 0, True, "c", 2, 3, "C"),  # case-insensitive, canonical label returned
        (("A", "B", "C"), 0, True, "Z", 1, 3, "B"),  # unknown theme inside the plan: normal step
        (("A", "B", "C"), 0, True, None, 1, 3, "B"),
        (("A", "B", "C"), 0, True, "A", 1, 3, "B"),  # matching theme is behind the target: ignored
        (("A", "B", "C"), 2, True, "Z", 3, 4, "Z"),  # exhausted plan adopts an invented theme
        (("A", "B", "C"), 2, True, "A", 3, 4, "More on Kafka"),  # exhausted, but the "new" one is already known
        (("A", "B", "C"), 2, True, None, 3, 4, "More on Kafka"),  # exhausted and no theme given
        (("A", "B", "C"), 2, True, "  ", 3, 4, "More on Kafka"),
        (("A", "B", "C"), 1, False, "B", 1, 3, "B"),  # stay: label is the current theme's
        (("A", "B", "C"), 1, False, "Whatever", 1, 3, "B"),
    ],
)
def test_theme_transition(plan, index, advance, next_theme, want_index, want_plan_len, want_label):
    session = make_session(plan, index, follow_ups=2)
    label = apply_theme_transition(session, advance, next_theme, "Kafka")
    assert (session.current_theme_index, len(session.theme_plan), label) == (want_index, want_plan_len, want_label)
    assert session.current_follow_up_count == (0 if advance else 3)


def test_theme_transition_with_an_empty_plan_uses_the_ai_theme_or_the_topic():
    session = make_session(plan=(), index=0)
    session.theme_plan = None
    assert apply_theme_transition(session, False, "Given", "Kafka") == "Given"
    session.theme_plan = []
    assert apply_theme_transition(session, False, None, "Kafka") == "Kafka"
    assert session.current_theme_index == 0


def test_theme_transition_never_moves_the_index_backwards():
    session = make_session(("A", "B", "C"), index=2)
    apply_theme_transition(session, True, "A", "Kafka")
    assert session.current_theme_index == 3


def test_theme_transition_clamps_a_stale_index():
    session = make_session(("A", "B"), index=9)
    apply_theme_transition(session, False, None, "Kafka")
    assert session.current_theme_index == 1


def test_theme_progress_never_exceeds_its_own_total():
    for plan, index, expected in [((), 0, (1, 0)), (("A",), 5, (1, 1)), (("A", "B", "C"), 1, (2, 3)),
                                  (("A", "B", "C"), 2, (3, 3))]:
        progress = ThemeProgressResponse.from_session(make_session(plan, index))
        assert (progress.current_theme_index, progress.total_themes) == expected


def test_fallback_question_uses_the_next_theme_in_the_plan():
    q = fallback_next_question(make_session(("A", "B", "C"), index=0), "Kafka")
    assert q.theme == "B" and q.is_follow_up is False and "B" in q.question


def test_fallback_question_when_the_plan_is_used_up():
    q = fallback_next_question(make_session(("A", "B"), index=1), "Kafka")
    assert q.theme == "advanced Kafka topics"


def test_fallback_templates_rotate_by_exchange_count_and_are_verbatim():
    assert len(FALLBACK_QUESTION_TEMPLATES) == 4
    seen = [fallback_next_question(make_session(("A", "B"), exchanges=n), "Kafka").question for n in range(8)]
    assert seen[:4] == [t.format("B") for t in FALLBACK_QUESTION_TEMPLATES] and seen[4:] == seen[:4]
    assert len(set(seen[:4])) == 4
    assert FALLBACK_QUESTION_TEMPLATES[0].startswith("Let's move on to {}. What are the most important things")


@pytest.mark.parametrize(
    "answered, expected",
    [
        (0, "This interview ended before any questions were answered, so there is nothing to assess yet. "
            "Start a new interview when you're ready."),
        (1, "You answered 1 question. A detailed written assessment could not be generated this time, but your "
            "per-question ratings and feedback below are complete."),
        (3, "You answered 3 questions. A detailed written assessment could not be generated this time, but your "
            "per-question ratings and feedback below are complete."),
    ],
)
def test_default_summary_texts(answered, expected):
    assert default_summary(make_session(exchanges=answered)) == expected


# ---------------------------------------------------------------- AI contract (ports MockInterviewAiContractTest)

def test_next_turn_request_serializes_the_field_names_the_ai_service_expects():
    request = NextTurnRequest(
        topic_name="Spring Boot", experience_level="SENIOR", difficulty="MEDIUM", theme_plan=["Beans", "Security"],
        current_theme_index=1, current_follow_up_count=2, remaining_seconds=540,
        prior_exchanges=[NextTurnExchange(question="Q1", user_answer="A1", theme="Beans", is_follow_up=False,
                                          rating="STRONG")],
        last_answer="my answer",
        current_question=NextTurnQuestionContext(question="Explain bean scopes.", theme="Beans", is_follow_up=True),
        must_advance_theme=True, max_follow_ups=4,
    )
    body = request.model_dump(by_alias=True)
    assert set(body) == {
        "topicName", "experienceLevel", "difficulty", "themePlan", "currentThemeIndex", "currentFollowUpCount",
        "remainingSeconds", "priorExchanges", "lastAnswer", "currentQuestion", "mustAdvanceTheme", "maxFollowUps",
    }
    assert body["mustAdvanceTheme"] is True  # a boolean must not be renamed
    assert body["currentQuestion"] == {"question": "Explain bean scopes.", "theme": "Beans", "isFollowUp": True}
    assert body["priorExchanges"][0] == {
        "question": "Q1", "userAnswer": "A1", "theme": "Beans", "isFollowUp": False, "rating": "STRONG",
    }


def test_first_turn_request_keeps_its_nulls():
    body = NextTurnRequest(
        topic_name="T", experience_level="SENIOR", difficulty="EASY", theme_plan=["A"], current_theme_index=0,
        current_follow_up_count=0, remaining_seconds=1800, prior_exchanges=[], must_advance_theme=False,
        max_follow_ups=4,
    ).model_dump(by_alias=True)
    assert body["lastAnswer"] is None and body["currentQuestion"] is None and body["priorExchanges"] == []


def test_next_turn_response_deserializes_the_ai_service_payload():
    response = NextTurnResponse.model_validate({
        "evaluation": {"rating": "STRONG", "feedback": "Clear and specific."},
        "next": {"question": "How would you secure an actuator endpoint?", "theme": "Security",
                 "isFollowUp": False, "advanceTheme": True},
    })
    assert response.evaluation.rating == "STRONG" and response.evaluation.feedback == "Clear and specific."
    assert response.next.theme == "Security"
    assert response.next.advance_theme is True, "advanceTheme must survive the round trip"
    assert response.next.is_follow_up is False


def test_next_turn_response_without_optional_parts():
    assert NextTurnResponse.model_validate({}).next is None
    assert NextTurnResponse.model_validate({"next": {"question": "Q"}}).next.advance_theme is False


def test_plan_and_report_responses():
    assert PlanInterviewResponse.model_validate({"themes": ["a", "b"], "extra": 1}).themes == ["a", "b"]
    report = GenerateInterviewReportResponse.model_validate({
        "strengths": ["Beans"], "weaknesses": ["Security"], "overallSummary": "You were strong on fundamentals.",
        "improvementSuggestions": [{"question": "Q", "userAnswer": "A", "theme": "Security", "betterAnswer": "Better"}],
    })
    assert report.overall_summary == "You were strong on fundamentals."
    assert report.improvement_suggestions[0].better_answer == "Better"
    assert report.improvement_suggestions[0].user_answer == "A"


def test_question_response_keeps_the_is_follow_up_name_the_frontend_reads():
    from app.schemas.interviews import InterviewQuestionResponse

    body = InterviewQuestionResponse(question="Q", theme="Beans", is_follow_up=True).model_dump(by_alias=True)
    assert body == {"question": "Q", "theme": "Beans", "isFollowUp": True}


# ---------------------------------------------------------------- start

async def test_start_uses_the_ai_plan_deduplicated_and_the_ai_opening_question(w):
    w.ai.plan_result = PlanInterviewResponse(themes=[" Beans ", "beans", "Security", ""])
    w.ai.turn_result = turn(None, "Tell me about beans.", "Beans", False, False)

    response = await start(w, "senior", "hard", 45)

    assert response.theme_progress.total_themes == 2
    assert (response.current_question.question, response.current_question.theme) == ("Tell me about beans.", "Beans")
    assert response.current_question.is_follow_up is False
    assert (response.config.experience_level, response.config.difficulty, response.config.duration_minutes) == (
        "SENIOR", "HARD", 45)  # trimmed and upper-cased
    assert w.ai.plan_calls == [("Spring Boot", "SENIOR", "HARD", 45)]
    assert response.status == "IN_PROGRESS" and response.exchanges == [] and response.resumed is False


async def test_the_opening_turn_request_is_what_the_spec_says(w):
    w.ai.plan_result = PlanInterviewResponse(themes=["Beans", "Security"])
    w.ai.turn_result = turn(None, "Q", "Beans", False, False)
    await start(w, "SENIOR", "MEDIUM", 45)
    sent = w.ai.turn_requests[0]
    assert (sent.current_theme_index, sent.current_follow_up_count, sent.remaining_seconds) == (0, 0, 45 * 60)
    assert (sent.prior_exchanges, sent.last_answer, sent.current_question) == ([], None, None)
    assert (sent.must_advance_theme, sent.max_follow_ups, sent.theme_plan) == (False, 4, ["Beans", "Security"])


async def test_opening_question_theme_falls_back_to_the_first_planned_theme(w):
    w.ai.plan_result = PlanInterviewResponse(themes=["Beans"])
    w.ai.turn_result = turn(None, "Q", None, False, False)
    assert (await start(w)).current_question.theme == "Beans"


@pytest.mark.parametrize("plan", [PlanInterviewResponse(themes=[]), PlanInterviewResponse(themes=None),
                                  PlanInterviewResponse(themes=["", "  "]), None])
async def test_an_empty_or_missing_plan_uses_the_default_plan(w, plan):
    w.ai.plan_result = plan
    response = await start(w, minutes=60)
    assert response.theme_progress.total_themes == 8


async def test_opening_fallback_text_is_verbatim(w):
    w.ai.plan_result = PlanInterviewResponse(themes=["Beans"])
    response = await start(w)  # next_turn returns None
    assert response.current_question.question == (
        "To get started, tell me about your experience with Beans and how you have applied it in practice."
    )
    assert response.current_question.theme == "Beans"


@pytest.mark.parametrize("bad", [turn(None, "", "T", False, False), turn(None, "   ", "T", False, False),
                                 NextTurnResponse(next=None)])
async def test_a_blank_opening_question_uses_the_fallback(w, bad):
    w.ai.plan_result = PlanInterviewResponse(themes=["Beans"])
    w.ai.turn_result = bad
    assert (await start(w)).current_question.question.startswith("To get started")


async def test_start_sets_the_deadline_from_the_duration(w):
    response = await start(w, minutes=45)
    assert response.deadline_at == w.clock.now + timedelta(minutes=45)
    assert response.remaining_seconds == 45 * 60


@pytest.mark.parametrize("minutes", [None, 0, 29, 31, 90, -30])
async def test_unsupported_durations_are_rejected(w, minutes):
    error = await api_error_of(start(w, minutes=minutes))
    assert (error.status_code, error.message) == (400, "durationMinutes must be one of 30, 45, or 60")


@pytest.mark.parametrize(
    "level, difficulty, field",
    [(None, "EASY", "experienceLevel"), ("", "EASY", "experienceLevel"),
     ("SENIOR", None, "difficulty"), ("SENIOR", "EXTREME", "difficulty")],
)
async def test_missing_or_unknown_enums_name_the_field(w, level, difficulty, field):
    error = await api_error_of(start(w, level, difficulty, 30))
    assert error.code == "INVALID_INTERVIEW_CONFIG" and error.message.startswith(f"{field} must be one of [")


async def test_start_without_any_body_is_a_config_error_when_nothing_is_running(w):
    error = await api_error_of(w.service.start("user-1", "topic-1", None))
    assert error.code == "INVALID_INTERVIEW_CONFIG"


async def test_start_without_a_body_resumes_a_running_interview(w):
    w.in_progress_session("Q", THEME_A)
    assert (await w.service.start("user-1", "topic-1", None)).resumed is True


async def test_resuming_calls_no_ai(w):
    w.in_progress_session("Q", THEME_A)
    await start(w)
    assert w.ai.plan_calls == [] and w.ai.turn_requests == []


async def test_an_expired_running_session_is_finalized_then_a_new_one_starts(w):
    old = w.in_progress_session("Q", THEME_A)
    w.clock.advance(minutes=21)
    response = await start(w, "JUNIOR", "EASY", 30)
    assert response.resumed is False and response.session_id != "session-1"
    assert (old.status, old.completion_reason) == ("COMPLETED", "TIME_EXPIRED")
    assert old.current_question is None and old.completed_at is not None


async def test_the_deadline_instant_itself_is_not_resumable(w):
    session = w.in_progress_session("Q", THEME_A)
    w.clock.now = session.deadline_at  # isBefore is strict
    assert (await start(w)).resumed is False


async def test_a_new_start_is_rejected_for_bad_config_even_after_finalizing_the_expired_one(w):
    old = w.in_progress_session("Q", THEME_A)
    w.clock.advance(minutes=21)
    await api_error_of(start(w, "WIZARD"))
    assert old.status == "COMPLETED"  # Java finalized first, then validated


async def test_start_for_unknown_or_foreign_topic_is_404(w):
    for user, topic in (("user-1", "nope"), ("user-2", "topic-1")):
        error = await api_error_of(w.service.start(user, topic, StartInterviewRequest()))
        assert (error.status_code, error.code) == (404, "TOPIC_NOT_FOUND")


# ---------------------------------------------------------------- answer

async def test_answer_normalises_input_and_records_the_exchange(w):
    session = w.in_progress_session("Explain bean scopes.", THEME_A)
    w.ai.turn_result = turn("strong", "Next?", THEME_B, False, True, feedback="Well done")

    response = await say(w, "  my answer  ")

    assert w.ai.turn_requests[0].last_answer == "my answer"
    recorded = session.exchanges[0]
    assert (recorded.question, recorded.theme, recorded.is_follow_up) == ("Explain bean scopes.", THEME_A, False)
    assert (recorded.user_answer, recorded.rating, recorded.points, recorded.feedback) == (
        "my answer", "STRONG", 100, "Well done")
    assert response.exchange.index == 1 and response.exchange.user_answer == "my answer"
    assert (response.evaluation.rating, response.evaluation.feedback, response.evaluation.points) == (
        "STRONG", "Well done", 100)
    assert response.is_complete is False and response.remaining_seconds == 20 * 60


async def test_exchange_indexes_are_one_based_and_grow(w):
    w.in_progress_session("Q", THEME_A)
    w.ai.turn_result = turn("STRONG", "Next", THEME_A, True, False)
    first, second = await say(w, "a1"), await say(w, "a2")
    assert (first.exchange.index, second.exchange.index) == (1, 2)


async def test_the_next_question_is_relabelled_with_the_theme_the_session_landed_on(w):
    session = w.in_progress_session("Q", THEME_A)
    w.ai.turn_result = turn("STRONG", "Next", "something the AI invented", False, True)
    response = await say(w, "answer")
    assert response.next_question.theme == THEME_B and session.current_question.theme == THEME_B


async def test_the_follow_up_flag_is_dropped_when_the_theme_advances(w):
    w.in_progress_session("Q", THEME_A)
    w.ai.turn_result = turn("STRONG", "Next", THEME_B, True, True)  # claims follow-up but also advances
    assert (await say(w, "answer")).next_question.is_follow_up is False


async def test_follow_up_flag_is_kept_when_staying_on_the_theme(w):
    w.in_progress_session("Q", THEME_A)
    w.ai.turn_result = turn("STRONG", "Next", THEME_A, True, False)
    assert (await say(w, "answer")).next_question.is_follow_up is True


async def test_next_theme_defaults_to_the_current_one_when_the_ai_names_none(w):
    session = w.in_progress_session("Q", THEME_A)
    w.ai.turn_result = turn("STRONG", "Next", None, True, False)
    assert (await say(w, "answer")).next_question.theme == THEME_A and session.current_theme_index == 0


async def test_unknown_rating_is_satisfactory_and_missing_feedback_gets_the_default(w):
    w.in_progress_session("Q", THEME_A)
    w.ai.turn_result = turn("OUTSTANDING", "Next", THEME_A, True, False, feedback="  ")
    response = await say(w, "answer")
    assert (response.evaluation.rating, response.evaluation.points, response.evaluation.feedback) == (
        "SATISFACTORY", 60, "This answer was recorded.")


async def test_the_follow_up_budget_counts_up_then_forces_an_advance(w):
    session = w.in_progress_session("Q", THEME_A)
    w.ai.turn_result = turn("STRONG", "More", THEME_A, True, False)
    for expected in (1, 2, 3, 4):
        await say(w, "answer")
        assert (session.current_follow_up_count, session.current_theme_index) == (expected, 0)
    assert w.ai.turn_requests[-1].must_advance_theme is False
    await say(w, "answer")  # the fifth: the budget is spent
    assert w.ai.turn_requests[-1].must_advance_theme is True
    assert (session.current_follow_up_count, session.current_theme_index) == (0, 1)


async def test_prior_exchanges_and_state_are_sent_to_the_ai(w):
    session = w.in_progress_session("Q2", THEME_B)
    session.current_theme_index, session.current_follow_up_count = 1, 2
    session.exchanges = [exchange("Q1", THEME_A, False, "A1", "STRONG", 100, "f")]
    w.ai.turn_result = turn("STRONG", "Next", THEME_B, True, False)
    await say(w, "A2")
    sent = w.ai.turn_requests[0]
    assert (sent.current_theme_index, sent.current_follow_up_count, sent.theme_plan) == (1, 2, [THEME_A, THEME_B])
    assert sent.prior_exchanges == [NextTurnExchange(question="Q1", user_answer="A1", theme=THEME_A,
                                                     is_follow_up=False, rating="STRONG")]
    assert (sent.experience_level, sent.difficulty, sent.topic_name) == ("SENIOR", "MEDIUM", "Spring Boot")
    assert sent.remaining_seconds == 20 * 60


async def test_blank_answer_uses_the_ai_next_question_but_a_fixed_evaluation(w):
    session = w.in_progress_session("Q", THEME_A)
    w.ai.turn_result = turn("STRONG", "Sharp next question", THEME_B, True, False, feedback="great!")
    response = await say(w, "")
    assert response.evaluation.feedback == "No answer was submitted for this question, so it scores zero."
    assert (response.evaluation.rating, response.evaluation.points) == ("WEAK", 0)
    assert response.next_question.question == "Sharp next question" and response.next_question.is_follow_up is False
    assert session.exchanges[0].user_answer == "" and w.ai.turn_requests[0].must_advance_theme is True


@pytest.mark.parametrize("text", [None, "", "   ", "\n\t"])
async def test_every_kind_of_blank_scores_zero(w, text):
    w.in_progress_session("Q", THEME_A)
    w.ai.turn_result = turn("STRONG", "Next", THEME_B, False, True)
    assert (await say(w, text)).exchange.points == 0


async def test_blank_answer_with_a_dead_ai_uses_the_fallback_question(w):
    w.in_progress_session("Q", THEME_A)
    w.ai.turn_error = RuntimeError("down")
    response = await say(w, "")
    assert response.evaluation.rating == "WEAK"
    assert response.next_question.theme == THEME_B and THEME_B in response.next_question.question


@pytest.mark.parametrize(
    "result",
    [None, NextTurnResponse(), turn("STRONG", "", THEME_A, False, False), turn("STRONG", "  ", THEME_A, False, False),
     NextTurnResponse(evaluation=None, next=turn("STRONG", "Q", THEME_A, False, False).next),
     NextTurnResponse(evaluation=turn("STRONG", "Q", THEME_A, False, False).evaluation, next=None)],
    ids=["none", "empty", "blank-question", "whitespace-question", "no-evaluation", "no-next"],
)
async def test_an_unusable_ai_turn_is_recorded_as_satisfactory_with_a_fallback_question(w, result):
    session = w.in_progress_session("Q", THEME_A)
    w.ai.turn_result = result
    response = await say(w, "a real answer")
    assert (response.evaluation.rating, response.evaluation.points) == ("SATISFACTORY", 60)
    assert response.evaluation.feedback == "We couldn't score this answer automatically, but it has been recorded."
    assert session.current_theme_index == 1 and session.current_follow_up_count == 0  # always advances


async def test_answer_when_already_completed_is_409(w):
    session = w.in_progress_session("Q", THEME_A)
    session.status = "COMPLETED"
    error = await api_error_of(say(w, "late"))
    assert (error.status_code, error.code, error.message) == (409, "INTERVIEW_ALREADY_COMPLETED",
                                                              "This interview has already been completed.")


async def test_answer_with_no_current_question_is_409(w):
    session = w.in_progress_session("Q", THEME_A)
    session.current_question = None
    error = await api_error_of(say(w, "answer"))
    assert (error.status_code, error.code, error.message) == (
        409, "NO_ACTIVE_QUESTION", "There is no question awaiting an answer on this interview.")


async def test_grace_period_allows_a_slightly_late_answer(w):
    session = w.in_progress_session("Q", THEME_A)
    w.ai.turn_result = turn("STRONG", "Next", THEME_A, True, False)
    w.clock.now = session.deadline_at + timedelta(seconds=4)
    response = await say(w, "just in time")
    assert response.is_complete is False and len(session.exchanges) == 1
    assert response.remaining_seconds == 0  # the clock is past the deadline, but the answer counted


async def test_past_the_grace_period_nothing_is_recorded(w):
    session = w.in_progress_session("Q", THEME_A)
    w.clock.now = session.deadline_at + timedelta(seconds=6)
    response = await say(w, "too late")
    assert response.is_complete is True and session.exchanges == [] and w.ai.turn_requests == []
    assert (response.evaluation, response.next_question, response.exchange, response.remaining_seconds) == (
        None, None, None, 0)
    assert session.status == "COMPLETED" and session.completion_reason == "TIME_EXPIRED"


async def test_answering_checks_ownership(w):
    w.in_progress_session("Q", THEME_A)
    for user, topic, sid in (("user-2", "topic-1", "session-1"), ("user-1", "other", "session-1"),
                             ("user-1", "topic-1", "missing"), ("user-1", "topic-1", "not-an-id")):
        error = await api_error_of(w.service.answer(user, topic, sid, AnswerInterviewRequest(answer="x")))
        assert error.status_code == 404


async def test_the_session_of_another_topic_is_not_found(w):
    from app.models.topic import Topic

    w.topics.items["topic-2"] = Topic(id="topic-2", public_id="topic-2", user_id="user-1", name="Other")
    w.in_progress_session("Q", THEME_A)
    error = await api_error_of(w.service.get("user-1", "topic-2", "session-1"))
    assert (error.status_code, error.code) == (404, "MOCK_INTERVIEW_NOT_FOUND")
    assert error.message == "No mock interview session found with id: session-1"


# ---------------------------------------------------------------- state / end / report

async def test_get_state_of_a_running_interview(w):
    w.in_progress_session("Q", THEME_A)
    state = await w.service.get("user-1", "topic-1", "session-1")
    assert state.is_complete is False and state.status == "IN_PROGRESS" and state.report is None
    assert state.current_question.question == "Q" and state.remaining_seconds == 20 * 60
    assert state.completion_reason is None and state.exchanges == [] and state.config.duration_minutes == 30


async def test_get_state_after_the_deadline_finalizes_and_hides_the_question(w):
    w.in_progress_session("Q", THEME_A)
    w.clock.advance(minutes=21)
    state = await w.service.get("user-1", "topic-1", "session-1")
    assert (state.is_complete, state.status, state.remaining_seconds, state.current_question) == (
        True, "COMPLETED", 0, None)
    assert state.report is not None and state.report.completion_reason == "TIME_EXPIRED"


async def test_get_state_of_a_user_ended_interview_returns_the_same_stored_report(w):
    w.in_progress_session("Q", THEME_A)
    ended = await w.service.end("user-1", "topic-1", "session-1")
    state = await w.service.get("user-1", "topic-1", "session-1")
    assert state.report == ended and len(w.reports.items) == 1 and state.completion_reason == "USER_ENDED"


async def test_end_before_the_deadline_is_user_ended_after_it_is_time_expired(w):
    w.in_progress_session("Q", THEME_A)
    assert (await w.service.end("user-1", "topic-1", "session-1")).completion_reason == "USER_ENDED"
    other = Interviews()
    other.in_progress_session("Q", THEME_A)
    other.clock.advance(minutes=25)
    assert (await other.service.end("user-1", "topic-1", "session-1")).completion_reason == "TIME_EXPIRED"


async def test_ending_twice_returns_the_same_report_without_another_ai_call(w):
    w.in_progress_session("Q", THEME_A)
    w.ai.report_result = report_response()
    first = await w.service.end("user-1", "topic-1", "session-1")
    second = await w.service.end("user-1", "topic-1", "session-1")
    assert first == second and len(w.ai.report_calls) == 1 and len(w.reports.items) == 1


async def test_report_content_comes_from_the_ai_and_the_session(w):
    session = w.in_progress_session("Q", THEME_A)
    session.exchanges = [
        exchange("q1", THEME_A, False, "a1", "STRONG", 100),
        exchange("q2", THEME_B, True, "a2", "WEAK", 20),
    ]
    session.completion_reason = None
    w.ai.report_result = report_response(
        summary="Solid.", strengths=("Beans",), weaknesses=("AOP",),
        suggestions=[("q2", "a2", THEME_B, "A better answer")])

    report = await w.service.end("user-1", "topic-1", "session-1")

    assert (report.session_id, report.score, report.max_score, report.pass_threshold) == ("session-1", 60, 100, 75)
    assert report.passed is False and report.overall_summary == "Solid."
    assert (report.strengths, report.weaknesses) == (["Beans"], ["AOP"])
    assert report.improvement_suggestions[0].better_answer == "A better answer"
    assert (report.config.experience_level, report.config.difficulty, report.config.duration_minutes) == (
        "SENIOR", "MEDIUM", 30)
    assert report.completion_reason == "USER_ENDED"
    assert [(e.index, e.question, e.user_answer, e.rating, e.points) for e in report.exchange_summary] == [
        (1, "q1", "a1", "STRONG", 100), (2, "q2", "a2", "WEAK", 20)]
    topic_name, level, difficulty, sent = w.ai.report_calls[0]
    assert (topic_name, level, difficulty) == ("Spring Boot", "SENIOR", "MEDIUM")
    assert [(e.question, e.user_answer, e.theme, e.rating) for e in sent] == [
        ("q1", "a1", THEME_A, "STRONG"), ("q2", "a2", THEME_B, "WEAK")]


@pytest.mark.parametrize("failure", ["error", "none"])
async def test_report_survives_a_dead_ai_with_the_default_summary(w, failure):
    session = w.in_progress_session("Q", THEME_A)
    session.exchanges = [exchange(points=100)]
    if failure == "error":
        w.ai.report_error = RuntimeError("down")
    report = await w.service.end("user-1", "topic-1", "session-1")
    assert report.overall_summary == default_summary(session)
    assert (report.strengths, report.weaknesses, report.improvement_suggestions) == ([], [], [])
    assert report.score == 100


@pytest.mark.parametrize("summary", ["", "   ", None])
async def test_a_blank_ai_summary_is_replaced_by_the_default(w, summary):
    session = w.in_progress_session("Q", THEME_A)
    w.ai.report_result = report_response(summary=summary)
    report = await w.service.end("user-1", "topic-1", "session-1")
    assert report.overall_summary == default_summary(session)
    assert report.strengths == ["s"]  # the rest of the AI report is still used


async def test_ai_report_with_null_lists_becomes_empty_lists(w):
    w.in_progress_session("Q", THEME_A)
    w.ai.report_result = GenerateInterviewReportResponse(overall_summary="ok")
    report = await w.service.end("user-1", "topic-1", "session-1")
    assert (report.strengths, report.weaknesses, report.improvement_suggestions) == ([], [], [])


async def test_report_for_a_deleted_topic_says_this_topic(w):
    w.in_progress_session("Q", THEME_A)
    del w.topics.items["topic-1"]
    # the topic is gone, so the lookup by public id 404s; ensure_report itself must still cope
    session = w.sessions.items["session-1"]
    session.status, session.completion_reason = "COMPLETED", "USER_ENDED"
    await w.service._ensure_report(session)
    assert w.ai.report_calls[0][0] == "this topic"


async def test_report_before_completion_is_409(w):
    w.in_progress_session("Q", THEME_A)
    error = await api_error_of(w.service.report("user-1", "topic-1", "session-1"))
    assert (error.status_code, error.code, error.message) == (
        409, "INTERVIEW_NOT_COMPLETED", "This interview is still in progress - no report has been generated yet.")


async def test_report_after_completion_generates_it_lazily_once(w):
    session = w.in_progress_session("Q", THEME_A)
    session.status, session.completion_reason = "COMPLETED", "COMPLETED_NATURALLY"
    first = await w.service.report("user-1", "topic-1", "session-1")
    second = await w.service.report("user-1", "topic-1", "session-1")
    assert first == second and first.completion_reason == "COMPLETED_NATURALLY" and len(w.reports.items) == 1


async def test_concurrent_report_requests_generate_exactly_one_report(w):
    w.in_progress_session("Q", THEME_A)
    w.ai.report_result = report_response()
    original = w.ai.generate_interview_report

    async def slow(*args):
        await asyncio.sleep(0.02)
        return await original(*args)

    w.ai.generate_interview_report = slow
    await w.service.end("user-1", "topic-1", "session-1")  # finalize first
    results = await asyncio.gather(*(w.service.report("user-1", "topic-1", "session-1") for _ in range(5)))
    assert len(w.reports.items) == 1 and all(r == results[0] for r in results)


# ---------------------------------------------------------------- list

async def test_list_is_newest_first_with_undated_sessions_last_and_one_report_query(w):
    base = w.clock.now
    for sid, offset in (("old", -3), ("new", 0), ("mid", -1)):
        w.sessions.items[sid] = MockInterviewSession(
            id=sid, topic_id="topic-1", user_id="user-1", experience_level="SENIOR", difficulty="EASY",
            duration_minutes=30, created_at=base + timedelta(hours=offset), exchanges=[exchange(), exchange()])
    w.sessions.items["undated"] = MockInterviewSession(
        id="undated", topic_id="topic-1", user_id="user-1", experience_level="JUNIOR", difficulty="EASY",
        duration_minutes=60, created_at=None)
    w.sessions.items["foreign"] = MockInterviewSession(id="foreign", topic_id="topic-1", user_id="user-2")

    summaries = await w.service.list("user-1", "topic-1")

    assert [s.session_id for s in summaries] == ["new", "mid", "old", "undated"]
    assert w.reports.batch_calls == 1
    assert summaries[0].answered_count == 2 and summaries[3].answered_count == 0
    assert (summaries[3].score, summaries[3].max_score, summaries[3].passed, summaries[3].created_at) == (
        None, None, None, None)
    assert summaries[3].config.experience_level == "JUNIOR"


async def test_list_shows_scores_only_for_sessions_with_a_report(w):
    session = w.in_progress_session("Q", THEME_A)
    session.exchanges = [exchange(points=100)]
    ended = await w.service.end("user-1", "topic-1", "session-1")
    w.sessions.items["session-2"] = MockInterviewSession(
        id="session-2", topic_id="topic-1", user_id="user-1", experience_level="SENIOR", difficulty="MEDIUM",
        duration_minutes=30, created_at=w.clock.now - timedelta(days=1), exchanges=[],
    )
    by_id = {s.session_id: s for s in await w.service.list("user-1", "topic-1")}
    assert (by_id["session-1"].status, by_id["session-1"].completion_reason, by_id["session-1"].score) == (
        "COMPLETED", "USER_ENDED", ended.score)
    assert (by_id["session-1"].max_score, by_id["session-1"].passed) == (100, True)
    assert (by_id["session-2"].status, by_id["session-2"].score) == ("IN_PROGRESS", None)


async def test_list_for_unknown_topic_is_404(w):
    assert (await api_error_of(w.service.list("user-1", "nope"))).code == "TOPIC_NOT_FOUND"


async def test_a_session_started_by_the_service_is_listed(w):
    started = await start(w)
    listed = await w.service.list("user-1", "topic-1")
    assert [s.session_id for s in listed] == [started.session_id] and listed[0].status == "IN_PROGRESS"
    assert QuestionState  # imported for type clarity in other tests
