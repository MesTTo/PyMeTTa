"""Purpose: verify the scaling gate's verdict, refusals and planted controls.

The centre of this file is the two-sided proof. A gate that can only pass is
not evidence, so the suite ships a family that is genuinely quadratic while
DECLARED linear, and a family whose cost is exactly three times its pinned row
while its class is untouched. The first must fail the exponent gate and only
that gate; the second must fail the constant guard and only that guard. If
either ever stops failing in its declared way, `control_verdict` fails the lane
and these tests fail with it.

Guarantees:
  - the exponent gate catches a planted quadratic in a family declared linear
    [tested: test_the_planted_quadratic_fails_only_the_exponent_gate].
  - the constant guard catches a planted 3x loss that leaves the class alone,
    and the exponent gate lets that same family through, which is what proves
    the two are independent
    [tested: test_the_planted_constant_factor_fails_only_the_growth_gate].
  - a family that left its declared route is refused rather than fitted
    [tested: test_a_family_that_left_its_route_is_refused_not_fitted].
  - the constant guard reads every size, not only the largest, so a curve that
    bends in the middle of its ladder cannot pass
    [tested: test_the_growth_gate_reads_every_size_not_only_the_largest].
  - recording never rewrites a control's pinned row, because the constant
    control's plant IS its distance from that row
    [tested: test_recording_leaves_every_control_row_pinned].
  - a ledger stamped under another configuration refuses the run before any
    family is measured, which is checked on the wiring and not only on the
    helper that decides it
    [tested: test_a_drifted_ledger_refuses_the_run_before_it_measures_anything].
  - the two gates COMPOSE as well as being independent: an O(log n) regression
    in a family declared constant passes the exponent gate at 0.1434 against a
    0.25 bound and is caught by the growth guard at 1.392x
    [tested: test_the_growth_guard_catches_a_log_n_regression_the_exponent_gate_admits].
  - moving the curve arithmetic into benchmarks.curves left memory-scale's
    fits unchanged, checked against the committed pins that the previous
    implementation produced
    [tested: test_the_shared_curve_arithmetic_reproduces_every_pinned_memory_scale_fit].
"""

import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from benchmarks import atomic_json, curves
from benchmarks.memory_scale import _MODEL_ORDER, _transform, fit_curve
from benchmarks.scaling import (
    LEDGER_PATH,
    POLICY_PATH,
    WORKLOADS,
    Measurement,
    configuration_drift,
    control_verdict,
    evaluate,
    ledger_document,
    reduce_repetitions,
)

MEMORY_SCALE_BASELINE = (
    Path(__file__).resolve().parents[2] / "benchmarks" / "memory-scale-baseline.json"
)

#: Two rows whose committed `fit` block does not describe the `representative`
#: beside it, so neither can serve as a frozen oracle. `table-reclamation` was
#: re-pinned by hand from [0, 0, 0, 0] to [168, 168, 168, 168] in 06380061 with
#: the reason recorded in the file, and its fit block still describes the zero
#: curve. `join-projection` is pinned on retired instructions, which are not
#: deterministic on a shared workstation, so its stored fit and its stored
#: representative came from different runs. Neither affects a verdict, because
#: `compare_baseline` reads the fit of the CURRENT measurement and never the
#: pinned one. Named here so a third cannot appear unnoticed.
STALE_MEMORY_SCALE_FITS = frozenset({"join-projection", "table-reclamation"})


def _measured(sizes, values, *, routes=None, problems=()):
    """One family's measurement, built directly rather than run, for the verdict."""
    return Measurement(
        sizes=tuple(sizes),
        samples=tuple((value,) for value in values),
        representative=tuple(values),
        work=tuple(sizes),
        routes=tuple(routes) if routes is not None else (None,) * len(sizes),
        problems=tuple(problems),
    )


def _family(**overrides):
    base = {
        "name": "probe",
        "expected_class": "linear",
        "sizes": [200, 400, 800, 1600],
        "maximum_exponent": 1.25,
        "maximum_growth": 1.1,
    }
    return base | overrides


def _pinned(sizes, values):
    return {"sizes": list(sizes), "representative": list(values)}


