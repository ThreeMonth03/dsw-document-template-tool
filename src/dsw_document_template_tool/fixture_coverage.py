"""Plan a compact set of generated projects that covers questionnaire branches."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .fixture_generator import GeneratedQuestionnaireEvents, generate_questionnaire_events


@dataclass(frozen=True, order=True)
class BranchToken:
    """One answer or collection shape that a generated fixture can exercise."""

    category: str
    question_uuid: str
    value: str

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-serializable representation."""

        return {
            "category": self.category,
            "question_uuid": self.question_uuid,
            "value": self.value,
        }


@dataclass(frozen=True)
class GeneratedFixturePlan:
    """Selected case indexes and their branch-coverage report."""

    case_indexes: tuple[int, ...]
    expected: frozenset[BranchToken]
    covered: frozenset[BranchToken]
    candidate_count: int
    case_limit: int

    @property
    def missing(self) -> frozenset[BranchToken]:
        """Return expected branches not covered by selected cases."""

        return self.expected - self.covered

    @property
    def complete(self) -> bool:
        """Return whether every expected branch has a selected fixture."""

        return not self.missing

    def as_dict(self) -> dict[str, Any]:
        """Return a stable JSON report suitable for CI artifacts."""

        categories = sorted({token.category for token in self.expected | self.covered})
        return {
            "candidate_count": self.candidate_count,
            "case_limit": self.case_limit,
            "selected_case_count": len(self.case_indexes),
            "selected_case_indexes": list(self.case_indexes),
            "complete": self.complete,
            "expected_branch_count": len(self.expected),
            "covered_branch_count": len(self.expected & self.covered),
            "missing_branch_count": len(self.missing),
            "categories": {
                category: {
                    "expected": _count_category(self.expected, category),
                    "covered": _count_category(self.expected & self.covered, category),
                    "missing": _count_category(self.missing, category),
                }
                for category in categories
            },
            "missing_branches": [token.as_dict() for token in sorted(self.missing)],
        }


def plan_generated_fixture_cases(
    questionnaire: dict[str, Any],
    *,
    seed: int,
    case_limit: int,
    candidate_count: int,
    max_events: int,
    max_items_per_list: int,
    answer_probability: float,
) -> GeneratedFixturePlan:
    """Select deterministic cases that greedily maximize reachable branch coverage."""

    if case_limit < 1:
        raise ValueError("case_limit must be positive")
    if candidate_count < case_limit:
        raise ValueError("candidate_count must be at least case_limit")

    expected = _expected_branch_tokens(
        questionnaire,
        max_items_per_list=max_items_per_list,
    )
    candidates: dict[int, frozenset[BranchToken]] = {}
    for case_index in range(candidate_count):
        generated = generate_questionnaire_events(
            questionnaire,
            seed=seed,
            case_index=case_index,
            max_events=max_events,
            max_items_per_list=max_items_per_list,
            answer_probability=answer_probability,
        )
        candidates[case_index] = _covered_branch_tokens(generated)

    selected: list[int] = []
    covered: set[BranchToken] = set()
    remaining = set(candidates)
    while remaining and len(selected) < case_limit:
        case_index = max(
            remaining,
            key=lambda index: (len((candidates[index] & expected) - covered), -index),
        )
        gain = (candidates[case_index] & expected) - covered
        if not gain:
            break
        selected.append(case_index)
        covered.update(gain)
        remaining.remove(case_index)

    return GeneratedFixturePlan(
        case_indexes=tuple(selected),
        expected=frozenset(expected),
        covered=frozenset(covered),
        candidate_count=candidate_count,
        case_limit=case_limit,
    )


def _expected_branch_tokens(
    questionnaire: dict[str, Any],
    *,
    max_items_per_list: int,
) -> set[BranchToken]:
    knowledge_model = _mapping(questionnaire.get("knowledgeModel"), "knowledgeModel")
    entities = _mapping(knowledge_model.get("entities"), "knowledgeModel.entities")
    chapters = _mapping(entities.get("chapters"), "knowledgeModel.entities.chapters")
    questions = _mapping(entities.get("questions"), "knowledgeModel.entities.questions")
    answers = _mapping(entities.get("answers"), "knowledgeModel.entities.answers")

    reachable: set[str] = set()

    def visit(question_uuid: str) -> None:
        if question_uuid in reachable:
            return
        question = questions.get(question_uuid)
        if not isinstance(question, dict):
            return
        reachable.add(question_uuid)
        for answer_uuid in _strings(question.get("answerUuids")):
            answer = answers.get(answer_uuid)
            if not isinstance(answer, dict):
                continue
            for follow_up_uuid in _strings(answer.get("followUpUuids")):
                visit(follow_up_uuid)
        for item_question_uuid in _strings(question.get("itemTemplateQuestionUuids")):
            visit(item_question_uuid)

    for chapter_uuid in _strings(knowledge_model.get("chapterUuids")):
        chapter = chapters.get(chapter_uuid)
        if not isinstance(chapter, dict):
            continue
        for question_uuid in _strings(chapter.get("questionUuids")):
            visit(question_uuid)

    expected: set[BranchToken] = set()
    for question_uuid in reachable:
        question = questions[question_uuid]
        question_type = question.get("questionType")
        if question_type == "OptionsQuestion":
            expected.update(
                BranchToken("option_answer", question_uuid, answer_uuid)
                for answer_uuid in _strings(question.get("answerUuids"))
            )
        elif question_type == "ListQuestion":
            expected.update(
                BranchToken("list_cardinality", question_uuid, str(item_count))
                for item_count in range(max_items_per_list + 1)
            )
        elif question_type == "MultiChoiceQuestion":
            expected.update(
                BranchToken("multi_choice_shape", question_uuid, str(shape)) for shape in range(4)
            )
        elif question_type == "ItemSelectQuestion":
            expected.update(
                {
                    BranchToken("item_select", question_uuid, "empty"),
                    BranchToken("item_select", question_uuid, "selected"),
                }
            )
    return expected


def _covered_branch_tokens(generated: GeneratedQuestionnaireEvents) -> frozenset[BranchToken]:
    tokens: set[BranchToken] = set()
    for item in _stat_items(generated, "selected_answer_indexes"):
        tokens.add(
            BranchToken(
                "option_answer",
                str(item["question_uuid"]),
                str(item["answer_uuid"]),
            )
        )
    for item in _stat_items(generated, "list_cardinalities"):
        tokens.add(
            BranchToken("list_cardinality", str(item["question_uuid"]), str(item["item_count"]))
        )
    for item in _stat_items(generated, "multi_choice_shapes"):
        tokens.add(
            BranchToken(
                "multi_choice_shape",
                str(item["question_uuid"]),
                str(item["shape"]),
            )
        )
    for item in _stat_items(generated, "item_selects"):
        value = "selected" if item["has_item"] else "empty"
        tokens.add(BranchToken("item_select", str(item["question_uuid"]), value))
    return frozenset(tokens)


def _stat_items(
    generated: GeneratedQuestionnaireEvents,
    key: str,
) -> Iterable[dict[str, Any]]:
    value = generated.stats.get(key, [])
    if not isinstance(value, list):
        return ()
    return (item for item in value if isinstance(item, dict))


def _count_category(tokens: Iterable[BranchToken], category: str) -> int:
    return sum(token.category == category for token in tokens)


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Expected questionnaire mapping at `{label}`")
    return value


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
