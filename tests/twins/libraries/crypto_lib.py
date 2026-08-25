"""examples/libraries/crypto_lib.metta in Python: content-addressed facts.

`crypto-hash` is lib_crypto's own function and the subject of the file, so the
twin names it through the function namespace; what it hashes is Python data.

`content-key` is an ordinary compiled definition. Its body calls a hyphenated
library function, which the STATIC `fn` namespace spells: inside a compiled
body `fn.crypto_hash(...)` is read as syntax and emits `(crypto-hash ...)`,
where the bound `m.fn` would be a host attribute the body cannot close over.
"""

from metta import G, S, fn, lib

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 28618 to 28694, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 28694 to 28708, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 28708 to 28683, on the release tree:
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
BUDGET = 28683

#: The digest of "hello", which the file claims twice: once from the library
#: call and once through the content key built on top of it.
HELLO_SHA256 = G("2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")

HELLO_SHA512 = G(
    "9b71d224bd62f3785d96d46ad3ea3d73319bfbc2890caadae2dff72519673ca7"
    "2323c3d99ba5c11d7c7acc6e14b8c5da0c4663475c2e5c3adef46f73bcdec043"
)


def twin(m):
    """Hash a string two ways, then define a key that hashes its own payload."""
    m += lib.crypto

    crypto_hash = m.fn.crypto_hash
    assert crypto_hash(S.sha256, G("hello")) == [HELLO_SHA256]
    assert crypto_hash(S.sha512, G("hello")) == [HELLO_SHA512]

    @m.define
    def content_key(text):
        # (= (content-key $text) (crypto-hash sha256 $text))
        return fn.crypto_hash(S.sha256, text)

    assert content_key(G("hello")) == [HELLO_SHA256]
