"""Purpose: a question that stops at its first answer costs the same, and
answers the same, however many functors the process allocated before it.

SWI-Prolog answers current_predicate/1 for a name with its arity open in the
procedure table's hash order, and that order follows the functor handles the
process allocated before the name's own. A search that stopped at the first
atom or arity it wanted therefore visited a count that moved whenever any
functor was created earlier, anywhere: point twins moved by -34 and -50 when a
change added predicates to the binding and ran none of them [measured
2026-09-24: 07-tagged_fixpoint's twin read 27136, 27048 and 27014 with 0, 2 and
13 bare functors created before it]. Each property here plants a different
number of fresh functors before building the same thing, and requires the
answer and its cost not to move.
Guarantees:
  - whether a tagged program answers a query costs the same wherever the
    space's storage functors land [tested:
    test_the_tagged_program_check_costs_the_same_wherever_its_functors_land]
  - a refused save names the same unwritable symbol wherever the space's
    storage functors land [tested:
    test_a_refused_save_names_the_same_symbol_wherever_its_functors_land]
  - asking whether a name is still defined, or visible from a space, costs the
    same wherever its arities' functors land [tested:
    test_the_name_checks_cost_the_same_wherever_its_arities_land]
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import os
import subprocess
import sys
import uuid

import metta
from metta import S
from metta._atoms.wire import _atom_from_wire
from metta._roots import workspace
from metta.algebra import has_tagged_program

#: How many plantings the in-process properties compare: the name checks'
#: costs moved across a dozen on the parent of this change, where a fresh name
#: per planting lands its two arities at a new offset each time.
_PLANTINGS = 12


def _plant_functors(space, count):
    """Allocate `count` functors nothing else will ever name."""
    prefix = f"functor_order_{uuid.uuid4().hex}"
    for index in range(count):
        space.runtime.must(f"functor(_, '{prefix}_{index}', 1)")


def _inferences(space, goal, **inputs):
    """What one Prolog goal costs, counted around it in the same query.

    Clause garbage collection is drained before the count starts. The engine's
    erase listener, materialize:source_owner_erased/1, runs on whichever thread
    trips the collector, so a collection landing inside the window charged the
    listener's work to the goal, and whether one lands there moves with
    everything the process allocated before, which the plantings vary on
    purpose. The name checks read 42 at one planting against 34 at the rest,
    3 runs of 3, when the reference-face labelling moved the collector's timing;
    the same runs read 34 throughout with the collection drained, and still 42
    with the same prefix spelled `true`
    [measured 2026-09-26T02:54:18+10:00: this file three times under each
    query prefix, one battery on b40cf835c with the labelling applied].
    """
    row = space.runtime.must(
        f"garbage_collect_clauses, statistics(inferences, Before), ({goal}), "
        "statistics(inferences, After), Spent is After - Before",
        **inputs,
    )
    return row["Spent"]


def _tagged_graph(space):
    """The cyclic graph 07-tagged_fixpoint's twin asks about."""
    for start, end, weight in ((S.a, S.b, 0.6), (S.b, S.a, 0.5), (S.a, S.c, 0.2), (S.b, S.c, 0.3)):
        space.add_tagged_fact(weight, S.edge(start, end))
    space.add_tagged_rule(1, S.path(metta.V.x, metta.V.y), S.edge(metta.V.x, metta.V.y))
    space.add_tagged_rule(
        1,
        S.path(metta.V.x, metta.V.z),
        S.edge(metta.V.x, metta.V.y),
        S.path(metta.V.y, metta.V.z),
    )


