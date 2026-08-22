"""examples/spaces/parametric_spaces.metta in Python: a space named by an expression.

`(cache &primary-kb 100)` is a ground expression used as a SPACE NAME, so two
instances of the same shape are two isolated spaces, and the same equation in
each reads its own parameters back out of `context-space`. Pattern
destructuring is the parameter surface, which is why no parameter builtin
exists.

This is the one example in the folder where the container doors cannot be used
at all: `m.space(name)` takes a `&`-prefixed string and refuses a parenthesised
one, so a space named by an expression has no handle and every door here goes
through `m.fn` with the naming TERM in the space position (residue, P14.10).
The two base names are symbols for the same reason.

The equation is at the container door as well: its body binds by DESTRUCTURING
a pattern, `(let (cache $base $limit) (context-space) ...)`, and Python's own
assignment is what `let` becomes only when the target is a name (residue,
P14.4).
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 8400 to 7221, -1179 (-14.0%), by the twin contract
#: change: five `(test ...)` terms became five Python `assert`s, so the `test`
#: wrapper left the engine five times and two `collapse`s went with it, while
#: both `evalc`s, both matches, the `get-type` question and every write stayed.
#: Against the example's 17000 the ratio is 0.4248.
#: Prior: 8400, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 7221

#: The two base names. A space named by a ground EXPRESSION has no handle door,
#: so its base name is a symbol here rather than a `m.space(...)` handle.
PRIMARY, SECONDARY = S["&primary-kb"], S["&secondary-kb"]  # rung: no handle door for a parameterised space name


def twin(m):
    """Make two instances of one cache shape, and read each one's parameters."""
    primary, secondary = S.cache(PRIMARY, 100), S.cache(SECONDARY, 10)
    new_space, add, match = m.fn("new-space"), m.fn("add-atom"), m.fn("match")

    new_space(primary)
    new_space(secondary)

    # The same equation reads the identifier of whichever instance owns it.
    config = equation(S["cache-config"]()).to(
        S.let(S.cache(V.base, V.limit), S["context-space"](), S.config(V.base, V.limit))  # rung: a let that DESTRUCTURES has no assignment spelling
    )
    add(primary, config)
    add(secondary, config)

    add(primary, S.entry(S.primary))
    add(secondary, S.entry(S.secondary))

    assert m.fn("evalc")(S["cache-config"](), primary) == S.config(PRIMARY, 100)
    assert m.fn("evalc")(S["cache-config"](), secondary) == S.config(SECONDARY, 10)

    assert match.all(primary, S.entry(V.which), V.which) == [S.primary]
    assert match.all(secondary, S.entry(V.which), V.which) == [S.secondary]

    assert m.fn("get-type")(primary) == S.SpaceType
