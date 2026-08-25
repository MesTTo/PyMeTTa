"""Purpose: examples/spaces/state.metta in Python: a state cell is a value.

`new-state` answers a cell, `get-state` reads it, and `change-state!` answers
the CELL it wrote, so a write composes with a read in one expression. The
original's `bind!` is the concept Python spells with `=`, so the name below is
an ordinary Python variable.

`State[T]` is the whole cell surface: constructing it is `new-state`, reading
`.value` is `get-state`, and assigning `.value` is `change-state!`. Three
engine names became one typed handle and one Python property.

One line still names the engine's own functions, and it is the COMPOSITION
rather than either half of it. Python's attribute assignment is a statement
that answers nothing, and the walrus does not rescue it: PEP 572 excludes
attribute and subscript targets, and CPython says so in as many words,
`state.value := S.active` refusing with "cannot use assignment expressions with
attribute" [measured 2026-08-24: ast.parse on this interpreter;
commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. So the perfect spelling is a setter that answers its subject,
the way `change-state!` does:

    assert state.set(S.active).value == S.active

Until one exists the composition is the engine's own, named through the mention
door: `fn.change_state` is `change-state!`, rung 4 stripping the bang the way it
strips a hyphen. Either evaluation door says it: the held engine the lazy view
runs on shares its state cells with the main one, so a `change-state!`
performed through `m.answers(...).one()` is what the handle reads afterwards
[measured 2026-08-24: the cell reads `active` after the answer-view
composition; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].

Where the walrus DOES reach is the closing claim, which is about a cell needing
no name at all: binding in expression position is `let`, so the cell is built,
written and read on two lines instead of three.

`space.type(atom)` is the get-type accessor, so both type claims are method
calls rather than named heads.
"""

from metta import S, State, fn, ground

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 1999 to 2923, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 2923 to 2924, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 2924 to 2944, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
BUDGET = 2944


def twin(m):
    """Make a cell, read it, write through it, and ask what it holds."""
    # !(bind! state (new-state rest)): binding a name to the cell is Python's
    # own name binding, which is why the two spellings read alike.
    state = State(S.rest, space=m)
    assert state.value == S.rest

    # The write composes with the read, in the engine, for the reason above.
    assert m.answers(fn.get_state(fn.change_state(state, S.active))) == [S.active]   # rung: no Python expression writes an attribute
    # And the name still denotes the same cell, so the handle reads it too.
    assert state.value == S.active

    # The type says what the cell HOLDS, which is upstream's own signature
    # (: new-state (-> $t (StateMonad $t))).
    assert m.type(State(5, space=m)) == S.StateMonad(S.Number)
    assert m.type(State(ground("hi"), space=m)) == S.StateMonad(S.String)

    # And a cell needs no name at all: built in expression position, written
    # through the binding the same line makes, and read.
    (cell := State(1, space=m)).value = 2
    assert cell.value == 2
