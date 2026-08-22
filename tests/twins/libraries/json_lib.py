"""The Python twin of examples/libraries/json_lib.metta.

JSON through lib_json, with MeTTa HE's names. The decision worth noticing is
HE's own and it is the mettafied one: a JSON object decodes into a SPACE of
`(key value)` atoms rather than an opaque dict, so looking a key up is a match
and a decoded document is queryable like any other space.

Every JSON document here is a MeTTa STRING, carried whole through `val(...)`,
which is the door for a Python value that is data rather than a name. The
decoded shapes on the answer side are Python tuples, which is what a MeTTa
expression already is.
"""

from petta import S, V, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 94061 to 94061, +0 (+0.00%), by the P14 twin-style
#: rewrite: no cost moved: this file states no equations of its own, so the
#: rewrite only changed how its terms are SPELLED and the atoms handed to the
#: engine are identical. Prior: ADDED 2026-08-22 at 94061 by the wave-3
#: libraries baseline, which recorded no cause.
BUDGET = 94061


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_json))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_json)))

    # An object becomes a space. get-keys answers one key per solution, the way
    # get-atoms does, so collapse it for a tuple.
    # !(test (let $d (json-decode "{\"a\":1,\"b\":2}") (collapse (get-keys $d)))
    #        (a b))
    yield m.eval(
        S.test(
            S.let(
                V.d,
                S["json-decode"](val('{"a":1,"b":2}')),
                S.collapse(S["get-keys"](V.d)),
            ),
            (S.a, S.b),
        )
    )
    # !(test (let $d (json-decode "{\"a\":1,\"b\":2}") (get-value $d a)) 1)
    yield m.eval(
        S.test(
            S.let(
                V.d,
                S["json-decode"](val('{"a":1,"b":2}')),
                S["get-value"](V.d, S.a),
            ),
            1,
        )
    )
    # An absent key answers nothing at all, so you test it with a match.
    # !(test (let $d (json-decode "{\"a\":1}") (collapse (get-value $d missing))) ())
    yield m.eval(
        S.test(
            S.let(
                V.d,
                S["json-decode"](val('{"a":1}')),
                S.collapse(S["get-value"](V.d, S.missing)),
            ),
            (),
        )
    )

    # Arrays become expressions, scalars stay themselves.
    # !(test (json-decode "[1,2,3]") (1 2 3))
    yield m.eval(S.test(S["json-decode"](val("[1,2,3]")), (1, 2, 3)))
    # !(test (json-decode "\"plain\"") "plain")
    yield m.eval(S.test(S["json-decode"](val('"plain"')), val("plain")))
    # !(test (json-decode "42") 42)
    yield m.eval(S.test(S["json-decode"](val("42")), 42))
    # !(test (json-decode "true") True)
    yield m.eval(S.test(S["json-decode"](val("true")), TRUE))
    # !(test (json-decode "null") Null)
    yield m.eval(S.test(S["json-decode"](val("null")), S.Null))

    # Nesting decodes all the way down, so an inner object is a space too.
    # !(test (let $outer (json-decode "{\"c\":{\"d\":2}}")
    #          (let $inner (get-value $outer c) (get-value $inner d)))
    #        2)
    yield m.eval(
        S.test(
            S.let(
                V.outer,
                S["json-decode"](val('{"c":{"d":2}}')),
                S.let(
                    V.inner,
                    S["get-value"](V.outer, S.c),
                    S["get-value"](V.inner, S.d),
                ),
            ),
            2,
        )
    )

    # Encoding inverts decoding.
    # !(test (json-decode (json-encode (1 2 3))) (1 2 3))
    yield m.eval(
        S.test(S["json-decode"](S["json-encode"]((1, 2, 3))), (1, 2, 3))
    )
    # !(test (json-decode (json-encode "text")) "text")
    yield m.eval(
        S.test(
            S["json-decode"](S["json-encode"](val("text"))), val("text")
        )
    )
    # !(test (let $d (json-decode (json-encode (dict-space ((k 1))))) (get-value $d k))
    #        1)
    yield m.eval(
        S.test(
            S.let(
                V.d,
                S["json-decode"](
                    S["json-encode"](S["dict-space"](((S.k, 1),)))
                ),
                S["get-value"](V.d, S.k),
            ),
            1,
        )
    )

    # dict-space builds one from pairs directly, without going through text.
    # !(test (let $d (dict-space ((name "ann") (age 3))) (get-value $d name)) "ann")
    yield m.eval(
        S.test(
            S.let(
                V.d,
                S["dict-space"](((S.name, val("ann")), (S.age, 3))),
                S["get-value"](V.d, S.name),
            ),
            val("ann"),
        )
    )
