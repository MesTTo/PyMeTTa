"""Purpose: price the FLOOR a Python twin of one example can reach, so a twin
over the band's ceiling can be told apart into the two things it can be: a
library slower than the engine at the same program, or a twin whose program is
not its example's.
Assumes: run as
  `python extensions/python/benchmarks/probes/twin_floor.py <example.metta>...`
  from the repository root. The control it builds stores every form the example
  stores through the cheapest write door there is and asks every runnable one
  through the structured evaluation door, asserting only that something came
  back; an assert-family form is asked as its SUBJECT, because that is what a
  twin asks before comparing in Python. So it authors no definition, states no
  extra claim and does no Python-side algebra, and its cost is the least any
  twin of that example could spend.
Guarantees: prints one row per example with the example's own cost, the band
  ceiling the lane applies, the control's cost and the shipped twin's, so a
  ceiling can be attributed. Eleven of the twenty-eight twins over the ceiling
  on 2026-09-07 had a floor ABOVE it, which is the band being tighter than the
  library's own floor for that example's shape and not a twin's fault
  [measured 2026-09-07: examples/ch08-data/08-01-atoms-lists-and-folds/
  10-multiset_operations.metta costs 6121 with a ceiling of 6733, its floor
  6985 and its twin 7290; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
Fails when: an example's forms cannot be parsed apart by balancing
  parentheses, which is the same reading `twin_coverage.example_forms` does.
"""  # noqa: D205  -- the contract header is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "extensions" / "python"))
sys.path.insert(0, str(ROOT / "extensions" / "python" / "tools"))

import twin_coverage as lane  # noqa: E402

CONTROL = '''\
"""A minimal twin: the example's own forms, stored and asked, nothing else."""

import json

import metta

#: Parsed at IMPORT, which is outside the lane's stats window, so the control
#: prices the writing and the asking and not the reading that supplies them.
STORED = [metta.parse(text) for text in json.loads({stored!r})]
ASSERT_HEADS = set(json.loads({heads!r}))
ASKED = []
for text in json.loads({asked!r}):
    form = metta.parse(text)
    children = getattr(form, "children", ())
    if children and str(children[0]) in ASSERT_HEADS and len(children) > 1:
        ASKED.append(children[1])
    else:
        ASKED.append(form)


def twin(m):
    """Store what the example stores, ask what it asks, hold what comes back."""
    for atom in STORED:
        m += atom
    for atom in ASKED:
        answered = m.eval(atom)
        assert answered is not None


BUDGET = 1
'''


def split(example: Path) -> tuple[list[str], list[str]]:
    """One example's stored forms and its runnable forms, as source text."""
    source = example.read_text(encoding="utf-8")
    stored: list[str] = []
    asked: list[str] = []
    index, size = 0, len(source)
    while index < size:
        char = source[index]
        if char == ";":
            index = source.find("\n", index)
            if index < 0:
                break
            continue
        if char == '"':
            index = lane._past_string(source, index)
            continue
        if char == "!" and index + 1 < size and source[index + 1] == "(":
            start = index
            index = lane._past_form(source, index + 1)
            asked.append(source[start + 1 : index])
            continue
        if char == "(":
            start = index
            index = lane._past_form(source, index)
            stored.append(source[start:index])
            continue
        index += 1
    return stored, asked


def floor(example: Path, scratch: Path) -> int | None:
    """The minimal control's cost for one example."""
    stored, asked = split(example)
    control = scratch / "floor_control.py"
    control.write_text(
        CONTROL.format(
            stored=json.dumps(stored),
            asked=json.dumps(asked),
            heads=json.dumps(sorted(lane.ASSERT_HEADS)),
        ),
        encoding="utf-8",
    )
    run = lane.run_twin(control)
    if run.cost is None:
        print(f"  control failed: {(run.outcome.error or '')[:300]}", file=sys.stderr)
    return run.cost


def main(paths: list[str]) -> int:
    """Print the four numbers a ceiling is attributed from, per example."""
    print(f"{'example':58} {'metta':>10} {'ceiling':>10} {'floor':>10} {'twin':>10}")
    with tempfile.TemporaryDirectory(prefix="metta-twin-floor-") as directory:
        scratch = Path(directory)
        for relative in paths:
            example = (ROOT / relative).resolve()
            twin = lane.twin_for(example)
            left, right = lane.run_example(example), lane.run_twin(twin)
            defined = lane.definitions(twin)
            authoring = (
                lane.DEFINITION_WARMUP + lane.DEFINITION_COST * defined if defined else 0
            )
            ceiling = (
                (left.cost or 0) * (1.0 + lane.BAND_PERCENT / 100.0) + authoring
            )
            print(
                f"{example.relative_to(ROOT)!s:58} {left.cost!s:>10} "
                f"{ceiling:>10.0f} {floor(example, scratch)!s:>10} "
                f"{right.cost!s:>10}",
                flush=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