# ------------------------------------------------------------------ the fitting


def test_curves_power_fit_recovers_a_planted_exponent():
    """Recover the exponent of a curve built from a known power law."""
    sizes = [10, 100, 1_000, 10_000]
    for exponent in (0.5, 1.0, 1.5, 2.0, 3.0):
        values = [7.0 * size**exponent for size in sizes]
        fit = curves.power_fit(sizes, values)
        assert fit.exponent == pytest.approx(exponent, abs=1e-9)
        assert fit.coefficient == pytest.approx(7.0, rel=1e-9)
        assert fit.r_squared == pytest.approx(1.0, abs=1e-9)
        assert all(slope == pytest.approx(exponent, abs=1e-9) for slope in fit.pair_slopes)


def test_curves_power_fit_reports_no_r_squared_for_a_flat_curve():
    """Report None rather than a number when nothing varies to be explained."""
    flat = curves.power_fit([10, 100, 1_000], [129, 129, 129])

    assert flat.exponent == pytest.approx(0.0)
    assert flat.r_squared is None
    assert flat.pair_slopes == (0.0, 0.0)


def test_curves_power_fit_refuses_a_curve_it_cannot_take_the_log_of():
    """Refuse a fit with fewer than two positive points instead of inventing one."""
    with pytest.raises(ValueError, match="at least two points"):
        curves.power_fit([10, 100], [0, 0])


def test_curves_select_model_names_the_shape_that_generated_the_points():
    """Pick each offered shape back out of points generated from it exactly."""
    sizes = [16, 64, 256, 1_024]
    for model in curves.STANDARD_MODELS:
        values = [3.0 * model.term(size) for size in sizes]
        best, scores = curves.select_model(sizes, values)
        assert best == model.name
        assert scores[model.name] == pytest.approx(0.0, abs=1e-9)


def test_atomic_json_keeps_the_previous_document_when_a_write_fails(tmp_path):
    """A failed write leaves the old pins readable and no temporary behind.

    Both sized lanes rewrite their ledger in place. A half-written pin left by
    an interrupted run is the worst outcome available, because the next run
    compares against it and believes the answer.
    """
    target = tmp_path / "ledger.json"
    atomic_json(target, {"families": {"write-door": [1, 2]}})

    with pytest.raises(TypeError):
        atomic_json(target, {"families": object()})

    assert json.loads(target.read_text(encoding="utf-8")) == {
        "families": {"write-door": [1, 2]}
    }
    assert [path.name for path in tmp_path.iterdir()] == ["ledger.json"]


def test_the_span_and_mean_normalisations_reach_the_same_memory_scale_verdicts():
    """The two nRMS rules differ in strictness, never in verdict, on every pin.

    memory_scale divides the residual RMS by the widest of the observed span,
    the mean and one; google/benchmark divides by the mean alone, which is the
    rule benchmarks.curves uses for the scaling lane. Two rules in one tree are
    only defensible while they agree, so this is the check that says they do.
    """
    document = json.loads(MEMORY_SCALE_BASELINE.read_text(encoding="utf-8"))

    for name, case in document["cases"].items():
        values = [float(value) for value in case["representative"]]
        span, mean = {}, {}
        for model in _MODEL_ORDER:
            fit = curves.least_squares(
                [_transform(model, size) for size in case["sizes"]], values
            )
            span[model] = fit.residual / max(fit.span, abs(fit.mean), 1.0)
            mean[model] = fit.residual / (abs(fit.mean) or 1.0)
        assert _memory_scale_verdict(span, case["expected"]) == _memory_scale_verdict(
            mean, case["expected"]
        ), name
        assert mean[case["expected"]] >= span[case["expected"]], (
            f"{name}: google's rule is meant to be the stricter of the two"
        )


def _memory_scale_verdict(scores, expected):
    """memory_scale's own acceptance test, over whichever scores it is given."""
    best = min(scores, key=lambda name: (scores[name], _MODEL_ORDER[name]))
    return _MODEL_ORDER[best] <= _MODEL_ORDER[expected] or scores[expected] <= 0.10


