"""The Python twin of examples/libraries/crypto_lib.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 43300


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_crypto))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_crypto"])))

    # !(test (crypto-hash sha256 "hello")
    #        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")
    yield m.eval(
        expr(
            S["test"],
            expr(S["crypto-hash"], S["sha256"], val("hello")),
            val("2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"),
        )
    )

    # !(test (crypto-hash sha512 "hello")
    #        "9b71d224bd62f3785d96d46ad3ea3d73319bfbc2890caadae2dff72519673ca72323c3d99ba5c11d7c7acc6e14b8c5da0c4663475c2e5c3adef46f73bcdec043")
    yield m.eval(
        expr(
            S["test"],
            expr(S["crypto-hash"], S["sha512"], val("hello")),
            val(
                "9b71d224bd62f3785d96d46ad3ea3d73319bfbc2890caadae2dff72519673ca72323c3d99ba5c11d7c7acc6e14b8c5da0c4663475c2e5c3adef46f73bcdec043"
            ),
        )
    )

    # (= (content-key $text) (crypto-hash sha256 $text))
    m += expr(
        S["="], expr(S["content-key"], V["text"]), expr(S["crypto-hash"], S["sha256"], V["text"])
    )

    # !(test (content-key "hello")
    #        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")
    yield m.eval(
        expr(
            S["test"],
            expr(S["content-key"], val("hello")),
            val("2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"),
        )
    )

    yield from ()
