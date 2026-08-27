"""Purpose: pin Phase 14's Python authoring surface against engine answers.

Guarantees:
  - ``yield from`` delegates only when nondeterminism is known and refuses
    ambiguous engine calls before they can splice application children [tested:
    test_yield_from_a_call_delegates_only_when_nondeterminism_is_known;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321].
  - a decorator-derived output declaration is stored before the equation it
    governs [tested:
    test_a_declared_output_type_takes_effect_through_the_decorator_door;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321].
  - Defined calls evaluate by default, stage inside rules, and resolve the
    same exact name through text and data [tested:
    test_calling_a_defined_object_evaluates_and_an_unmatched_call_answers_itself,
    test_one_name_resolution_rule_across_every_door,
    test_a_rules_generator_scopes_its_variables_to_its_parameters;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from metta import (
    Atom,
    Expression,
    S,
    V,
    equation,
    rules,
)
from metta.errors import CompileError, EngineError


def test_calling_a_defined_object_evaluates_and_an_unmatched_call_answers_itself(
    metta,
):
    """A Defined call uses the answer protocol, including not-reducible."""
    space = metta._new_space()

    @space.define(name="p14-surface-call")
    def call(value):
        return value + 1

    assert call(1) == [2]
    space.clear()
    assert call(2) == [S["p14-surface-call"](2)]
    assert isinstance(S["p14-surface-call"](1), Expression)


def test_one_name_resolution_rule_across_every_door(metta):
    """Text and atom calls select the same exact name in a named space."""
    space = metta._new_space()

    @space.define(name="p14-surface-exact")
    def python_spelling(value):
        return Local(value)  # noqa: F821  -- capitalised free names are constructors in compiled bodies

    expected = [S.Local(7)]
    assert python_spelling(7) == expected
    assert space.eval("(p14-surface-exact 7)") == expected
    assert space.eval(S["p14-surface-exact"](7)) == expected
    assert space.eval("(python_spelling 7)") == [S["python_spelling"](7)]
    assert space.eval(S["python_spelling"](7)) == [S["python_spelling"](7)]


def test_a_rules_generator_scopes_its_variables_to_its_parameters(metta):
    """Rule parameters stage Defined calls and emit the container-door atom."""
    space = metta._new_space()

    @space.define(name="p14-surface-double")
    def double(value):
        return value + value

    @rules
    def arithmetic(value):
        yield equation(S["p14-surface-via-rule"](value)).to(double(value))

    longhand = S["="](
        S["p14-surface-via-rule"](V.value),
        S["p14-surface-double"](V.value),
    )
    assert arithmetic == (longhand,)
    space += arithmetic
    assert arithmetic[0] in space
    assert space.eval(S["p14-surface-via-rule"](6)) == [12]

    @space.rules
    def bound(value):
        yield equation(S["p14-surface-bound-rule"](value)).to(double(value))

    assert bound[0] in space
    assert space.eval(S["p14-surface-bound-rule"](7)) == [14]


def test_yield_from_a_call_delegates_only_when_nondeterminism_is_known(metta):
    """Known generators delegate; ambiguous calls name both safe spellings."""
    local = metta._new_space()

    @local.define(name="p14-surface-stream")
    def local_stream(start, stop):
        if start < stop:
            yield start
            yield from local_stream(start + 1, stop)

    assert local.eval(S.collapse(S["p14-surface-stream"](1, 5))) == [
        Expression(1, 2, 3, 4)
    ]

    @metta.define
    def p14_surface_inherited_stream(value):
        yield value
        yield value + 1

    inherited = metta._new_space()

    with pytest.raises(CompileError, match="yield p14_surface_inherited_stream"):

        @inherited.define
        def p14_surface_consumer(value):
            yield from p14_surface_inherited_stream(value)
            yield 99

    @local.define
    def p14_surface_values():
        return (1, 2)

    with pytest.raises(CompileError, match="bind the returned data"):

        @local.define
        def p14_surface_iter_values():
            yield from p14_surface_values()


def test_a_declared_output_type_takes_effect_through_the_decorator_door(metta):
    """An Atom result declaration keeps the equation body's result unevaluated."""
    space = metta._new_space()

    @space.define(name="p14_surface_output_typed")
    def output_typed(value: int) -> Atom:
        return value + 42

    argument = S["+"](1, 1)
    assert space.eval(S["p14_surface_output_typed"](argument)) == [S["+"](2, 42)]


