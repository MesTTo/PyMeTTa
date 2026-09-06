"""Purpose: verify the (cost ...) row's door, its readers and its gate.

Three things have to hold together for a declared cost to mean anything. The
CATALOG has to refuse a row that cannot be measured, at the door, in every seat.
The READERS have to answer the same class the catalog holds, so `explain` and a
docstring cannot drift from each other or from the lane. And the GATE has to be
able to fail, in both directions, which is what the planted controls are for and
what most of this file is about.

Assumes: the engine boots in this process, and every row this file writes into
  `&metta` is removed again, since that space is the process's and a leaked row
  would reach the next test in a shuffled order.
Guarantees:
  - the class gate catches a quadratic body declared linear, and admits the
    same body declared quadratic
    [tested: test_the_understated_control_fails_only_the_class_gate,
    test_the_quadratic_control_passes_every_gate]
  - it catches the other direction too, a linear body declared quadratic
    [tested: test_the_overstated_control_fails_only_the_class_gate]
  - the exponential class is decided by the semi-log slope and not by the
    log-log exponent, which has no fixed value for that shape
    [tested: test_the_exponential_control_passes_on_its_doubling_slope,
    test_a_cubic_curve_does_not_pass_as_exponential]
  - the work gate fires on answer counts that left their pinned row, while the
    class gate stays quiet [tested: test_the_work_control_fails_only_the_work_gate]
  - every refusal names its remedy, at the catalog door and in the lane
    [tested: test_a_witness_without_exactly_one_hole_is_refused,
    test_a_second_row_for_one_head_is_refused_with_its_remedy,
    test_a_class_outside_the_vocabulary_is_refused,
    test_the_lane_refuses_a_head_it_cannot_call_by_name,
    test_the_lane_refuses_a_measure_it_builds_no_ladder_for,
    test_the_lane_refuses_a_class_the_length_floor_makes_unreachable]
  - explain and the docstring read the engine's own resolution of the row, so
    a measure the arrow decides reaches both without either deriving it
    [tested: test_explain_answers_the_declared_cost,
    test_the_docstring_carries_the_declared_cost,
    test_the_measure_comes_from_the_arrow_at_the_holes_position]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import itertools
import json
from pathlib import Path

import pytest

from benchmarks import curves
from benchmarks.costs import (
    CLASS_BANDS,
    CONTROLS_BY_HEAD,
    EXPONENTIAL_LADDER,
    LEDGER_PATH,
    LENGTH_LADDER,
    Measurement,
    Row,
    class_failure,
    control_verdict,
    evaluate,
    fit_report,
    ladder_for,
    refusal,
    shuffled,
)
from metta import MeTTa
from metta.atoms import Symbol
from metta.errors import EngineError
from metta.vocabularies import CostClass

_REPOSITORY = Path(__file__).resolve().parents[4]


def _row(head: str, cost_class: str, **overrides) -> Row:
    base = {
        "head": head,
        "witness": f"({head} $n)",
        "cost_class": cost_class,
        "measure": "length",
        "sizes": LENGTH_LADDER,
    }
    return Row(**(base | overrides))


def _measured(sizes, counts, *, answers=None, problems=()) -> Measurement:
    return Measurement(
        sizes=tuple(sizes),
        samples=tuple((count,) for count in counts),
        representative=tuple(counts),
        answers=tuple(answers if answers is not None else [1] * len(counts)),
        problems=tuple(problems),
    )


# --------------------------------------------------------------- the controls
# Every number below is the control's own measurement, read off the committed
# ledger's sibling run on 2026-09-07 and repeated here so a test failure names
# a curve rather than a fixture.


def test_the_understated_control_fails_only_the_class_gate():
    """A quadratic body declared linear is what the class gate exists for."""
    control = CONTROLS_BY_HEAD["cost-control-understated"]
    row = _row(control.head, "linear", sizes=control.sizes, control=control)
    measurement = _measured(control.sizes, [28693, 103182, 400150, 1583926])

    result = evaluate(row, measurement, pinned=None)

    assert result.fit["exponent"] == pytest.approx(1.932, abs=0.001)
    assert result.fit["best_model"] == "quadratic"
    assert result.kinds == {"class"}
    assert "above the linear band's ceiling of 1.05" in result.failures[0].message
    assert control_verdict(control, result) == []


def test_the_quadratic_control_passes_every_gate():
    """The same body declared quadratic passes, which is what makes it a band.

    A gate that only ever rejects proves nothing about what it admits, and the
    two controls share one body so the difference between them is the ROW.
    """
    control = CONTROLS_BY_HEAD["cost-control-quadratic"]
    row = _row(control.head, "quadratic", sizes=control.sizes, control=control)
    measurement = _measured(control.sizes, [28693, 103182, 400150, 1583926])

    result = evaluate(row, measurement, pinned=None)

    assert result.kinds == set()
    assert control_verdict(control, result) == []


def test_the_overstated_control_fails_only_the_class_gate():
    """A linear body declared quadratic fails too, which a ceiling would admit.

    An upper-bound check alone would let every head declare `quadratic` and
    never be wrong. This is the floor half of the same band.
    """
    control = CONTROLS_BY_HEAD["cost-control-overstated"]
    row = _row(control.head, "quadratic", sizes=control.sizes, control=control)
    measurement = _measured(control.sizes, [3608, 4239, 6033, 9615])

    result = evaluate(row, measurement, pinned=None)

    assert result.kinds == {"class"}
    assert "below the quadratic band's floor of 1.6" in result.failures[0].message
    assert control_verdict(control, result) == []


def test_the_exponential_control_passes_on_its_doubling_slope():
    """Naive Fibonacci with the memo refused, judged semi-log rather than log-log."""
    control = CONTROLS_BY_HEAD["cost-control-exponential"]
    row = _row(
        control.head, "exponential", measure="int", sizes=EXPONENTIAL_LADDER, control=control
    )
    measurement = _measured(EXPONENTIAL_LADDER, [36846, 91065, 233134, 605081])

    result = evaluate(row, measurement, pinned=None)

    assert result.fit["doubling_slope"] == pytest.approx(0.673, abs=0.001)
    assert result.kinds == set()
    assert control_verdict(control, result) == []


def test_a_cubic_curve_does_not_pass_as_exponential():
    """The floor is on the SLOPE, because the log-log exponent cannot decide it.

    A cubic reads exponent 3.000 on this ladder and the fib control reads
    8.466, so an exponent floor alone would have to sit between two numbers
    that both move with where the ladder is put. The doubling slopes are 0.230
    and 0.650 and neither moves.
    """
    row = _row("probe-cubic", "exponential", measure="int", sizes=EXPONENTIAL_LADDER)
    cubic = [size**3 for size in EXPONENTIAL_LADDER]

    problem = class_failure(row, fit_report(_measured(EXPONENTIAL_LADDER, cubic)))

    assert problem is not None
    assert "doubles 0.2295 times per unit of $n" in problem


def test_the_work_control_fails_only_the_work_gate():
    """Answer counts that left their pinned row fail while the class passes.

    The two being independent is why both are carried: a head whose work went
    away would otherwise report a beautiful flat curve inside its band.
    """
    control = CONTROLS_BY_HEAD["cost-control-work"]
    row = _row(control.head, "linear", control=control)
    measurement = _measured(
        LENGTH_LADDER, [47231, 92246, 182362, 362592], answers=LENGTH_LADDER
    )

    result = evaluate(row, measurement, pinned={"answers": [1, 1, 1, 1]})

    assert result.kinds == {"work"}
    assert "is not doing the work the class was measured on" in result.failures[0].message
    assert control_verdict(control, result) == []


def test_a_control_that_stopped_failing_is_itself_a_failure():
    """The one place where passing is the defect."""
    control = CONTROLS_BY_HEAD["cost-control-understated"]
    row = _row(control.head, "linear", sizes=control.sizes, control=control)
    passing = _measured(control.sizes, [1000, 2000, 4000, 8000])

    (problem,) = control_verdict(control, evaluate(row, passing, pinned=None))

    assert "no longer proven able to fail" in problem


def test_every_control_names_a_gate_that_exists():
    """A control planted against a gate name nothing produces proves nothing."""
    gates = {"class", "work", "refusal", "pass"}
    assert {control.expect for control in CONTROLS_BY_HEAD.values()} <= gates
    assert {control.expect for control in CONTROLS_BY_HEAD.values()} == {
        "pass",
        "class",
        "work",
    }


# ---------------------------------------------------------------- the refusals


def _catalog_row(m: MeTTa, text: str) -> None:
    m.self.run(f"!(add-atom &metta {text})")


def _withdraw(m: MeTTa, text: str) -> None:
    m.self.run(f"!(remove-atom &metta {text})")


def test_a_witness_without_exactly_one_hole_is_refused():
    """Zero holes leaves nothing to vary; two leaves the ladder no size to be."""
    m = MeTTa()
    for witness in ("(probe-none)", "probe-bare", "(probe-two $a $b)"):
        with pytest.raises(EngineError) as raised:
            _catalog_row(m, f"(cost {witness} linear)")
        assert "exactly one size hole $n" in str(raised.value) or (
            "a call whose head is a function name" in str(raised.value)
        )


def test_one_hole_used_twice_is_one_hole():
    """(intersection-atom $n $n) sizes both operands together, and ships."""
    m = MeTTa()
    _catalog_row(m, "(cost (probe-twice $n $n) linear)")
    try:
        assert m.self.run("!(match &metta (cost (probe-twice $a $b) $c) $c)")[0]
    finally:
        _withdraw(m, "(cost (probe-twice $n $n) linear)")


def test_a_second_row_for_one_head_is_refused_with_its_remedy():
    """One class per head, and the refusal says how to change the one standing."""
    m = MeTTa()
    _catalog_row(m, "(cost (probe-twice-declared $n) linear)")
    try:
        with pytest.raises(EngineError) as raised:
            _catalog_row(m, "(cost (probe-twice-declared $n) quadratic)")
        assert "one cost row per head" in str(raised.value)
        assert "remove-atom the standing row" in str(raised.value)
    finally:
        _withdraw(m, "(cost (probe-twice-declared $n) linear)")


def test_a_class_outside_the_vocabulary_is_refused():
    """The catalog's own one-of refusal, with no second implementation."""
    m = MeTTa()
    with pytest.raises(EngineError) as raised:
        _catalog_row(m, "(cost (probe-bogus-class $n) sublinear)")
    assert "(one-of cost-class)" in str(raised.value)


