"""The Python twin of examples/libraries/crypto_lib.metta.

Content-addressed facts: a fact that carries the digest of its own payload.

`(= (content-key $text) (crypto-hash sha256 $text))` stays at the container door
because a compiled body reaches a free name EXACTLY as written, and `crypto-hash`
is not a name Python can spell; the residue table records that against P14.4.
"""

from petta import S, V, equation, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 43300 to 43300, +0 (+0.00%), by the P14 twin-style
#: rewrite: the twin's atoms are unchanged: content-key stays a
#: container-door equation because its body calls a hyphenated name, and
#: equation(...).to(...) builds what S["="](...) built. Prior: ADDED
#: 2026-08-22 at 43300 by the wave-3 libraries baseline, which recorded no
#: cause.
BUDGET = 43300

#: The digest of "hello", which the file asserts twice: once from the library
#: call and once through the content key built on top of it.
HELLO_SHA256 = val(
    "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
)


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_crypto))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_crypto)))

    # !(test (crypto-hash sha256 "hello") "2cf24dba...")
    yield m.eval(
        S.test(S["crypto-hash"](S.sha256, val("hello")), HELLO_SHA256)
    )
    # !(test (crypto-hash sha512 "hello") "9b71d224...")
    yield m.eval(
        S.test(
            S["crypto-hash"](S.sha512, val("hello")),
            val(
                "9b71d224bd62f3785d96d46ad3ea3d73319bfbc2890caadae2dff72519673ca"
                "72323c3d99ba5c11d7c7acc6e14b8c5da0c4663475c2e5c3adef46f73bcdec043"
            ),
        )
    )

    # A content key: the fact carries the digest of its own payload.
    # (= (content-key $text) (crypto-hash sha256 $text))
    m += equation(S["content-key"](V.text)).to(
        S["crypto-hash"](S.sha256, V.text)
    )

    # !(test (content-key "hello") "2cf24dba...")
    yield m.eval(S.test(S["content-key"](val("hello")), HELLO_SHA256))
