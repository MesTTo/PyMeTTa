"""examples/translation/translatorrule_for.metta in Python: adding a form to the language.

`for` is not a builtin here; it is one equation registered as a translator
rule, after which `(for $var $collection $body)` expands at compile time into a
`let` over a superposition. So the example is about writing a binding form, and
the form it writes is the one Python spells with `for ... in`.

Both definitions compile. `for` is a Python keyword, so the head is named
explicitly and the def carries a spellable Python name; its three parameters
are annotated `Atom`, which is the declaration `(: for (-> Atom Atom Atom
%Undefined%))` said in Python's own notation and is what makes each argument
arrive unreduced. That annotation is load-bearing rather than decorative:
without it the collection and the body reduce before the `let` binds anything,
and the modulus in the body then runs on an unbound name.

`myfun`'s body mentions the new form and hands it three arguments: a variable
to bind, the collection, and the template. The template is Python's conditional
expression, which lowers to the engine's own `if`, so nothing there is written
as a term that Python can spell.
"""

from typing import Any

from metta import Atom, S, V

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Register a `for` form, then write a definition that uses it."""

    @m.define(name="for")
    def for_form(var: Atom, collection: Atom, body: Atom) -> Any:
        # (= (for $var $collection $body)
        #    (noeval (let $var (superpose $collection) $body)))
        return S.noeval(S.let(var, S.superpose(collection), body))  # rung: the bound NAME arrives in a parameter, where Python's assignment binds a name it can see

    m.fn.add_translator_rule(S["for"])       # (add-translator-rule! for)

    @m.define
    def myfun(items):
        # (= (myfun $L) (for $x $L (if (== (% $x 2) 0) (even $x) (odd $x))))
        return S["for"](
            V.x, items, S.even(V.x) if V.x % 2 == 0 else S.odd(V.x)
        )

    assert myfun((3, 4)) == [S.odd(3), S.even(4)]   # ((odd 3) (even 4))
