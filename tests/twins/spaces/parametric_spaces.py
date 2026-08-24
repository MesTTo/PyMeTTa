"""Purpose: examples/spaces/parametric_spaces.metta in Python: a space named by an expression.

`(cache &primary-kb 100)` is a ground expression used as a SPACE NAME, so two
instances of the same shape are two isolated spaces, and the same equation in
each reads its own parameters back out of `context-space`. Pattern
destructuring is the parameter surface, which is why no parameter builtin
exists.

Every door here is the container door now. `metta.space(name)` takes an ATOM as
the name, so a parameterised space has a handle like any other space and `+=`,
`space[pattern]`, `space.eval(term)` and `space.type(atom)` all work here
exactly as they work everywhere else
[measured 2026-08-24: `metta.space(S.cache(S["&primary-kb"], 100))` answers a
handle whose two instances stay isolated; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. The two base names
stay symbols because that is what they are: `&primary-kb` is a PARAMETER of the
space's name and never denotes a space of its own in this program.

The equation is the one thing still written as a term: its body binds by
DESTRUCTURING a pattern, `(let (cache $base $limit) (context-space) ...)`, and
Python's own assignment is what `let` becomes only when the target is a name
(residue, P14.4). PERFECT: `solve(S.cache(V.base, V.limit), fn.context_space())`
inside a compiled body, the expression-position function the guide rules for
exactly this case; measured 2026-08-24, a body naming `solve` is refused,
"'solve' is not a parameter of cache-config, not a function the engine knows"
[commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
"""

import metta
from metta import S, V, equation, fn

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
BUDGET = 1

#: The two base names, which are parameters of a space's name rather than
#: spaces: nothing in the program ever writes to `&primary-kb` itself.
PRIMARY, SECONDARY = S["&primary-kb"], S["&secondary-kb"]  # rung: a parameter of a space name, not a space


def twin(m):
    """Make two instances of one cache shape, and read each one's parameters."""
    primary = metta.space(S.cache(PRIMARY, 100))
    secondary = metta.space(S.cache(SECONDARY, 10))

    # The same equation reads the identifier of whichever instance owns it.
    config = equation(S.cache_config()).to(
        S.let(S.cache(V.base, V.limit), fn.context_space(), S.config(V.base, V.limit))  # rung: a let that DESTRUCTURES has no assignment spelling
    )
    primary += config
    secondary += config

    primary += S.entry(S.primary)
    secondary += S.entry(S.secondary)

    assert primary.eval(S.cache_config()) == [S.config(PRIMARY, 100)]
    assert secondary.eval(S.cache_config()) == [S.config(SECONDARY, 10)]

    assert [row.which for row in primary[S.entry(V.which)]] == [S.primary]
    assert [row.which for row in secondary[S.entry(V.which)]] == [S.secondary]

    assert m.type(primary) == S.SpaceType
