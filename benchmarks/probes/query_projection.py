"""Purpose: measure complete shared and indexed query projections by width.

Owns resources: one native space, dropped after the samples and answer checks.
Guarantees: checks both decoders' first answer against the fixture before sampling
[source: extensions/python/benchmarks/probes/query_projection.py:main; commit=WORKTREE].
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _workspace import on_path

on_path()

import janus_swi as janus  # noqa: E402

from metta import Expression, S, Space  # noqa: E402

PROLOG = '''
projection_query(Decoder, Space, PatternsTagged, Names, Row) :-
    call(Decoder, ["e", PatternsTagged], Patterns, Bindings),
    metta_py_prepare_patterns(Patterns, PlainPatterns, Modifiers, Segments),
    metta_py_match_goal(Segments, Space, PlainPatterns, Goal),
    ( Modifiers == [] -> call(Goal)
    ; call(Goal), metta_py_call_modifiers(Modifiers) ),
    metta_py_row(Names, Bindings, Row).
projection_drive(Repeats, Goal, Used, Seconds) :-
    forall(Goal, true),
    statistics(cputime, T0), statistics(inferences, Before),
    forall(between(1, Repeats, _), (call(Goal), fail; true)),
    statistics(inferences, After), statistics(cputime, T1),
    Used is After - Before, Seconds is T1 - T0.
'''


def main() -> None:
    """Print raw samples for the measured crossover, without selecting a pin."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=1000)
    parser.add_argument("--samples", type=int, default=11)
    options = parser.parse_args()
    rows = []
    with Space("&projection-crossover") as space:
        janus.consult("projection_probe", data=PROLOG)
        for width in (2, 16, 64, 128):
            head = f"projection_{width}"
            space.add(Expression(S[head], *range(width)))
            names = [f"x{i}" for i in range(width)]
            patterns = [["e", [["s", head], *(["v", name] for name in names)]]]
            for decoder in ("metta_py_decode_shared", "metta_py_decode_indexed"):
                inputs = {"Space": space.name, "Patterns": patterns, "Names": names,
                          "Decoder": decoder, "Repeats": options.repeats}
                goal = "projection_query(Decoder,Space,Patterns,Names,Row)"
                assert janus.query_once(goal, inputs)["Row"] == [["n", value] for value in range(width)]
                samples = [janus.query_once(
                    "projection_drive(Repeats,projection_query(Decoder,Space,Patterns,Names,_),Used,Seconds)",
                    inputs) for _ in range(options.samples)]
                rows.append({"width": width, "decoder": decoder, "repeats": options.repeats,
                             "inferences": [sample["Used"] for sample in samples],
                             "cpu_seconds": [sample["Seconds"] for sample in samples]})
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
