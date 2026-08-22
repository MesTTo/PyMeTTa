"""Purpose: pin the parametric state cell and the type that says what it holds.
Assumes: nothing beyond the ordinary MeTTa surface; a cell is engine
  vocabulary reachable with no import.
Guarantees:
  - (new-state V) answers a first-class cell, change-state! answers the cell it
    wrote so writes compose, and a cell's type is (StateMonad <type of V>).
  [tested: test_a_state_cell_is_a_value_typed_by_what_it_holds; commit=657ae9672c07b628f8a20c7fe39aa43e58b0014f]
  - the older named spelling still works, because a cell is a handle atom and a
    plain symbol names one too.
  [tested: test_a_state_cell_is_a_value_typed_by_what_it_holds; commit=657ae9672c07b628f8a20c7fe39aa43e58b0014f]
Fails when: read as a claim about the PRINTED form. The arbiter renders a cell
  as (State <value>) and this engine renders it as its handle, the way it
  already renders a space handle; that divergence is recorded beside
  'new-state'/2 in engine/metta.pl and is not closed here.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

import re

from petta import MeTTa


def _answers(metta: MeTTa, source: str) -> list[str]:
    """Return one runnable's answers in their stable textual form."""
    groups = metta.run(source)
    assert len(groups) == 1
    return [str(atom) for atom in groups[0]]


#: A declaration's type variable prints with the engine's allocation name,
#: `$_18268`, which differs between runs. Only the SHAPE is the claim here, so
#: every machine name becomes `$v` before comparison.
_MACHINE_VARIABLE = re.compile(r"\$_\d+")


def _normalised(metta: MeTTa, source: str) -> list[str]:
    """Answers with every machine variable name replaced by `$v`."""
    return [_MACHINE_VARIABLE.sub("$v", answer) for answer in _answers(metta, source)]


def test_a_state_cell_is_a_value_typed_by_what_it_holds() -> None:
    """The cell is the value, and (StateMonad $t) is what it holds."""
    metta = MeTTa("&statecell")

    # A cell is a value: it can be built, passed and written through without
    # ever being given a name. This is the arbiter's own composability probe,
    # LeaTTa tests/semantics/grounded/25-state-rendering.metta.
    assert _answers(metta, "!(get-state (new-state 5))") == ["5"]
    assert _answers(metta, "!(get-state (change-state! (new-state 1) 2))") == ["2"]

    # And it nests, because the content is any value at all.
    assert _answers(
        metta, "!(get-state (get-state (new-state (new-state 5))))"
    ) == ["5"]
    assert _answers(metta, "!(get-state (new-state (A B)))") == ["(A B)"]
    assert _answers(metta, '!(get-state (new-state "hi"))') == ['"hi"']

    # The TYPE is parametric in the content, which is the signature this row
    # exists for.
    # The declaration's own variable prints as the engine's machine name, so
    # the shape is compared with the name normalised away.
    assert _normalised(metta, "!(get-type new-state)") == ["(-> $v (StateMonad $v))"]
    assert _normalised(metta, "!(get-type get-state)") == ["(-> (StateMonad $v) $v)"]
    assert _normalised(metta, "!(get-type change-state!)") == [
        "(-> (StateMonad $v) $v (StateMonad $v))"
    ]
    assert _answers(metta, "!(get-type (new-state 5))") == ["(StateMonad Number)"]
    assert _answers(metta, '!(get-type (new-state "hi"))') == ["(StateMonad String)"]
    assert _answers(metta, "!(get-type (new-state True))") == ["(StateMonad Bool)"]
    assert _answers(metta, "!(let $c (new-state 5) (get-metatype $c))") == [
        "Grounded"
    ]

    # Two cells built from the same value are DIFFERENT cells.
    assert _answers(metta, "!(== (new-state 5) (new-state 5))") == ["False"]
    assert _answers(metta, "!(let $c (new-state 5) (== $c $c))") == ["True"]

    # The older named spelling is unchanged: bind! binds the name to the cell,
    # so the name reads and writes it exactly as before.
    assert _answers(metta, "!(bind! statecell-named (new-state 7))") == ["()"]
    assert _answers(metta, "!(get-state statecell-named)") == ["7"]
    metta.run("!(change-state! statecell-named 9)")
    assert _answers(metta, "!(get-state statecell-named)") == ["9"]

    # And a bare symbol still names a cell nothing allocated, which is what
    # lib/lib_llm.metta writes.
    metta.run("!(change-state! &statecell-plain 3)")
    assert _answers(metta, "!(get-state &statecell-plain)") == ["3"]