def test_the_shared_curve_arithmetic_reproduces_every_pinned_memory_scale_fit():
    """Recompute every committed memory-scale fit and get the committed numbers.

    The pins were produced by the arithmetic that lived inside memory_scale
    before it moved into benchmarks.curves, so this file is a frozen
    differential: agreement means the move changed nothing.
    """
    document = json.loads(MEMORY_SCALE_BASELINE.read_text(encoding="utf-8"))
    stale = set()
    for name, case in document["cases"].items():
        fresh = fit_curve(case["sizes"], case["representative"])
        pinned = case["fit"]
        matches = fresh["best_model"] == pinned["best_model"] and all(
            fresh["models"][model][key] == value
            for model, values in pinned["models"].items()
            for key, value in values.items()
        )
        if not (matches and fresh["power_exponent"] == pinned["power_exponent"]):
            stale.add(name)

    assert stale == set(STALE_MEMORY_SCALE_FITS), (
        "a memory-scale pin's fit block stopped describing its own representative; "
        f"expected exactly {sorted(STALE_MEMORY_SCALE_FITS)}, found {sorted(stale)}"
    )


def test_the_shared_power_fit_drops_zero_points_the_way_the_old_path_did():
    """The 23 pins only prove the move on curves this lane happens to have run.

    None of them carries a zero, and this lane has had one: table-reclamation
    was pinned [0, 0, 0, 0] until 06380061 re-pinned it. The move replaced an
    inline "keep the points with a positive value, fit their log-log slope" with
    a call to curves.power_fit guarded by a COUNT of positive points rather than
    a list of them, so the shapes where the two implementations could diverge
    are exactly the ones no pin covers. The property is that a zero is dropped
    and the rest is fitted, which is stated here rather than left to the pins.
    """
    sizes = [10, 100, 1000, 10000]

    assert fit_curve(sizes, [0, 0, 0, 0])["power_exponent"] is None
    assert fit_curve(sizes, [0, 0, 0, 7])["power_exponent"] is None
    for values in ([0, 0, 5, 10], [4, 0, 16, 32], [4, 8, 16, 0], [7, 7, 7, 7]):
        kept = [(size, value) for size, value in zip(sizes, values, strict=True) if value > 0]
        expected = curves.power_fit([size for size, _ in kept], [value for _, value in kept])
        assert fit_curve(sizes, values)["power_exponent"] == expected.exponent, values


# ------------------------------------------------------------- the two controls


def test_the_planted_quadratic_fails_only_the_exponent_gate():
    """A quadratic planted in a family declared linear fails the class gate.

    The numbers are the planted control's own measurement: a full scan of the
    space added to every write, so a cost paid once per step grows with
    everything written so far.
    """
    family = _family(
        name="planted-quadratic",
        sizes=[50, 100, 200, 400],
        control={"fails": "exponent"},
    )
    measurement = _measured([50, 100, 200, 400], [11807, 36080, 122132, 444246])

    result = evaluate(family, measurement, pinned=None)

    assert result.fit["exponent"] == pytest.approx(1.746, abs=0.001)
    assert result.fit["best_model"] == "quadratic"
    assert result.kinds == {"exponent"}
    assert control_verdict(family, result) == []


def test_the_planted_constant_factor_fails_only_the_growth_gate():
    """A 3x constant loss fails the constant guard and passes the class gate.

    The two gates being independent is the whole point of carrying both, and
    this is the case that proves it: the exponent is 0.999 against a 1.25 bound
    while every size costs about three times its pinned row.
    """
    sizes = [200, 400, 800, 1600]
    family = _family(
        name="planted-constant-factor",
        sizes=sizes,
        control={"fails": "growth", "pinned_from": "write-door"},
    )
    measurement = _measured(sizes, [16229, 32430, 64830, 129632])

    result = evaluate(family, measurement, _pinned(sizes, [5429, 10828, 21630, 43230]))

    assert result.fit["exponent"] == pytest.approx(0.999, abs=0.001)
    assert result.fit["exponent"] < family["maximum_exponent"]
    assert result.kinds == {"growth"}
    assert result.fit["growth"] == [
        pytest.approx(3.0, abs=0.02) for _ in sizes
    ]
    assert control_verdict(family, result) == []


