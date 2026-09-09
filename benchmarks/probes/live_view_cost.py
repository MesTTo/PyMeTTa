"""Purpose: measure what a live view costs per touching write, per strategy,
against the recompute each replaces, and answer the three structural facts the
implementation's own comments cite.

Assumes:
  - it runs from the repository root with `extensions/python` importable, and
    the engine's inference counter is the measurement: wall clock under 100ms
    on a loaded box is bimodal, while `m.stats().inferences` is deterministic
Guarantees:
  - `--costs` reports inferences per touching write at three relation sizes
    for each of the three strategies beside the equivalent uncached recompute
    [measured 2026-09-08: pattern 90/90/90, heads 200/575/4245, tabled
    1156/1689/7089 and recompute 178/553/4223 inferences per touching
    write at 10, 100 and 1,000 rows, minimum of three;
    command=python extensions/python/benchmarks/probes/live_view_cost.py --costs;
    fixture=an edge ring with a weight per node and private tabled probe-total;
    commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4]
  - `--forms`, `--effects` and `--naming` each print the one fact
    `metta.structures` cites them for
    [measured 2026-09-07: --forms prints tables=2 answers=2 for the three
    probe-step shapes, --effects prints pureStructural for a bare pattern,
    oracleIO for a call that matches and writesState for add-atom, --naming
    prints the seed row Row(y=$_1) beside the event row $_2;
    command=python extensions/python/benchmarks/probes/live_view_cost.py --forms,
    then --effects, then --naming; fixture=the probe's own spaces]
Fails when: run without a working janus; it needs the engine.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from metta import S, V, space  # noqa: E402
from metta._atoms.factories import Expression, Symbol, Variable, _match  # noqa: E402


def _cost(context, work, repeats: int = 3) -> int:
    """The minimum of `repeats` inference counts, the repository's rule."""
    counts = []
    for _ in range(repeats):
        with context.stats() as spent:
            work()
        counts.append(spent.inferences)
    return min(counts)


@contextmanager
def _private_total(sp):
    """Keep the view's transaction-safe table policy scoped to the probe."""
    row = "(cache probe-total (incremental private))"
    sp.run(f"!(add-atom &metta {row})")
    try:
        yield
    finally:
        sp.run(f"!(remove-atom &metta {row})")


def costs() -> None:
    """Inferences per touching write for each strategy, and the recompute.

    The baseline is what a program writes WITHOUT a view: a subscription on
    the same heads whose callback re-answers the query. Both run inside the
    write's own dispatch on the home engine, which is what makes the two
    counts comparable: a query cursor opened outside a callback runs on its
    own engine and the home engine's counter does not see it (measured
    2026-09-07: the same 1,000-row join read 5 inferences standalone and
    3,173 inside a callback).
    """
    print(f"{'measurement':<34}{'10':>8}{'100':>8}{'1000':>8}")
    readings: dict[str, list[int]] = {}
    for size in (10, 100, 1000):
        with space() as sp, _private_total(sp):
            sp.run("!(import! &self (library lib_tabling))")
            for index in range(size):
                sp.add(S.edge(S[f"n{index}"], S[f"n{(index + 1) % size}"]))
                sp.add(S.weight(S[f"n{index}"], index))
            sp.run(
                f"(= (probe-total) (max-atom (collapse "
                f"(match {sp.name} (weight $n $w) $w))))"
            )
            sp.run("!(tabled (probe-total))")
            counter = [size]

            def one_write():
                counter[0] += 1
                sp.add(S.weight(S[f"m{counter[0]}"], counter[0]))

            def elsewhere():
                counter[0] += 1
                sp.add(S.unrelated(counter[0]))

            def ten_writes():
                sp.transaction(lambda: [one_write() for _ in range(10)] and None)

            def recompute(_event):
                # list(), not `.rows`: Answers is lazy and `.rows` is another
                # lazy view, so a discarded `.rows` reads nothing at all.
                list(sp.match(S.edge(V.a, V.n), S.weight(V.n, V.w)))

            taken: dict[str, int] = {}
            with sp.live(S.weight(V.n, V.w)):
                taken["pattern, touching write"] = _cost(sp, one_write)
            with sp.live(S.edge(V.a, V.n), S.weight(V.n, V.w)):
                taken["heads, touching write"] = _cost(sp, one_write)
                taken["heads, untouching write"] = _cost(sp, elsewhere)
                taken["heads, transaction of ten"] = _cost(sp, ten_writes)
            with sp.live(S["probe-total"]()) as view:
                if view.strategy.value != "tabled":
                    msg = f"the probe wanted the tabled strategy, got {view.strategy}"
                    raise RuntimeError(msg)
                taken["tabled, invalidating write"] = _cost(sp, one_write)
                # A write the table's own subgoal does not read leaves it
                # VALID, so the view reads the counter and stops there.
                taken["tabled, table stays valid"] = _cost(sp, elsewhere)
            with sp.subscribe(S.weight(V.n, V.w), recompute, on="both"):
                taken["recompute, touching write"] = _cost(sp, one_write)
                taken["recompute, transaction of ten"] = _cost(sp, ten_writes)
            with sp.subscribe(S.weight(V.n, V.w), lambda _event: None, on="both"):
                taken["bare subscription, write"] = _cost(sp, one_write)
        for label, value in taken.items():
            readings.setdefault(label, []).append(value)
    for label, values in readings.items():
        cells = "".join(f"{value:>8}" for value in values)
        print(f"{label:<34}{cells}")


