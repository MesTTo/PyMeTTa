"""Purpose: pin Phase 5's Python annotation and conversion seam."""

from petta import Atom, Expr, Gnd, Sym, Var
from petta.ops import type_atoms_for


def test_the_four_metatypes_stay_distinct_across_the_seam():
    expected = {
        Atom: "Atom",
        Sym: "Symbol",
        Var: "Variable",
        Expr: "Expression",
        Gnd: "Grounded",
    }

    assert {
        annotation: str(type_atoms_for(annotation)[0])
        for annotation in expected
    } == expected
