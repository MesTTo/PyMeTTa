"""examples/functions/partialdef.metta in Python: a definition answering a partial.

`(mp)` answers `(+)`, which takes both its arguments later, so `(mp 1 1)` is
2. `..` composes two partial applications, and `(plus1times2)` answers that
composition, so `(plus1times2 1)` is `(1 + 1) * 2`.

All three definitions are decorated Python functions. `..` carries its MeTTa
name through `name=".."`, because `..` is not a Python identifier, while its
BODY is ordinary Python: `f1(f2(arg))` applies two parameters in turn, which
is the variable-head application the subset already reads.

The other two bodies are partial applications of heads Python's operators
cannot reach. `(+)`, `(* 2)` and `(+ 1)` have no operator spelling, because
`+` needs both operands to be an operator at all, so they are written by
CALLING the word-table symbols: `S.add()` is `(+)` and `S.mul(2)` is `(* 2)`.
The decorated `compose` object carries its exact MeTTa head `..` when another
compiled body mentions it.
"""

from metta import S

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Answer a partial application from a definition, then compose two."""

    @m.define
    def mp():
        # (= (mp) (+))
        return S.add()

    assert m.eval(S.mp(1, 1)) == [2]

    @m.define(name="..")
    def compose(f1, f2, arg):
        # (= (.. $f1 $f2 $arg) ($f1 ($f2 $arg)))
        return f1(f2(arg))

    @m.define
    def plus1times2():
        # (= (plus1times2) (.. (* 2) (+ 1)))
        return compose(S.mul(2), S.add(1))

    assert m.eval(S.plus1times2(1)) == [4]
