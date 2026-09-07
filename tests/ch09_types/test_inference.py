"""Purpose: the declarations a program's own atoms justify, which
``Space.infer_types()`` proposes and never adds by itself.
Guarantees:
  - the narrowest kind covering a position is what a proposal carries, with a
    variable contributing nothing and disagreeing children contributing Atom
    [tested: test_a_position_takes_the_narrowest_kind_covering_its_children,
    test_disagreeing_children_make_a_position_an_atom; commit=8d67307403c1e41ccf058bd3c8d4c079dd7cf7d5]
  - a head the space declares is never proposed for, and `declare=True` adds
    exactly the proposals, after which there is nothing left to propose
    [tested: test_a_declared_head_is_skipped,
    test_declaring_adds_exactly_the_proposals; commit=8d67307403c1e41ccf058bd3c8d4c079dd7cf7d5]
  - proposing changes nothing, and the one thing accepting a proposal CAN
    change is named where it can be read [tested:
    test_proposing_adds_nothing, test_an_atom_position_stops_evaluating_that_argument;
    commit=8d67307403c1e41ccf058bd3c8d4c079dd7cf7d5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import inspect

import pytest

from metta import S, stubs
from metta._declarations import inferred
from metta._space import Space
from metta.errors import MettaError
from metta.foreign import SpaceProvider


def test_a_position_takes_the_narrowest_kind_covering_its_children(metta):
    """One kind per position, and the equation body decides the result."""
    with metta._new_space() as m:
        m.run(
            """
            (inf-user 1 ada)
            (inf-user 2 bob)
            (inf-text "a" True)
            (= (inf-double $x) (* $x 2))
            (= (inf-greet $n) "hi")
            (= (inf-zero) 7)
            """
        )
        assert [str(atom) for atom in m.infer_types()] == [
            "(: inf-user (-> Number Symbol %Undefined%))",
            "(: inf-text (-> String Bool %Undefined%))",
            "(: inf-double (-> %Undefined% Number))",
            "(: inf-greet (-> %Undefined% String))",
            "(: inf-zero (-> Number))",
        ]


def test_disagreeing_children_make_a_position_an_atom(metta):
    """Two kinds at one position have no narrower cover than the top one."""
    with metta._new_space() as m:
        m.run('(inf-mixed 1)\n(inf-mixed "a")\n(inf-mixed sym)\n')
        assert [str(atom) for atom in m.infer_types()] == [
            "(: inf-mixed (-> Atom %Undefined%))"
        ]


def test_a_nested_call_carries_its_heads_declared_result(metta):
    """An expression at a position is what its head is declared to answer."""
    with metta._new_space() as m:
        m.run(
            """
            (: inf-circle (-> Number Shape))
            (= (inf-circle $r) (Circle $r))
            (inf-drawn (inf-circle 2))
            (inf-drawn (inf-circle 3))
            (inf-plain (whatever a))
            """
        )
        proposed = {str(atom) for atom in m.infer_types()}
        assert "(: inf-drawn (-> Shape %Undefined%))" in proposed
        assert "(: inf-plain (-> Expression %Undefined%))" in proposed


def test_two_arities_are_two_proposals(metta):
    """A head answered at two arities has two signatures, not one."""
    with metta._new_space() as m:
        m.run("(inf-pair 1)\n(inf-pair 1 2)\n")
        # A set, because the order between one head's two arities is the order
        # the space STORED them, and a data run stores a head's atoms together
        # rather than in source order [measured 2026-09-07].
        assert {str(atom) for atom in m.infer_types()} == {
            "(: inf-pair (-> Number %Undefined%))",
            "(: inf-pair (-> Number Number %Undefined%))",
        }
        rows = inferred(m)
        assert {row.name for row in rows} == {"inf-pair"}
        assert sorted(row.arity for row in rows) == [1, 2]


def test_a_declared_head_is_skipped(metta):
    """A declaration is the program's own answer; a proposal beside it is noise."""
    with metta._new_space() as m:
        m.run("(: inf-said (-> Number Number))\n(= (inf-said $x) $x)\n(inf-said 1)\n")
        assert m.infer_types() == []


