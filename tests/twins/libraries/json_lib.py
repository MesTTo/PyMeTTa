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

A decoded object answers its space NAME as a Symbol, and the space door takes
a Symbol as readily as a string, so `opened` is `petta.space(answers.one())`
with nothing between them.
"""

import petta
from petta import G, S, V

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1


def twin(m):
    """Decode objects, arrays and scalars, then encode them back."""
    m.fn["import!"](m, S.library(S["lib_json"]))

    decode, encode = m.fn.json_decode, m.fn.json_encode

    def opened(answers):
        """The handle for the space json-decode or dict-space answered by name."""
        return petta.space(answers.one())

    # An object becomes a space, so its keys are the heads of its atoms.
    doc = opened(decode(G('{"a":1,"b":2}')))
    assert [atom[0] for atom in doc] == [S.a, S.b]
    assert [row.v for row in doc[S.a(V.v)]] == [1]
    # An absent key answers nothing at all rather than a null.
    assert [row.v for row in opened(decode(G('{"a":1}')))[S.missing(V.v)]] == []

    # Arrays become expressions, scalars stay themselves.
    assert list(decode(G("[1,2,3]")).one()) == [1, 2, 3]
    assert decode(G('"plain"')) == [G("plain")]
    assert decode(G("42")) == [42]
    assert decode(G("true")) == [True]
    assert decode(G("null")) == [S.Null]

    # Nesting decodes all the way down, so an inner object is a space too.
    outer = opened(decode(G('{"c":{"d":2}}')))
    [nested] = [row.v for row in outer[S.c(V.v)]]
    inner = petta.space(nested)
    assert [row.v for row in inner[S.d(V.v)]] == [2]

    # Encoding inverts decoding.
    assert list(decode(encode((1, 2, 3))).one()) == [1, 2, 3]
    assert decode(encode(G("text"))) == [G("text")]
    round_trip = opened(decode(encode(m.fn.dict_space(((S.k, 1),)))))
    assert [row.v for row in round_trip[S.k(V.v)]] == [1]

    # dict-space builds one from pairs directly, without going through text.
    pairs = opened(m.fn.dict_space(((S.name, G("ann")), (S.age, 3))))
    assert [row.v for row in pairs[S.name(V.v)]] == [G("ann")]
