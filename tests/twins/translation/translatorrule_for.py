"""examples/translation/translatorrule_for.metta in Python: adding a form to the language.

`for` is not a builtin here; it is three lines of MeTTa registered as a
translator rule, after which `(for $x $L body)` expands at compile time into a
`let` over a superposition. So the example is about writing a binding form, and
the form it writes is the one Python spells with `for ... in`.

Both equations are terms. The rule's own body binds a variable the CALLER
supplies, `(let $var (superpose $collection) $body)`, where the bound name is
held in a parameter and Python's assignment binds a name it can see; and
`myfun`'s body carries `even` and `odd` as lowercase data constructors, which a
compiled body reads as calls (residue, P14.4).

Calling is ordinary: `m.fn.myfun(...)` answers once per element, which is
what a `for` form is for, and the answers compare as the sequence they are.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def twin(m):
    """Register a `for` form, then write a definition that uses it."""
    # (: for (-> Atom Atom Atom %Undefined%))
    m += S[":"](S["for"], S["->"](S.Atom, S.Atom, S.Atom, S["%Undefined%"]))

    # (= (for $var $collection $body) (noeval (let $var (superpose $collection) $body)))
    m += equation(S["for"](V.var, V.collection, V.body)).to(
        S.noeval(S.let(V.var, S.superpose(V.collection), V.body))  # rung: the bound NAME is a parameter here, where Python's assignment binds a name it can see
    )
    # Known issue: a call through the function namespace answers a LAZY view,
    # so the perfect statement-level spelling of a directive,
    # `m.fn.add_translator_rule(head)`, REGISTERS NOTHING until something pulls
    # its answers [measured 2026-08-23: the rule fires only after list() of the
    # view]. The term door evaluates eagerly, so a directive is written that
    # way until a side-effecting call runs at statement level.
    m.eval(S["add-translator-rule!"](S["for"]))

    # (= (myfun $L) (for $x $L (if (== (% $x 2) 0) (even $x) (odd $x))))
    parity = S["if"](S["=="](S["%"](V.x, 2), 0), S.even(V.x), S.odd(V.x))  # rung: this `if` is DATA, the third argument of an Atom-typed form
    m += equation(S.myfun(V.items)).to(S["for"](V.x, V.items, parity))

    assert m.fn.myfun((3, 4)) == [S.odd(3), S.even(4)]