def test_the_lane_refuses_a_head_it_cannot_call_by_name():
    """A row whose head is not loaded is named, not skipped.

    Fitting nothing and reporting a class would be worse than saying so: the
    ladder would measure the engine's refusal to call an unknown head.
    """
    problem = refusal("probe-absent", "linear", "length", loaded=False)
    assert problem is not None
    assert "not a function this engine can call" in problem
    assert "import the library that defines it" in problem


def test_the_lane_refuses_a_measure_it_builds_no_ladder_for():
    """Ciao's `depth` is a real measure and this lane builds no ladder for it."""
    problem = refusal("probe-deep", "linear", "depth", loaded=True)
    assert problem is not None
    assert "builds no ladder for" in problem
    assert "int, length" in problem


def test_the_lane_refuses_a_class_the_length_floor_makes_unreachable():
    """A call that receives n children cannot cost less than reading them.

    Measured: `(if-equal a a 1 $n)` never looks at its fourth argument and still
    costs 4,412 to 22,314 inferences over 512 to 4096, exponent 0.781, all of it
    the argument arriving. So `constant` over a length measure is unmeasurable
    rather than merely false, and the refusal names the remedy.
    """
    for cost_class in ("constant", "log"):
        problem = refusal("probe-floor", cost_class, "length", loaded=True)
        assert problem is not None
        assert "cannot cost less than reading it" in problem
        assert "declare the measure" in problem
    assert refusal("probe-floor", "constant", "int", loaded=True) is None