def test_a_control_that_stops_failing_fails_the_lane():
    """A negative control that quietly starts passing is itself a failure."""
    family = _family(name="planted-quadratic", control={"fails": "exponent"})
    passing = evaluate(family, _measured(family["sizes"], [100, 200, 400, 800]), None)

    assert passing.kinds == set()
    problems = control_verdict(family, passing)

    assert len(problems) == 1
    assert "passed every gate" in problems[0]
    assert "exponent" in problems[0]


def test_a_control_that_fails_the_wrong_gate_fails_the_lane():
    """A control firing a different gate is not the control anybody declared."""
    sizes = [200, 400, 800, 1600]
    family = _family(name="planted-constant-factor", control={"fails": "growth"})
    quadratic = evaluate(
        family,
        _measured(sizes, [16229, 129632, 1036800, 8294400]),
        _pinned(sizes, [16229, 32430, 64830, 129632]),
    )

    problems = control_verdict(family, quadratic)

    assert len(problems) == 1
    assert "planted to fail exactly the growth gate" in problems[0]


# ------------------------------------------------------------------- refusals


def test_a_family_that_left_its_route_is_refused_not_fitted():
    """A size that fell back to another route is refused rather than measured.

    Without this a `&mork:` family silently becomes an ordinary native space
    when the backend artefact is absent, and its much cheaper native curve is
    compared against a MORK pin as though it were an improvement.
    """
    sizes = [200, 400, 800, 1600]
    family = _family(name="mork-write", route="foreign")
    measurement = _measured(
        sizes,
        [5429, 10828, 21630, 43230],
        routes=["foreign", "foreign", "native", "native"],
    )

    result = evaluate(family, measurement, _pinned(sizes, [30010, 59897, 119899, 240505]))

    assert result.fit == {"refused": True}
    assert result.kinds == {"route"}
    messages = [failure.message for failure in result.failures]
    # Both halves fire: each offending size is named against the declaration,
    # and the ladder is separately called out for not holding one route.
    assert messages[:2] == [
        "mork-write at size 800 took route 'native', not the declared 'foreign'",
        "mork-write at size 1600 took route 'native', not the declared 'foreign'",
    ]
    assert "did not stay on one route" in messages[2]


def test_a_family_whose_work_is_wrong_is_refused_not_fitted():
    """Answers are checked outside the measured region, and a wrong one refuses.

    A workload whose work quietly went away would otherwise report a beautiful
    flat curve and pass every gate in this file.
    """
    family = _family(name="chain-join")
    measurement = _measured(
        family["sizes"],
        [3402, 6559, 12959, 25759],
        problems=["size 1600: expected 1599 chained pairs, got 0"],
    )

    result = evaluate(family, measurement, None)

    assert result.fit == {"refused": True}
    assert result.kinds == {"work"}


def test_a_family_that_changed_route_across_its_ladder_is_refused():
    """The literal requirement: a fallback AT SOME SIZE refuses the whole fit.

    This holds whether or not the family pinned a route, because a ladder
    measured half on one route and half on another describes neither.
    """
    sizes = [200, 400, 800, 1600]
    undeclared = _family(name="parse-forms")
    measurement = _measured(
        sizes, [5222, 10422, 20822, 41624], routes=["c", "c", "prolog", "prolog"]
    )

    result = evaluate(undeclared, measurement, None)

    assert result.fit == {"refused": True}
    assert result.kinds == {"route"}
    assert "did not stay on one route" in result.failures[0].message


def test_repetitions_that_disagree_about_the_route_refuse_rather_than_pick_one():
    """A backend that loaded in some processes and not others is not a coin toss.

    Reading the route from whichever repetition came back first would make the
    verdict depend on scheduling. The distinct names are joined instead, which
    no declaration can match and no consistency check can accept.
    """
    def repetition(second_route):
        return [
            {"size": 10, "inferences": 50, "work": 1, "route": "foreign", "problem": None},
            {"size": 20, "inferences": 99, "work": 2, "route": second_route, "problem": None},
        ]

    measurement = reduce_repetitions(
        [10, 20], [repetition("foreign"), repetition("native"), repetition("foreign")]
    )

    assert measurement.routes == ("foreign", "foreign|native")
    result = evaluate(_family(name="mork-write", route="foreign"), measurement, None)
    assert result.kinds == {"route"}


