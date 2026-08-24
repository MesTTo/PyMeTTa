"""Purpose: examples/spaces/spaces.metta in Python: writes a later match can see.

`matchtrickery` adds two atoms and matches them in one expression, and the
example's point is the ordering: `let*` binds both writes before the match
reads the space, so the match sees them.

The whole equation compiles, and every part of it is a Python spelling now. A
statement sequence inside a compiled body IS `let*`, so the two writes bind and
the match reads afterwards, in the source order the example depends on;
the local handle returned by `context-space` takes ordinary `+=` writes; and
`match(space, pattern, template)` is the ask itself, the same word Python reads
at three positions. Calling the definition and reading its answers are
ordinary Python.
"""

from metta import S, V, fn, match

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
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
        space = fn.context_space()
        space += S.foo(S.a)
        space += S.foo(S.b)
        return match(space, S.foo(V.x), S.bar(V.x))

    assert matchtrickery() == [S.bar(S.a), S.bar(S.b)]
