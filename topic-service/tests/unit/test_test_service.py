import pytest

from app.clients.ai_schemas import AiQuestion, AiQuestionEvaluation, EvaluateAnswersResponse
from app.errors import ApiError
from app.models.test_session import Question, Section, Status
from app.models.topic import Topic
from app.schemas.tests import SubmitAnswerRequest, SubmitTestRequest
from app.services.test_service import TestService, calculate_points, match_evaluations
from tests.unit.fakes_tests import (
    DEFAULT_QUESTIONS,
    FakeReports,
    FakeSessions,
    FakeTestAi,
    FakeTopicsWithScores,
    question,
)

M, S = Section.MCQ, Section.SUBJECTIVE


# ---------- scoring table ----------

@pytest.mark.parametrize(
    "section, answer, correct, points",
    [
        (M, "B", True, 1), (M, "A", False, -1), (M, None, True, 0), (M, None, False, 0),
        (M, "", True, 1), (M, "", False, -1),  # an empty string is an answer, not "unanswered"
        (S, "text", True, 5), (S, "text", False, -5), (S, None, True, 0), (S, None, False, 0),
        (S, "", True, 5), (S, "", False, -5),
    ],
)
def test_points_table(section, answer, correct, points):
    assert calculate_points(section, answer, correct) == points


# ---------- matching AI evaluations to questions ----------

def stored_questions(*ids) -> list[Question]:
    return [Question(question_id=i, section=M, text=f"t{i}") for i in ids]


def verdicts(*items) -> EvaluateAnswersResponse:
    return EvaluateAnswersResponse(per_question=[AiQuestionEvaluation(question_id=i, is_correct=c, evaluation=e)
                                                 for i, c, e in items])


def test_matches_by_question_id_regardless_of_order():
    matched = match_evaluations(stored_questions("a", "b"), verdicts(("b", False, "B"), ("a", True, "A")))
    assert [(m.question_id, m.evaluation) for m in matched] == [("a", "A"), ("b", "B")]


def test_falls_back_to_position_when_the_ai_sends_no_ids():
    matched = match_evaluations(stored_questions("a", "b"), verdicts((None, True, "first"), (None, False, "second")))
    assert [m.evaluation for m in matched] == ["first", "second"]


def test_empty_string_ids_also_trigger_position_matching():
    matched = match_evaluations(stored_questions("a"), verdicts(("", True, "only")))
    assert matched[0].evaluation == "only"


def test_position_fallback_does_not_run_off_the_end():
    with pytest.raises(ApiError) as exc:
        match_evaluations(stored_questions("a", "b"), verdicts((None, True, "only one")))
    assert exc.value.status_code == 502


def test_a_missing_evaluation_is_a_502():
    with pytest.raises(ApiError) as exc:
        match_evaluations(stored_questions("a", "b"), verdicts(("a", True, "A")))
    assert (exc.value.status_code, exc.value.code) == (502, "AI_SERVICE_ERROR")
    assert exc.value.message == "No evaluation found for question: b"


def test_partial_ids_do_not_trigger_position_matching():
    with pytest.raises(ApiError):
        match_evaluations(stored_questions("a", "b"), verdicts(("a", True, "A"), (None, True, "x")))


def test_missing_per_question_is_a_502():
    with pytest.raises(ApiError) as exc:
        match_evaluations(stored_questions("a"), EvaluateAnswersResponse(per_question=None))
    assert exc.value.status_code == 502


def test_empty_per_question_is_a_502_when_there_are_questions():
    with pytest.raises(ApiError):
        match_evaluations(stored_questions("a"), EvaluateAnswersResponse(per_question=[]))


# ---------- fixtures ----------

class World:
    def __init__(self, ai: FakeTestAi) -> None:
        self.topics, self.sessions, self.reports, self.ai = FakeTopicsWithScores(), FakeSessions(), FakeReports(), ai
        self.service = TestService(self.topics, self.sessions, self.reports, ai)
        self.topic: Topic | None = None

    async def create_topic(self, name="Kafka", user="u1", public="pub-1") -> Topic:
        self.topic = await self.topics.insert(Topic(public_id=public, user_id=user, name=name))
        return self.topic

    def submit(self, session_id, answers: dict | None, user="u1", topic="pub-1"):
        request = SubmitTestRequest(
            answers=None if answers is None
            else [SubmitAnswerRequest(question_id=k, user_answer=v) for k, v in answers.items()]
        )
        return self.service.submit(user, topic, session_id, request)