def test_a_family_the_primary_counter_cannot_see_is_refused_not_fitted():
    """Zero inferences means the work happened where this counter does not look.

    Log-log space has no meaning for it, so the fit would raise. Naming the
    condition is more useful than a traceback, and it is the case a future
    family doing its work entirely in Python would hit.
    """
    invisible = _measured([200, 400, 800, 1600], [0, 0, 0, 0])

    result = evaluate(_family(), invisible, None)

    assert result.fit == {"refused": True}
    assert result.kinds == {"work"}
    assert "the primary counter cannot see" in result.failures[0].message


def test_a_refused_family_is_never_fitted_even_when_its_curve_looks_perfect():
    """Refusal happens before the fit, so a clean curve cannot rescue a bad route."""
    family = _family(name="mork-write", route="foreign")
    exactly_linear = _measured(
        family["sizes"], [200, 400, 800, 1600], routes=["native"] * 4
    )

    result = evaluate(family, exactly_linear, None)

    assert "exponent" not in result.fit
    assert result.kinds == {"route"}


# --------------------------------------------------------------- the two gates


def test_the_growth_gate_reads_every_size_not_only_the_largest():
    """A curve that bends in the middle of its ladder still fails the guard.

    The sibling project's guard compares `counts[-1]` alone, and the coverage
    survey records the same weakness in the memory-scale gate. Here the largest
    size is unchanged and the middle is 40% over.
    """
    sizes = [200, 400, 800, 1600]
    family = _family()
    pinned = _pinned(sizes, [5429, 10828, 21630, 43230])
    bent = _measured(sizes, [5429, 15159, 21630, 43230])

    result = evaluate(family, bent, pinned)

    assert result.kinds == {"growth"}
    assert "at size 400" in result.failures[0].message


def test_the_growth_gate_passes_a_family_that_did_not_move():
    """The pinned row it was recorded from is the row it compares against."""
    sizes = [200, 400, 800, 1600]
    values = [5429, 10828, 21630, 43230]

    result = evaluate(_family(), _measured(sizes, values), _pinned(sizes, values))

    assert result.failures == []
    assert result.fit["growth"] == [1.0, 1.0, 1.0, 1.0]


def test_a_changed_ladder_invalidates_the_pinned_row():
    """A row measured at other sizes cannot be compared against silently."""
    family = _family(sizes=[200, 400, 800])
    result = evaluate(
        family,
        _measured([200, 400, 800], [5429, 10828, 21630]),
        _pinned([200, 400, 800, 1600], [5429, 10828, 21630, 43230]),
    )

    assert result.kinds == {"growth"}
    assert "sizes changed" in result.failures[0].message


def test_the_constant_family_fails_when_its_lookup_starts_scanning():
    """A lost index turns the selective query linear, and the class gate says so."""
    sizes = [400, 800, 1600, 3200]
    family = _family(name="selective-query", expected_class="constant", sizes=sizes)
    family["maximum_exponent"] = 0.25

    flat = evaluate(family, _measured(sizes, [100, 97, 97, 97]), None)
    scanning = evaluate(family, _measured(sizes, [400, 800, 1600, 3200]), None)

    assert flat.failures == []
    assert scanning.kinds == {"exponent"}
    assert scanning.fit["exponent"] == pytest.approx(1.0, abs=1e-9)


