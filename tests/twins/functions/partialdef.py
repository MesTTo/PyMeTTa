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
CALLING the symbol: `S["+"]()` is `(+)` and `S["*"](2)` is `(* 2)`. `..` is
named the same way, at rung 5 of the descent ladder, since the Python name
`compose` is bound to the decorated function and a compiled body will not
reach a sibling definition whose MeTTa name differs from its Python one.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Answer a partial application from a definition, then compose two."""

    @m.define
    def mp():
        # (= (mp) (+))
        return S["+"]()

    assert m.eval(S.mp(1, 1)) == [2]

    @m.define(name="..")
    def compose(f1, f2, arg):
        # (= (.. $f1 $f2 $arg) ($f1 ($f2 $arg)))
        return f1(f2(arg))

    # `compose` is bound in Python and its MeTTa name is `..`, so this body
    # cannot call it by either spelling: a host binding blocks rung 4's map
    # and `..` is not an identifier at all. Rung 5 names it exactly. Same wall
    # as basics/fibsmart, and the same fix would close both: let the resolver
    # read a bound `Defined`'s own MeTTa name.
    @m.define
    def plus1times2():
        # (= (plus1times2) (.. (* 2) (+ 1)))
        return S[".."](S["*"](2), S["+"](1))

    assert m.eval(S.plus1times2(1)) == [4]
