"""Scenario detection and reply logic, fed with the exact prompts ai-service builds."""

import json
import random

from app import prompts
from app.schemas import ChatMessage, LearnMode, Role
from app.scope_validator import SCOPE_CLASSIFIER_PROMPT

from fake_llm.scenarios import respond

RNG = random.Random(1)


def reply_to(messages, json_mode=False):
    return respond(messages, RNG, json_mode=json_mode)


def interview_turn(**overrides):
    args = dict(
        topic_name="Docker",
        experience_level="INTERMEDIATE",
        difficulty="MEDIUM",
        theme_plan=["Docker Fundamentals", "Core Building Blocks", "Testing Strategies"],
        current_theme_index=0,
        current_follow_up_count=0,
        remaining_seconds=1500,
        prior_exchanges=[],
        last_answer=None,
        current_question=None,
    )
    args.update(overrides)
    return json.loads(reply_to(prompts.build_interview_next_turn_messages(**args), json_mode=True).text)


def test_scope_check_accepts_tech_topics_and_declines_others():
    def classify(topic):
        return reply_to([{"role": "system", "content": SCOPE_CLASSIFIER_PROMPT}, {"role": "user", "content": f"Topic: {topic}"}])

    assert classify("Spring Boot").text == "YES"
    assert classify("Cricket world cup").text == "NO"


def test_learn_modes_are_told_apart():
    history = [ChatMessage(role=Role.AI, content="Which area?"), ChatMessage(role=Role.USER, content="A deep dive please")]
    clarify = reply_to(prompts.build_messages("Redis", LearnMode.CLARIFY, []))
    content = reply_to(prompts.build_messages("Redis", LearnMode.GENERATE_CONTENT, history))
    follow_up = reply_to(prompts.build_messages(
        "Redis", LearnMode.FOLLOW_UP, history + [ChatMessage(role=Role.USER, content="Can you show me an example?")]
    ))

    assert clarify.scenario == "learn_clarify" and "Redis" in clarify.text
    assert content.scenario == "learn_content" and "```" in content.text
    assert follow_up.scenario == "learn_follow_up" and "```python" in follow_up.text


def test_learn_declines_off_topic_messages():
    history = [ChatMessage(role=Role.USER, content="Who will win the cricket match tonight?")]
    reply = reply_to(prompts.build_messages("Python", LearnMode.FOLLOW_UP, history))
    assert reply.scenario == "learn_decline"
    assert "interview preparation" in reply.text


def test_student_learners_get_placement_flavoured_questions():
    reply = reply_to(prompts.build_messages("Java", LearnMode.CLARIFY, [], experience_level="STUDENT"))
    assert "placement" in reply.text.lower()


def test_test_generation_returns_ten_mcq_and_ten_subjective():
    reply = reply_to(prompts.build_test_generation_messages("PostgreSQL"))
    questions = json.loads(reply.text)["questions"]

    assert reply.scenario == "test_generate"
    assert [q["section"] for q in questions].count("MCQ") == 10
    assert [q["section"] for q in questions].count("SUBJECTIVE") == 10
    assert len({q["questionId"] for q in questions}) == 20
    for q in questions:
        if q["section"] == "MCQ":
            assert len(q["options"]) == 4 and q["correctOption"] in q["options"]
        else:
            assert q["modelAnswer"]


def test_retest_targets_previous_weaknesses():
    messages = prompts.build_test_generation_messages("PostgreSQL", strengths=["Caching"], weaknesses=["Concurrency", "Indexes"])
    texts = [q["text"] for q in json.loads(reply_to(messages).text)["questions"]]
    assert any(t.startswith("Revisiting Concurrency:") for t in texts)
    assert any(t.startswith("Revisiting Indexes:") for t in texts)


