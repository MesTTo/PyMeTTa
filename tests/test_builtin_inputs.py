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
    MeTTa defines, refuses an unbound argument and names the MeTTa operation
    [tested: test_every_builtin_refuses_an_unbound_input_by_name;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - no such refusal names a Prolog predicate the MeTTa program never wrote
    [tested: test_a_raising_builtin_names_the_metta_operation_not_the_host_predicate;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - `+ - * /` invert one unbound slot among integers, CLP(FD) solves the
    nonlinear cases past that, and every backward query outside both refuses
    with a named reason rather than a bare instantiation error
    [tested: test_arithmetic_inverts_past_the_linear_case_or_refuses_with_the_reason;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the four cross-file residual inputs and the already-repaired surface match
    path refuse under their own written names
    [tested: test_the_residual_positions_refuse_by_their_own_names;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
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

from metta import MeTTa, MettaError

REPO = Path(__file__).resolve().parents[3]

# The probe, run on a fresh engine. The TABLE is the engine's own, so this
# cannot go stale by hand: declaring a type for a new builtin adds a row to it
# in the same stroke. Every Prolog intermediate is _-prefixed because janus
# converts every NAMED variable of a query back to Python and an unbound one
# raises rather than arriving absent.
_PROBE = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from metta import MeTTa, MettaError

TABLE = (
    "findall([_Name, _Position, _Kinds], "
    "( guarded_input_position(_Name, _Arity, _Position), "
    "  seam:builtin_type_declaration(_Name, ['->'|_Chain]), "
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

context = MeTTa()
engine = context.self
rows = context.runtime.once(TABLE)["Rows"]
report = {"probed": 0, "unnamed": [], "answered": [], "raised": []}
for name, position, kinds in rows:
    written = [("$metta-hole" if index + 1 == position else FILLER[kind])
               for index, kind in enumerate(kinds)]
    source = "!({} {})".format(name, " ".join(written))
    report["probed"] += 1
    try:
        answers = engine.run(source)
    except MettaError as refused:
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
        check=False,
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
    engine = MeTTa().self
    for source, position in (
        ("!(car-atom $u)", 1),
        ("!(index-atom $u 0)", 1),
        ("!(sort-atom $u)", 1),
        ("!(size-atom $u)", 1),
    ):
        with pytest.raises(MettaError) as refused:
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
    engine = MeTTa().self
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
    with metta._new_space() as space:
        groups = space.run("!(match $u (f 1) matched)")
    assert len(groups) == 1 and len(groups[0]) == 1
    answer = str(groups[0][0])
    assert answer.startswith("(Error (match ")
    assert "match expects a space as the first argument" in answer


def test_the_residual_positions_refuse_by_their_own_names(metta):
    """The cross-file residual inputs refuse under the names programs wrote.

    Each operation's unbound-input refusal must carry the MeTTa operation
    name, never the host predicate that happened to raise first.
    """
    engine = MeTTa().self
    for operation, source, leaked_host_name in (
        ("add-reduct", "!(add-reduct $u a)", "add-atom"),
        ("git-import!", "!(git-import! $u)", "atom_string"),
        ("sleep", "!(sleep $u)", "must_be"),
        ("sread", "!(sread $u)", "atom_codes"),
    ):
        with pytest.raises(MettaError) as refused:
            engine.run(source)
        message = str(refused.value)
        assert operation in message, source
        assert leaked_host_name not in message, source

    with metta._new_space() as space:
        groups = space.run("!(match $u (f 1) matched)")
    answer = str(groups[0][0])
    assert answer.startswith("(Error (match ")
    assert "match expects a space as the first argument" in answer


def test_arithmetic_inverts_past_the_linear_case_or_refuses_with_the_reason():
    """`+ - * /` are relations, and where they stop they say so.

    Each solves for ONE unbound slot among integers, which nothing in the tree
    recorded until now, so a function written forwards reads backwards for
    free. Past one unknown the rearrangement becomes a CONSTRAINT: 25 = X*X is
    nonlinear and no reordering of is/2 computes it, so the engine posts it to
    CLP(FD) and labels what propagation leaves. A domain the constraint leaves
    unbounded has nothing finite to search, and deciding a polynomial equation
    over the integers is undecidable (Hilbert's tenth problem), so that case
    refuses BY NAME rather than raising SWI's bare "Arguments are not
    sufficiently instantiated", which named neither the operation's modes nor
    what to write instead [measured 2026-08-21: every case below raised it].
    """
    engine = MeTTa().self
    answers = lambda query: [  # noqa: E731 - one shape, read many times
        str(a) for g in engine.run(query) for a in g
    ]

    # The fragment, one unknown among integers, forwards and backwards. The
    # name carries this row's prefix because &self is shared by every MeTTa()
    # in a process: README.md registers a Python `double`, so a plain `double`
    # here answers twice whenever tests/test_readme.py ran first in the same
    # worker [measured 2026-08-21].
    engine.run("(= (p225-double $x) (* 2 $x))")
    assert answers("!(p225-double 5)") == ["10"]
    assert answers("!(let 10 (p225-double $x) $x)")[0] == "5"
    assert answers("!(let 5 (+ $p 2) $p)") == ["3"]
    assert answers("!(let 6 (- $r 4) $r)") == ["10"]
    assert answers("!(let 12 (* $q 4) $q)") == ["3"]
    assert answers("!(let 3 (/ $s 4) $s)") == ["12"]
    # No integer answers it, so the relation FAILS rather than erroring.
    assert answers("!(collapse (let 7 (p225-double $x) $x))") == ["()"]

    # Past the fragment: every solution, not one, and in the solver's order.
    assert answers("!(collapse (let 25 (* $x $x) $x))") == ["(-5 5)"]
    assert answers("!(collapse (let 25 (* $x $y) ($x $y)))") == [
        "((-25 -1) (-5 -5) (-1 -25) (1 25) (5 5) (25 1))"
    ]
    # A posted CLP(FD) bound narrows it to one, which is the composition the
    # specification measured as `25 #= B*B, B #>= 0` answering B = 5.
    assert answers("!(collapse (let True (#>= $x 0) (let 25 (* $x $x) $x)))") == ["(5)"]
    # Unsatisfiable is no answers, not an error.
    assert answers("!(collapse (let 26 (* $x $x) $x))") == ["()"]

    # Where it stops, it names the reason. Nothing here may reach the user as
    # SWI's own instantiation error.
    for source, reason in (
        ("!(let 10 (+ $x $y) ($x $y))", "no finite domain to search"),
        ("!(let 0 (- $x $x) $x)", "no finite domain to search"),
        ("!(* $x 2)", "no finite domain to search"),
        ("!(collapse (* $x $y))", "no finite domain to search"),
        # Evaluation is inside-out, so a composed backward query reaches its
        # inner operation with two unknowns. The # operators post rather than
        # solve, which is why they still earn their place.
        ("!(let 20 (* (+ $a 1) 4) $a)", "no finite domain to search"),
        # `/` may answer a float, so there is no integer relation to post.
        ("!(let 5 (/ $x $y) ($x $y))", "only +, - and * have an integer relation"),
        # A float operand has no finite domain either, and reaches the same
        # refusal through the recovery rather than through the solver.
        ("!(let 10.0 (* 2.0 $x) $x)", "an operand is still unbound"),
    ):
        with pytest.raises(MettaError) as refused:
            engine.run(source)
        message = str(refused.value)
        assert reason in message, (source, message)
        assert "sufficiently instantiated" not in message, (source, message)

    # And the numeric doctrine underneath is untouched: integer zero division
    # is still a contained Error atom and float division still saturates.
    assert answers("!(/ 7 0)") == ["(Error (/ 7 0) DivisionByZero)"]
    assert answers("!(% 7 0)") == ["(Error (% 7 0) DivisionByZero)"]
    assert answers("!(/ 1.0 0.0)") == ["inf"]
    assert answers("!(* 6 7)") == ["42"]
