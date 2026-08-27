"""Purpose: pin the parametric state cell and the type that says what it holds.
Assumes: nothing beyond the ordinary MeTTa surface; a cell is engine
  vocabulary reachable with no import.
Guarantees:
  - (new-state V) answers a first-class cell, change-state! answers the cell it
    wrote so writes compose, and a cell's type is (StateMonad <type of V>).
  [tested: test_a_state_cell_is_a_value_typed_by_what_it_holds; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the older named spelling still works, because a cell is a handle atom and a
    plain symbol names one too.
  [tested: test_a_state_cell_is_a_value_typed_by_what_it_holds; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - compiled ``State.value`` reads, writes, and augmented writes lower to the
    engine cell heads, while speculative writes refuse before mutation
    [tested: test_compiled_state_properties_round_trip_through_engine_heads,
    test_speculative_state_write_is_fenced; commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
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

import pytest

from metta import MeTTa, State
from metta.errors import MettaError


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
    metta = MeTTa().space("&statecell")

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
    # lib/lib_llm/lib_llm.metta writes.
    metta.run("!(change-state! &statecell-plain 3)")
    assert _answers(metta, "!(get-state &statecell-plain)") == ["3"]


def test_compiled_state_properties_round_trip_through_engine_heads(metta) -> None:
    """A closed-over cell is a State operand, not a pinned host attribute."""
    hits = State(1, space=metta)

    @metta.define
    def state_property_round_trip():
        hits.value += 1
        return hits.value

    @metta.define
    def state_property_replace(replacement):
        hits.value = replacement
        return hits.value

    assert state_property_round_trip() == [2]
    assert state_property_round_trip() == [3]
    assert state_property_replace(8) == [8]
    assert state_property_round_trip() == [9]


def test_speculative_state_write_is_fenced(metta) -> None:
    """The non-backtrackable cell store cannot escape a discarded snapshot."""
    cell = State(4, space=metta)
    with metta.speculative():
        with pytest.raises(MettaError, match=r"state.*speculative|speculative.*state"):
            cell.value = 5
        with pytest.raises(MettaError, match=r"state.*speculative|speculative.*state"):
            State(0, space=metta)
    assert cell.value == 4
