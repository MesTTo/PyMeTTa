"""Purpose: the extension-cost harness behind EXTENDING.md's table.

The table is the page's central claim and the thing a library author picks a
tier on. It was produced by a throwaway outside the repo that hardcoded an
absolute path and was run by nobody, so nothing noticed when one of its five
rows stopped reproducing. These tests assert the properties the table's shape
depends on, so a harness that starts measuring the loop instead of the call
fails here rather than quietly publishing.
Guarantees:
  - the driver's own cost is subtracted, so a tier cheaper than a MeTTa
    function reads as cheaper [tested test_extension_cost_rows_are_marginal]
  - an unannotated @m.define costs exactly what the equivalent MeTTa equation
    costs [tested test_extension_cost_rows_are_marginal]
  - an annotated one costs the same IN INFERENCES, which is a fact about the
    counter and not about the work: a specialised type check compiles to a VM
    instruction SWI does not count. What it still costs is gated as the
    typed-call instructions:u ceiling in benchmarks/baseline.json, and this
    file asserts the parity so that the table cannot quietly imply annotating
    is free [tested test_extension_cost_rows_are_marginal]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from benchmarks.extension_cost import encoding_rows, rows


# One measurement for the module, deliberately. rows() installs its drivers
# into the one engine the process has, and installing the same driver name
# twice gives it two clauses: the recursion then leaves a choice point per
# level and a deep drive runs out of stack instead of measuring anything,
# which _install_drivers says in as many words. Three rounds because a
# committed counter baseline compares at least three samples.
@pytest.fixture(scope="module")
def drives():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return rows(calls=500, rounds=3)


@pytest.fixture(scope="module")
def measured(drives):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return {row.tier: row for row in drives}


def test_extension_cost_rows_are_marginal(measured):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    baseline = measured["ordinary MeTTa function"].inferences

    # A tier cheaper than a MeTTa function can only READ as cheaper once the
    # loop's own cost is out of the way. With the driver included, every row
    # sits above it and the three native tiers become indistinguishable.
    assert measured["Prolog grounded predicate"].inferences < baseline
    assert measured["translator rule (a macro)"].inferences < baseline

    # @m.define lowers Python into MeTTa equations, so with no annotations it
    # compiles to what the hand-written equation compiles to. This is a
    # compiler result rather than an approximation, so it is asserted tightly.
    # The tolerance is per-call, and the residual is a fixed per-DRIVE cost
    # divided by the call count: 0.06 at 500 calls, 0.01 at the 3000 the
    # published table uses.
    assert measured["@m.define, no annotations"].inferences == pytest.approx(
        baseline, abs=0.1
    )

    # Annotations generate a type declaration, and a declared call emits a
    # type check per argument and one on the result. Until 2026-08-17 that cost
    # this tier over three times the baseline and the assertion here said so.
    #
    # It no longer does, and the reason is worth more than the number: the
    # checks are specialised to a Prolog builtin when the declared type is
    # Number, String or Bool, and SWI compiles number/1 to a VM instruction it
    # does not COUNT. So the cost did not go to zero, it went somewhere this
    # column cannot see. Asserting a gap that is no longer visible here would
    # fail on a real improvement; asserting nothing would let this table tell a
    # library author that annotating is free, which is false.
    #
    # So the inference column records parity, honestly, and the cost that
    # remains is gated where it is visible: the typed-call case in
    # benchmarks/baseline.json holds an instructions:u ceiling that reverting
    # the specialisation overshoots by 44%.
    assert measured["@m.define, annotated"].inferences == pytest.approx(baseline, abs=0.1)

    assert measured["Python operation, encoded"].inferences > baseline


def test_the_raw_python_path_does_not_walk_its_argument():
    """The encoded path's single published number is its BEST case.

    The encoding walks the term and the raw path does not, so the gap between
    them is a function of argument size, and a library passes structures
    rather than integers.
    """
    sized = {label: (encoded, raw) for label, encoded, raw in encoding_rows(calls=100, rounds=2)}
    raw_costs = {raw for _, raw in sized.values()}
    assert len(raw_costs) == 1, sized

    smallest = sized["integer"][0]
    largest = sized["flat, 64 items"][0]
    assert largest > smallest * 5, sized


def test_a_moved_tier_fails_the_gate(tmp_path, drives):
    """The baseline has to actually refuse a moved row.

    Until 2026-08-16 these numbers were reported and not gated, so a
    with_metta_module/2 fast path took the annotated @m.define tier from 20.00
    to 22.00 and the run said nothing; it was found by reading the table. A
    baseline that cannot fail would leave that exactly as it was while reading
    like coverage, which is the worse of the two.
    """
    import json

    from benchmarks.extension_cost import compare

    baseline = tmp_path / "moved.json"
    compare(drives, update=True, path=baseline)
    compare(drives, update=False, path=baseline)  # agrees with itself

    recorded = json.loads(baseline.read_text())
    for case in recorded["benchmarks"].values():
        case["inferences"] -= 1000
    baseline.write_text(json.dumps(recorded))

    with pytest.raises(AssertionError, match="inference regression"):
        compare(drives, update=False, path=baseline)
