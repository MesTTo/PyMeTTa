"""Purpose: pin every adopted advisory lint and its lawful control.

Guarantees:
  - all fifteen assigned design rows map to nine warning kinds plus one named
    suppression intent, and every warning has a positive and allowed-control
    test [tested: extensions/python/tests/ch14_seeing_your_program/test_lint_family.py; commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - lint evidence and suppression intent remain queryable in ``&metta`` until
    the owning space is cleared [tested:
    test_lint_evidence_and_intent_follow_space_clear; commit=acb40f1912f131ae088083d1af29b4b283019bea]
"""

from __future__ import annotations

import asyncio

import pytest

from metta import Expression, S, V, aio, equation
from metta._lint_events import _AUTHORITIES, _INTENT_AUTHORITY


@pytest.fixture()
def m(metta):
    """Give each diagnostic scenario an isolated logical space."""
    with metta._new_space() as space:
        yield space


def _kind(m, kind: str):
    return [finding for finding in m.lint() if finding.kind == kind]


def _answers(m, name: str):
    m.run(f"(= ({name}) (superpose (1 2)))")
    return m.answers(S[name]())


def _intent_pattern(m, kind: str):
    return S["lint-intent"](
        S[str(m.name)],
        S[kind],
        V.path,
        V.directive_line,
        V.column,
        V.target_start,
        V.target_end,
        V.authority,
    )


def _evidence_pattern(m, kind: str):
    return S["lint-evidence"](
        S[str(m.name)],
        S[kind],
        V.subject,
        V.path,
        V.line,
        V.column,
        V.authority,
    )


def test_all_fifteen_assigned_rows_have_a_code_authority():
    """Every audit ID stays grep-visible beside the implementation it rules."""
    citations = " ".join((*_AUTHORITIES.values(), _INTENT_AUTHORITY))
    rows = {
        "P14-14-02",
        "P14-39-05",
        "P14-40-07",
        "STYLE-150",
        "GG-008",
        "P14-40-09",
        "GG-004",
        "GG-014",
        "GG-013",
        "GG4-006",
        "GG5-007",
        "L9Z2-08",
        "L9Z2-09",
        "L9Z3-03",
        "L9Z1-06",
    }
    assert len(rows) == 15
    assert all(row in citations for row in rows)


def test_capital_functions_and_lowercase_data_are_linted_not_refused(m):
    """Both halves of the first-letter convention remain lawful MeTTa."""
    m.run("(lowercase-data item)(= (CapitalFunction $x) $x)")

    findings = _kind(m, "first-letter-role-convention")

    assert {finding.payload["role"] for finding in findings} == {"data", "function"}
    assert m.eval(S.CapitalFunction(S.answer)) == [S.answer]
    assert S["lowercase-data"](S.item) in m


def test_capital_data_and_lowercase_functions_are_allowed(m):
    """The conventional pair produces no first-letter finding."""
    m.run("(CapitalData item)(= (lowercase-function $x) $x)")

    assert not _kind(m, "first-letter-role-convention")


def test_an_interpreter_equation_shadow_is_linted_not_refused(m):
    """A writable equation over ``eval`` stays installed and visible."""
    m.run("(= (eval $x) shadowed)")

    findings = _kind(m, "interpreter-equation-shadow")

    assert [finding.subject for finding in findings] == ["eval"]
    assert S["="](S.eval(V.x), S.shadowed) in m


def test_an_ordinary_equation_is_allowed_by_the_shadow_rule(m):
    """User-defined heads do not resemble translator-owned heads by spelling."""
    m.run("(= (ordinary-equation $x) $x)")

    assert not _kind(m, "interpreter-equation-shadow")


def test_an_operation_call_inside_a_compiled_loop_is_linted(m):
    """A per-item host crossing reports the operation's published effect."""
    @m.op(name="lint_loop_bump", effect="pureStructural")
    def lint_loop_bump(value: int) -> int:
        return value + 1

    @m.define(name="lint-loop-sum")
    def loop_sum(values):
        total = 0
        for value in values:
            total += lint_loop_bump(value)
        return total

    findings = _kind(m, "operation-crossing-in-loop")

    assert len(findings) == 1
    assert findings[0].subject == "lint_loop_bump"
    assert findings[0].payload["effect"] == "pureStructural"
    assert m.eval(S["lint-loop-sum"]((1, 2))) == [5]


