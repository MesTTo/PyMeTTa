"""Purpose: pin every adopted advisory lint and its lawful control.

Guarantees:
  - all fifteen assigned design rows map to nine warning kinds plus one named
    suppression intent, and every warning has a positive and allowed-control
    test [tested: extensions/python/tests/ch14_seeing_your_program/test_lint_family.py; commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - lint evidence and suppression intent remain queryable in ``&metta`` until
    the owning space is cleared [tested:
    test_lint_evidence_and_intent_follow_space_clear; commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - finding payloads retain their audit IDs and point at an immutable public
    rule description [tested: test_lint_authorities_are_durable_public_references;
    commit=2a32acb6d254ea12085526913c7b9a1a555b8ee0]
  - finite constructor coverage retains tagged enum members and correlations
    between literal fields [tested: test_finite_constructor_coverage_preserves_field_correlations;
    commit=WORKTREE]
"""

from __future__ import annotations

import asyncio

import pytest

import metta.aio as _aio_surface
from metta import Expression, Grounded, S, V, equation
from metta._spaces.intents import _AUTHORITIES, _INTENT_AUTHORITY, _LINT_CATALOGUE


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


def test_lint_authorities_are_durable_public_references():
    """Runtime evidence names an immutable document rather than local scratch."""
    assert _LINT_CATALOGUE == (
        "https://github.com/MesTTo/MeTTa-Kernel/blob/"
        "7de3d32d25a7166b12f7c68c179e9cbb931ac044/"
        "website/guide/run-query.md#lint-a-space"
    )
    authorities = (*_AUTHORITIES.values(), _INTENT_AUTHORITY)
    for authority in authorities:
        assert "github.com/MesTTo/MeTTa-Kernel/blob/" in authority
        assert "/website/guide/run-query.md#" in authority


def test_an_event_kind_carries_its_remedy_and_a_rule_kind_is_not_an_event():
    """Each engine-observed event kind holds authority and remedy in one record.

    A finding rendered from an event reads both off that record, so neither
    can be missing; a lint rule composes its own text and cannot be raised
    as an event at all.
    """
    from metta._spaces.intents import _EVENTS, _RULES, detail_for, make_event

    for kind, ruling in _EVENTS.items():
        assert ruling.authority and ruling.detail
        assert detail_for(kind) == ruling.detail
    assert not set(_EVENTS) & set(_RULES)
    with pytest.raises(KeyError):
        make_event("det-equations-overlap", "subject", path="p.py", line=1, column=0)


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


def test_a_det_claim_broken_by_two_equal_heads_is_reported(m):
    """The other way a det claim fails: too many answers rather than too few.

    Neither existing overlap rule reaches this and both are right not to. The
    equations are not duplicates, because their bodies differ, and neither is
    a strict instance of the other, because the heads are variants. What makes
    it wrong is the declaration.
    """
    m.run("(: two (-[det]-> Number Number))")
    m.run("(= (two $x) $x)")
    m.run("(= (two $x) (+ $x 1))")

    findings = _kind(m, "det-equations-overlap")

    assert [finding.subject for finding in findings] == ["two"]
    assert "-[nondet]->" in findings[0].detail, "the message names the other remedy"
    assert findings[0].severity == "hint", "a heuristic: it proves the overlap, not the answers"
    assert len(m.eval(S.two(1))) == 2, "two answers from a function declared det"


def test_the_overlap_hint_reports_what_it_can_prove_and_no_more(m):
    """Overlapping heads mean both equations are TRIED, not that both answer.

    A guarded second body keeps the det claim for some calls and breaks it for
    others, so the finding cannot promise two answers. Deciding which needs the
    body analysis the typechecker audit refused as interprocedural; this costs
    an alpha-key comparison, and says so.
    """
    m.run("(: guarded (-[det]-> Number Number))")
    m.run("(= (guarded $x) $x)")
    m.run("(= (guarded $x) (if (> $x 100) 999 (empty)))")

    assert len(m.eval(S.guarded(1))) == 1, "the claim HOLDS for this call"
    assert len(m.eval(S.guarded(200))) == 2, "and breaks for this one"

    findings = _kind(m, "det-equations-overlap")
    assert [finding.subject for finding in findings] == ["guarded"]
    assert "at most one body succeeds" in findings[0].detail, (
        "the message must not claim every call answers twice"
    )


def test_distinct_heads_and_a_relation_are_both_silent(m):
    """A det function may have many equations; a plain arrow may answer twice."""
    m.run("(: pick (-[det]-> Number Number))")
    m.run("(= (pick 1) 10)(= (pick 2) 20)")
    m.run("(: rel (-> Number Number))")
    m.run("(= (rel $x) $x)(= (rel $x) (+ $x 1))")

    assert not _kind(m, "det-equations-overlap")


def test_a_det_claim_broken_by_an_uncovered_constructor_is_reported(m):
    """`-[det]->` promises exactly one answer; an uncovered member gives zero.

    The finding is the contradiction between the declaration and the
    equations, not partiality, which is ordinary MeTTa. The members were
    declared one by one, so the missing set is a difference rather than an
    analysis: the decidable corner of exhaustiveness.
    """
    m.run("(: Red Colour)(: Green Colour)(: Blue Colour)")
    m.run("(: paint (-[det]-> Colour Number))")
    m.run("(= (paint Red) 1)(= (paint Green) 2)")

    findings = _kind(m, "uncovered-constructor")

    assert [finding.subject for finding in findings] == ["paint"]
    assert findings[0].payload["missing"] == ["Blue"]
    assert findings[0].severity == "warning"
    assert "-[semidet]->" in findings[0].detail, "the message names the other remedy"
    assert m.eval(S.paint(S.Blue)) == [], "reported rather than refused"