def test_evaluation_grades_every_question_and_names_concepts():
    questions = json.loads(reply_to(prompts.build_test_generation_messages("Go")).text)["questions"]
    answers = []
    for i, q in enumerate(questions):
        if q["section"] == "MCQ":
            user = q["correctOption"] if i % 2 == 0 else next(o for o in q["options"] if o != q["correctOption"])
            answers.append({"questionId": q["questionId"], "section": "MCQ", "question": q["text"],
                            "correctAnswer": q["correctOption"], "userAnswer": user})
        else:
            answers.append({"questionId": q["questionId"], "section": "SUBJECTIVE", "question": q["text"],
                            "correctAnswer": q["modelAnswer"], "userAnswer": q["modelAnswer"] if i % 2 == 0 else None})

    report = json.loads(reply_to(prompts.build_test_evaluation_messages("Go", answers)).text)
    graded = {item["questionId"]: item["isCorrect"] for item in report["perQuestion"]}

    assert set(graded) == {q["questionId"] for q in questions}
    for i, q in enumerate(questions):
        assert graded[q["questionId"]] is (i % 2 == 0), q["text"]
    assert report["strengths"] and report["weaknesses"]


def test_interview_plan_has_the_requested_number_of_themes():
    plan = json.loads(reply_to(prompts.build_interview_plan_messages("Kafka", "SENIOR", "HARD", 45)).text)
    assert len(plan["themes"]) == 6
    assert plan["themes"][0] == "Kafka Fundamentals"
    assert not any(theme.endswith("?") for theme in plan["themes"])


def test_interview_opening_turn_has_no_evaluation():
    turn = interview_turn()
    assert turn["evaluation"] is None
    assert turn["next"]["theme"] == "Docker Fundamentals"
    assert turn["next"]["isFollowUp"] is False


def test_strong_answer_gets_a_follow_up_on_the_same_theme():
    opening = interview_turn()["next"]
    turn = interview_turn(
        current_question={"question": opening["question"], "theme": opening["theme"], "isFollowUp": False},
        last_answer=" ".join(["Containers package an application with its dependencies so it runs the same everywhere."] * 5),
    )
    assert turn["evaluation"]["rating"] == "STRONG"
    assert turn["next"] == {**turn["next"], "theme": "Docker Fundamentals", "isFollowUp": True, "advanceTheme": False}
    assert turn["next"]["question"] != opening["question"]


def test_weak_answer_moves_to_the_next_theme():
    turn = interview_turn(
        current_question={"question": "What is a container?", "theme": "Docker Fundamentals", "isFollowUp": False},
        last_answer="no idea",
    )
    assert turn["evaluation"]["rating"] == "WEAK"
    assert turn["next"]["theme"] == "Core Building Blocks"
    assert turn["next"]["advanceTheme"] is True


def test_exhausted_follow_up_budget_forces_a_new_theme():
    turn = interview_turn(
        current_question={"question": "What is a container?", "theme": "Docker Fundamentals", "isFollowUp": True},
        last_answer=" ".join(["A detailed and correct answer about images, layers and the container runtime."] * 5),
        must_advance_theme=True,
    )
    assert turn["evaluation"]["rating"] == "STRONG"
    assert turn["next"]["advanceTheme"] is True and turn["next"]["isFollowUp"] is False


def test_turns_never_repeat_an_asked_question():
    asked = []
    for _ in range(12):
        opening = interview_turn(asked_questions=asked)["next"]["question"]
        assert opening not in asked
        asked.append(opening)


def test_report_splits_strong_and_weak_themes():
    exchanges = [
        {"question": "Q1", "userAnswer": "long answer", "theme": "Docker Fundamentals", "rating": "STRONG"},
        {"question": "Q2", "userAnswer": "short", "theme": "Testing Strategies", "rating": "WEAK"},
        {"question": "Q3", "userAnswer": None, "theme": "Testing Strategies", "rating": "SATISFACTORY"},
    ]
    report = json.loads(reply_to(prompts.build_interview_report_messages("Docker", "JUNIOR", "EASY", exchanges)).text)
    assert report["strengths"] == ["Docker Fundamentals"]
    assert report["weaknesses"] == ["Testing Strategies"]
    assert [s["question"] for s in report["improvementSuggestions"]] == ["Q2", "Q3"]
    assert report["improvementSuggestions"][1]["userAnswer"] is None


def test_report_for_an_empty_interview():
    report = json.loads(reply_to(prompts.build_interview_report_messages("Docker", "JUNIOR", "EASY", [])).text)
    assert report["strengths"] == [] and report["improvementSuggestions"] == []
    assert "before answering" in report["overallSummary"]


def test_unknown_prompts_get_a_generic_reply():
    assert reply_to([{"role": "user", "content": "hi"}]).scenario == "unknown"
    assert json.loads(reply_to([{"role": "user", "content": "hi"}], json_mode=True).text)
