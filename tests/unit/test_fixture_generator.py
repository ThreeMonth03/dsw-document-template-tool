"""Tests for deterministic questionnaire fixture generation."""

from __future__ import annotations

from dsw_document_template_tool.fixture_coverage import plan_generated_fixture_cases
from dsw_document_template_tool.fixture_generator import generate_questionnaire_events


def test_generate_questionnaire_events_is_deterministic_and_path_aware() -> None:
    """Generated events should be stable and follow DSW questionnaire path rules."""

    questionnaire = _synthetic_questionnaire()

    first = generate_questionnaire_events(
        questionnaire,
        seed=20260522,
        case_index=0,
        max_events=50,
        max_items_per_list=2,
    )
    second = generate_questionnaire_events(
        questionnaire,
        seed=20260522,
        case_index=0,
        max_events=50,
        max_items_per_list=2,
    )

    assert first == second
    assert first.events
    assert first.events[0]["path"] == "chapter-1.q-options"
    assert first.events[0]["value"]["type"] == "AnswerReply"

    paths = [event["path"] for event in first.events]
    assert "chapter-1.q-options.answer-b.q-follow-up" in paths
    assert "chapter-1.q-list" in paths
    assert any(
        path.startswith("chapter-1.q-list.") and path.endswith(".q-list-value") for path in paths
    )

    list_event = next(event for event in first.events if event["path"] == "chapter-1.q-list")
    assert list_event["value"]["type"] == "ItemListReply"
    assert len(list_event["value"]["value"]) == 2


def test_generate_questionnaire_events_covers_different_option_answers_across_cases() -> None:
    """The fixed seed still varies branches by case index."""

    questionnaire = _synthetic_questionnaire()

    selected_answers = {
        generate_questionnaire_events(
            questionnaire,
            seed=20260522,
            case_index=case_index,
            max_events=50,
            max_items_per_list=1,
        ).events[0]["value"]["value"]
        for case_index in range(4)
    }

    assert selected_answers == {"answer-a", "answer-b"}


def test_generate_questionnaire_events_cycles_nested_followup_answers() -> None:
    """Nested follow-up options should not get stuck on one parent parity."""

    questionnaire = _synthetic_questionnaire()
    nested_answers: set[str] = set()

    for case_index in range(8):
        generated = generate_questionnaire_events(
            questionnaire,
            seed=20260522,
            case_index=case_index,
            max_events=50,
            max_items_per_list=1,
        )
        nested_answers.update(
            entry["answer_uuid"]
            for entry in generated.stats["selected_answer_indexes"]
            if entry["question_uuid"] == "q-nested-options"
        )

    assert nested_answers == {"nested-a", "nested-b"}


def test_generate_questionnaire_events_cycles_list_cardinalities() -> None:
    """List questions should cover empty, single, and repeated item shapes."""

    questionnaire = _synthetic_questionnaire()
    item_counts = {
        entry["item_count"]
        for case_index in range(6)
        for entry in generate_questionnaire_events(
            questionnaire,
            seed=20260522,
            case_index=case_index,
            max_events=50,
            max_items_per_list=2,
        ).stats["list_cardinalities"]
        if entry["question_uuid"] == "q-list"
    }

    assert item_counts == {0, 1, 2}


def test_plan_generated_fixture_cases_covers_branches_with_compact_selection() -> None:
    """The planner should cover every reachable branch without rendering its full pool."""

    plan = plan_generated_fixture_cases(
        _synthetic_questionnaire(),
        seed=20260522,
        case_limit=4,
        candidate_count=24,
        max_events=50,
        max_items_per_list=2,
        answer_probability=1.0,
    )

    assert plan.complete
    assert plan.case_indexes == (0, 1, 2, 7)
    assert len(plan.covered) == len(plan.expected)
    assert plan.as_dict()["missing_branches"] == []


def test_plan_generated_fixture_cases_reports_insufficient_case_limit() -> None:
    """A deliberately small limit should produce a reviewable incomplete report."""

    plan = plan_generated_fixture_cases(
        _synthetic_questionnaire(),
        seed=20260522,
        case_limit=1,
        candidate_count=24,
        max_events=50,
        max_items_per_list=2,
        answer_probability=1.0,
    )

    report = plan.as_dict()
    assert not plan.complete
    assert report["missing_branch_count"] > 0
    assert report["categories"]["option_answer"]["missing"] > 0


def _synthetic_questionnaire() -> dict[str, object]:
    return {
        "knowledgeModel": {
            "chapterUuids": ["chapter-1"],
            "entities": {
                "chapters": {
                    "chapter-1": {
                        "uuid": "chapter-1",
                        "questionUuids": ["q-options", "q-list", "q-multi"],
                    }
                },
                "questions": {
                    "q-options": {
                        "uuid": "q-options",
                        "title": "Choose a branch",
                        "questionType": "OptionsQuestion",
                        "answerUuids": ["answer-a", "answer-b"],
                    },
                    "q-follow-up": {
                        "uuid": "q-follow-up",
                        "title": "Explain the selected branch",
                        "questionType": "ValueQuestion",
                    },
                    "q-nested-options": {
                        "uuid": "q-nested-options",
                        "title": "Choose a nested branch",
                        "questionType": "OptionsQuestion",
                        "answerUuids": ["nested-a", "nested-b"],
                    },
                    "q-list": {
                        "uuid": "q-list",
                        "title": "Datasets",
                        "questionType": "ListQuestion",
                        "itemTemplateQuestionUuids": ["q-list-value"],
                    },
                    "q-list-value": {
                        "uuid": "q-list-value",
                        "title": "Dataset name",
                        "questionType": "ValueQuestion",
                    },
                    "q-multi": {
                        "uuid": "q-multi",
                        "title": "Methods",
                        "questionType": "MultiChoiceQuestion",
                        "choiceUuids": ["choice-a", "choice-b", "choice-c"],
                    },
                },
                "answers": {
                    "answer-a": {"uuid": "answer-a", "followUpUuids": []},
                    "answer-b": {
                        "uuid": "answer-b",
                        "followUpUuids": ["q-follow-up", "q-nested-options"],
                    },
                    "nested-a": {"uuid": "nested-a", "followUpUuids": []},
                    "nested-b": {"uuid": "nested-b", "followUpUuids": []},
                },
            },
        }
    }
