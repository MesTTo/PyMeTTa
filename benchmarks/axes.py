"""Purpose: price the three independent axes of a host crossing, which
  EXTENDING.md describes and only one of which the extension-cost table
  measures.

The cost table answers "where does the body live" (a called `op` against a
lowered `@define`). The other two axes had no numbers at all: which side
DRIVES the crossing, and whether a value crosses TRANSPARENT (translated into
MeTTa structure) or OPAQUE (held whole by reference). Both change the cost
class rather than a constant, so a reader choosing between them was choosing
blind.

Read the columns the way DEVELOPING.md requires. Inferences are deterministic
and decide anything that stays inside the engine. They are BLIND across the
janus boundary, where foreign code retires no inferences at all, so the
direction axis is decided by retired instructions and the inference column is
reported beside it only to show that blindness.

Assumes:
  - `perf stat -e instructions:u` runs unprivileged, which needs
    perf_event_paranoid <= 2; `measure_instructions` hard-errors otherwise
  - the caller drives one case per process, so engine boot is a constant the
    paired control subtracts
Guarantees:
  - every published figure is a difference of two measured drives, so engine
    boot and loop overhead are subtracted rather than assumed small
  - a case and its control differ only by the work being priced
  - the minimum over rounds is reported, the standard defence against a
    scheduler that took the process away mid-measurement
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Callable

from metta import MeTTa, S, Space
from metta.testing import measure_instructions

# Enough crossings that the difference dominates process-to-process variation,
# and few enough that one case stays well inside the measurement timeout.
CROSSINGS = 20_000
# The value sizes the image axis sweeps. Transparent translation is linear in
# the value's size and opaque reference is flat, so a single size would read as
# a constant factor and hide the class difference entirely.
SIZES = (1, 10, 100, 1000)
IMAGE_CROSSINGS = 2_000
ROUNDS = 3


def _install_driver(space: Space, name: str, body: str | None) -> None:
    """A tail-recursive counter, the extension-cost harness's own driver shape.

    `body` of None is the control: the same loop with nothing in it, whose
    cost every published figure subtracts.
    """
    if body is None:
        space.run(f"(= ({name} $n) (if (> $n 0) ({name} (- $n 1)) done))")
    else:
        space.run(f"(= ({name} $n)   (if (> $n 0) (let $_ {body} ({name} (- $n 1))) done))")


def _engine_out(space: Space, *, control: bool) -> None:
    """The engine drives, calling out to Python once per iteration."""

    @space.op(name="ax-out", effect="pureStructural", transport="raw")
    def _out(x):
        return x

    _install_driver(space, "ax-out-drive", None if control else "(ax-out 1)")
    space.run(f"!(ax-out-drive {CROSSINGS})")


def _host_in(space: Space, *, control: bool, text: bool = False) -> None:
    """The host drives, calling into the engine once per iteration.

    Two doors, because they are not the same measurement. A prebuilt term is
    the crossing on its own, which is what the direction axis is asking about.
    A source string is that crossing plus a parse of the same text on every
    call, so it prices the string door rather than the direction.
    """
    space.run("(= (ax-in $x) $x)")
    term = S["ax-in"](1)
    if control:
        for _ in range(CROSSINGS):
            pass
    elif text:
        for _ in range(CROSSINGS):
            space.eval("(ax-in 1)")
    else:
        for _ in range(CROSSINGS):
            space.eval(term)


def _image(space: Space, *, size: int, opaque: bool, control: bool) -> None:
    """One Python list crossing per iteration, transparent or opaque.

    The list is built ONCE and returned by reference each time, so what is
    measured is the crossing rather than Python's own construction of it. The
    opaque case hands back the same object; the transparent case lets the
    encoded transport walk it into a MeTTa expression.
    """
    payload = list(range(size))

    @space.op(name="ax-img", effect="pureStructural")
    def _transparent():
        return payload

    @space.op(name="ax-blob", effect="pureStructural", transport="raw")
    def _opaque():
        return payload

    body = None if control else ("(ax-blob)" if opaque else "(ax-img)")
    _install_driver(space, "ax-img-drive", body)
    space.run(f"!(ax-img-drive {IMAGE_CROSSINGS})")


def _cases() -> dict[str, Callable[[Space], None]]:
    """Every case name a subprocess can be pointed at, with its control."""
    cases: dict[str, Callable[[Space], None]] = {
        "direction-engine-out": lambda s: _engine_out(s, control=False),
        "direction-engine-out-null": lambda s: _engine_out(s, control=True),
        "direction-host-in": lambda s: _host_in(s, control=False),
        "direction-host-in-text": lambda s: _host_in(s, control=False, text=True),
        "direction-host-in-null": lambda s: _host_in(s, control=True),
    }
    for size in SIZES:
        cases[f"image-transparent-{size}"] = lambda s, n=size: _image(
            s, size=n, opaque=False, control=False
        )
        cases[f"image-opaque-{size}"] = lambda s, n=size: _image(
            s, size=n, opaque=True, control=False
        )
        cases[f"image-null-{size}"] = lambda s, n=size: _image(
            s, size=n, opaque=False, control=True
        )
    return cases


_DRIVEN: list[str] = []


def run_case(name: str) -> int:
    """Drive one case and answer the engine inferences it retired.

    That counter is the one blind across the boundary, and it is reported so a
    reader can see the blindness rather than infer it.

    ONE case per process, and the second is refused rather than measured.
    Every `MeTTa()` context shares one engine and registrations are
    process-wide, so a second case installs its driver's head a second time;
    the recursion then leaves a choice point per level and a deep drive runs
    out of stack instead of measuring anything. Driving four cases in one process is what that looks
    like from outside: a run that never finishes.
    """
    if _DRIVEN:
        raise RuntimeError(
            f"axes: {_DRIVEN[0]} already ran in this process, so {name} would "
            f"install a second clause of one driver head and measure a choice "
            f"point. Drive one case per process, which is what --case is for."
        )
    _DRIVEN.append(name)
    case = _cases()[name]
    space = MeTTa().self
    with space.stats() as stats:
        case(space)
    return int(stats.inferences)


def _measure(name: str) -> tuple[int, int]:
    """Answer retired instructions and engine inferences for one case."""
    command = [sys.executable, "-m", "benchmarks.axes", "--case", name]
    return min(measure_instructions(command, rounds=ROUNDS)), inferences_of(name)


def inferences_of(name: str) -> int:
    """Engine inferences for one case, from a process that drove only it.

    Separate from `_measure` and free of `perf`, because the inference figures
    are the deterministic half: they carry the documented claims (four
    inferences per transparent element, a constant opaque crossing) and a
    regression test can assert them on a machine with no performance counters
    at all.
    """
    printed = subprocess.run(  # noqa: S603 - this module's own path and case names
        [sys.executable, "-m", "benchmarks.axes", "--case", name],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    ).stdout
    return int(printed.strip())


def _report() -> None:
    """Both axes, each figure a difference against its own control."""
    print(f"direction, per crossing, {CROSSINGS} crossings, min of {ROUNDS}")
    for label, case, null in (
        ("engine calls out", "direction-engine-out", "direction-engine-out-null"),
        ("host drives in", "direction-host-in", "direction-host-in-null"),
        ("host drives, text", "direction-host-in-text", "direction-host-in-null"),
    ):
        hot, hot_inferences = _measure(case)
        cold, cold_inferences = _measure(null)
        print(
            f"  {label:<18} "
            f"{(hot - cold) / CROSSINGS:10.1f} instructions "
            f"{(hot_inferences - cold_inferences) / CROSSINGS:8.2f} inferences"
        )

    print(f"\nvalue image, per crossing, {IMAGE_CROSSINGS} crossings")
    for size in SIZES:
        null, null_inferences = _measure(f"image-null-{size}")
        row = [f"  size {size:<5}"]
        for label, case in (
            ("transparent", f"image-transparent-{size}"),
            ("opaque", f"image-opaque-{size}"),
        ):
            hot, hot_inferences = _measure(case)
            row.append(
                f"{label} {(hot - null) / IMAGE_CROSSINGS:9.1f} instr "
                f"{(hot_inferences - null_inferences) / IMAGE_CROSSINGS:7.2f} inf"
            )
        print("   ".join(row))


def main(argv: list[str] | None = None) -> int:
    """Run one case, list the cases, or report both axes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", help="drive one case and exit, for perf stat")
    parser.add_argument("--list", action="store_true", help="every case name")
    arguments = parser.parse_args(argv)
    if arguments.list:
        for name in _cases():
            print(name)
        return 0
    if arguments.case:
        # The only thing on stdout, because the driver reads it back.
        print(run_case(arguments.case))
        return 0
    _report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
