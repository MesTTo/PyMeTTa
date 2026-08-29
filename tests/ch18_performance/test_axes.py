"""Purpose: hold EXTENDING.md's crossing-axis claims to their harness.

The extension-cost table is gated, so its numbers cannot drift. The axis
figures beside it are a recorded run, and a recorded number with no oracle is
how this repository's tables went stale before: the ordinary row read 3.00
against a gated 4.00 for days because nothing held the page to the harness.

What is asserted is the COMPLEXITY CLASS rather than the constant, through the
same `power_fit` the scaling gate uses, so a few percent of drift passes and
turning one class into the other does not. The published claim is that a
transparent crossing is linear in the value's size and an opaque one is
constant, which in log-log space is an exponent approaching 1 against an
exponent of 0.

Inferences are the deterministic half of the harness and need no performance
counters, so this runs on a machine that cannot read `perf`.
Guarantees:
  - an opaque crossing stays constant in the value's size, exponent 0
    [tested test_an_opaque_crossing_is_constant_in_the_values_size]
  - a transparent crossing stays linear, its pair slopes climbing to 1
    [tested test_a_transparent_crossing_stays_linear_in_the_values_size]
  - letting the engine call out stays cheaper than driving it from the host,
    and keeps agreeing with the gated extension-cost table
    [tested test_the_engine_calling_out_stays_cheaper_than_the_host_driving_in]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from benchmarks.axes import CROSSINGS, IMAGE_CROSSINGS, SIZES, inferences_of
from benchmarks.curves import power_fit


@pytest.fixture(scope="module")
def crossing():
    """Per-crossing inferences for each case, each from its own process.

    One process per case is not a preference: two `MeTTa()` handles share one
    engine, so a second case in one process installs a driver head twice and
    measures a choice point. `run_case` refuses that outright.
    """
    cache: dict[str, int] = {}

    def measure(case: str, null: str, crossings: int) -> float:
        for name in (case, null):
            if name not in cache:
                cache[name] = inferences_of(name)
        return (cache[case] - cache[null]) / crossings

    return measure


def _ladder(crossing, kind: str) -> list[float]:
    """One per-crossing cost per swept value size."""
    return [
        crossing(f"image-{kind}-{size}", f"image-null-{size}", IMAGE_CROSSINGS)
        for size in SIZES
    ]


def test_an_opaque_crossing_is_constant_in_the_values_size(crossing):
    """Exponent 0, and no R-squared, which is what a flat curve reports."""
    costs = _ladder(crossing, "opaque")
    fit = power_fit(SIZES, costs)
    assert fit.exponent == pytest.approx(0.0, abs=0.05), (
        f"an opaque crossing fitted an exponent of {fit.exponent:.3f} over "
        f"sizes {list(SIZES)} costing {costs}. It is published as constant in "
        f"the value's size, which is the whole reason to reach for it"
    )


def test_a_transparent_crossing_stays_linear_in_the_values_size(crossing):
    """Pair slopes climbing to 1, which is linear.

    The pair slopes rather than the single fitted exponent, because a fixed
    per-crossing cost sits under the linear term and drags that one exponent
    below 1 until the sizes are large enough to wash it out.
    """
    costs = _ladder(crossing, "transparent")
    fit = power_fit(SIZES, costs)
    assert fit.pair_slopes[-1] == pytest.approx(1.0, abs=0.15), (
        f"a transparent crossing's largest pair slope was "
        f"{fit.pair_slopes[-1]:.3f} over sizes {list(SIZES)} costing {costs}. "
        f"EXTENDING.md publishes it as linear in the value's size"
    )
    # The class alone is a weaker oracle than the page's own claim: a
    # transparent crossing costing a hundred inferences an element would fit
    # the same exponent and contradict the published rate. So the rate is
    # asserted too, across the widest pair of sizes, where the fixed
    # per-crossing cost contributes least.
    per_element = (costs[-1] - costs[0]) / (SIZES[-1] - SIZES[0])
    assert per_element == pytest.approx(4.0, abs=0.5), (
        f"a transparent crossing grew {per_element:.3f} inferences an element "
        f"between sizes {SIZES[0]} and {SIZES[-1]}, where EXTENDING.md "
        f"publishes four"
    )
    # The claim a reader picks an image on is the class difference, so the two
    # ladders have to disagree about their shape and not merely their scale.
    assert fit.exponent > power_fit(SIZES, _ladder(crossing, "opaque")).exponent


def test_the_engine_calling_out_stays_cheaper_than_the_host_driving_in(crossing):
    """The direction axis, whose published gap is about five times."""
    out = crossing("direction-engine-out", "direction-engine-out-null", CROSSINGS)
    into = crossing("direction-host-in", "direction-host-in-null", CROSSINGS)
    assert out * 4 < into, (
        f"a crossing cost {out:.2f} inferences with the engine calling out and "
        f"{into:.2f} with the host driving in. EXTENDING.md tells a reader to "
        f"put the loop in MeTTa on the strength of that gap"
    )
    # The gated extension-cost table pins the same crossing at 12.00, so the
    # two harnesses disagreeing means one of them stopped measuring the call.
    assert out == pytest.approx(12.0, abs=1.0)