def forms() -> None:
    """table-stats reports per FUNCTION, whatever the call's arguments are."""
    with space() as sp:
        sp.run("!(import! &self (library lib_tabling))")
        sp.add(S.edge(S.a, S.b), S.edge(S.b, S.c))
        sp.run(f"(= (probe-step $x $y) (match {sp.name} (edge $x $y) $y))")
        sp.run("!(tabled (probe-step $a $b))")
        sp.eval("(probe-step a $y)")
        sp.eval("(probe-step b $y)")
        for spelled in ("(probe-step $x0 $x1)", "(probe-step a $y)", "(probe-step b $y)"):
            answer = sp.eval(f"(table-stats {spelled})")[0]
            counters = {
                str(pair.children[0]): str(pair.children[1])
                for pair in answer.children
                if len(pair.children) == 2
            }
            print(f"{spelled:<26} tables={counters['tables']} answers={counters['answers']}")
        built = sp.eval(
            Expression([Symbol("table-stats"), Expression(
                [Symbol("probe-step"), Variable("x0"), Variable("x1")]
            )])
        )[0]
        print("as a built atom, once lib_tabling is loaded:", str(built)[:40], "...")


def effects() -> None:
    """The effect JOIN says writesState for every real query; the head does not."""
    with space() as sp:
        sp.add(S.person(S.bob, 30))
        sp.run(
            f"(= (probe-oldest) (max-atom (collapse "
            f"(match {sp.name} (person $n $a) $a))))"
        )
        for label, target in (
            ("a bare pattern", S.person(V.n, V.a)),
            ("a call that matches", Expression([Symbol("probe-oldest")])),
            ("add-atom", S["add-atom"](S[str(sp.name)], S.x)),
        ):
            plan = sp.effect_plan(target)
            print(f"{label:>20}: {plan.effect.value:>22}  {list(plan.operations)}")


def naming() -> None:
    """A stored atom's variables are named differently by seed and by event."""
    with space() as sp:
        sp.add(S.rule(V.x))
        seeded = [str(row) for row in sp.match(S.rule(V.y)).rows]
        events: list[str] = []
        with sp.subscribe(S.rule(V.y), events.append, on="both"):
            sp.remove(S.rule(V.x))
        print("seed row  :", seeded)
        print("event row :", [str(event.bindings["y"]) for event in events])
        print(
            "directional match of a compound against a bare variable:",
            _match(Expression([Symbol("rule"), Variable("y")]), Variable("X")),
        )


def main(argv: list[str]) -> int:
    """Run the selected probes; all of them with no flag."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--costs", action="store_true")
    parser.add_argument("--forms", action="store_true")
    parser.add_argument("--effects", action="store_true")
    parser.add_argument("--naming", action="store_true")
    arguments = parser.parse_args(argv)
    selected = [
        probe
        for probe, wanted in (
            (costs, arguments.costs),
            (forms, arguments.forms),
            (effects, arguments.effects),
            (naming, arguments.naming),
        )
        if wanted
    ] or [costs, forms, effects, naming]
    for probe in selected:
        print(f"--- {probe.__name__} ---")
        probe()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