@pytest.fixture
async def world():
    w = World(FakeTestAi())
    await w.create_topic()
    return w


def wire(model) -> dict:
    return model.model_dump(by_alias=True)


# ---------- start ----------

async def test_start_stores_questions_with_answers_but_never_returns_them(world):
    started = await world.service.start("u1", "pub-1")
    assert len(started.questions) == len(DEFAULT_QUESTIONS)
    assert all(set(wire(q)) == {"questionId", "section", "text", "options"} for q in started.questions)
    stored = world.sessions.items[started.session_id]
    assert stored.questions[0].correct_option == "B" and stored.questions[3].model_answer == "model s1"
    assert stored.status == Status.IN_PROGRESS and stored.attempt_number == 1
    assert (started.attempt_number, started.based_on_previous_attempt) == (1, False)


async def test_subjective_questions_have_null_options_on_the_wire(world):
    started = await world.service.start("u1", "pub-1")
    assert wire(started.questions[3])["options"] is None
    assert wire(started.questions[0])["options"] == ["A", "B", "C", "D"]


async def test_start_is_idempotent_while_in_progress(world):
    first = await world.service.start("u1", "pub-1")
    second = await world.service.start("u1", "pub-1")
    assert first.session_id == second.session_id
    assert len(world.ai.generate_calls) == 1 and len(world.sessions.items) == 1


async def test_first_attempt_sends_no_history_to_the_ai(world):
    await world.service.start("u1", "pub-1")
    assert world.ai.generate_calls == [{"topic": "Kafka", "strengths": None, "weaknesses": None}]


async def test_second_attempt_is_biased_by_the_previous_report(world):
    first = await world.service.start("u1", "pub-1")
    await world.submit(first.session_id, {})
    second = await world.service.start("u1", "pub-1")
    assert second.session_id != first.session_id
    assert (second.attempt_number, second.based_on_previous_attempt) == (2, True)
    assert world.ai.generate_calls[1] == {"topic": "Kafka", "strengths": ["Basics"], "weaknesses": ["Internals"]}
    assert world.sessions.items[second.session_id].based_on_previous_attempt is True


async def test_previous_report_without_weaknesses_is_not_a_basis(world):
    world.ai.weaknesses = []
    first = await world.service.start("u1", "pub-1")
    await world.submit(first.session_id, {})
    second = await world.service.start("u1", "pub-1")
    assert second.based_on_previous_attempt is False
    assert world.ai.generate_calls[1]["weaknesses"] == []  # still passed through as given


async def test_attempt_number_counts_all_sessions_for_this_user_and_topic(world):
    first = await world.service.start("u1", "pub-1")
    await world.submit(first.session_id, {})
    second = await world.service.start("u1", "pub-1")
    await world.submit(second.session_id, {})
    assert (await world.service.start("u1", "pub-1")).attempt_number == 3


async def test_other_users_and_topics_do_not_affect_attempt_numbers(world):
    await world.create_topic("Spark", user="u2", public="pub-2")
    await world.service.start("u2", "pub-2")
    assert (await world.service.start("u1", "pub-1")).attempt_number == 1


async def test_start_for_unknown_or_foreign_topic_is_404(world):
    for user, topic in (("u1", "missing"), ("u2", "pub-1")):
        with pytest.raises(ApiError) as exc:
            await world.service.start(user, topic)
        assert exc.value.code == "TOPIC_NOT_FOUND"
    assert world.ai.generate_calls == []


@pytest.mark.parametrize("bad", [AiQuestion(question_id="x", section="ESSAY", text="t"),
                                 AiQuestion(question_id="x", section=None, text="t"),
                                 AiQuestion(question_id=None, section="MCQ", text="t")])