def test_failed_equation_publication_rolls_back_its_early_declaration(
    metta, monkeypatch
):
    """An early declaration cannot outlive the equation it was meant to type."""
    space = metta._new_space()
    runtime_type = type(metta.runtime)
    real_do_must = runtime_type.do_must
    target_adds = 0

    def fail_equation(runtime, goal, *inputs):
        nonlocal target_adds
        if (
            goal == "metta_py_add"
            and inputs[0] == space.name
        ):
            target_adds += 1
            if target_adds == 2:
                msg = "forced equation publication failure"
                raise EngineError(msg)
        return real_do_must(runtime, goal, *inputs)

    monkeypatch.setattr(runtime_type, "do_must", fail_equation)

    def p14_surface_failed(value: int) -> int:
        return value + 1

    with pytest.raises(EngineError, match="forced equation publication failure"):
        space.define(p14_surface_failed)

    declaration = S[":"](
        S["p14_surface_failed"],
        S["->"](S.Number, S.Number),
    )
    assert declaration not in space


def test_the_staging_split_folds_ground_calls_and_stages_op_terms(metta):
    """The rules-body staging split, all four cells, asserted on the laws.

    A call carrying a RULE VARIABLE stages its call term; a GROUND defined
    call runs at construction and embeds its single result (constant folding
    by construction, the design's own cell); an op call with a rule variable
    stages the OP-CALL TERM without running the host body (no effect fires
    on a variable); a ground op call runs now, firing its effect exactly
    once. A ground defined call answering several results keeps its call
    term, because folding one answer of many would drop multiplicity.
    """
    space = metta._new_space()
    fired = []

    @space.define(name="p14-split-double")
    def double(value):
        return value + value

    @space.define(name="p14-split-fib")
    def fib(n):
        if n <= 1:
            return n
        return fib(n - 1) + fib(n - 2)

    @space.define(name="p14-split-both")
    def both(value):
        yield value
        yield value + 1

    @space.op(name="p14-split-stamp", effect="writesState")
    def stamp(x: int) -> int:
        fired.append(x)
        return x * 10

    @rules
    def cells(value):
        yield equation(S["p14-split-stage"](value)).to(double(value))
        yield equation(S["p14-split-fold"]()).to(fib(10))
        yield equation(S["p14-split-multi"]()).to(both(3))
        yield equation(S["p14-split-op-stage"](value)).to(stamp(value))
        yield equation(S["p14-split-op-ground"]()).to(stamp(4))

    # Construction already happened at decoration: exactly one host effect,
    # the ground op call's, and never one carrying a variable.
    assert fired == [4]

    space += cells
    stage, fold, multi, op_stage, op_ground = cells
    assert stage == S["="](
        S["p14-split-stage"](V.value), S["p14-split-double"](V.value)
    )
    assert fold == S["="](S["p14-split-fold"](), 55)
    # Multiplicity preserved: the two-answer ground call stays a call term.
    assert multi == S["="](S["p14-split-multi"](), S["p14-split-both"](3))
    assert op_stage == S["="](
        S["p14-split-op-stage"](V.value), S["p14-split-stamp"](V.value)
    )
    assert op_ground == S["="](S["p14-split-op-ground"](), 40)

    # Every law answers, and the staged op crosses at application time.
    assert space.eval(S["p14-split-stage"](6)) == [12]
    assert space.eval(S["p14-split-fold"]()) == [55]
    assert sorted(space.eval(S["p14-split-multi"]())) == [3, 4]
    assert space.eval(S["p14-split-op-stage"](6)) == [60]
    assert fired == [4, 6]