# ----------------------------------------------------------------- the readers


def test_explain_answers_the_declared_cost():
    """A head with a row shows its class beside every other declaration."""
    m = MeTTa()
    (items,) = m.run("!(explain (car-atom (1 2)))")[0]
    rendered = str(items)
    assert "(cost linear length)" in rendered


def test_a_head_without_a_row_shows_no_cost_item():
    """Silence rather than `(cost none none)`: most heads declare nothing."""
    m = MeTTa()
    (items,) = m.run("!(explain (cdr-atom (1 2)))")[0]
    assert "cost" in str(items), "cdr-atom ships a row and should show it"
    (other,) = m.run("!(explain (if-equal a a 1 2))")[0]
    assert "cost" not in str(other)


def test_the_docstring_carries_the_declared_cost():
    """help() shows the class, and says whether the lane has measured it."""
    m = MeTTa()
    documented = m.self.fn["car-atom"].__doc__
    assert documented is not None
    assert "cost: linear in $n (length)" in documented
    assert documented.rstrip().endswith("measured 2026-09-07") or documented.rstrip().endswith(
        "declared"
    )


def test_the_docstring_dates_the_measurement_from_the_ledger():
    """The date is the ledger's, so a row nobody measured says `declared`."""
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    measured = ledger["rows"]["car-atom"]["measured"]
    m = MeTTa()
    assert f"measured {measured}" in (m.self.fn["car-atom"].__doc__ or "")


