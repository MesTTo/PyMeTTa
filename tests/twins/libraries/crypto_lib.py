"""examples/libraries/crypto_lib.metta in Python: content-addressed facts.

`crypto-hash` is lib_crypto's own function and the subject of the file, so the
twin names it through the function namespace; what it hashes is Python data.

`content-key` stays at the container door. A compiled body reaches a free name
EXACTLY as written and `crypto-hash` is not a name Python can spell, which the
residue table records against P14.4.
"""

from petta import G, S, V, equation

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1

#: The digest of "hello", which the file claims twice: once from the library
#: call and once through the content key built on top of it.
HELLO_SHA256 = G("2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")

HELLO_SHA512 = G(
    "9b71d224bd62f3785d96d46ad3ea3d73319bfbc2890caadae2dff72519673ca7"
    "2323c3d99ba5c11d7c7acc6e14b8c5da0c4663475c2e5c3adef46f73bcdec043"
)


def twin(m):
    """Hash a string two ways, then define a key that hashes its own payload."""
    m.eval(S["import!"](m, S.library(S["lib_crypto"])))

    crypto_hash = m.fn.crypto_hash
    assert crypto_hash(S.sha256, G("hello")) == [HELLO_SHA256]
    assert crypto_hash(S.sha512, G("hello")) == [HELLO_SHA512]

    # A content key: the fact carries the digest of its own payload.
    m += equation(S["content-key"](V.text)).to(S["crypto-hash"](S.sha256, V.text))

    assert m.fn.content_key(G("hello")) == [HELLO_SHA256]