def test_known_map_filter_and_fold_111x_shapes_are_linted(m):
    """Every engine iterator spelling reports its per-element Python op."""
    @m.op(name="lint_unary_hot", effect="readOnlyLookup")
    def unary(value: int) -> int:
        return value + 1

    @m.op(name="lint_binary_hot", effect="readOnlyLookup")
    def binary(left: int, right: int) -> int:
        return left + right

    m.run(
        "(= (lint-map-call) (map-atom (1 2) lint_unary_hot))"
        "(= (lint-filter-call) (filter-atom (1 2) lint_unary_hot))"
        "(= (lint-fold-call) (foldl-atom (1 2) 0 lint_binary_hot))"
    )

    findings = _kind(m, "operation-crossing-in-loop")

    assert sorted(finding.subject for finding in findings) == [
        "lint_binary_hot",
        "lint_unary_hot",
        "lint_unary_hot",
    ]
    assert {finding.payload["effect"] for finding in findings} == {"readOnlyLookup"}
    assert m.eval(S["lint-map-call"]()) == [Expression(2, 3)]


def test_an_operation_call_outside_a_compiled_loop_is_allowed(m):
    """One operation crossing is not the per-item cost pattern."""
    @m.op(name="lint_once_bump", effect="pureStructural")
    def lint_once_bump(value: int) -> int:
        return value + 1

    @m.define(name="lint-once-call")
    def once(value):
        return lint_once_bump(value)

    assert m.eval(S["lint-once-call"](3)) == [4]
    assert not _kind(m, "operation-crossing-in-loop")


def test_a_module_level_defined_call_is_linted_not_refused(m, tmp_path):
    """Import-time driving runs normally and leaves source evidence."""
    source = (
        "@space.define(name='lint-import-call')\n"
        "def imported(value):\n"
        "    return value + 1\n"
        "observed = imported(4)\n"
    )
    path = tmp_path / "lint_import_call.py"
    path.write_text(source, encoding="utf-8")
    namespace = {"space": m, "__name__": "lint_import_call"}

    exec(compile(source, path, "exec"), namespace)

    assert list(namespace["observed"]) == [5]
    assert len(_kind(m, "module-level-defined-call")) == 1


def test_a_module_level_definition_without_a_call_is_allowed(m, tmp_path):
    """Import-time declarations are the intended module-level shape."""
    source = (
        "@space.define(name='lint-import-definition')\n"
        "def imported(value):\n"
        "    return value + 1\n"
    )
    path = tmp_path / "lint_import_definition.py"
    path.write_text(source, encoding="utf-8")
    namespace = {"space": m, "__name__": "lint_import_definition"}

    exec(compile(source, path, "exec"), namespace)

    assert list(namespace["imported"](4)) == [5]
    assert not _kind(m, "module-level-defined-call")


def test_an_effectful_ground_operation_at_rule_construction_is_linted(m):
    """The effect fires once and its lattice rank reaches the finding."""
    fired = []

    @m.op(name="lint-construction-write", effect="writesState")
    def write(value: int) -> int:
        fired.append(value)
        return value

    @m.rules
    def construction():
        yield equation(S["lint-construction"]()).to(write(7))

    findings = _kind(m, "effectful-operation-at-construction")

    assert fired == [7]
    assert construction[0] in m
    assert len(findings) == 1
    assert findings[0].payload["effect"] == "writesState"


def test_a_pure_ground_operation_at_rule_construction_is_allowed(m):
    """The lattice's pureStructural floor is not an effect warning."""
    @m.op(name="lint-construction-pure", effect="pureStructural")
    def pure(value: int) -> int:
        return value

    @m.rules
    def construction():
        yield equation(S["lint-pure-construction"]()).to(pure(7))

    assert construction[0] in m
    assert not _kind(m, "effectful-operation-at-construction")