def test_a_catalogue_row_is_not_data_about_a_head(metta):
    """`:` and `@doc` rows are the space describing itself, not atoms to read."""
    with metta._new_space() as m:
        m.run('(: inf-known Number)\n(@doc inf-noted (@desc "noted"))\n')
        assert m.infer_types() == []


def test_proposing_adds_nothing(metta):
    """Reading a space cannot change it, which is why declare is a keyword."""
    with metta._new_space() as m:
        m.run("(inf-quiet 1)\n")
        before = m.digest()
        assert m.infer_types() != []
        assert m.digest() == before


def test_declaring_adds_exactly_the_proposals(metta):
    """What goes in is what came out, and get-type then answers it."""
    with metta._new_space() as m:
        m.run("(inf-added 1 ada)\n")
        proposals = m.infer_types()
        added = m.infer_types(declare=True)
        assert added == proposals
        assert [str(atom) for atom in m.atoms() if str(atom).startswith("(: ")] == [
            str(atom) for atom in proposals
        ]
        assert str(m.type(S["inf-added"])) == "(-> Number Symbol %Undefined%)"
        # Nothing is left to propose, so the door is idempotent under accept.
        assert m.infer_types() == []


def test_an_atom_position_stops_evaluating_that_argument(metta):
    """The one behaviour accepting a proposal can change, pinned where it is read.

    `Atom` is a metatype: an argument declared `Atom` reaches the head
    unevaluated. A mixed position proposes `Atom`, so accepting that proposal
    changes what a call to the head sees, and `infer_types`'s own docstring
    says so. This is the measurement behind that sentence.
    """
    with metta._new_space() as m:
        m.run("(= (inf-shows $x) $x)\n")
        assert [str(a) for a in m.run("!(inf-shows (+ 1 2))")[0]] == ["3"]
        m.run("(: inf-shows (-> Atom Atom))\n")
        assert [str(a) for a in m.run("!(inf-shows (+ 1 2))")[0]] == ["(+ 1 2)"]


def test_a_space_that_cannot_be_enumerated_refuses(metta):
    """The proposal is a walk, so a provider that declines to be walked says so.

    The refusal is the capability check every whole-space door already makes,
    reached before anything enters the engine, which is why the walk below is
    never called.
    """

    class NoEnumerate(SpaceProvider):
        """A provider that declines the one capability a proposal needs."""

        called = False

        def atoms(self):
            NoEnumerate.called = True
            return iter(())

        def can_run(self, capability, /, **request):
            if capability == "enumerate":
                return False
            return super().can_run(capability, **request)

    name = "&inf-no-enumerate"
    metta._register_space(NoEnumerate(), name)
    try:
        backed = Space(name, _runtime=metta._rt)
        with pytest.raises(MettaError, match="declines this enumerate request"):
            backed.infer_types()
        assert not NoEnumerate.called
    finally:
        metta._unregister_space(name)


def test_the_signature_and_the_stub_both_say_inferred(metta):
    """One proposal, three faces, and each says which of the two it is."""
    with metta._new_space() as m:
        m.run("(= (inf-shown $x) (* $x 2))\n(: inf-told (-> Number Number))\n(= (inf-told $x) $x)\n")
        assert str(inspect.signature(m.fn["inf-shown"])) == "(x1: '%Undefined%', /) -> 'Number'"
        assert "(inferred from stored atoms, not declared)" in m.fn["inf-shown"].__doc__
        assert "(inferred from stored atoms, not declared)" not in m.fn["inf-told"].__doc__
        text = stubs(m)
        assert "def inf_shown(x1: Any, /) -> int | float:" in text
        assert "(inferred from stored atoms, not declared)" in text
        assert "def inf_told(x1: int | float, /) -> int | float:" in text
