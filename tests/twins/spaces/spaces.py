"""Purpose: examples/spaces/spaces.metta in Python: writes a later match can see.

`matchtrickery` adds two atoms and matches them in one expression, and the
example's point is the ordering: `let*` binds both writes before the match
reads the space, so the match sees them.

The whole equation compiles. A statement sequence inside a compiled body IS
`let*`, so the two writes bind and the match reads afterwards, in the source
order the example depends on; `fn.add_atom` and `fn.match` name the engine's
own functions through the mention door, which spells the hyphen the Python
grammar cannot; and `fn.context_space()` is `&self`, the space the equation is
being written into, without naming a space as a symbol. Calling the definition
and reading its answers are ordinary Python.

One line names a head Python already spells. `match` dissolves into
`space[pattern]`, and the subscript is a Python-side query a compiled body
cannot perform, so the body names the engine's own head. PERFECT: the subscript
lowers inside a compiled body the way the other structure operations do.
"""

from petta import S, V, fn

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Store one self-writing definition, then read what calling it answers."""

    # (= (matchtrickery)
    #    (let* (($t1 (add-atom &self (foo a)))
    #           ($t2 (add-atom &self (foo b))))
    #          (match &self (foo $1) (bar $1))))
    @m.define
    def matchtrickery():
        _first = fn.add_atom(fn.context_space(), S.foo(S.a))
        _second = fn.add_atom(fn.context_space(), S.foo(S.b))
        return fn.match(fn.context_space(), S.foo(V.x), S.bar(V.x))  # rung: inside a compiled body the space door is the engine's own match; the subscript is a Python-side query

    assert matchtrickery() == [S.bar(S.a), S.bar(S.b)]
