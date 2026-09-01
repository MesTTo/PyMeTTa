"""examples/ch08-data/08-03-the-shipped-libraries/05-json_lib.metta in Python: a JSON object IS a space.

That is MeTTa HE's decision and the one worth showing: `json-decode` answers a
SPACE of (key value) atoms rather than an opaque dict, so this twin never
learns a new type. Its keys are the heads of the space's atoms, its lookup is a
subscript, an absent key answers no rows rather than a null, and a nested
object is another space.

`json-decode`, `json-encode` and `dict-space` are the codec under test and stay
named. What dissolves is everything the example wrapped around them: `let` is
assignment, `collapse` is a list, and `get-keys` and `get-value` are what
iterating and subscripting a space already are.

A decoded object answers its space NAME as a Symbol, which is what the space
door takes, so `opened` is `metta.space(answers.one())` with nothing between
them and no name ever spelled as text.
"""

import metta
from metta import G, S, V, lib


def twin(m):
    """Decode objects, arrays and scalars, then encode them back."""
    m += lib.json

    decode, encode = m.fn.json_decode, m.fn.json_encode

    def opened(answers):
        """The handle for the space json-decode or dict-space answered by name."""
        return metta.space(answers.one())

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
    inner = metta.space(nested)
    assert [row.v for row in inner[S.d(V.v)]] == [2]

    # Encoding inverts decoding.
    assert list(decode(encode((1, 2, 3))).one()) == [1, 2, 3]
    assert decode(encode(G("text"))) == [G("text")]
    round_trip = opened(decode(encode(m.fn.dict_space(((S.k, 1),)))))
    assert [row.v for row in round_trip[S.k(V.v)]] == [1]

    # dict-space builds one from pairs directly, without going through text.
    pairs = opened(m.fn.dict_space(((S.name, G("ann")), (S.age, 3))))
    assert [row.v for row in pairs[S.name(V.v)]] == [G("ann")]


#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 64654 to 64977, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 64977 to 64986, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 64986 to 65020, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
#: RE-PINNED 2026-08-25, 65020 to 65022, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 65022 to 64464 (-558), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-09-01, 64464 to 61410 (-3054), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 61410 to 61376 (-34), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 61376 to 61490 (+114), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
BUDGET = 61490