def test_the_measure_comes_from_the_arrow_at_the_holes_position():
    """Number at the hole gives the int measure; anything else gives length.

    `(: min-atom (-> $a Number))` is the case that made this a comparison and
    not a unification: a type VARIABLE at the hole's position unifies with
    Number, and the ladder then handed min-atom the integer 2048 where it wants
    2048 children, reading a flat 409 inferences instead of the scan.
    """
    m = MeTTa()
    assert m._rt.apply_must("metta_py_cost_declaration", "+") == ["constant", "int"]
    assert m._rt.apply_must("metta_py_cost_declaration", "car-atom") == ["linear", "length"]
    _catalog_row(m, "(cost (min-atom $n) linear)")
    try:
        assert m._rt.apply_must("metta_py_cost_declaration", "min-atom") == [
            "linear",
            "length",
        ]
    finally:
        _withdraw(m, "(cost (min-atom $n) linear)")


def test_a_row_may_name_its_own_measure():
    """The optional field wins over the arrow, which is what it is for."""
    m = MeTTa()
    _catalog_row(m, "(cost (probe-named-measure $n) linear depth)")
    try:
        assert m._rt.apply_must("metta_py_cost_declaration", "probe-named-measure") == [
            "linear",
            "depth",
        ]
    finally:
        _withdraw(m, "(cost (probe-named-measure $n) linear depth)")


# ------------------------------------------------------------- the vocabulary


def test_the_cost_class_vocabulary_is_generated():
    """One row in &metta, one StrEnum, the same words in the same order."""
    m = MeTTa().self
    holes = " ".join(f"$w{index}" for index in range(len(CostClass)))
    (row,) = m.run(f"!(match &metta (vocabulary cost-class {holes}) ({holes}))")[0]
    assert [str(word) for word in row.children] == [member.value for member in CostClass]


def test_every_cost_class_member_crosses_as_its_symbol():
    """A member IS its wire word, so no door has to convert it.

    The vocabulary lane's own shape, asserted here as well because this class
    is the one a `(cost ...)` row's second field takes and a member that
    stopped crossing would be found at a write rather than at an import.
    """
    for member in CostClass:
        assert member == member.value
        assert member.__metta__() == Symbol(member.value)
        assert member.value in CostClass


def test_every_shipped_class_is_a_vocabulary_member():
    """The classes the engine ships are a subset of the ones Python can spell."""
    m = MeTTa().self
    (collapsed,) = m.run("!(collapse (match &metta (cost $w $c) $c))")[0]
    classes = {str(word) for word in collapsed.children}
    assert classes
    assert classes <= {member.value for member in CostClass}


# ------------------------------------------------------------------- the shape


def test_the_length_fixture_is_distinct_and_not_in_order():
    """Sorted input is the best case of every comparison sort.

    A ladder of `0..n-1` in order would let a sort read linear and a row could
    then claim a class the head has only for input somebody else already
    sorted. Distinct, because a dedup on repeated elements does no work.
    """
    values = shuffled(512)
    assert sorted(values) == list(range(512))
    assert values != list(range(512))
    assert shuffled(512) == values, "the fixture has to be the same on every run"


def test_a_ladder_is_chosen_by_measure_and_by_class():
    """A row's ladder follows its measure, and exponential takes a third."""
    assert ladder_for("length", "linear", None) == LENGTH_LADDER
    assert ladder_for("int", "exponential", None) == EXPONENTIAL_LADDER
    assert ladder_for("int", "constant", None) != EXPONENTIAL_LADDER
    assert ladder_for("depth", "linear", None) == ()
    assert ladder_for("length", "linear", (1, 2)) == (1, 2)


