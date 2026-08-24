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
commit=WORKTREE]. So the perfect spelling is a setter that answers its subject,
the way `change-state!` does:

    assert state.set(S.active).value == S.active

Until one exists the composition is the engine's own, named through the mention
door: `fn.change_state` is `change-state!`, rung 4 stripping the bang the way it
strips a hyphen. Either evaluation door says it: the held engine the lazy view
runs on shares its state cells with the main one, so a `change-state!`
performed through `m.answers(...).one()` is what the handle reads afterwards
[measured 2026-08-24: the cell reads `active` after the answer-view
composition; commit=WORKTREE].

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
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Make a cell, read it, write through it, and ask what it holds."""
    # !(bind! state (new-state rest)): binding a name to the cell is Python's
    # own name binding, which is why the two spellings read alike.
    state = State(S.rest, space=m)
    assert state.value == S.rest

    # The write composes with the read, in the engine, for the reason above.
    assert m.answers(fn.get_state(fn.change_state(state, S.active))).one() == S.active  # rung: no Python expression writes an attribute
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
