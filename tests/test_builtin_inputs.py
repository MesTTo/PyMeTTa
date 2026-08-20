"""Purpose: a builtin handed an unbound variable where it needs a value says
so, in the program's own vocabulary, instead of binding the variable, making
an answer up, running away, or naming a host predicate.
Assumes:
  - the probe runs in a SUBPROCESS on a freshly booted engine, because the
    claim is about the ENGINE and not about whatever a shared session has
    been turned into [measured 2026-08-19: after a hundred test files have
    shared one process, three hundred named spaces exist and the extension
    seam has been rewired several times, and (py-call $u) then reports a
    context-less instantiation_error although the compiled goal is still
    'py-call'/2 and calling that predicate directly refuses correctly]
Guarantees:
  - every position the engine's type surface declares strict, on a builtin
    PeTTa defines, refuses an unbound argument and names the MeTTa operation
    [tested: test_every_builtin_refuses_an_unbound_input_by_name;
    commit=WORKTREE]
  - no such refusal names a Prolog predicate the MeTTa program never wrote
    [tested: test_a_raising_builtin_names_the_metta_operation_not_the_host_predicate;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import json
import subprocess
import sys
from pathlib import Path

import pytest

from petta import MeTTa, PettaError

REPO = Path(__file__).resolve().parents[3]

# The probe, run on a fresh engine. The TABLE is the engine's own, so this
# cannot go stale by hand: declaring a type for a new builtin adds a row to it
# in the same stroke. Every Prolog intermediate is _-prefixed because janus
# converts every NAMED variable of a query back to Python and an unbound one
# raises rather than arriving absent.
_PROBE = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from petta import MeTTa, PettaError

TABLE = (
    "findall([_Name, _Position, _Kinds], "
    "( guarded_input_position(_Name, _Arity, _Position), "
    "  builtin_type_declaration(_Name, ['->'|_Chain]), "
    "  length(_Chain, _Arity), append(_Types, [_], _Chain), "
    "  findall(_Kind, "
    "          ( member(_Type, _Types), "
    "            ( nonvar(_Type), "
    "              memberchk(_Type, ['Expression', 'Number', 'BigInt', "
    "                                'String', 'Bool', 'Symbol', 'Variable']) "
    "              -> _Kind = _Type ; _Kind = other ) ), "
    "          _Kinds) ), "
    "Rows)"
)
FILLER = {"Expression": "(a b)", "Number": "1", "BigInt": "9223372036854775808",
          "String": '"s"', "Bool": "true",
          "Symbol": "&probe-space", "Variable": "$probe-bound", "other": "a"}

engine = MeTTa()
rows = engine.runtime.once(TABLE)["Rows"]
report = {"probed": 0, "unnamed": [], "answered": [], "raised": []}
for name, position, kinds in rows:
    written = [("$petta-hole" if index + 1 == position else FILLER[kind])
               for index, kind in enumerate(kinds)]
    source = "!({} {})".format(name, " ".join(written))
    report["probed"] += 1
    try:
        answers = engine.run(source)
    except PettaError as refused:
        if name not in str(refused):
            report["unnamed"].append([source, str(refused)])
        continue
    except Exception as unexpected:
        report["raised"].append([source, type(unexpected).__name__])
        continue
    rendered = [str(a) for group in answers for a in group]
    # An (Error ...) term naming the operation is the other refusal style the
    # engine uses, and it is a refusal by name.
    if rendered and all(r.startswith("(Error ({}".format(name)) for r in rendered):
        continue
    report["answered"].append([source, rendered])
print(json.dumps(report))
"""


@pytest.fixture(scope="module")
def report():
    """Run the generated probe on a freshly booted engine and read it back."""
    finished = subprocess.run(
        [sys.executable, "-c", _PROBE, str(REPO / "bindings" / "python")],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(REPO),
    )
    assert finished.returncode == 0, finished.stderr[-3000:]
    return json.loads(finished.stdout.splitlines()[-1])


def test_every_builtin_refuses_an_unbound_input_by_name(report):
    """Reproduced 2026-08-19 by this probe's own ancestor, which found four
    different silent wrongs at once: 28 positions bound the caller's variable,
    (car-atom $u) unifying $u with a fresh cons cell and answering its head;
    13 answered a fresh variable and 12 answered a value derived from nothing;
    2 exhausted the stack, (subtraction-atom $u (a b)) walking a list with
    both ends open; and 7 raised naming a host predicate.

    A table that emptied itself would pass every assertion below, so its size
    is asserted first.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    assert report["probed"] >= 80, report["probed"]
    assert report["answered"] == [], report["answered"]
    assert report["raised"] == [], report["raised"]


def test_a_raising_builtin_names_the_metta_operation_not_the_host_predicate(report):
    """Reproduced 2026-08-19: !(sort-atom $u) said msort/2 and !(sread $u)
    said atom_codes/2, naming Prolog predicates the MeTTa program never wrote
    and cannot act on. Every refusal names its own operation now, which is the
    same assertion from the other side: a message naming a host predicate
    would not contain the MeTTa name.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    assert report["unnamed"] == [], report["unnamed"]


def test_the_measured_examples_read_as_metta():
    """The four the specification measured, spelled out, because a generated
    probe proves the property and a written-out case proves it reads.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    engine = MeTTa()
    for source, position in (
        ("!(car-atom $u)", 1),
        ("!(index-atom $u 0)", 1),
        ("!(sort-atom $u)", 1),
        ("!(size-atom $u)", 1),
    ):
        with pytest.raises(PettaError) as refused:
            engine.run(source)
        message = str(refused.value)
        assert f"argument {position}" in message, source
        assert "unbound variable" in message, source
        assert "msort" not in message, source

    # And the operations themselves are untouched.
    assert [str(a) for g in engine.run("!(car-atom (1 2))") for a in g] == ["1"]
    assert [str(a) for g in engine.run("!(size-atom (1 2 3))") for a in g] == ["3"]


def test_a_relational_position_still_enumerates():
    """The rule refuses only what it can prove is an input. A position that is
    relational by design keeps its behaviour, and the engine names those
    rather than leaving them to be discovered: (index-atom (a b) $i)
    enumerates, and enumerates the truth table, cons builds a pattern with an
    open tail, which the engine's own prelude writes as (cons Error $_), and
    union-atom splits a list from the right, which a shipped library does.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    engine = MeTTa()
    answers = lambda query: [  # noqa: E731 - one shape, read three times
        str(a) for g in engine.run(query) for a in g
    ]
    assert answers("!(collapse (index-atom (a b) $i))") == ["(a b)"]
    assert answers("!(collapse (and $a true))") == ["(True False)"]
    assert answers("!(collapse (cons-atom a $tail))") != []
    assert answers("!(collapse (let (union-atom $xs (3)) (1 2 3) $xs))") == ["((1 2))"]


def test_a_surface_match_on_an_unbound_space_answers_the_error(metta):
    """The compiled door, not the predicate: match/4 always refused an
    unbound space by name, but the emission fused the body template and the
    result into one variable, so the Error atom failed to unify with the
    already-bound body and the clause died silently, zero answers where a
    direct call answered the refusal [measured 2026-08-19 on the wave-7
    merged tree]. The template and the result are distinct variables now.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    with metta.new_space() as space:
        groups = space.run("!(match $u (f 1) matched)")
    assert len(groups) == 1 and len(groups[0]) == 1
    answer = str(groups[0][0])
    assert answer.startswith("(Error (match ")
    assert "match expects a space as the first argument" in answer
