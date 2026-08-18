"""Purpose: measure what each extension point costs per call, which is the
table EXTENDING.md is built on, and hold every row to a committed baseline. That table was produced by a throwaway outside
the repo, hardcoding an absolute path and run by nobody, so its numbers could
drift without anything saying so, and one of its five rows no longer
reproduced.

Every tier is measured in ONE process against ONE driver shape, so the numbers
compare. The driver's own cost is measured separately and subtracted, which is
what makes a row the cost of the CALL rather than of the loop around it.

Read the two columns differently. Inferences are deterministic, so they are
the number to compare tiers on: five runs of one workload gave the same count
every time while wall clock swung 6.9% on the same box. Wall clock is advisory
and is here because it is the only column that sees the janus crossing, which
costs one inference and real microseconds.
Guarantees:
  - the driver's own cost is subtracted, so a row is the marginal cost of one
    call [tested: test_extension_cost_rows_are_marginal]
  - every tier is measured in one process against one driver shape
    [tested: test_extension_cost_rows_are_marginal]
  - every tier, and the driver itself, is held to a committed inference count
    in extension-baseline.json, so a change that moves one is a gate failure
    rather than a number a reader has to notice [tested 2026-08-16:
    test_a_moved_tier_fails_the_gate]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from petta import MeTTa
from petta.testing import BenchmarkBaseline

CALLS = 3_000
C_EXTENSION = (
    Path(__file__).resolve().parent.parent.parent
    / "examples/integration/c_extension"
)
ROUNDS = 3


@dataclass(frozen=True)
class Row:
    """One tier's marginal cost per call, and the drive it came from.

    `samples` is the drive's RAW inference totals, one per round, which is
    what a committed baseline compares: the marginal figure is a difference
    of two drives and would hide a change that moved both.
    """

    tier: str
    inferences: float
    microseconds: float
    samples: tuple[int, ...] = ()
    # The driver's own drive is measured and baselined but not published: it
    # is the loop the other rows have subtracted, not an extension point.
    published: bool = True


def _drive(space: MeTTa, prefix: str, name: str, calls: int) -> tuple[int, float]:
    source = f"({prefix}-{name} {calls})"
    space.one(source)  # warm the compiled path
    start = time.perf_counter()
    with space.stats() as counted:
        space.one(source)
    return counted.inferences, time.perf_counter() - start


def _measure(
    space: MeTTa, prefix: str, name: str, calls: int, rounds: int
) -> tuple[float, float, tuple[int, ...]]:
    """The minimum over rounds, which is the standard defence against a
    scheduler that took the process away mid-measurement. The samples come
    back too, because a committed baseline compares them rather than the
    minimum this returns."""
    samples = [_drive(space, prefix, name, calls) for _ in range(rounds)]
    return (
        min(inferences for inferences, _ in samples),
        min(seconds for _, seconds in samples),
        tuple(int(inferences) for inferences, _ in samples),
    )


def _install_drivers(space: MeTTa, prefix: str, bodies: dict[str, str]) -> None:
    """One driver per tier, plus an empty one whose cost is the loop itself.

    A driver per tier rather than one taking the body as an argument: an Atom
    parameter and an eval would put the evaluator's own cost inside every row,
    which is the thing the subtraction exists to remove.

    The prefix keeps the two tables apart. The engine is one per process, so
    installing the same driver name twice gives it two clauses: the recursion
    then leaves a choice point per level, and a deep drive runs out of stack
    instead of measuring anything. A fresh space would isolate the equations
    but not the macro, which add-translator-rule! runs from user at compile
    time, so the prefix is the separation that works for every tier.
    """
    space.run(
        f"(= ({prefix}-null $n)"
        f"   (if (> $n 0) ({prefix}-null (- $n 1)) done))"
    )
    for name, body in bodies.items():
        space.run(
            f"(= ({prefix}-{name} $n)"
            f"   (if (> $n 0) (let $_ {body} ({prefix}-{name} (- $n 1))) done))"
        )


def rows(calls: int = CALLS, rounds: int = ROUNDS) -> list[Row]:
    """Every tier, measured in one process."""
    space = MeTTa()

    space.run("(= (ec-metta $x) (+ $x 1))")
    space.run(
        "(= (ec-macro $x) (quote (+ $x 1)))\n"
        "!(add-translator-rule! ec-macro)\n"
        "(= (ec-macro-call $x) (ec-macro $x))"
    )
    space.register_prolog("'ec-prolog'(X, Y) :- Y is X + 1.", names=["ec-prolog"])

    # The C tier needs a compiled shared object, and a C toolchain is not one
    # of the engine's requirements. Say when the row is absent rather than
    # leaving a reader to assume it was measured.
    shared_object = C_EXTENSION / "cbump.so"
    has_c = shared_object.exists()
    if has_c:
        # Not the example's loader.pl, which resolves its path against the
        # working directory and so only loads from the repo root.
        space.register_prolog(
            ":- use_module(library(shlib)).\n"
            f":- use_foreign_library('{shared_object}', install_cbump).\n",
            names=["c-bump"],
        )

    @space.define(name="ec-defined")
    def ec_defined(x: int) -> int:
        return x + 1

    @space.define(name="ec-plain")
    def ec_plain(x):
        return x + 1

    @space.register_op(name="ec-op-encoded")
    def _encoded(x):
        return x + 1

    @space.register_op(name="ec-op-raw", raw=True)
    def _raw(x):
        return x + 1

    bodies = {
        "metta": "(ec-metta 1)",
        "defined": "(ec-defined 1)",
        "definedplain": "(ec-plain 1)",
        # The macro expands INTO the driver, which is the whole point of it:
        # measuring a function whose body is a macro measures the function.
        "macro": "(ec-macro 1)",
        "prolog": "(ec-prolog 1)",
        "opraw": "(ec-op-raw 1)",
        "opencoded": "(ec-op-encoded 1)",
    }
    if has_c:
        bodies["c"] = "(c-bump 1)"
    _install_drivers(space, "ec-tier", bodies)

    base_inferences, base_seconds, base_samples = _measure(
        space, "ec-tier", "null", calls, rounds
    )
    labels = {
        "metta": "ordinary MeTTa function",
        "definedplain": "@m.define, no annotations",
        "defined": "@m.define, annotated",
        "macro": "translator rule (a macro)",
        "prolog": "Prolog grounded predicate",
        "opraw": "Python operation, raw=True",
        "opencoded": "Python operation, encoded",
    }
    if has_c:
        labels["c"] = "C foreign predicate"
    else:
        print("note: cbump.so is not built, so the C row is absent", file=sys.stderr)
    # The driver's own drive is a row too, so a change that moves the loop
    # rather than a tier is visible instead of cancelling out of every row.
    measured = [
        Row(
            tier="the driver itself",
            inferences=base_inferences / calls,
            microseconds=base_seconds / calls * 1e6,
            samples=base_samples,
            published=False,
        )
    ]
    for name, label in labels.items():
        inferences, seconds, samples = _measure(space, "ec-tier", name, calls, rounds)
        measured.append(
            Row(
                tier=label,
                inferences=(inferences - base_inferences) / calls,
                microseconds=(seconds - base_seconds) / calls * 1e6,
                samples=samples,
            )
        )
    return measured


ENCODING_CALLS = 200


def encoding_rows(calls: int = ENCODING_CALLS, rounds: int = ROUNDS) -> list[tuple[str, float, float]]:
    """What the wire encoding costs as the argument grows.

    The single number in the published table is a one-argument integer, which
    is the encoded path's best case: the encoding WALKS the term and the raw
    path does not, so the gap between them is a function of argument size and
    a library passes structures rather than integers.

    Fewer calls than the tier table, because the driver recursion retains its
    argument per frame and a sixty-four item list a thousand frames deep runs
    the engine out of stack. Inferences are exact rather than sampled, so 200
    calls settle these rows as firmly as 3000 would.
    """
    space = MeTTa()

    @space.register_op(name="ec-size-encoded")
    def _encoded(x):
        return 1

    @space.register_op(name="ec-size-raw", raw=True)
    def _raw(x):
        return 1

    arguments = {
        "integer": "1",
        "flat, 4 items": "(1 2 3 4)",
        "flat, 16 items": "(" + " ".join(str(n) for n in range(16)) + ")",
        "flat, 64 items": "(" + " ".join(str(n) for n in range(64)) + ")",
        "nested, depth 4": "(a " * 4 + "x" + ")" * 4,
        "nested, depth 8": "(a " * 8 + "x" + ")" * 8,
    }
    bodies = {}
    for index, argument in enumerate(arguments.values()):
        bodies[f"enc{index}"] = f"(ec-size-encoded {argument})"
        bodies[f"raw{index}"] = f"(ec-size-raw {argument})"
    _install_drivers(space, "ec-size", bodies)
    base, _, _ = _measure(space, "ec-size", "null", calls, rounds)

    measured = []
    for index, label in enumerate(arguments):
        encoded, _, _ = _measure(space, "ec-size", f"enc{index}", calls, rounds)
        raw, _, _ = _measure(space, "ec-size", f"raw{index}", calls, rounds)
        measured.append(
            (label, (encoded - base) / calls, (raw - base) / calls)
        )
    return measured


def _render(measured: list[Row]) -> str:
    baseline = next(row for row in measured if row.tier.startswith("ordinary"))
    lines = [
        "| extension point | inferences/call | vs MeTTa | microseconds/call | vs MeTTa |",
        "|---|---|---|---|---|",
    ]
    for row in sorted(
        (row for row in measured if row.published), key=lambda r: r.inferences
    ):
        by_inference = row.inferences / baseline.inferences if baseline.inferences else 0.0
        by_wall = row.microseconds / baseline.microseconds if baseline.microseconds else 0.0
        lines.append(
            f"| {row.tier} | {row.inferences:.2f} | {by_inference:.2f}x "
            f"| {row.microseconds:.2f} | {by_wall:.2f}x |"
        )
    return "\n".join(lines)


BASELINE = Path(__file__).resolve().parent / "extension-baseline.json"


def _case_name(tier: str) -> str:
    """One baseline key per tier, stable across a wording change to the table.

    Derived from the tier label rather than kept as a second list, because a
    list maintained in two places drifts and the label is already the thing
    the table is keyed on.
    """
    kept = [c if c.isalnum() else "-" for c in tier.lower()]
    return "extcost-" + "-".join(part for part in "".join(kept).split("-") if part)


def compare(measured: list[Row], *, update: bool, path: Path = BASELINE) -> None:
    """Hold every tier to a committed inference count.

    The published numbers had no baseline behind them, so a change that moved
    one of them passed the gate and was found by reading the table: on
    2026-08-16 a with_metta_module/2 fast path took the annotated @m.define
    tier from 20.00 to 22.00 and nothing said so. The raw drive totals are
    compared rather than the marginal figures, because a marginal is a
    difference of two drives and cancels a change that moved both.
    """
    baseline = BenchmarkBaseline(path, update=update)
    for row in measured:
        if not row.samples:
            continue
        baseline.observe_counter(
            _case_name(row.tier),
            unit="calls",
            operations=CALLS,
            samples=list(row.samples),
        )
    baseline.finish()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--update", action="store_true")
    arguments = parser.parse_args(argv)

    measured = rows()
    print(_render(measured))
    print()
    print("| argument | encoded | raw=True | ratio |")
    print("|---|---|---|---|")
    for label, encoded, raw in encoding_rows():
        ratio = encoded / raw if raw else 0.0
        print(f"| {label} | {encoded:.2f} | {raw:.2f} | {ratio:.2f}x |")
    compare(measured, update=arguments.update)
    return 0


if __name__ == "__main__":
    sys.exit(main())