def test_a_staged_operation_in_a_law_is_linted_not_refused(m):
    """The op term lands and crosses only when the law is applied."""
    fired = []

    @m.op(name="lint-law-write", effect="writesState")
    def write(value: int) -> int:
        fired.append(value)
        return value + 1

    @m.rules
    def law(value):
        yield equation(S["lint-law"](value)).to(write(value))

    findings = _kind(m, "operation-staged-in-law")

    assert fired == []
    assert len(findings) == 1
    assert findings[0].payload["effect"] == "writesState"
    assert m.eval(S["lint-law"](4)) == [5]
    assert fired == [4]


def test_a_staged_defined_function_in_a_law_is_allowed(m):
    """The zero-crossing compiled-function cell is not an op warning."""
    @m.define(name="lint-law-defined")
    def double(value):
        return value + value

    @m.rules
    def law(value):
        yield equation(S["lint-defined-law"](value)).to(double(value))

    assert m.eval(S["lint-defined-law"](4)) == [8]
    assert not _kind(m, "operation-staged-in-law")


def test_zip_over_unordered_answers_is_lawful_and_linted(m):
    """Sequence compatibility remains, while correspondence is diagnosed."""
    left = _answers(m, "lint-zip-left")
    right = _answers(m, "lint-zip-right")

    pairs = list(zip(left, right, strict=True))

    assert pairs == [(1, 1), (2, 2)]
    assert len(_kind(m, "unordered-answers-zip")) == 1


def test_independent_iteration_over_answers_is_allowed_by_the_zip_rule(m):
    """Materializing one unordered multiset asserts no row correspondence."""
    answers = _answers(m, "lint-zip-control")

    assert list(answers) == [1, 2]
    assert not _kind(m, "unordered-answers-zip")


def test_reversed_over_unordered_answers_is_lawful_and_linted(m):
    """Reversal remains a Sequence operation but has no semantic ordering."""
    answers = _answers(m, "lint-reversed")

    values = list(reversed(answers))

    assert values == [2, 1]
    assert len(_kind(m, "unordered-answers-reversed")) == 1


def test_forward_iteration_over_answers_is_allowed_by_the_reversed_rule(m):
    """Ordinary consumption does not claim reverse order."""
    answers = _answers(m, "lint-reversed-control")

    assert list(answers) == [1, 2]
    assert not _kind(m, "unordered-answers-reversed")


def test_a_sync_engine_call_inside_async_def_is_linted_not_refused(m):
    """The sync call returns its answer even though it can block the loop."""
    m.run("(= (lint-async-target) 7)")

    async def drive():
        return m.eval(S["lint-async-target"]())

    assert asyncio.run(drive()) == [7]
    assert len(_kind(m, "sync-engine-call-in-async")) == 1


def test_async_metta_engine_driving_is_allowed(m):
    """The asynchronous facade keeps synchronous engine work off the loop."""
    async def drive():
        async with aio.AsyncMeTTa(metta=m) as async_metta:
            await async_metta.run("(= (lint-async-control) 8)")
            return await async_metta.eval(S["lint-async-control"]())

    assert asyncio.run(drive()) == [8]
    assert not _kind(m, "sync-engine-call-in-async")


def test_a_named_metta_ok_intent_suppresses_only_its_bound_rule(m):
    """An exact directive hides the finding but preserves intent and evidence."""
    @m.op(name="lint_suppressed_crossing", effect="pureStructural")
    def lint_suppressed_crossing(value: int) -> int:
        return value + 1

    @m.define(name="lint-suppressed-loop")
    def loop(values):
        total = 0
        for value in values:
            # metta: ok(operation-crossing-in-loop)
            total += lint_suppressed_crossing(value)
        return total

    assert m.eval(S["lint-suppressed-loop"]((1, 2))) == [5]
    assert not _kind(m, "operation-crossing-in-loop")
    catalog = m._at("&metta")
    intents = catalog.match(_intent_pattern(m, "operation-crossing-in-loop"))
    evidence = catalog.match(_evidence_pattern(m, "operation-crossing-in-loop"))
    assert len(intents) == 1
    assert intents[0].authority.value.startswith("L9Z1-06;")
    assert len(evidence) == 1