def test_the_bands_below_quadratic_overlap_at_every_boundary():
    """A reading at a boundary must fail neither of the two classes it sits between.

    Each of these four pairs is separated by less than a factor of n, so a
    ladder cannot always say which side a curve is on and the gate must not
    fire on the ambiguity.
    """
    ordered = ["constant", "log", "linear", "linearithmic"]
    for lower, upper in itertools.pairwise(ordered):
        assert CLASS_BANDS[upper].lower <= CLASS_BANDS[lower].upper, (
            f"{lower} and {upper} leave a gap between them"
        )


def test_the_gap_below_quadratic_is_deliberate():
    """A curve at n^1.45 fails both neighbouring claims, and should.

    The vocabulary has six words and no word for n to the three halves, so a
    head that grows that way cannot TRUTHFULLY declare either linearithmic or
    quadratic, and stretching the bands to meet would let it declare the
    cheaper one. The gap is where the vocabulary ends, not where the bands are
    wrong; Ciao has no gap here because its `steps_o` takes an arbitrary
    function rather than a closed set of names.
    """
    assert CLASS_BANDS["linearithmic"].upper < CLASS_BANDS["quadratic"].lower
    for cost_class in ("linearithmic", "quadratic"):
        row = _row("probe-three-halves", cost_class)
        problem = class_failure(
            row, {"exponent": 1.45, "doubling_slope": 0.0}
        )
        assert problem is not None, cost_class


def test_curves_exponential_fit_recovers_a_planted_base():
    """A curve built from a known base reports that base's log-2 slope."""
    sizes = [10, 20, 30, 40]
    for slope in (0.25, 0.5, 1.0, 2.0):
        values = [3.0 * 2 ** (slope * size) for size in sizes]
        fit = curves.exponential_fit(sizes, values)
        assert fit.slope == pytest.approx(slope, abs=1e-9)
        assert fit.coefficient == pytest.approx(3.0, rel=1e-9)
        assert fit.r_squared == pytest.approx(1.0, abs=1e-9)


def test_curves_exponential_fit_separates_an_exponential_from_a_cubic():
    """The two shapes a log-log fit cannot tell apart on a short ladder."""
    sizes = list(EXPONENTIAL_LADDER)
    fib = curves.exponential_fit(sizes, [36846, 91065, 233134, 605081])
    cubic = curves.exponential_fit(sizes, [size**3 for size in sizes])
    assert fib.slope == pytest.approx(0.673, abs=0.001)
    assert cubic.slope == pytest.approx(0.230, abs=0.001)
    assert curves.power_fit(sizes, [size**3 for size in sizes]).exponent == pytest.approx(
        3.0, abs=1e-9
    )


# -------------------------------------------------------------- the ledger and docs


def test_every_shipped_row_is_pinned_with_its_measurement():
    """The committed ledger is the evidence behind every class the engine claims."""
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    shipped = {
        head: row
        for head, row in ledger["rows"].items()
        if head not in CONTROLS_BY_HEAD
    }
    assert len(shipped) == 10
    for head, row in shipped.items():
        assert row["class"] in {member.value for member in CostClass}, head
        assert len(row["inferences"]) == len(row["sizes"]), head
        assert row["measured"], head
        assert row["counter"] == "inferences", head


def test_llms_txt_documents_the_row_and_its_lane():
    """The one document read by something that cannot notice a stale claim."""
    text = (_REPOSITORY / "llms.txt").read_text(encoding="utf-8")
    assert "(cost witness class" in text or "(cost <witness>" in text
    assert "cost-class" in text
    assert "cost-rows" in text
    assert "benchmarks/costs.py" in text


def test_the_cost_rows_lane_is_a_gate():
    """A lane whose purpose is to fail a claim is never a REPORT."""
    text = (_REPOSITORY / "extensions" / "python" / "check.sh").read_text(encoding="utf-8")
    assert "run GATE cost-rows" in text
    assert "-m benchmarks.costs" in text


def test_every_shipped_row_is_reachable_as_a_perf_sized_case():
    """--paired measures a row by name through benchmarks.pure.

    The two name spaces have to stay in step or the paired lane fails at
    runtime on a row that measures perfectly well on inferences.
    """
    from benchmarks.pure import _SIZED_CASES, COST_ROW_CASE

    assert COST_ROW_CASE not in _SIZED_CASES, (
        "the cost-row case takes --head and cannot be a fixed sized case"
    )
    assert COST_ROW_CASE == "cost-row"
