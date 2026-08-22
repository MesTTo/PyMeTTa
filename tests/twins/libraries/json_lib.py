"""examples/libraries/json_lib.metta in Python: a JSON object IS a space.

That is MeTTa HE's decision and the one worth showing: `json-decode` answers a
SPACE of (key value) atoms rather than an opaque dict, so this twin never
learns a new type. Its keys are the heads of the space's atoms, its lookup is a
subscript, an absent key answers no rows rather than a null, and a nested
object is another space.

`json-decode`, `json-encode` and `dict-space` are the codec under test and stay
named. What dissolves is everything the example wrapped around them: `let` is
assignment, `collapse` is a list, and `get-keys` and `get-value` are what
iterating and subscripting a space already are.

One round trip through a string: a decoded object answers its space NAME, and
the space door takes a name, so the twin says `str()` between them.
"""

from petta import S, V, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 94061 to 87412, -6649 (-7.07%), by the idiomatic
#: rewrite: `get-keys`, `get-value`, the `collapse`s and the `let` chains
#: left the engine for iterating a space, subscripting it and assignment,
#: because a decoded object IS a space; the decoding and encoding stay.
#: Measured min-of-three with the MORK backend linked into this worktree,
#: which the earlier figure may not have been. Prior: 94061 was the last
#: figure for the generator twin that yielded `m.eval(S.test(...))` once per
#: runnable form.
BUDGET = 87412


def twin(m):
    """Decode objects, arrays and scalars, then encode them back."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_json)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    decode, encode = m.fn("json-decode"), m.fn("json-encode")

    def opened(name):
        """The handle for a space json-decode or dict-space answered by name."""
        return m.space(str(name))

    # An object becomes a space, so its keys are the heads of its atoms.
    doc = opened(decode(val('{"a":1,"b":2}')))
    assert [atom[0] for atom in doc] == [S.a, S.b]
    assert doc[S.a(V.v)]["v"] == [1]
    # An absent key answers nothing at all rather than a null.
    assert opened(decode(val('{"a":1}')))[S.missing(V.v)]["v"] == []

    # Arrays become expressions, scalars stay themselves.
    assert list(decode(val("[1,2,3]"))) == [1, 2, 3]
    assert decode(val('"plain"')) == val("plain")
    assert decode(val("42")) == 42
    assert decode(val("true")) is True
    assert decode(val("null")) == S.Null

    # Nesting decodes all the way down, so an inner object is a space too.
    outer = opened(decode(val('{"c":{"d":2}}')))
    inner = opened(outer[S.c(V.v)]["v"][0])
    assert inner[S.d(V.v)]["v"] == [2]

    # Encoding inverts decoding.
    assert list(decode(encode((1, 2, 3)))) == [1, 2, 3]
    assert decode(encode(val("text"))) == val("text")
    assert opened(decode(encode(m.fn("dict-space")(((S.k, 1),)))))[S.k(V.v)]["v"] == [1]

    # dict-space builds one from pairs directly, without going through text.
    pairs = m.fn("dict-space")(((S.name, val("ann")), (S.age, 3)))
    assert opened(pairs)[S.name(V.v)]["v"] == [val("ann")]
