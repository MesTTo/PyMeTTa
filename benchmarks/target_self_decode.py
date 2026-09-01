"""Purpose: preserve the cost proof for receiver-aware structured targets.

An evaluation target already needs one O(n) wire decode. Rebinding ``&self``
with a second O(n) term walk is correct but avoidable; the production decoder
performs the replacement during its first walk instead.

The historical alpha-unique control measured the second walk at about 400,000
inferences on one 50,000-term target. This promoted probe reconstructs that A/B
on the current codec: ``one-pass`` calls ``metta_py_decode_target/4`` and
``two-pass`` calls ``metta_py_decode_shared/3`` followed by
``metta_substitute_self/3``. Run from ``extensions/python`` with::

    python -m benchmarks.target_self_decode

The 2026-09-01 promoted measurement was 1,000,145 against 1,400,165
inferences and 52.725 against 58.822 ms CPU per decode: a 400,020-inference
(28.57%) and 6.097 ms (10.36%) saving, with identical decoded terms
[measured: min of three rounds over ten decodes per arm;
command=python -m benchmarks.target_self_decode; fixture=CPython 3.14,
50,000 three-child nodes and the provisioned repository engine;
commit=WORKTREE].
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from metta import Expression, S, V
from metta._engine import Runtime, runtime


def _target_wire(terms: int) -> list:
    """Build the large no-self control that exposes a redundant full walk."""
    return Expression(
        [S.node(V[f"x{index % 100}"], index % 10) for index in range(terms)]
    ).to_wire()


def _sample(rt: Runtime, wire: list, arm: str, repeats: int) -> tuple[float, float]:
    if arm == "one-pass":
        body = "metta_py_decode_target('&benchmark-target', W, _, _)"
        close_output = ""
    else:
        body = "metta_py_decode_shared(W, T, _), metta_substitute_self('&benchmark-target', T, _)"
        # forall/2 existentially scopes T, but Janus still sees its syntactic
        # query variable. Ground it after the measurement so the result codec
        # never has to carry an unbound implementation detail.
        close_output = ", T = none"
    row = rt.once(
        "statistics(inferences, Before), statistics(cputime, CpuBefore), "
        f"forall(between(1, Repeats, _), ({body})), "
        "statistics(inferences, After), statistics(cputime, CpuAfter), "
        "Used is After - Before, Cpu is CpuAfter - CpuBefore"
        f"{close_output}",
        Repeats=repeats,
        W=wire,
    )
    return float(row["Used"]) / repeats, float(row["Cpu"]) / repeats


def _assert_equivalent(rt: Runtime, wire: list) -> None:
    """Refuse to compare two arms unless their decoded terms alpha-agree."""
    row = rt.once(
        "findall(ok, (metta_py_decode_target('&benchmark-target', W, One, _), "
        "metta_py_decode_shared(W, Plain, _), "
        "metta_substitute_self('&benchmark-target', Plain, Two), "
        "One =@= Two), [ok]), One = none, Plain = none, Two = none",
        W=wire,
    )
    if not row:
        msg = "one-pass and two-pass target decoding diverged"
        raise AssertionError(msg)


def main(argv: Sequence[str] | None = None) -> int:
    """Measure the production decoder against the rejected second walk."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--terms", type=int, default=50_000)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--rounds", type=int, default=3)
    arguments = parser.parse_args(argv)
    if arguments.terms < 1 or arguments.repeats < 1 or arguments.rounds < 1:
        parser.error("terms, repeats, and rounds must all be positive")

    rt = runtime()
    wire = _target_wire(arguments.terms)
    _assert_equivalent(rt, wire)
    samples = {
        arm: [_sample(rt, wire, arm, arguments.repeats) for _ in range(arguments.rounds)]
        for arm in ("one-pass", "two-pass")
    }
    minima = {arm: min(values, key=lambda value: value[1]) for arm, values in samples.items()}
    for arm in ("one-pass", "two-pass"):
        inference, cpu = minima[arm]
        print(
            f"{arm}: inferences/decode={inference:.0f} "
            f"cpu/decode={cpu * 1_000:.3f}ms samples={samples[arm]}"
        )
    baseline = minima["two-pass"][0]
    saved = baseline - minima["one-pass"][0]
    print(f"saved: {saved:.0f} inferences/decode ({saved / baseline:.2%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