async def test_an_unusable_question_from_the_ai_is_a_502_and_stores_nothing(world, bad):
    world.ai.questions = [question("ok"), bad]
    with pytest.raises(ApiError) as exc:
        await world.service.start("u1", "pub-1")
    assert (exc.value.status_code, exc.value.code) == (502, "AI_SERVICE_ERROR")
    assert world.sessions.items == {}


# ---------- get ----------

async def test_get_returns_the_session_without_answers(world):
    started = await world.service.start("u1", "pub-1")
    again = await world.service.get("u1", "pub-1", started.session_id)
    assert wire(again) == wire(started)


@pytest.mark.parametrize("test_id", ["f" * 24, "not-an-object-id", ""])
async def test_get_unknown_or_malformed_id_is_404(world, test_id):
    with pytest.raises(ApiError) as exc:
        await world.service.get("u1", "pub-1", test_id)
    assert (exc.value.status_code, exc.value.code) == (404, "TEST_NOT_FOUND")


async def test_get_is_scoped_to_user_and_topic(world):
    started = await world.service.start("u1", "pub-1")
    await world.create_topic("Spark", user="u1", public="pub-2")
    await world.create_topic("Kafka", user="u2", public="pub-3")
    for user, topic in (("u2", "pub-3"), ("u1", "pub-2")):
        with pytest.raises(ApiError) as exc:
            await world.service.get(user, topic, started.session_id)
        assert exc.value.code == "TEST_NOT_FOUND"


# ---------- submit ----------

ANSWERS = {"m1": "B", "m2": "A", "m3": None, "s1": "my essay", "s2": None}


async def test_submit_scores_a_mixed_test(world):
    world.ai.correct = {"m1", "s1"}  # m1 right (+1), m2 wrong (-1), m3 unanswered (0), s1 right (+5), s2 unanswered
    started = await world.service.start("u1", "pub-1")
    report = await world.submit(started.session_id, ANSWERS)
    assert report.raw_score == 5 and report.passed is False
    assert [(r.question_id, r.points_awarded, r.is_correct) for r in report.question_summary] == [
        ("m1", 1, True), ("m2", -1, False), ("m3", 0, False), ("s1", 5, True), ("s2", 0, False)
    ]


async def test_unanswered_questions_get_the_fixed_text_even_if_the_ai_comments(world):
    started = await world.service.start("u1", "pub-1")
    report = await world.submit(started.session_id, {"m1": "B"})
    by_id = {r.question_id: r for r in report.question_summary}
    assert by_id["m2"].evaluation == "Not answered." and by_id["m2"].is_correct is False
    assert by_id["m2"].user_answer is None and by_id["m2"].points_awarded == 0
    assert by_id["m1"].evaluation == "feedback m1"


async def test_an_empty_string_is_an_answer_and_scored_as_wrong(world):
    world.ai.correct = set()
    started = await world.service.start("u1", "pub-1")
    report = await world.submit(started.session_id, {"m1": "", "s1": ""})
    by_id = {r.question_id: r for r in report.question_summary}
    assert (by_id["m1"].points_awarded, by_id["s1"].points_awarded) == (-1, -5)
    assert by_id["m1"].user_answer == "" and by_id["m1"].evaluation == "feedback m1"
    assert report.raw_score == -6


async def test_all_unanswered_scores_zero_and_fails(world):
    started = await world.service.start("u1", "pub-1")
    report = await world.submit(started.session_id, {})
    assert (report.raw_score, report.passed, report.max_score, report.pass_threshold) == (0, False, 60, 36)


@pytest.mark.parametrize("raw, passed", [(35, False), (36, True), (37, True), (60, True), (-60, False)])
async def test_pass_threshold_is_inclusive_at_36(raw, passed):
    # one question worth `raw` points is not possible, so fake the evaluation of many MCQs
    count = abs(raw)
    questions = [question(f"m{i}") for i in range(count)] or [question("m0")]
    w = World(FakeTestAi(questions=questions, correct=None if raw > 0 else set()))
    await w.create_topic()
    started = await w.service.start("u1", "pub-1")
    report = await w.submit(started.session_id, {q.question_id: "x" for q in questions})
    assert (report.raw_score, report.passed) == (raw, passed)