def test_the_growth_guard_catches_a_log_n_regression_the_exponent_gate_admits():
    """The two gates COMPOSE, and the constant family needs both of them.

    selective-query is declared constant with an exponent bound of 0.25, which
    is deliberately loose: over an eightfold ladder an O(log n) lookup fits
    exponent 0.1434, so the exponent gate lets it straight through. Tightening
    the bound to exclude it is the wrong repair, because this tree already
    carries two instruction lanes gated tighter than their own measured layout
    noise and the recorded consequence is a re-pin past a real regression. The
    growth guard covers it instead, at 1.392x the pinned row by the top size.

    So the 0.25 bound is defensible only while the growth guard exists, and
    loosening this family's maximum_growth past about 1.39 would leave a matcher
    that swapped a hash index for a balanced tree undetected. That is a
    different property from the two planted controls, which show each gate
    catches something the other does not; this one shows a regression neither
    catches alone.
    """
    sizes = [400, 800, 1600, 3200]
    family = _family(name="selective-query", expected_class="constant", sizes=sizes)
    family["maximum_exponent"] = 0.25
    flat = [100, 97, 97, 97]
    log_n = [round(flat[0] * math.log2(size) / math.log2(sizes[0])) for size in sizes]

    admitted = evaluate(family, _measured(sizes, log_n), None)
    caught = evaluate(family, _measured(sizes, log_n), _pinned(sizes, flat))

    assert log_n == [100, 112, 123, 135]
    assert admitted.fit["exponent"] == pytest.approx(0.1434, abs=5e-4)
    assert admitted.failures == []
    assert caught.kinds == {"growth"}
    assert evaluate(family, _measured(sizes, flat), _pinned(sizes, flat)).failures == []


# ------------------------------------------------------ policy and ledger shape


def _policy():
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _ledger():
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def test_every_policy_family_has_a_workload_a_ladder_and_a_declared_class():
    """The policy and the code cannot drift apart without this failing."""
    policy = _policy()
    declared = {family["name"] for family in policy["families"]}

    assert declared == set(WORKLOADS)
    for family in policy["families"]:
        assert len(family["sizes"]) >= 3, family["name"]
        # sorted AND unique: a repeated size divides by log(1) in the pair
        # slopes and contributes nothing to the regression.
        assert family["sizes"] == sorted(set(family["sizes"])), family["name"]
        assert family["expected_class"] in {model.name for model in curves.STANDARD_MODELS}
        assert family["maximum_exponent"] > 0
        assert family["maximum_growth"] > 1.0


#: The exponent of the next class above each declared one. A family declared
#: linear whose bound is 1.9 is not a linear gate, it is a quadratic gate
#: wearing the word linear, and nothing else in the policy would say so.
CLASS_CEILING = {
    "constant": 1.0,
    "log_n": 1.0,
    "linear": 2.0,
    "n_log_n": 2.0,
    "quadratic": 3.0,
    "cubic": 4.0,
}


def test_every_bound_stays_below_the_class_above_the_one_it_declares():
    """A declared class has to constrain its own bound, or it declares nothing.

    This is the only thing standing between a quietly raised maximum_exponent
    and a green lane, and the same for a growth bound loose enough to let a
    family double.
    """
    for family in _policy()["families"]:
        name, declared = family["name"], family["expected_class"]
        assert family["maximum_exponent"] < CLASS_CEILING[declared], (
            f"{name} is declared {declared} but its bound of "
            f"{family['maximum_exponent']} admits the class above it"
        )
        assert family["maximum_growth"] < 2.0, (
            f"{name} may double and still pass, which is not a constant guard"
        )


def test_every_ladder_spans_enough_to_separate_a_linear_from_a_quadratic():
    """A ladder flat at the tens is how two quadratics survived a sibling kernel.

    Over a ladder spanning a factor of R, a quadratic costs R times more than a
    linear one at the top. Requiring at least eightfold keeps that separation
    far above any bound in the policy.
    """
    for family in _policy()["families"]:
        sizes = family["sizes"]
        assert sizes[-1] / sizes[0] >= 8, f"{family['name']} spans only {sizes}"


def test_every_gated_family_has_a_pinned_row_and_every_control_is_named():
    """A family with no pinned row has no constant guard, so say which have one."""
    policy = _policy()
    ledger = _ledger()
    controls = {
        family["name"]: family["control"]
        for family in policy["families"]
        if family.get("control") is not None
    }

    assert set(controls) == {"planted-quadratic", "planted-constant-factor"}
    assert {control["fails"] for control in controls.values()} == {"exponent", "growth"}
    for family in policy["families"]:
        name = family["name"]
        if name == "planted-quadratic":
            # Its plant is the declared class, which needs no pinned row at all;
            # giving it one would add a second gate it is not there to prove.
            assert name not in ledger["families"]
            continue
        assert name in ledger["families"], name
        assert ledger["families"][name]["sizes"] == family["sizes"]


