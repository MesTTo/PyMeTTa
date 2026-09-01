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
  - an unannotated numeric operator follows Python's live protocol and costs
    more than the equivalent native MeTTa equation, while an annotated operand
    proves the native head and restores inference parity
    [measured: 28.00 unannotated and 3.00 annotated against 3.00 MeTTa;
    command=python -m benchmarks.extension_cost; fixture=3000 calls, min-of-3,
    C reader and C extension enabled; commit=WORKTREE]
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

    # An unannotated `x + 1` cannot prove that x is a native number. P7 keeps
    # Python's live operator protocol in that case, including overloads and
    # reflected methods, so this row pays a Python crossing rather than the
    # pure engine + head. The committed counter baseline pins the exact 28.00;
    # this relation keeps a stale pre-P7 parity claim from returning.
    assert measured["@m.define, no annotations"].inferences > baseline

    # The int annotations prove that the body may lower to the pure engine +
    # head. This benchmark calls it with a literal, so the argument contract is
    # discharged at the call site; the result's number/1 check compiles to a VM
    # instruction SWI does not count as an inference. The wall-clock and the
    # typed-call instruction ceiling still cover that residual work.
    assert measured["@m.define, annotated"].inferences == pytest.approx(
        baseline, abs=0.1
    )

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


def test_a_pinned_row_nothing_measures_fails_the_gate(tmp_path, drives):
    """A row no measurement reaches is a dead receipt that can never fail.

    The C foreign row sat exactly that way from the ac083177 partition until
    2026-08-26: its path constant landed one directory short, has_c read
    False with the artifact built, and the pinned row survived as coverage
    that no longer covered anything. Compare mode now refuses such rows and
    update mode prunes them aloud.
    """
    import json

    from benchmarks.extension_cost import compare

    baseline = tmp_path / "stale.json"
    compare(drives, update=True, path=baseline)

    recorded = json.loads(baseline.read_text())
    donor = next(iter(recorded["benchmarks"].values()))
    recorded["benchmarks"]["extcost-a-renamed-tier"] = dict(donor)
    baseline.write_text(json.dumps(recorded))

    with pytest.raises(AssertionError, match="nothing measured"):
        compare(drives, update=False, path=baseline)

    compare(drives, update=True, path=baseline)
    pruned = json.loads(baseline.read_text())
    assert "extcost-a-renamed-tier" not in pruned["benchmarks"]
    compare(drives, update=False, path=baseline)