def test_a_named_metta_ok_intent_does_not_suppress_another_rule(m):
    """The directive names one rule rather than disabling the lint pass."""
    m.run("(lowercase-control data)")

    # metta: ok(operation-crossing-in-loop)
    findings = m.lint()

    assert "first-letter-role-convention" in {finding.kind for finding in findings}


def test_lint_evidence_and_intent_follow_space_clear(m):
    """Reflection does not outlive the logical space that owns it."""
    @m.op(name="lint_clear_crossing", effect="pureStructural")
    def lint_clear_crossing(value: int) -> int:
        return value + 1

    @m.define(name="lint-clear-loop")
    def loop(values):
        total = 0
        for value in values:
            # metta: ok(operation-crossing-in-loop)
            total += lint_clear_crossing(value)
        return total

    catalog = m._at("&metta")
    intent = _intent_pattern(m, "operation-crossing-in-loop")
    evidence = _evidence_pattern(m, "operation-crossing-in-loop")
    assert catalog.match(intent)
    assert catalog.match(evidence)

    m.clear()

    assert not catalog.match(intent)
    assert not catalog.match(evidence)


def test_a_retired_operation_is_not_named_by_the_wrapper_it_left_behind(m):
    """One reader answers both doors, and only while the registry owns it."""
    from metta._ops import OPERATION_REGISTRATION, live_registration

    @m.op(name="lint_retired_crossing", effect="pureStructural")
    def lint_retired_crossing(value: int) -> int:
        return value + 1

    @m.define(name="lint-retired-loop")
    def loop(values):
        total = 0
        for value in values:
            total += lint_retired_crossing(value)
        return total

    assert [f.subject for f in _kind(m, "operation-crossing-in-loop")] == [
        "lint_retired_crossing"
    ]
    assert live_registration(lint_retired_crossing) is not None

    m.unregister_op("lint_retired_crossing")

    # The wrapper still carries the attribute: liveness is the registry's
    # answer, not the attribute's presence.
    assert hasattr(lint_retired_crossing, OPERATION_REGISTRATION)
    assert live_registration(lint_retired_crossing) is None


def test_a_bundle_lands_with_its_evidence_through_every_door(m):
    """One bundle law: each door publishes, and a batch defers whole.

    The doors had diverged: `+=` published a bundle's construction evidence
    while `add(*bundle)` silently skipped it, because the splat erases the
    bundle before the door runs, and the eager spelling published under an
    active batch for equations a discard would never land [measured
    2026-09-01, +185 inferences of reflection writes on one spelling only].
    The bundle rides whole through add(), which owns the law; evidence keys
    by its owning bundle, so each leg here carries its own op and bundle.
    """
    from metta import equation, rules

    def built(tag: str):
        @m.op(name=f"lint-parity-{tag}", effect="writesState")
        def write(value: int) -> int:
            return value

        @rules
        def parity_bundle():
            yield equation(S[f"lint-parity-{tag}"]()).to(write(9))

        return parity_bundle

    def subjects():
        found = _kind(m, "effectful-operation-at-construction")
        return {finding.subject for finding in found}

    # The whole-bundle add publishes exactly as += does.
    m.add(built("adds"))
    assert "lint-parity-adds" in subjects()

    # A discarded batch lands neither the equations nor the evidence.
    with pytest.raises(RuntimeError, match="planted"):
        with m.batch():
            m.add(built("discarded"))
            msg = "planted"
            raise RuntimeError(msg)
    assert "lint-parity-discarded" not in subjects()
    assert not m.match(S["lint-parity-discarded"]())

    # A committed batch lands both, deferred together to the flush.
    with m.batch():
        m.add(built("committed"))
        assert "lint-parity-committed" not in subjects()
    assert "lint-parity-committed" in subjects()
