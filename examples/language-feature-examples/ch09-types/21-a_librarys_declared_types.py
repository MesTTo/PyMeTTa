"""examples/ch09-types/21-a_librarys_declared_types.metta in Python: the types an import brought in.

`m += lib.datastructures` brings the library's declarations in with its
equations, and `space.type` reads them back: a declaration is an atom in the
space, and an imported one is no different from a local one.

Two doors answer the same question at different arities. `space.type(atom)` is
the single-answer door and REFUSES when there is no type, naming the term,
where the original collapses `get-type` to the empty bag; `m.answers(...)` over
the built form is that bag, so both spellings are here for the two terms whose
arguments do not fit.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, Symbol, arrow, lib
from metta.errors import EngineError

EMPTY = S.FTEmpty


def twin(m):
    """Read the four declarations back, then ask about two that do not fit."""
    m += lib.datastructures

    # `FTree` is declared `Type`, which is what makes the other three mean
    # anything.
    assert m.type(S.FTree) == S.Type

    # `FTEmpty` takes nothing, so its type is the type itself: it IS a tree
    # rather than a way of making one. The other two are arrows, and their
    # argument types say what each field holds.
    assert m.type(EMPTY) == S.FTree
    assert m.type(S.FTSingle) == arrow(S.Atom, S.FTree)
    assert m.type(S.FTDeep) == arrow(S.Expression, S.FTree, S.Expression, S.FTree)

    # Applying one answers the type its arrow ends in, which is how trees
    # built out of different constructors are all one type.
    assert m.type(S.FTSingle(1)) == S.FTree
    assert m.type(S.FTDeep((1, 2), EMPTY, (3, 4))) == S.FTree

    # A nullary constructor is a SYMBOL, and out here the metatype IS the
    # Python class, so nothing crosses the seam to ask for it. Wrapping it in
    # brackets would be a one-element expression rather than the atom the
    # library means, and neither side writes that form: the coverage lane
    # reads call position out of the corpus text, where a one-element
    # expression and a nullary call are the same characters.
    assert type(EMPTY) is Symbol
    assert type(S.FTSingle(1)) is Expression

    # The argument types are checked, and an application that does not fit has
    # no type at all rather than a wrong one.
    for bad in (S.FTSingle(1, 2), S.FTDeep(1, EMPTY, (3, 4))):
        assert m.answers(S.get_type(bad)) == []
        refused = None
        try:
            m.type(bad)
        except EngineError as refusal:
            refused = refusal
        assert "returned no type" in str(refused)
        assert repr(bad) in str(refused)


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 22672 inferences, 0.9700x the example's 23372; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 22672 to 22926 (+254), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
BUDGET = 22926
