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

Calling is ordinary: `m.fn(name).all(...)` is the door for a function that
answers once per element, which is what a `for` form is for.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4111 to 3628, -483 (-11.7%), by the twin contract
#: change: `(test (collapse (myfun (3 4))) ...)` became one `assert` over
#: `.all()`, so `test` and `collapse` left the engine while the rule, its
#: registration, the expansion it drives and the two answers stayed in it.
#: Against the example's 8639 the ratio is 0.4200.
#: Prior: 4111, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 3628


def twin(m):
    """Register a `for` form, then write a definition that uses it."""
    # (: for (-> Atom Atom Atom %Undefined%))
    m += S[":"](S["for"], S["->"](S.Atom, S.Atom, S.Atom, S["%Undefined%"]))

    # (= (for $var $collection $body) (noeval (let $var (superpose $collection) $body)))
    m += equation(S["for"](V.var, V.collection, V.body)).to(
        S.noeval(S.let(V.var, S.superpose(V.collection), V.body))  # rung: the bound NAME is a parameter here, where Python's assignment binds a name it can see
    )
    m.fn("add-translator-rule!")(S["for"])

    # (= (myfun $L) (for $x $L (if (== (% $x 2) 0) (even $x) (odd $x))))
    parity = S["if"](S["=="](S["%"](V.x, 2), 0), S.even(V.x), S.odd(V.x))  # rung: this `if` is DATA, the third argument of an Atom-typed form
    m += equation(S.myfun(V.items)).to(S["for"](V.x, V.items, parity))

    assert m.fn("myfun").all((3, 4)) == [S.odd(3), S.even(4)]
