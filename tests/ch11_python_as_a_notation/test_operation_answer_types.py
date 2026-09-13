"""Purpose: declare host answer types without treating None as an answer.

Guarantees:
  - only return alternatives consumed by the host bridge are removed;
    parameters, contained values and full annotation claims remain [tested:
    test_host_answer_types_remove_only_empty_return_alternatives,
    test_nullable_host_operations_keep_parameters_and_annotation_claims;
    commit=WORKTREE]
"""

from typing import Annotated

import pytest

from metta import Expression, G, MeTTa, S, V


@pytest.mark.parametrize(("annotation", "expected"), [
    (int | None, [S.Number]),
    (Annotated[int | None, S.Gt(0)], [S.Annotated(S.Number, S.Gt(0))]),
    (Annotated[None, S.Gt(0)], []),
    (S["|"](S.NoneType, S.Number), [S.Number]),
    (S.Annotated(S["|"](S.NoneType, S.Number), S.Gt(0)), [S.Annotated(S.Number, S.Gt(0))]),
    (S["|"](S.NoneType, S.Annotated(S["|"](S.NoneType, S.Number), S.Gt(0))), [S.Annotated(S.Number, S.Gt(0))]),
    (S["|"](S.NoneType, S.NoneType), []),
    (S["|"](), []),
    (Expression([]), [Expression([])]),
    (S.Annotated(), [S.Annotated()]),
    (Expression([S.NoneType, S.Number]), [Expression([S.NoneType, S.Number])]),
    (S["->"](S.Number, S.NoneType), [S["->"](S.Number, S.NoneType)]),
])
def test_host_answer_types_remove_only_empty_return_alternatives(annotation, expected):
    """Project the outer answer type; None inside a returned value still counts."""
    with MeTTa() as context:
        space = context.self

        def absent(_key: int):
            return None

        absent.__annotations__["return"] = annotation
        space.op(absent, effect="pureStructural")
        answers = [row.result for row in space.match(S[":"](S.absent, S["->"](S.Number, V.result)))]
        assert answers == expected
        assert space.eval(S.absent(0)) == []


def test_nullable_host_operations_keep_parameters_and_annotation_claims():
    """A nullable argument remains a value while a nullable return may be empty."""
    with MeTTa() as context:
        space = context.self

        @space.op(effect="pureStructural")
        def nullable_answer(key: int | None) -> Annotated[int | None, S.Gt(0)]:
            return key

        arrows = [row.arrow for row in space.match(S[":"](S["nullable-answer"], V.arrow))]
        result = S.Annotated(S.Number, S.Gt(0))
        assert set(arrows) == {S["->"](S.Number, result), S["->"](S.NoneType, result)}
        annotations = [row.type for row in space.match(S.annotation(S["nullable-answer"], S["return"](V.type)))]
        assert annotations == [S.Annotated(S.Union(S.Number, S.NoneType), S.Gt(0))]
        assert space.eval(S["nullable-answer"](3)) == [3]
        assert space.eval(S["nullable-answer"](G(None))) == []


def test_authored_operation_arrows_keep_their_explicit_return_type():
    """Generated answer projection leaves supplied native declarations intact."""
    with MeTTa() as context:
        space = context.self
        supplied = S[":"](S["authored-return"], S["->"](S.Number, S.NoneType))

        @space.op(effect="pureStructural", declarations=(supplied,))
        def authored_return(_key: int) -> int | None:
            return None

        arrows = [row.arrow for row in space.match(S[":"](S["authored-return"], V.arrow))]
        assert set(arrows) == {S["->"](S.Number, S.Number), supplied.args[1]}


@pytest.mark.parametrize(("annotation", "answers", "full"), [
    (None, [], S.NoneType),
    (int, [S.Number], S.Number),
])
def test_nullary_host_operations_preserve_result_annotation_for_empty_answers(annotation, answers, full):
    """A zero-parameter signature keeps its annotation even with no answers."""
    with MeTTa() as context:
        space = context.self

        def absent_nullary():
            return None

        absent_nullary.__annotations__["return"] = annotation
        space.op(absent_nullary, effect="pureStructural")
        name = S["absent-nullary"]
        assert [row.type for row in space.match(S[":"](name, S["->"](V.type)))] == answers
        assert [row.type for row in space.match(S.annotation(name, S["return"](V.type)))] == [full]
        assert space.eval(name()) == []