def test_the_constant_control_is_pinned_against_the_unmultiplied_family():
    """The plant is the distance between the control and the row it copies."""
    ledger = _ledger()
    control = ledger["families"]["planted-constant-factor"]
    source = ledger["families"]["write-door"]

    assert control["representative"] == source["representative"]
    assert "THE PLANT" in control["cause"]["chain"][0]


def test_recording_leaves_every_control_row_pinned():
    """Recording rewrites measured families and never a control's own cost.

    Re-pinning the constant control against itself would replace the plant with
    its own inflated cost and the lane would go green having proved nothing.
    """
    policy = _policy()
    previous = _ledger()
    sizes = [200, 400, 800, 1600]
    inflated = {
        "write-door": _result("write-door", sizes, [9999, 19999, 39999, 79999]),
        "planted-constant-factor": _result(
            "planted-constant-factor", sizes, [999999, 1999999, 3999999, 7999999]
        ),
    }

    document = ledger_document(
        inflated, policy, previous, stamp={}, repetitions=3, cause_commit="TEST"
    )

    assert document["families"]["write-door"]["representative"] == [
        9999,
        19999,
        39999,
        79999,
    ]
    control = document["families"]["planted-constant-factor"]
    assert control["representative"] == [9999, 19999, 39999, 79999]
    assert control["representative"] != [999999, 1999999, 3999999, 7999999]


def _result(name, sizes, values):
    """One evaluated family, for the ledger tests that do not need a measurement."""
    return evaluate(_family(name=name, sizes=sizes), _measured(sizes, values), None)


# ------------------------------------------------------------------ integration


def test_reduce_repetitions_takes_the_minimum_and_keeps_every_sample():
    """Repetitions are processes, and the representative is their minimum."""
    sizes = [10, 20]
    repetitions = [
        [
            {"size": 10, "inferences": 105, "work": 10, "route": None, "problem": None},
            {"size": 20, "inferences": 210, "work": 20, "route": None, "problem": None},
        ],
        [
            {"size": 10, "inferences": 100, "work": 10, "route": None, "problem": None},
            {"size": 20, "inferences": 215, "work": 20, "route": None, "problem": None},
        ],
    ]

    measurement = reduce_repetitions(sizes, repetitions)

    assert measurement.samples == ((105, 100), (210, 215))
    assert measurement.representative == (100, 210)
    assert measurement.noise == {"absolute_max": 5, "relative_max": 5 / 100}


def test_reduce_repetitions_reports_each_distinct_problem_once():
    """The same check failing in every process is one finding, not three."""
    repeated = [
        [{"size": 10, "inferences": 5, "work": 0, "route": None, "problem": "no answers"}]
        for _ in range(3)
    ]

    measurement = reduce_repetitions([10], repeated)

    assert measurement.problems == ("size 10: no answers",)


def test_configuration_drift_names_every_fact_that_moved():
    """A ledger recorded under another configuration is not comparable.

    The C reader's presence alone moves this lane's own parse-forms ladder by
    10.58 to 10.86 times, so comparing across it produces a confounded verdict.
    The tree already refuses a drifted comparison for baseline.json; this is the
    same rule for this ledger.
    """
    live = {"c_reader": True, "mork_backend": "foreign", "python_version": "3.14.4"}

    assert configuration_drift(live, {}) == []
    assert configuration_drift(live, {"configuration": live}) == []
    assert configuration_drift(
        live, {"configuration": live | {"c_reader": False, "mork_backend": "native"}}
    ) == [
        "c_reader: pinned under False, measuring under True",
        "mork_backend: pinned under 'native', measuring under 'foreign'",
    ]


