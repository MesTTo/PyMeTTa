"""The Python twin of examples/spaces/parametric_spaces.metta: a space named by an expression.

A ground expression is a space name, so `(cache &primary-kb 100)` and
`(cache &secondary-kb 10)` are two isolated spaces carrying their own parameters,
and `context-space` inside an equation reads whichever instance owns it. Pattern
destructuring is the parameter surface, so there is no second parameter builtin.

Every form here is a TERM, and it is the one file in this folder where that is
the whole story rather than a detail: `petta.space(name)` refuses anything that
does not begin with `&` ("a space name starts with &, as in &self or &kb"), so a
space named by a ground expression has NO handle, and with no handle there is no
`+=` and no `.eval`. The residue files it against P14.10. The equation the two
spaces share is built once as a Python value and written twice, which is the one
thing the Python side does add here.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 8400 across the P14 twin-style rewrite: every form is the
#: same term it was, spelled with named symbols and tuples instead of nested
#: expr() calls, and naming the shared cache-config equation once writes the
#: same atom twice. Measured 8400 before and after.
#: Prior: ADDED 2026-08-22 at 8400 by the wave-3 spaces baseline.
BUDGET = 8400


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    new_space, add = S["new-space"], S["add-atom"]
    primary = S.cache(S["&primary-kb"], 100)
    secondary = S.cache(S["&secondary-kb"], 10)

    # !(new-space (cache &primary-kb 100))
    yield m.eval(new_space(primary))
    # !(new-space (cache &secondary-kb 10))
    yield m.eval(new_space(secondary))

    # The same equation reads the identifier of whichever instance owns it.
    # (= (cache-config)
    #    (let (cache $base $limit) (context-space) (config $base $limit)))
    config = equation(S["cache-config"]()).to(
        S.let(
            S.cache(V.base, V.limit),
            S["context-space"](),
            S.config(V.base, V.limit),
        )
    )

    # !(add-atom (cache &primary-kb 100) (= (cache-config) ...))
    yield m.eval(add(primary, config))
    # !(add-atom (cache &secondary-kb 10) (= (cache-config) ...))
    yield m.eval(add(secondary, config))

    # !(add-atom (cache &primary-kb 100) (entry primary))
    yield m.eval(add(primary, S.entry(S.primary)))
    # !(add-atom (cache &secondary-kb 10) (entry secondary))
    yield m.eval(add(secondary, S.entry(S.secondary)))

    # !(test (evalc (cache-config) (cache &primary-kb 100)) (config &primary-kb 100))
    yield m.eval(
        S.test(
            S.evalc(S["cache-config"](), primary),
            S.config(S["&primary-kb"], 100),
        )
    )
    # !(test (evalc (cache-config) (cache &secondary-kb 10)) (config &secondary-kb 10))
    yield m.eval(
        S.test(
            S.evalc(S["cache-config"](), secondary),
            S.config(S["&secondary-kb"], 10),
        )
    )

    # Each instance holds its own atoms.
    # !(test (collapse (match (cache &primary-kb 100) (entry $which) $which)) (primary))
    yield m.eval(
        S.test(
            S.collapse(S.match(primary, S.entry(V.which), V.which)),
            (S.primary,),
        )
    )
    # !(test (collapse (match (cache &secondary-kb 10) (entry $which) $which)) (secondary))
    yield m.eval(
        S.test(
            S.collapse(S.match(secondary, S.entry(V.which), V.which)),
            (S.secondary,),
        )
    )

    # !(test (get-type (cache &primary-kb 100)) SpaceType)
    yield m.eval(S.test(S["get-type"](primary), S.SpaceType))
