"""Purpose: examples/types/engine_surface.metta in Python: the engine's own type surface.

Nothing is imported here. The engine reads its own declarations at boot and
consults them LAST, so `get-type` answers for a special form, a structure
operation or the state cell while the program's space stays the program's own.
This twin asks all of them through `space.type(atom)`, the get-type accessor,
and builds every expected arrow from PYTHON TYPES: `Atom`, `Variable` and
`Expression` are the metatype classes, `int`, `bool` and `str` are Number, Bool
and String, and `Any` is `%Undefined%`, all through the one conversion table.

Two things it also shows. The declarations are FACTS the engine holds, not
atoms in the program's space, so iterating that space finds only what the
program itself declared. And a program's own declaration is answered AHEAD of
the engine's, without taking the operation away: after `(: car-atom MyOverride)`
the builtin still answers, and `get-type` answers both.

`map-atom` likewise has two declared arrows, one for each callable surface;
`sort-atom` and `repr` take evaluated values and therefore use `%Undefined%`
parameters rather than evaluation-masking metatypes.
[source: examples/types/engine_surface.metta:22; commit=f053d9d46aa43b9beec360eae30b9016ffbf231f]
"""

from typing import Any

from metta import Atom, Expression, S, V, Variable, arrow, fn, ground, typed

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 12298 to 13860, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 13860 to 13863, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 13863 to 13865, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
BUDGET = 13865


def twin(m):
    """Read the engine's declared types, then overlay one of them."""
    # Special forms are compiled by the translator and have no registry entry,
    # so they were the least reachable half of the surface. `if` is a Python
    # keyword, so its name takes rung 5's bracket.
    # !(test (get-type if) (-> Bool Atom Atom $t)), and seven more
    assert m.type(fn["if"]).alpha_eq(arrow(bool, Atom, Atom, V.t))
    assert m.type(fn.let) == arrow(Atom, Any, Atom, Any)
    assert m.type(fn.chain) == arrow(Atom, Variable, Atom, Any)
    assert m.type(fn.quote) == arrow(Atom, Atom)
    assert m.type(fn.collapse) == arrow(Atom, Atom)
    assert m.type(fn.superpose) == arrow(Expression, Any)
    assert m.type(fn.match) == arrow(S.SpaceType, Atom, Atom, Any)
    assert m.fn.get_type(fn.map_atom) == [
        arrow(Expression, Variable, Atom, Expression),
        arrow(Expression, Expression, Expression),
    ]

    # Expression structure, from the reference corelib dump.
    # !(test (get-type car-atom) (-> Expression %Undefined%)), and four more
    assert m.type(fn.car_atom) == arrow(Expression, Any)
    assert m.type(fn.cdr_atom) == arrow(Expression, Expression)
    assert m.type(fn.cons_atom) == arrow(Atom, Expression, Atom)
    assert m.type(fn.size_atom) == arrow(Expression, int)
    assert m.type(fn.index_atom) == arrow(Expression, int, Atom)

    # PeTTa's own, with no dump entry to take.
    # !(test (get-type sort-atom) (-> %Undefined% Expression)), and three more
    assert m.type(fn.sort_atom) == arrow(Any, Expression)
    assert m.type(fn.is_var) == arrow(Atom, bool)
    assert m.type(fn.repr) == arrow(Any, str)
    assert m.type(fn.current_time) == arrow(int)

    # The state cell is a VALUE and its type says what it holds.
    # !(test (get-type new-state) (-> $t (StateMonad $t))), and four more
    cell = S.StateMonad
    assert m.type(fn.new_state).alpha_eq(arrow(V.t, cell(V.t)))
    assert m.type(fn.change_state).alpha_eq(arrow(cell(V.t), V.t, cell(V.t)))
    assert m.type(fn.get_state).alpha_eq(arrow(cell(V.t), V.t))
    assert m.type(fn.new_state(5)) == cell(S.Number)
    assert m.type(fn.new_state(ground("hi"))) == cell(S.String)

    # The surface is FACTS, not atoms in the program's space: a program still
    # sees only its own declarations when it enumerates them, which is what
    # iterating a space is for. The subscript door would be the other spelling
    # and it reads a wholly-variable `(: $n $t)` as an annotation rather than
    # as data, where the engine's own match keeps it structural (friction,
    # P14.29).
    # (: program-own-type MyType)
    # !(test (collapse (match &self (: $n $t) $n)) (program-own-type))
    m += typed(S.program_own_type, S.MyType)
    assert list(m) == [typed(S.program_own_type, S.MyType)]

    # And a program's own declaration is answered ahead of the engine's,
    # because the table is consulted last. The operation itself is untouched:
    # this asks the ENGINE for the head of an expression, which is the whole
    # point of the claim, where `e[0]` would only ask Python.
    # (: car-atom MyOverride)
    # !(test (car-atom (a b)) a)
    # !(test (collapse (get-type car-atom)) (MyOverride (-> Expression %Undefined%)))
    m += typed(fn.car_atom, S.MyOverride)
    assert m.fn.car_atom(S.a(S.b)) == [S.a]
    assert m.fn.get_type(fn.car_atom) == [S.MyOverride, arrow(Expression, Any)]