def test_a_drifted_ledger_refuses_the_run_before_it_measures_anything(tmp_path, capsys):
    """The refusal has to be WIRED IN, not merely available as a helper.

    `configuration_drift` returning the right list decides nothing on its own:
    move the call below the measurement loop, or drop the `return 1`, and every
    other test here still passes while the lane silently compares across
    configurations. Measured on 2026-08-27, that comparison is worth 10.58 to
    10.86 times on parse-forms alone, and the growth guard would fire on it and
    name a parser regression where only the box differed.

    The pinned stamp is drifted on `python_version` rather than on a route,
    which makes the test independent of whether this box has engine/reader.so or
    the MORK artefact. It runs `run_suite` directly; the stamp it collects boots
    an engine in a SPAWNED child, so this process stays engine-free.
    """
    import multiprocessing

    from bench import finish_process
    from benchmarks.scaling import run_suite

    pinned = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    drifted = tmp_path / "drifted-ledger.json"
    atomic_json(
        drifted,
        pinned | {"configuration": pinned["configuration"] | {"python_version": "0.0.0"}},
    )

    status = run_suite(
        names=["selective-query"],
        repetitions=1,
        timeout=300.0,
        output=None,
        record=False,
        paired=False,
        cause_commit="TEST",
        policy_path=POLICY_PATH,
        ledger_path=drifted,
        context=multiprocessing.get_context("spawn"),
        finish_process=finish_process,
    )
    printed = capsys.readouterr().out

    assert status == 1
    assert "CONFIGURATION DRIFT python_version: pinned under '0.0.0'" in printed
    assert "re-pin with --record" in printed
    assert "selective-query" not in printed, (
        "the run measured a family before refusing, so the drift check is below "
        "the measurement loop instead of above it"
    )


def test_every_scaling_family_is_reachable_as_a_perf_sized_case():
    """--paired measures a family by name through benchmarks.pure.

    The two name spaces have to stay in step or the paired lane fails at
    runtime on a family that measures perfectly well on inferences.
    """
    from benchmarks.pure import _SIZED_CASES

    assert {f"scaling-{name}" for name in WORKLOADS} <= set(_SIZED_CASES)


def test_the_families_keep_their_engine_invariants_in_their_own_process():
    """Drive `--selfcheck`, which is where the engine-level checks now live.

    It confirms that no family hands back `&self`, that both declared routes
    report this tree's shipping configuration, and that the plants are still in
    the WORKLOADS rather than only in the recorded numbers.

    It runs as a SUBPROCESS on purpose, which keeps this file engine-free.
    Booting an engine here to make the same three checks in-process made the
    combination of this file with test_mork_space, test_adoptions and
    test_async_scheduler segfault 3 times in 20, against 0 in 20 both without
    this file and with an inert file of the same wall time, always inside
    janus's finalizer on another test's worker thread. No single one of the
    three checks reproduced it (0 in 20 each); the cumulative engine state did.
    """
    completed = subprocess.run(
        [sys.executable, "-m", "benchmarks.scaling", "--selfcheck"],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "every family keeps its engine-level invariants" in completed.stdout


def test_this_file_stays_engine_free():
    """No test here may boot an engine, which is what keeps the lane safe.

    The rule is structural rather than stylistic: an engine in the pytest
    process is what made this file crash its neighbours, and the reason the
    checks moved into `--selfcheck` was to remove it. A future test that calls
    a workload directly would put it back, so the file says so about itself.
    """
    source = Path(__file__).read_text(encoding="utf-8")
    body = source[source.index("# ---") :]
    # Spelled in pieces so the needles do not occur literally in this file and
    # make the check fail on its own text.
    instantiate = "WORKLOADS" + "["
    engine = "MeTTa" + "("

    assert instantiate not in body, (
        "a test here instantiates a workload, which boots an engine in the "
        "pytest process; put the check in benchmarks.scaling --selfcheck instead"
    )
    assert engine not in body


def test_a_flat_expression_family_stays_under_the_procedure_arity_ceiling():
    """SWI refuses an arity above 1024 and a wide row becomes exactly that."""
    from benchmarks.scaling import MAX_FLAT_CHILDREN

    segment = next(
        family for family in _policy()["families"] if family["name"] == "segment-split"
    )

    assert max(segment["sizes"]) < MAX_FLAT_CHILDREN