async def test_evaluation_request_has_every_question_in_order_with_the_right_reference_answer(world):
    started = await world.service.start("u1", "pub-1")
    await world.submit(started.session_id, {"m1": "B", "s1": "essay", "ghost": "ignored"})
    sent = world.ai.evaluate_calls[0]
    assert sent["topic"] == "Kafka"
    assert [a["questionId"] for a in sent["answers"]] == ["m1", "m2", "m3", "s1", "s2"]
    by_id = {a["questionId"]: a for a in sent["answers"]}
    assert by_id["m1"] == {"questionId": "m1", "section": "MCQ", "question": "Q m1?", "correctAnswer": "B",
                           "userAnswer": "B"}
    assert by_id["s1"]["correctAnswer"] == "model s1" and by_id["s1"]["section"] == "SUBJECTIVE"
    assert by_id["m2"]["userAnswer"] is None


async def test_duplicate_answers_for_one_question_last_one_wins(world):
    started = await world.service.start("u1", "pub-1")
    request = SubmitTestRequest(answers=[SubmitAnswerRequest(question_id="m1", user_answer="A"),
                                         SubmitAnswerRequest(question_id="m1", user_answer="B")])
    await world.service.submit("u1", "pub-1", started.session_id, request)
    assert {a["questionId"]: a["userAnswer"] for a in world.ai.evaluate_calls[0]["answers"]}["m1"] == "B"


async def test_position_matching_end_to_end(world):
    world.ai.no_ids = True
    world.ai.correct = None
    started = await world.service.start("u1", "pub-1")
    report = await world.submit(started.session_id, {"m1": "B", "m2": "B"})
    assert report.raw_score == 2 and report.question_summary[0].evaluation == "feedback m1"


async def test_session_is_completed_with_answers_and_score(world):
    started = await world.service.start("u1", "pub-1")
    await world.submit(started.session_id, ANSWERS)
    stored = world.sessions.items[started.session_id]
    assert stored.status == Status.COMPLETED and stored.completed_at is not None
    assert stored.raw_score == sum(a.points_awarded for a in stored.answers)
    assert [a.question_id for a in stored.answers] == ["m1", "m2", "m3", "s1", "s2"]


async def test_report_content_and_topic_aggregate(world):
    world.ai.correct = {"m1", "s1"}
    started = await world.service.start("u1", "pub-1")
    report = await world.submit(started.session_id, ANSWERS)
    assert report.test_session_id == started.session_id
    assert (report.strengths, report.weaknesses) == (["Basics"], ["Internals"])
    assert (report.attempt_number, report.based_on_previous_attempt) == (1, False)
    assert report.avg_score_at_time == 5.0
    topic = world.topics.items[world.topic.id]
    assert (topic.test_count, topic.avg_score) == (1, 5.0)
    stored_report = world.reports.items[0]
    assert stored_report.topic_id == world.topic.id and stored_report.test_session_id == started.session_id


async def test_report_correct_answer_is_revealed_only_now(world):
    started = await world.service.start("u1", "pub-1")
    report = await world.submit(started.session_id, {})
    by_id = {r.question_id: r for r in report.question_summary}
    assert by_id["m1"].correct_answer == "B" and by_id["s1"].correct_answer == "model s1"
    assert by_id["m1"].question_text == "Q m1?" and by_id["m1"].section == "MCQ"


async def test_averages_accumulate_across_tests(world):
    scores = []
    for answers in ({"s1": "x", "s2": "x"}, {"s1": "x", "s2": "x", "m1": "B", "m2": "B"}, {"m1": "B"}):
        started = await world.service.start("u1", "pub-1")
        scores.append((await world.submit(started.session_id, answers)).avg_score_at_time)
    assert scores == [10.0, pytest.approx((10 + 12) / 2), pytest.approx((10 + 12 + 1) / 3)]
    assert world.topics.items[world.topic.id].test_count == 3


async def test_submit_requires_in_progress(world):
    started = await world.service.start("u1", "pub-1")
    await world.submit(started.session_id, {})
    calls = len(world.ai.evaluate_calls)
    with pytest.raises(ApiError) as exc:
        await world.submit(started.session_id, {})
    assert (exc.value.status_code, exc.value.code) == (409, "TEST_ALREADY_COMPLETED")
    assert len(world.ai.evaluate_calls) == calls  # no AI call is wasted
    assert len(world.reports.items) == 1


