"""Deterministic branch-sweeping questionnaire fixtures for render regression."""

from __future__ import annotations

import hashlib
import random
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GeneratedQuestionnaireEvents:
    """Generated event payload plus lightweight coverage statistics."""

    events: list[dict[str, Any]]
    stats: dict[str, Any]


@dataclass
class _GeneratorState:
    rng: random.Random
    seed: int
    case_index: int
    max_events: int
    max_items_per_list: int
    answer_probability: float
    namespace: uuid.UUID
    events: list[dict[str, Any]] = field(default_factory=list)
    item_uuids_by_list_question_uuid: dict[str, list[str]] = field(default_factory=dict)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def budget_remaining(self) -> bool:
        return len(self.events) < self.max_events

    def add_event(self, *, path: str, value: dict[str, Any], question_type: str) -> None:
        if not self.budget_remaining:
            return
        event_index = len(self.events)
        self.events.append(
            {
                "type": "SetReplyEvent",
                "uuid": str(uuid.uuid5(self.namespace, f"event:{event_index:04d}:{path}")),
                "path": path,
                "value": value,
            }
        )
        self.stats[question_type] = self.stats.get(question_type, 0) + 1

    def add_branch_stat(self, key: str, value: dict[str, Any]) -> None:
        values = self.stats.setdefault(key, [])
        if isinstance(values, list):
            values.append(value)


def generate_questionnaire_events(
    questionnaire: dict[str, Any],
    *,
    seed: int,
    case_index: int,
    max_events: int = 260,
    max_items_per_list: int = 2,
    answer_probability: float = 1.0,
) -> GeneratedQuestionnaireEvents:
    """Generate deterministic branch-sweeping DSW `SetReplyEvent` values.

    The generator intentionally consumes the DSW API's compiled `knowledgeModel`
    instead of replaying KM package history. That keeps the fixture robust when a
    KM package is upgraded: if DSW can create the project, this generator follows
    the same final chapter/question/answer graph DSW renders. Each question
    derives an independent deterministic permutation from the case index. This
    avoids coupling nested branches to the same remainder as their parents while
    keeping every generated case reproducible.
    """

    knowledge_model = _require_dict(questionnaire, "knowledgeModel")
    entities = _require_dict(knowledge_model, "entities")
    state = _GeneratorState(
        rng=random.Random(f"{seed}:{case_index}"),
        seed=seed,
        case_index=case_index,
        max_events=max_events,
        max_items_per_list=max_items_per_list,
        answer_probability=answer_probability,
        namespace=uuid.uuid5(uuid.NAMESPACE_URL, f"dsw-random-fixture:{seed}:{case_index}"),
        stats={
            "seed": seed,
            "case_index": case_index,
            "max_events": max_events,
            "max_items_per_list": max_items_per_list,
            "selected_answer_indexes": [],
            "list_cardinalities": [],
            "multi_choice_shapes": [],
            "item_selects": [],
        },
    )

    chapters = _require_dict(entities, "chapters")
    questions = _require_dict(entities, "questions")
    for chapter_uuid in _string_list(knowledge_model.get("chapterUuids")):
        chapter = chapters.get(chapter_uuid)
        if not isinstance(chapter, dict):
            continue
        for question_uuid in _string_list(chapter.get("questionUuids")):
            _visit_question(
                state=state,
                entities=entities,
                questions=questions,
                question_uuid=question_uuid,
                path=[chapter_uuid],
                depth=0,
            )
            if not state.budget_remaining:
                break
        if not state.budget_remaining:
            break

    state.stats["event_count"] = len(state.events)
    state.stats["list_question_count"] = len(state.item_uuids_by_list_question_uuid)
    return GeneratedQuestionnaireEvents(events=state.events, stats=state.stats)


def _visit_question(
    *,
    state: _GeneratorState,
    entities: dict[str, Any],
    questions: dict[str, Any],
    question_uuid: str,
    path: list[str],
    depth: int,
) -> None:
    if depth > 48 or not state.budget_remaining:
        return
    question = questions.get(question_uuid)
    if not isinstance(question, dict):
        return
    if state.rng.random() > state.answer_probability:
        return

    question_type = str(question.get("questionType") or "")
    question_path = [*path, question_uuid]
    question_path_string = ".".join(question_path)

    if question_type == "OptionsQuestion":
        _answer_options_question(
            state=state,
            entities=entities,
            questions=questions,
            question=question,
            question_path=question_path,
            question_path_string=question_path_string,
            depth=depth,
        )
    elif question_type == "ListQuestion":
        _answer_list_question(
            state=state,
            entities=entities,
            questions=questions,
            question=question,
            question_path=question_path,
            question_path_string=question_path_string,
            depth=depth,
        )
    elif question_type == "ValueQuestion":
        state.add_event(
            path=question_path_string,
            value={
                "type": "StringReply",
                "value": _generated_text(state, question, question_path_string),
            },
            question_type=question_type,
        )
    elif question_type == "IntegrationQuestion":
        state.add_event(
            path=question_path_string,
            value={
                "type": "IntegrationReply",
                "value": {
                    "type": "PlainType",
                    "value": _generated_text(state, question, question_path_string),
                },
            },
            question_type=question_type,
        )
    elif question_type == "MultiChoiceQuestion":
        selected_choice_uuids = _select_choice_uuids(state, question, question_path_string)
        state.add_branch_stat(
            "multi_choice_shapes",
            {
                "path": question_path_string,
                "question_uuid": question_uuid,
                "choice_count": len(_string_list(question.get("choiceUuids"))),
                "shape": _choice_shape(state, question_path_string),
                "selected_count": len(selected_choice_uuids),
            },
        )
        if selected_choice_uuids:
            state.add_event(
                path=question_path_string,
                value={"type": "MultiChoiceReply", "value": selected_choice_uuids},
                question_type=question_type,
            )
    elif question_type == "ItemSelectQuestion":
        item_uuid = _select_item_uuid(state, question)
        state.add_branch_stat(
            "item_selects",
            {
                "path": question_path_string,
                "question_uuid": question_uuid,
                "has_item": item_uuid is not None,
            },
        )
        if item_uuid is not None:
            state.add_event(
                path=question_path_string,
                value={"type": "ItemSelectReply", "value": item_uuid},
                question_type=question_type,
            )


