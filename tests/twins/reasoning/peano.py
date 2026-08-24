"""Purpose: examples/reasoning/peano.metta in Python: growing a space 300 times.

Each round reads every `(num $t)` in the space and writes `(num (S $t))` back,
refusing a duplicate, so 300 rounds leave 301 atoms. The claim is that count,
and Python counts it: `collapse` is `list()` and `length` is `len()`, and a
lazy answer view counts through the engine without pulling an atom into Python.

All four definitions are compiled now, and each one is the Python statement its
MeTTa form already was. An assignment is `let`; a statement sequence is `let*`;
`if`/`else` is the conditional; a `case` with one capturing arm is an ordinary
binding. Only `collapse` still declares a rung, because the dissolution table
sends it to `list()` and a compiled body has no lowering for that.

`&self` inside a stored body is the ambient space, and bare `match(pattern,
template)` is what reads it: the one-pattern form lowers to
`(match (context-space) ...)`. Where the example passes `&self` as an ARGUMENT
the handle itself crosses, because a space is a grounded atom wherever a term
wants one.

`expandK` keeps its camelCase head through the explicit `name=`, because the
implicit name is the mechanical image and `def expand_k` would install
`expand-k`, a different head from the one the example makes matchable.
"""

from metta import S, V, fn, match, superpose

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Expand the space 300 times, then count what is in it."""

    @m.define
    def add_atom_no_duplicate(space, atom):
        """Write the atom unless the space already answers a match for it."""
        # (= (add-atom-no-duplicate $Space $Atom)
        #    (if (== () (collapse (once (match $Space $Atom $Atom))))
        #        (add-atom $Space $Atom)
        #        (empty)))
        seen = S.collapse(S.once(match(space, atom, atom)))  # rung: `collapse` is list(), which a compiled body has no lowering for (P14.4)
        if seen == ():
            return fn.add_atom(space, atom)
        return superpose()

    @m.define
    def expand_once():
        """For every existing (num $t), add (num (S $t))."""
        # (= (expand-once)
        #    (case (match &self (num $t) $t)
        #          (($x (add-atom-no-duplicate &self (num (S $x)))))))
        found = match(S.num(V.t), V.t)
        return add_atom_no_duplicate(m, S.num(S.S(found)))

    @m.define(name="expandK")
    def expand_k(n):
        """Run expand-once n times, then answer done."""
        # (= (expandK $n)
        #    (if (== $n 0) done (let $temp1 (expand-once) (expandK (- $n 1)))))
        if n == 0:
            return S.done
        _round = expand_once()
        return expand_k(n - 1)

    @m.define
    def demo_peano(k):
        """Seed the space with Z, expand it k times, and read every number."""
        # (= (demo-peano $K)
        #    (let* (($s (add-atom &self (num Z))) ($g (expandK $K)))
        #          (match &self (num $1) $1)))
        _seeded = fn.add_atom(m, S.num(S.Z))
        _grown = expand_k(k)
        return match(S.num(V.stored), V.stored)

    # !(test (length (collapse (demo-peano 300))) 301)
    assert len(demo_peano(300)) == 301