def test_a_python_enum_reaches_the_coverage_check_without_extra_machinery(m):
    """Tagged enum constructors expose their finite domain through Literal."""
    from enum import StrEnum

    @m.define
    class Shade(StrEnum):
        pale = "pale"
        deep = "deep"
        vivid = "vivid"

    m.run("(: intensity (-[det]-> Shade Number))")
    m.run("(= (intensity (Shade pale)) 1)(= (intensity (Shade deep)) 2)")

    findings = _kind(m, "uncovered-constructor")

    assert [finding.subject for finding in findings] == ["intensity"]
    assert findings[0].payload["missing"] == ["(Shade vivid)"]
    assert m.eval(S.intensity(S.Shade(S.pale))) == [Grounded(1)]
    assert m.eval(S.intensity(S.Shade(S.unknown)))[0].head == S.Error
    m.run("(= (intensity (Shade vivid)) 3)")
    assert not _kind(m, "uncovered-constructor")


def test_finite_constructor_coverage_preserves_field_correlations(m):
    """Repeated pattern variables cover equal fields, not their cross product."""
    m.run("(: Pair (-> (Annotated Symbol (Literal a b)) (Annotated Symbol (Literal a b)) Choice))")
    m.run("(: rank (-[det]-> Choice Number))(= (rank (Pair $same $same)) 1)")
    assert _kind(m, "uncovered-constructor")[0].payload["missing"] == [
        "(Pair a b)", "(Pair b a)",
    ]
    m.run("(= (rank (Pair $left $right)) 2)")
    assert not _kind(m, "uncovered-constructor")


def test_a_constructor_pattern_covers_its_constructor(m):
    """The algebraic case, in the shape upstream's own fixture is written in.

    `(: Circle (-> Number Shape))` makes Circle a member of the type it
    RETURNS, and `(area (Circle $r))` covers it by pattern rather than by
    name. Counting only bare symbols saw enums and missed every algebraic
    type, which is the more important half.
    """
    m.run("(: Shape Type)")
    m.run("(: Circle (-> Number Shape))(: Square (-> Number Shape))(: Point Shape)")
    m.run("(: area (-[det]-> Shape Number))")
    m.run("(= (area (Circle $r)) (* 3 (* $r $r)))")
    m.run("(= (area (Square $s)) (* $s $s))")

    findings = _kind(m, "uncovered-constructor")

    assert [finding.subject for finding in findings] == ["area"]
    assert findings[0].payload["missing"] == ["Point"], (
        "the nullary constructor is the one no pattern reaches"
    )


def test_a_plain_arrow_promises_nothing_so_partiality_is_not_a_finding(m):
    """A function is a relation; answering nothing is legal without a claim."""
    m.run("(: Hot Heat)(: Cold Heat)")
    m.run("(: describe (-> Heat Number))")
    m.run("(= (describe Hot) 1)")

    assert not _kind(m, "uncovered-constructor")


def test_the_two_ways_a_det_claim_is_kept(m):
    """Cover every member, or bind the position with a variable."""
    m.run("(: Up Way)(: Down Way)")
    m.run("(: go (-[det]-> Way Number))(: fall (-[det]-> Way Number))")
    m.run("(= (go Up) 1)(= (go Down) 2)")
    m.run("(= (fall Up) 1)(= (fall $any) 0)")

    assert not _kind(m, "uncovered-constructor")


def test_semidet_is_the_remedy_rather_than_a_second_finding(m):
    """Saying the function is partial is what the message asks for."""
    m.run("(: Yes Answer2)(: No Answer2)")
    m.run("(: maybe-rank (-[semidet]-> Answer2 Number))")
    m.run("(= (maybe-rank Yes) 1)")

    assert not _kind(m, "uncovered-constructor")


def test_a_builtin_equation_shadow_is_linted_not_refused(m):
    """A writable equation over a shipped builtin stays installed and answers.

    The engine permits this deliberately and scopes it: the equation compiles
    into this space's own module, so the engine's version and every other
    space's are untouched. Nothing said so, which is what the finding is for.
    The dangerous cases refuse instead, by name, so this fires only where the
    engine chose silence.
    """
    assert m.eval(S["max-atom"](Expression([1, 5, 3]))) == [Grounded(5)]

    m.run("(= (max-atom $x) shadowed)")
    findings = _kind(m, "builtin-equation-shadow")

    assert [finding.subject for finding in findings] == ["max-atom"]
    assert findings[0].severity == "warning", "lawful, so not an error"
    assert m.eval(S["max-atom"](Expression([1, 5, 3]))) == [S.shadowed], (
        "the equation is installed; the finding reports it rather than blocking it"
    )


def test_a_users_own_name_is_not_a_builtin_shadow(m):
    """`fun/1` enumerates user functions too, so the question must be `builtin_fun/1`."""
    m.run("(= (a-name-the-engine-does-not-ship $x) $x)")

    assert not _kind(m, "builtin-equation-shadow")


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
        async with _aio_surface.AsyncMeTTa(metta=m) as async_metta:
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
    from metta._binding.dispatch import OPERATION_REGISTRATION, live_registration

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
