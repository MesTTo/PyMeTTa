"""examples/libraries/crypto_lib.metta in Python: content-addressed facts.

`crypto-hash` is lib_crypto's own function and the subject of the file, so the
twin names it; what it hashes is Python data.

`content-key` stays at the container door. A compiled body reaches a free name
EXACTLY as written and `crypto-hash` is not a name Python can spell, which the
residue table records against P14.4.
"""

from petta import S, V, equation, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 43300 to 40428, -2872 (-6.63%), by the idiomatic
#: rewrite: three `test` wrappers left the engine for `assert`; the two
#: library hashes and the one stored equation are the whole of what remains.
#: Measured min-of-three with the MORK backend linked into this worktree,
#: which the earlier figure may not have been. Prior: 43300 was the last
#: figure for the generator twin that yielded `m.eval(S.test(...))` once per
#: runnable form.
BUDGET = 40428

#: The digest of "hello", which the file claims twice: once from the library
#: call and once through the content key built on top of it.
HELLO_SHA256 = val("2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")

HELLO_SHA512 = val(
    "9b71d224bd62f3785d96d46ad3ea3d73319bfbc2890caadae2dff72519673ca7"
    "2323c3d99ba5c11d7c7acc6e14b8c5da0c4663475c2e5c3adef46f73bcdec043"
)


def twin(m):
    """Hash a string two ways, then define a key that hashes its own payload."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_crypto)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    crypto_hash = m.fn("crypto-hash")
    assert crypto_hash(S.sha256, val("hello")) == HELLO_SHA256
    assert crypto_hash(S.sha512, val("hello")) == HELLO_SHA512

    # A content key: the fact carries the digest of its own payload.
    m += equation(S["content-key"](V.text)).to(S["crypto-hash"](S.sha256, V.text))

    assert m.fn("content-key")(val("hello")) == HELLO_SHA256
