"""examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/10-include.metta in Python: pasting a module rather than importing it.

A refusal here is a VALUE rather than a raise, so the three claims about it
compare error atoms rather than catching anything.

`include` answers what the module's LAST directive answered and puts its
forms in the INCLUDING space, where `import!` answers the unit and gives the
module a space of its own. Both take a module path, which is a name rather
than a string: `_fixtures/included/rows` is a path the reader spells, so it
comes through the exact subscript door.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from pathlib import Path

from metta import G, S, V

#: A module path resolves against the file that includes it, and the file
#: that includes these is a Python one four directories away from the
#: fixtures, so the paths are ABSOLUTE here where the original writes them
#: relative. The residue table records the relative form against P14.13.
_FIXTURES = (
    Path(__file__).resolve().parents[6]
    / Path("examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/_fixtures/included")
)
ROWS = S[str(_FIXTURES / "rows")]
SILENT = S[str(_FIXTURES / "silent")]


def twin(m):
    """Include a module, read what it left, and meet the three refusals."""
    include = m.fn.include

    # The module defines a function, states a fact, and ends in a runnable.
    # Including it answers that runnable's answer.
    assert include(ROWS) == [42]

    # And the function and the fact are in THIS space now.
    assert m.fn["included-double"](5) == [10]
    assert [row.x for row in m[S.included_fact(V.x)]] == [S.carried]

    # Which is the whole difference from `import!`: that door answers the
    # unit and the module's atoms are reachable through the space it made.
    assert m.fn["import!"](m, ROWS) == [True]

    # A module with no directive has no last answer, so the include answers
    # nothing at all rather than a unit standing in for one.
    assert include(SILENT) == []
    assert [row.x for row in m[S.silent_fact(V.x)]] == [S.here]

    # A name that resolves to nothing is refused by name, and so are the two
    # module-path BASES: `self` and `top` name directories rather than
    # modules, so including one is a category error.
    assert include(S.nosuchmodule) == [
        S.Error(S.include(S.nosuchmodule), G("no module named nosuchmodule is available"))
    ]
    not_a_module = G("include: the running context is not a module")
    assert include(S.self) == [S.Error(S.include(S.self), not_a_module)]
    assert include(S.top) == [S.Error(S.include(S.top), not_a_module)]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 5003 inferences, 0.5099x the example's 9811; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 5003 to 4998 (-5), metta_substitute_self/3 probes the
#: term for the text &self before walking it, one C write and one C substring
#: probe, where the twins-lane merge's one-equation door (08f6f4df) walked
#: every natively added equation in a named space unconditionally, so every
#: twin that adds or defines an equation in a named space drops by about that
#: equation's size in inferences; the same probe now guards the reader's per-
#: form door (record_translated_from/4), the deferred door's fallback
#: (stored_equation_source/4), a batch's arriving equations
#: (mark_or_translate_equation/5) and the removal probe (remove_equation/6),
#: where the walk is new and skipped for a term that never says &self, and a
#: twin that only removes or re-adds such equations pays the two-inference
#: probe per door crossing instead. Every twin here re-reads its budget on this
#: tree, minimum of three fresh processes [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
BUDGET = 4998