def _answer_options_question(
    *,
    state: _GeneratorState,
    entities: dict[str, Any],
    questions: dict[str, Any],
    question: dict[str, Any],
    question_path: list[str],
    question_path_string: str,
    depth: int,
) -> None:
    answers = _require_dict(entities, "answers")
    answer_uuids = _string_list(question.get("answerUuids"))
    if not answer_uuids:
        return
    answer_index = _cycled_index(state, question_path_string, len(answer_uuids))
    answer_uuid = answer_uuids[answer_index]
    answer = answers.get(answer_uuid)
    if not isinstance(answer, dict):
        return
    state.add_event(
        path=question_path_string,
        value={"type": "AnswerReply", "value": answer_uuid},
        question_type="OptionsQuestion",
    )
    state.add_branch_stat(
        "selected_answer_indexes",
        {
            "path": question_path_string,
            "question_uuid": str(question.get("uuid") or question_path[-1]),
            "answer_uuid": answer_uuid,
            "answer_index": answer_index,
            "answer_count": len(answer_uuids),
        },
    )
    follow_up_path = [*question_path, answer_uuid]
    for follow_up_question_uuid in _string_list(answer.get("followUpUuids")):
        _visit_question(
            state=state,
            entities=entities,
            questions=questions,
            question_uuid=follow_up_question_uuid,
            path=follow_up_path,
            depth=depth + 1,
        )


def _answer_list_question(
    *,
    state: _GeneratorState,
    entities: dict[str, Any],
    questions: dict[str, Any],
    question: dict[str, Any],
    question_path: list[str],
    question_path_string: str,
    depth: int,
) -> None:
    cardinality_period = state.max_items_per_list + 1
    item_count = _cycled_index(state, question_path_string, cardinality_period)
    state.add_branch_stat(
        "list_cardinalities",
        {
            "path": question_path_string,
            "question_uuid": str(question.get("uuid") or question_path[-1]),
            "item_count": item_count,
            "max_items_per_list": state.max_items_per_list,
        },
    )
    if item_count == 0:
        return

    list_question_uuid = str(question.get("uuid") or question_path[-1])
    item_uuids = [
        str(uuid.uuid5(state.namespace, f"item:{question_path_string}:{item_index}"))
        for item_index in range(item_count)
    ]
    state.item_uuids_by_list_question_uuid.setdefault(list_question_uuid, []).extend(item_uuids)
    state.add_event(
        path=question_path_string,
        value={"type": "ItemListReply", "value": item_uuids},
        question_type="ListQuestion",
    )

    item_template_question_uuids = _string_list(question.get("itemTemplateQuestionUuids"))
    for item_uuid in item_uuids:
        item_path = [*question_path, item_uuid]
        for item_question_uuid in item_template_question_uuids:
            _visit_question(
                state=state,
                entities=entities,
                questions=questions,
                question_uuid=item_question_uuid,
                path=item_path,
                depth=depth + 1,
            )
            if not state.budget_remaining:
                return


def _select_choice_uuids(
    state: _GeneratorState,
    question: dict[str, Any],
    question_path_string: str,
) -> list[str]:
    choice_uuids = _string_list(question.get("choiceUuids"))
    if not choice_uuids:
        return []
    shape = _choice_shape(state, question_path_string)
    if shape == 0:
        return []
    if shape == 1:
        choice_index = _cycled_index(state, f"{question_path_string}:single", len(choice_uuids))
        return [choice_uuids[choice_index]]
    if shape == 2:
        selected = [
            choice_uuid
            for index, choice_uuid in enumerate(choice_uuids)
            if (index + state.case_index) % 3 == 0
        ]
        fallback_index = _cycled_index(
            state,
            f"{question_path_string}:subset-fallback",
            len(choice_uuids),
        )
        return selected or [choice_uuids[fallback_index]]
    return choice_uuids


def _select_item_uuid(
    state: _GeneratorState,
    question: dict[str, Any],
) -> str | None:
    list_question_uuid = question.get("listQuestionUuid")
    if not isinstance(list_question_uuid, str):
        return None
    item_uuids = state.item_uuids_by_list_question_uuid.get(list_question_uuid, [])
    if not item_uuids:
        return None
    question_uuid = str(question.get("uuid"))
    return item_uuids[_cycled_index(state, question_uuid, len(item_uuids))]


def _generated_text(state: _GeneratorState, question: dict[str, Any], path: str) -> str:
    title = str(question.get("title") or "Untitled question")
    digest = hashlib.sha256(path.encode("utf-8")).hexdigest()[:8]
    return f"Generated fixture {state.case_index:03d} ({digest}) for: {title}"


def _require_dict(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Expected questionnaire mapping at `{key}`")
    return value


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _choice_shape(state: _GeneratorState, question_path_string: str) -> int:
    return _cycled_index(state, question_path_string, 4)


def _cycled_index(state: _GeneratorState, key: str, period: int) -> int:
    """Return a reproducible, independently permuted index for one case block."""

    if period < 1:
        raise ValueError("period must be positive")
    block_index, offset = divmod(state.case_index, period)
    indexes = list(range(period))
    random.Random(f"{state.seed}:{key}:{block_index}").shuffle(indexes)
    return indexes[offset]
