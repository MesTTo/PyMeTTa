"""Purpose: examples/reasoning/peano.metta in Python: growing a space 300 times.

Each round reads every `(num $t)` in the space and writes `(num (S $t))` back,
refusing a duplicate, so 300 rounds leave 301 atoms. The claim is that count,
and Python counts it: `collapse` is `list()` and `length` is `len()`, so the
whole claim is `len(...) == 301` over the answers the call already hands back.

All four definitions stay at the container door, and each names the construct
that has no compiled spelling:

- `add-atom-no-duplicate` matches against a space its CALLER names, and a
  compiled `match()` takes its space as a literal, never as a parameter;
- `expand-once` is a `case`, which is what Python's `match` statement would
  spell and the subset has no lowering for yet;
- `expandK` and `demo-peano` bind with `let` and `let*` over calls to the two
  names above, which a compiled body reaches only through the function
  namespace, putting back the very indirection the ladder is measuring.

`HERE` is the `(context-space)` term, which is what `&self` means inside a
stored body: the space the equation runs in, resolved when it runs.
"""

from petta import HERE, UNIT, S, V, equation, fn, if_

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1


def twin(m):
    """Expand the space 300 times, then count what is in it."""
    # Nothing is written twice: an atom that already matches is skipped.
    seen = fn.collapse(fn.once(fn.match(V.Space, V.Atom, V.Atom)))  # rung: a compiled match() takes its space as a literal, never as this clause's parameter (P14.4)
    m += equation(S["add-atom-no-duplicate"](V.Space, V.Atom)).to(
        if_(UNIT.eq(seen), fn.add_atom(V.Space, V.Atom), fn.empty())
    )

    # For every existing (num $t), add (num (S $t)).
    m += equation(S["expand-once"]()).to(
        fn.case(fn.match(HERE, S.num(V.t), V.t),  # rung: a `case` over a match, neither of which a compiled body spells (P14.4)
                ((V.x, S["add-atom-no-duplicate"](HERE, S.num(S.S(V.x)))),))
    )

    m += equation(S.expandK(V.n)).to(
        if_(V.n.eq(0), S.done,
            fn.let(V.temp1, S["expand-once"](), S.expandK(V.n - 1)))  # rung: a let over a call a compiled body reaches only through the namespace (P14.4)
    )

    m += equation(S["demo-peano"](V.K)).to(
        fn["let*"](((V.s, fn.add_atom(HERE, S.num(S.Z))), (V.g, S.expandK(V.K))),  # rung: a let* over the same calls (P14.4)
                   fn.match(HERE, S.num(V.stored), V.stored))  # rung: a match INSIDE a stored body, where the subscript door is a Python read (P14.4)
    )

    assert len(m.fn.demo_peano(300)) == 301
