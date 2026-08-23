"""Purpose: examples/spaces/parametric_spaces.metta in Python: a space named by an expression.

`(cache &primary-kb 100)` is a ground expression used as a SPACE NAME, so two
instances of the same shape are two isolated spaces, and the same equation in
each reads its own parameters back out of `context-space`. Pattern
destructuring is the parameter surface, which is why no parameter builtin
exists.

This is the one example in the folder where the container doors cannot be used
at all: `metta.space(name)` takes a `&`-prefixed string and refuses a
parenthesised one, so a space named by an expression has no handle and every
door here goes through the engine's own functions with the naming TERM in the
space position (residue, P14.10). PERFECT: `metta.space(S.cache(PRIMARY, 100))`,
the creation door taking an ATOM as the name, after which every container door
works here as it does everywhere else. The two base names are symbols for the
same reason.

The equation is at the container door as well: its body binds by DESTRUCTURING
a pattern, `(let (cache $base $limit) (context-space) ...)`, and Python's own
assignment is what `let` becomes only when the target is a name (residue,
P14.4). PERFECT: unpacking, `_, base, limit = fn.context_space()`, which is what
Python spells structure-over-a-value-in-hand with.

`get-type` is the one door here that HAS a Python spelling now: `space.type(a)`
is the accessor, so the closing claim is an ordinary method call.
"""

from metta import S, V, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=133aaa81396e8587d496a1e31b78c38741dbd2f4].
BUDGET = 1

#: The two base names. A space named by a ground EXPRESSION has no handle door,
#: so its base name is a symbol here rather than a `metta.space(...)` handle.
PRIMARY, SECONDARY = S["&primary-kb"], S["&secondary-kb"]  # rung: no handle door for a parameterised space name


def twin(m):
    """Make two instances of one cache shape, and read each one's parameters."""
    primary, secondary = S.cache(PRIMARY, 100), S.cache(SECONDARY, 10)
    new_space, add = m.fn["new-space"], m.fn["add-atom"]
    match, evalc = m.fn["match"], m.fn["evalc"]

    new_space(primary).one()
    new_space(secondary).one()

    # The same equation reads the identifier of whichever instance owns it.
    config = equation(S["cache-config"]()).to(
        S.let(S.cache(V.base, V.limit), S["context-space"](), S.config(V.base, V.limit))  # rung: a let that DESTRUCTURES has no assignment spelling
    )
    add(primary, config).one()  # rung: the target is a naming TERM, so `space += atom` has no handle to take
    add(secondary, config).one()  # rung: as above

    add(primary, S.entry(S.primary)).one()  # rung: as above
    add(secondary, S.entry(S.secondary)).one()  # rung: as above

    assert evalc(S["cache-config"](), primary).one() == S.config(PRIMARY, 100)
    assert evalc(S["cache-config"](), secondary).one() == S.config(SECONDARY, 10)

    # A call carrying a caller variable answers rows, so the claim reads the
    # projection rather than the row.
    assert match(primary, S.entry(V.which), V.which).which == [S.primary]  # rung: as above, and the subscript door needs a handle too
    assert match(secondary, S.entry(V.which), V.which).which == [S.secondary]  # rung: as above

    assert m.type(primary) == S.SpaceType
