"""Purpose: demonstrate that annotations can control evaluation and become
facts derived from a compiled definition's source.

The reflection vocabulary has these shapes; the path and coordinates are an
illustrative source location, while the executable checks below read the live
facts:

(source-span &my-space checked "example.py" 10 0 13 17)
(free-variable &my-space checked helper)
(effect checked pureStructural)

Guarantees:
  - Atom parameters preserve written terms while ordinary parameters receive
    reduced values [tested: annotation_contracts example; commit=3cfbe0d7417b1c453c2dc12d47e2e47e7de461f7]
  - local type claims and source-derived definition facts are visible through
    the public API [tested: annotation_contracts example; commit=3cfbe0d7417b1c453c2dc12d47e2e47e7de461f7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from _common import check, done

import metta

m = metta.MeTTa().space()


@m.pure
def anyatom(term: metta.Atom) -> metta.Atom:
    return term

@m.pure
def anyval(term):
    return term


m.run("(= (side) 42)")
check("Atom preserves the call", m.run("!(anyatom (side))"), [[m.parse("(side)")]])
check("ordinary input reduces", m.run("!(anyval (side))"), [[42]])


@m.define
def checked(value):
    result: int = value
    return result


check("the type claim accepts a number", m.run("!(checked 7)"), [[7]])
check("the type claim rejects a string", m.run('!(checked "nope")'), [[]])
check("the source span names this file", checked.source_span.path, __file__)
check("the compiled definition is pure", checked.pure, True)
done("annotation_contracts")