#: One fresh process per planting, the way the twins lane prices a twin: inside
#: one process the order of a space's storage arities stayed put across a
#: dozen plantings, while across processes it moved between three functors
#: planted after boot and five [measured 2026-09-24 on the parent of this
#: change: 66 inferences with 0 to 3 planted, 44 with 5 to 21].
_TAGGED_CHILD = """
import sys, uuid
from metta import MeTTa, S, V
m = MeTTa().self
for index in range(int(sys.argv[1])):
    m.runtime.must(f"functor(_, 'functor_order_{uuid.uuid4().hex}', 1)")
for start, end, weight in ((S.a, S.b, 0.6), (S.b, S.a, 0.5), (S.a, S.c, 0.2), (S.b, S.c, 0.3)):
    m.add_tagged_fact(weight, S.edge(start, end))
m.add_tagged_rule(1, S.path(V.x, V.y), S.edge(V.x, V.y))
m.add_tagged_rule(1, S.path(V.x, V.z), S.edge(V.x, V.y), S.path(V.y, V.z))
row = m.runtime.must(
    "statistics(inferences, Before), metta_py_has_tagged_program(Space, Query, true),"
    " statistics(inferences, After), Spent is After - Before",
    Space=m.name, Query=S.path(S.a, S.c).to_wire())
print("COST", row["Spent"])
"""


def test_the_tagged_program_check_costs_the_same_wherever_its_functors_land(tmp_path):
    """A tagged program answers `path` at the same cost after 0, 5 and 13
    functors planted at boot, each in its own process.

    The check read every stored atom until the first tagged conclusion, in the
    storage arities' hash order, so how many edge facts it passed before a
    rule depended on where the space's functors landed.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    program = tmp_path / "tagged_cost.py"
    program.write_text(_TAGGED_CHILD, encoding="utf-8")
    repository = workspace()
    costs = []
    for planted in (0, 5, 13):
        result = subprocess.run(
            [sys.executable, str(program), str(planted)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(tmp_path),
            env={
                **os.environ,
                "METTA_PATH": str(repository),
                "PYTHONPATH": str(repository / "extensions" / "python"),
            },
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        costs.append(int(result.stdout.split("COST")[-1].split()[0]))
    assert len(set(costs)) == 1, costs
    with metta.space() as space:
        _tagged_graph(space)
        assert has_tagged_program(space, S.path(S.a, S.c))
        assert not has_tagged_program(space, S.unrelated(S.a))


def test_a_refused_save_names_the_same_symbol_wherever_its_functors_land():
    """Three atoms of three arities, each holding a symbol that reads back as
    a variable: a save refuses and names the least of them, every time.

    It named the first one the space's storage arities met in hash order, so
    which symbol a refusal reported depended on where the space's functors
    landed.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    named = set()
    for planted in range(_PLANTINGS):
        with metta.space() as space:
            _plant_functors(space, planted)
            space.add(S.first(S["$zeta"]))
            space.add(S.second(S.b, S["$alpha"]))
            space.add(S.third(S.c, S.d, S["$mid"]))
            row = space.runtime.must("metta_py_unwritable_atom(Space, Bad)", Space=space.name)
            named.add(str(_atom_from_wire(row["Bad"])))
    assert named == {"$alpha"}


def test_the_name_checks_cost_the_same_wherever_its_arities_land():
    """A name holding a clause at one arity and none at another is still
    defined, and visible from its space, at the same cost in every planting.

    Both checks stopped at the first arity with a clause, in the procedure
    table's hash order, so meeting the empty arity first cost one more step
    depending on where the name's functors landed.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    defined, visible = [], []
    for planted in range(_PLANTINGS):
        with metta.space() as space:
            _plant_functors(space, planted)
            name = f"functor_order_name_{uuid.uuid4().hex}"
            # The release check asks user, the visibility check the space's own
            # module, so the name is written into both.
            homes = ("user", space.runtime.must("metta_py_module(Space, Module)", Space=space.name)["Module"])
            for home in homes:
                space.runtime.must(
                    "dynamic(Home:Name/2), _Head =.. [Name, held], assertz(Home:_Head)", Home=home, Name=name
                )
            space.runtime.must("assertz(fun(Name))", Name=name)
            try:
                defined.append(_inferences(space, "metta_py_name_still_defined(Name)", Name=name))
                visible.append(_inferences(space, "metta_py_function_visible(Space, Name)",
                                           Space=space.name, Name=name))
            finally:
                for home in homes:
                    space.runtime.must("abolish(Home:Name/2), abolish(Home:Name/1)", Home=home, Name=name)
                space.runtime.must("retractall(fun(Name))", Name=name)
    assert len(set(defined)) == 1, defined
    assert len(set(visible)) == 1, visible
