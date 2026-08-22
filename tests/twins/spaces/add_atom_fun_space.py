"""examples/spaces/add_atom_fun_space.metta in Python: the target is computed.

A function answers a SPACE NAME and the write lands in that space. Nothing has
to create it first: a name is a space the moment it is written to, and the `&`
prefix is what makes it a space name rather than an ordinary symbol.

So the write here does NOT go through `space += atom`. That door takes a
handle, and this example's whole point is a target the program works out for
itself, so the write names the engine's own `add-atom` through `m.fn` and hands
it the CALL `(space)`, unevaluated, exactly where the original hands it
(residue, P14.10). Reading the result is the container door again: iterating
the space the function named is `for atom in space`.
"""

from petta import S, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1826 to 1075, -751 (-41.1%), by the twin contract
#: change: `(test (match (space) $a $a) ...)` became one `assert` over the
#: space's own iteration, so `test` and `match` both left the engine while the
#: equation and the computed-target write stayed in it. Against the example's
#: 4221 the ratio is 0.2547.
#: Prior: 1826, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 1075


def twin(m):
    """Answer a space name from a function, then write into what it names."""
    target = m.space("&my_space_name")

    # (= (space) &my_space_name)
    m += equation(S.space()).to(S[target.space_name])

    # !(add-atom (space) (my test atom))
    m.fn("add-atom")(S.space(), (S.my, S.test, S.atom))

    assert list(target) == [S.my(S.test, S.atom)]
