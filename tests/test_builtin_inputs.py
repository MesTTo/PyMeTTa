"""Purpose: a builtin handed an unbound variable where it needs a value says
so, in the program's own vocabulary, instead of binding the variable, making
an answer up, running away, or naming a host predicate.
Guarantees:
  - every position the engine's type surface declares strict, on a builtin
    PeTTa defines, refuses an unbound argument and names the MeTTa operation
    [tested test_every_builtin_refuses_an_unbound_input_by_name]
  - no such refusal names a Prolog predicate the MeTTa program never wrote
    [tested test_a_raising_builtin_names_the_metta_operation_not_the_host_predicate]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import MeTTa, PettaError

# The table is the ENGINE's, so this probe cannot go stale by hand: declaring
# a type for a new builtin adds a row to it in the same stroke. Every
# intermediate is _-prefixed because janus converts every NAMED variable of a
# query back to Python and an unbound one raises rather than arriving absent.
_TABLE = (
    "findall([_Name, _Position, _Kinds], "
    "( guarded_input_position(_Name, _Arity, _Position), "
    "  builtin_type_declaration(_Name, ['->'|_Chain]), "
    "  length(_Chain, _Arity), append(_Types, [_], _Chain), "
    "  findall(_Kind, "
    "          ( member(_Type, _Types), "
    "            ( nonvar(_Type), "
    "              memberchk(_Type, ['Expression', 'Number', 'String', "
    "                                'Bool', 'Symbol', 'Variable']) "
    "              -> _Kind = _Type ; _Kind = other ) ), "
    "          _Kinds) ), "
    "Rows)"
)

# A value of each kind, written the way a MeTTa program writes it. The hole
# is a MeTTa variable, which is exactly the unbound argument being probed.
_FILLER = {
    "Expression": "(a b)",
    "Number": "1",
    "String": '"s"',
    "Bool": "true",
    "Symbol": "&probe-space",
    "Variable": "$probe-bound",
    "other": "a",
}

# Prolog predicates a MeTTa program never wrote. A refusal naming one of
# these is the P1.8 defect, whatever else it gets right.
_HOST_PREDICATE_MARKS = ("system:", "/2:", "/3:", "/4:", "msort", "atom_codes")


@pytest.fixture(scope="module")
def probes(metta):
    """One MeTTa call per guarded position, with that position unbound."""
    rows = metta.runtime.once(_TABLE)["Rows"]
    built = []
    for name, position, kinds in rows:
        written = [
            "$petta-hole" if index + 1 == position else _FILLER[kind]
            for index, kind in enumerate(kinds)
        ]
        built.append((name, position, f"!({name} {' '.join(written)})"))
    return built


def test_every_builtin_refuses_an_unbound_input_by_name(metta, probes):
    """Reproduced 2026-08-19 by this probe's own ancestor, which found four
    different silent wrongs at once: 28 positions bound the caller's variable,
    `(car-atom $u)` unifying $u with [H|_] and answering the fresh head; 13
    answered a fresh variable and 12 answered a value derived from nothing;
    2 exhausted the stack, `(subtraction-atom $u (a b))` walking a list with
    both ends open; and 7 raised naming a host predicate.

    A table that emptied itself would pass every assertion below, so its size
    is asserted first."""
    assert len(probes) >= 80, len(probes)

    wrong = []
    for name, position, source in probes:
        try:
            answers = metta.run(source)
        except PettaError as refused:
            if name not in str(refused):
                wrong.append((source, f"refused without naming it: {refused}"))
            continue
        except Exception as unexpected:  # noqa: BLE001 - reported, not hidden
            wrong.append((source, f"raised {type(unexpected).__name__}"))
            continue
        rendered = [str(a) for group in answers for a in group]
        # An (Error ...) term naming the operation is the other refusal
        # style the engine uses, and it is a refusal by name.
        if all(r.startswith(f"(Error ({name}") for r in rendered) and rendered:
            continue
        wrong.append((source, f"answered {rendered}"))
    assert wrong == [], wrong


def test_a_raising_builtin_names_the_metta_operation_not_the_host_predicate(
    metta, probes
):
    """Reproduced 2026-08-19: `!(sort-atom $u)` said `msort/2` and
    `!(sread $u)` said `atom_codes/2`, naming Prolog predicates the MeTTa
    program never wrote and cannot act on."""
    named_host = []
    for name, _position, source in probes:
        try:
            metta.run(source)
        except PettaError as refused:
            message = str(refused)
            if any(mark in message for mark in _HOST_PREDICATE_MARKS):
                named_host.append((source, message))
    assert named_host == [], named_host


def test_the_measured_examples_read_as_MeTTa(metta):
    """The four the specification measured, spelled out, because a generated
    probe proves the property and a written-out case proves it reads."""
    for source, position in (
        ("!(car-atom $u)", 1),
        ("!(index-atom $u 0)", 1),
        ("!(sort-atom $u)", 1),
        ("!(size-atom $u)", 1),
    ):
        with pytest.raises(PettaError) as refused:
            metta.run(source)
        message = str(refused.value)
        assert f"argument {position}" in message, source
        assert "unbound variable" in message, source
        assert "msort" not in message, source

    # And the operations themselves are untouched.
    assert [str(a) for g in metta.run("!(car-atom (1 2))") for a in g] == ["1"]
    assert [str(a) for g in metta.run("!(size-atom (1 2 3))") for a in g] == ["3"]


def test_a_relational_position_still_enumerates(metta):
    """The rule refuses only what it can prove is an input. A position that is
    relational by design keeps its behaviour, and the engine names those
    rather than leaving them to be discovered: `(index-atom (a b) $i)`
    enumerates, `and` enumerates the truth table, and `cons` builds a pattern
    with an open tail, which the engine's own prelude writes as
    `(cons Error $_)`."""
    m = MeTTa()
    assert [str(a) for g in m.run("!(collapse (index-atom (a b) $i))") for a in g] == [
        "(a b)"
    ]
    assert [str(a) for g in m.run("!(collapse (and $a true))") for a in g] == [
        "(True False)"
    ]
    assert [str(a) for g in m.run("!(collapse (cons-atom a $tail))") for a in g] != []
