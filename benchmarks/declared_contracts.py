"""Purpose: measure static discharge of repeated declared-call contracts.

Assumes:
  - run from ``extensions/python`` with the repository's provisioned Python
    interpreter and engine.
Guarantees:
  - every compared pair executes the same loop and asserts the same answer;
  - the ``proved`` pair differs only by a callee contract whose argument is
    proved by the caller's declaration and whose result is unconstrained;
  - the ``checked-result`` and ``unproved`` pairs retain one runtime check for
    separate, named reasons.
Fails when:
  - calls or rounds are not positive, or either arm answers differently.
Decides:
  - report engine inferences and CPU time as min-of-three by default. Both
    paths remain O(1) per call; this benchmark prices the constant factor that
    dominated the profile after declaration lookup was already indexed.

Run with::

    python -m benchmarks.declared_contracts

Nguyen et al.'s soft-contract verification supplies the governing rule:
discharge only a contract proved by static information, and retain the check
for an unknown (POPL 2014, DOI 10.1145/2628136.2628156).

At 100,000 compiled calls, the proved custom-contract overhead fell from
46.002 to 2.000 inferences per call and from 1.763 to 0.247 microseconds CPU.
When the result still needed checking, the overhead fell from 91.004 to
50.002 inferences and from 2.676 to 1.612 microseconds. The unproved control
kept its check at 49.002 inferences and 1.317 microseconds, while the existing
Number VM shortcut stayed at a two-inference differential. Reflective calls,
which have no statically typed caller, retained their full 100.004-inference
and 6.840-microsecond contract cost
[measured: min of seven, before at
60b9fbb2e961711cd653967367300505de41d478 and after at WORKTREE;
command=python -m benchmarks.declared_contracts --calls 100000
--reflective-calls 2000 --rounds 7; fixture=CPython 3.14, C reader, one
fresh process per tree; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from metta import MeTTa, Space


@dataclass(frozen=True)
class Sample:
    """One measured engine interval."""

    inferences: int
    cpu: float


_SOURCE = """
(: dc-Payload Type)
(: dc-value dc-Payload)

(= (dc-plain-id $x) $x)
(: dc-typed-id-open (-> dc-Payload %Undefined%))
(= (dc-typed-id-open $x) $x)
(: dc-typed-id-closed (-> dc-Payload dc-Payload))
(= (dc-typed-id-closed $x) $x)
(= (dc-plain-number-id $x) $x)
(: dc-typed-number-id (-> Number %Undefined%))
(= (dc-typed-number-id $x) $x)

(: dc-plain-proof-drive (-> Number dc-Payload %Undefined%))
(= (dc-plain-proof-drive $n $x)
   (if (> $n 0)
       (let $_ (dc-plain-id $x)
            (dc-plain-proof-drive (- $n 1) $x))
       $x))
(: dc-typed-proof-drive (-> Number dc-Payload %Undefined%))
(= (dc-typed-proof-drive $n $x)
   (if (> $n 0)
       (let $_ (dc-typed-id-open $x)
            (dc-typed-proof-drive (- $n 1) $x))
       $x))

(: dc-plain-result-drive (-> Number dc-Payload %Undefined%))
(= (dc-plain-result-drive $n $x)
   (if (> $n 0)
       (let $_ (dc-plain-id $x)
            (dc-plain-result-drive (- $n 1) $x))
       $x))
(: dc-typed-result-drive (-> Number dc-Payload %Undefined%))
(= (dc-typed-result-drive $n $x)
   (if (> $n 0)
       (let $_ (dc-typed-id-closed $x)
            (dc-typed-result-drive (- $n 1) $x))
       $x))

(: dc-plain-number-drive (-> Number Number %Undefined%))
(= (dc-plain-number-drive $n $x)
   (if (> $n 0)
       (let $_ (dc-plain-number-id $x)
            (dc-plain-number-drive (- $n 1) $x))
       $x))
(: dc-typed-number-drive (-> Number Number %Undefined%))
(= (dc-typed-number-drive $n $x)
   (if (> $n 0)
       (let $_ (dc-typed-number-id $x)
            (dc-typed-number-drive (- $n 1) $x))
       $x))

(= (dc-plain-unproved-drive $n $x)
   (if (> $n 0)
       (let $_ (dc-plain-id $x)
            (dc-plain-unproved-drive (- $n 1) $x))
       $x))
(= (dc-typed-unproved-drive $n $x)
   (if (> $n 0)
       (let $_ (dc-typed-id-open $x)
            (dc-typed-unproved-drive (- $n 1) $x))
       $x))
