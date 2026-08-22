"""examples/integration/c_extension/handle.metta in Python: an opaque native handle.

A thousand-element C vector reaches MeTTa as ONE value whose contents never
cross: reading an element is a call into C, not a walk over text. The four
predicates arrive through `m.register_prolog(path=, names=)`, and every question
about the vector is `m.fn(name)(...)`, an ordinary Python call whose argument is
the term that builds the vector, so the handle never leaves the engine.

Two claims dissolve. `get-metatype` is `atom.metatype`, a property of the atom
Python already holds, and the example's `let` around it exists only because
`get-metatype` does not reduce its argument, which a Python name does not need
to be told. The identity claim stays a term, because MeTTa's `==` on a grounded
value is what the example is asking about and Python comparing a name with
itself would be asking something else.

`bump-thrice` stays at the container door: its body names `vector-new` and
`vector-bump`, and a compiled body names a function by exactly its MeTTa
spelling, which neither of those is a Python identifier for (residue, P14.4).
"""

from pathlib import Path

from petta import S, V, equation, val

#: The space the imports write.
SELF = S["&self"]  # rung: no import door hangs off the space handle

#: The build artefact and the Prolog file that loads it. Marked data because a
#: twin may not write a bare string; `.value` is the path a Python door takes.
HANDLE_SO = Path(val("examples/integration/c_extension/handle.so").value)
HANDLE_LOADER_PL = Path(val("examples/integration/c_extension/handle_loader.pl").value)

#: The four predicates handle.c exports, named once.
VECTOR_OPS = [S["vector-new"], S["vector-nth"], S["vector-bump"], S["vector-length"]]

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 105529 to 101395, -4134 (-3.92%), by the twin contract
#: change: six `if`/`file-exists` guards, five `test` wrappers, two `let`
#: bindings and a `get-metatype` left the engine for Python's own `if`,
#: `Path.exists()`, `assert`, a Python name and `atom.metatype`, which reads a
#: property of an atom already in hand at no engine cost at all. The C calls did
#: not move. Against the example's 118550 the ratio is 0.8553 [measured
#: 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/integration/c_extension/handle.metta`, with handle.so built by
#: check.sh's own `swipl-ld` line]. Prior: ADDED 2026-08-22 at 105529 by the
#: wave-3 twin baseline, which priced a transliteration.
BUDGET = 101395


def twin(m):
    """Make native vectors, read them, bump them, and ask what one is."""
    m.eval(S["import!"](SELF, S.library(S.lib_import)))
    m.eval(S["import!"](SELF, S.library(S.lib_file)))

    if not HANDLE_SO.exists():
        # The example prints its skip here. A twin has no door for prose.
        return

    m.register_prolog(path=HANDLE_LOADER_PL, names=[op.name for op in VECTOR_OPS])

    # A thousand elements, one value: length and element access are C calls.
    assert m.fn("vector-length")(S["vector-new"](1000)) == 1000
    assert m.fn("vector-nth")(S["vector-new"](1000), 700) == 700

    # The state behind the handle is the native one, so three bumps through
    # three separate calls land on the same memory.
    m += equation(S["bump-thrice"]()).to(
        S.let(V.v, S["vector-new"](4),  # rung: a compiled body cannot name `vector-new` or `vector-bump`, so its `let` stays a term too
              S.progn(S["vector-bump"](V.v, 0),
                      S["vector-bump"](V.v, 0),
                      S["vector-bump"](V.v, 0))))
    assert m.fn("bump-thrice")() == 3

    # It is an ordinary grounded value, and it compares by identity.
    # `get-metatype` is the atom's own `metatype`, reached without the
    # example's `let`, which exists only because get-metatype does not reduce
    # its argument. Two frictions show here: `metatype` answers a NAME rather
    # than the symbol, and `Handle` is not a `Gnd` subclass, so the design's
    # "the Python class IS the metatype" rule does not hold for a handle.
    vector = m.one(S["vector-new"](1))
    assert vector.metatype == S.Grounded.name
    assert m.eval(S["=="](vector, vector)) == [True]