async def test_losing_the_completion_race_adds_no_report_and_does_not_count_the_test(world):
    started = await world.service.start("u1", "pub-1")
    world.sessions.lose_the_completion_race = True
    with pytest.raises(ApiError) as exc:
        await world.submit(started.session_id, ANSWERS)
    assert exc.value.code == "TEST_ALREADY_COMPLETED"
    assert world.reports.items == []
    assert world.topics.items[world.topic.id].test_count == 0


async def test_missing_evaluation_is_a_502_and_leaves_the_test_open(world):
    world.ai.drop = {"m2"}
    started = await world.service.start("u1", "pub-1")
    with pytest.raises(ApiError) as exc:
        await world.submit(started.session_id, ANSWERS)
    assert (exc.value.status_code, exc.value.code) == (502, "AI_SERVICE_ERROR")
    assert world.sessions.items[started.session_id].status == Status.IN_PROGRESS
    assert world.reports.items == [] and world.topics.items[world.topic.id].test_count == 0


async def test_answered_question_with_no_verdict_is_a_502_not_a_crash(world):
    world.ai.override = EvaluateAnswersResponse(
        per_question=[AiQuestionEvaluation(question_id=q.question_id, is_correct=None) for q in DEFAULT_QUESTIONS]
    )
    started = await world.service.start("u1", "pub-1")
    with pytest.raises(ApiError) as exc:
        await world.submit(started.session_id, {"m1": "B"})
    assert exc.value.status_code == 502
    assert world.sessions.items[started.session_id].status == Status.IN_PROGRESS


async def test_unanswered_question_with_no_verdict_is_fine(world):
    world.ai.override = EvaluateAnswersResponse(
        per_question=[AiQuestionEvaluation(question_id=q.question_id, is_correct=None) for q in DEFAULT_QUESTIONS]
    )
    started = await world.service.start("u1", "pub-1")
    assert (await world.submit(started.session_id, {})).raw_score == 0


async def test_missing_answers_list_is_a_400_before_any_ai_call(world):
    started = await world.service.start("u1", "pub-1")
    with pytest.raises(ApiError) as exc:
        SubmitTestRequest(answers=None).ensure_valid()
    assert (exc.value.status_code, exc.value.message) == (400, "Answers are required")
    assert world.ai.evaluate_calls == [] and started.session_id


async def test_submit_scoped_to_user(world):
    started = await world.service.start("u1", "pub-1")
    await world.create_topic("Kafka", user="u2", public="pub-9")
    with pytest.raises(ApiError) as exc:
        await world.submit(started.session_id, {}, user="u2", topic="pub-9")
    assert exc.value.code == "TEST_NOT_FOUND"


# ---------- report and list ----------

async def test_report_before_submit_is_404(world):
    started = await world.service.start("u1", "pub-1")
    with pytest.raises(ApiError) as exc:
        await world.service.report("u1", "pub-1", started.session_id)
    assert (exc.value.status_code, exc.value.code) == (404, "TEST_REPORT_NOT_FOUND")


async def test_report_equals_what_submit_returned(world):
    started = await world.service.start("u1", "pub-1")
    submitted = await world.submit(started.session_id, ANSWERS)
    assert wire(await world.service.report("u1", "pub-1", started.session_id)) == wire(submitted)


async def test_list_has_one_item_per_report_with_one_session_query(world):
    ids = []
    for _ in range(3):
        started = await world.service.start("u1", "pub-1")
        await world.submit(started.session_id, {"m1": "B"})
        ids.append(started.session_id)
    items = await world.service.list("u1", "pub-1")
    assert [i.session_id for i in items] == ids
    assert [i.attempt_number for i in items] == [1, 2, 3]
    assert all(i.completed_at is not None for i in items) and world.sessions.find_by_ids_calls == 1


async def test_list_ignores_in_progress_tests_and_other_users(world):
    await world.service.start("u1", "pub-1")
    assert await world.service.list("u1", "pub-1") == []
    with pytest.raises(ApiError):
        await world.service.list("u2", "pub-1")