"""


def _space() -> Space:
    space = MeTTa().self
    space.run("!(pragma! max-stack-depth 100000000)")
    space.run(_SOURCE)
    return space


def _assert_value(value: object, arm: str) -> None:
    if str(value) != "dc-value":
        message = f"{arm} answered {value!r}, expected dc-value"
        raise AssertionError(message)


def _compiled_runner(space: Space, arm: str, calls: int) -> Callable[[], Sample]:
    argument = "1" if arm.endswith("number-drive") else "dc-value"
    source = f"({arm} {calls} {argument})"

    def run() -> Sample:
        with space.stats() as stats:
            value = space._one(source)
        if arm.endswith("number-drive"):
            if value != 1:
                message = f"{arm} answered {value!r}, expected 1"
                raise AssertionError(message)
        else:
            _assert_value(value, arm)
        return Sample(int(stats.inferences), float(stats.cputime))

    return run


def _reflective_runner(
    space: Space, arm: str, calls: int
) -> Callable[[], Sample]:
    source = f"({arm} dc-value)"

    def run() -> Sample:
        value: object | None = None
        with space.stats() as stats:
            for _ in range(calls):
                value = space._one(source)
        _assert_value(value, arm)
        return Sample(int(stats.inferences), float(stats.cputime))

    return run


def _measure_pair(
    left: Callable[[], Sample],
    right: Callable[[], Sample],
    rounds: int,
) -> tuple[list[Sample], list[Sample]]:
    left()
    right()
    samples: dict[str, list[Sample]] = {"left": [], "right": []}
    for round_index in range(rounds):
        order = (("left", left), ("right", right))
        if round_index % 2:
            order = tuple(reversed(order))
        for name, runner in order:
            samples[name].append(runner())
    return samples["left"], samples["right"]


def _minimum(samples: list[Sample]) -> Sample:
    return Sample(
        min(sample.inferences for sample in samples),
        min(sample.cpu for sample in samples),
    )


def _print_pair(
    name: str,
    plain: list[Sample],
    declared: list[Sample],
    calls: int,
) -> None:
    plain_min = _minimum(plain)
    declared_min = _minimum(declared)
    inference_delta = declared_min.inferences - plain_min.inferences
    cpu_delta = declared_min.cpu - plain_min.cpu
    print(name)
    for arm, minimum, samples in (
        ("plain", plain_min, plain),
        ("declared", declared_min, declared),
    ):
        print(
            f"  {arm}: inferences/call={minimum.inferences / calls:.3f} "
            f"cpu/call={minimum.cpu * 1_000_000 / calls:.3f}us "
            f"samples={samples}"
        )
    print(
        f"  delta: inferences/call={inference_delta / calls:+.3f} "
        f"cpu/call={cpu_delta * 1_000_000 / calls:+.3f}us"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Measure proved, residual, unknown, and reflective contract paths."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--calls", type=int, default=20_000)
    parser.add_argument("--reflective-calls", type=int, default=1_000)
    parser.add_argument("--rounds", type=int, default=3)
    arguments = parser.parse_args(argv)
    if (
        arguments.calls < 1
        or arguments.reflective_calls < 1
        or arguments.rounds < 1
    ):
        parser.error("calls, reflective-calls, and rounds must be positive")

    space = _space()
    pairs = (
        (
            "compiled-proved",
            "dc-plain-proof-drive",
            "dc-typed-proof-drive",
            arguments.calls,
            _compiled_runner,
        ),
        (
            "compiled-checked-result",
            "dc-plain-result-drive",
            "dc-typed-result-drive",
            arguments.calls,
            _compiled_runner,
        ),
        (
            "compiled-proved-number",
            "dc-plain-number-drive",
            "dc-typed-number-drive",
            arguments.calls,
            _compiled_runner,
        ),
        (
            "compiled-unproved",
            "dc-plain-unproved-drive",
            "dc-typed-unproved-drive",
            arguments.calls,
            _compiled_runner,
        ),
        (
            "reflective",
            "dc-plain-id",
            "dc-typed-id-open",
            arguments.reflective_calls,
            _reflective_runner,
        ),
    )
    try:
        for name, plain_name, declared_name, calls, factory in pairs:
            plain, declared = _measure_pair(
                factory(space, plain_name, calls),
                factory(space, declared_name, calls),
                arguments.rounds,
            )
            _print_pair(name, plain, declared, calls)
    finally:
        space.drop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
