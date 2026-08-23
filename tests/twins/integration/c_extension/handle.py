"""examples/integration/c_extension/handle.metta in Python: an opaque native handle.

A thousand-element C vector reaches MeTTa as ONE value whose contents never
cross: reading an element is a call into C, not a walk over text. The four
predicates arrive through `m.register_prolog(path=, names=)`, and every question
about the vector is `m.fn.<name>(...)`, an ordinary Python call whose argument
is the term that builds the vector, so the handle never leaves the engine.

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

from metta import S, V, equation

#: The two engine libraries the example opens, spelled with their real
#: underscores.
LIB_IMPORT, LIB_FILE = S["lib_import"], S["lib_file"]

#: The build artefact and the Prolog file that loads it, as host paths for a
#: Python door.
HANDLE_SO = Path("examples/integration/c_extension/handle.so")
HANDLE_LOADER_PL = Path("examples/integration/c_extension/handle_loader.pl")

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def twin(m):
    """Make native vectors, read them, bump them, and ask what one is."""
    # Known issue: `import!` has no Python door on the handle. The perfect
    # spelling is `m.import_(target)`, or `m += lib.<name>` for a shipped
    # library (appendix stamp 1), and neither exists yet, so the directive is
    # reached by its own bang name, which performs it where it is written.
    m.fn["import!"](m, S.library(LIB_IMPORT))
    m.fn["import!"](m, S.library(LIB_FILE))

    if not HANDLE_SO.exists():
        # The example prints its skip here. A twin has no door for prose.
        return

    m.register_prolog(
        path=HANDLE_LOADER_PL,
        names=["vector-new", "vector-nth", "vector-bump", "vector-length"],
    )

    # A thousand elements, one value: length and element access are C calls.
    assert m.fn.vector_length(S.vector_new(1000)).one() == 1000
    assert m.fn.vector_nth(S.vector_new(1000), 700).one() == 700

    # The state behind the handle is the native one, so three bumps through
    # three separate calls land on the same memory.
    m += equation(S.bump_thrice()).to(
        S.let(V.v, S.vector_new(4),  # rung: a compiled body cannot name `vector-new` or `vector-bump`, so its `let` stays a term too
              S.progn(S.vector_bump(V.v, 0),
                      S.vector_bump(V.v, 0),
                      S.vector_bump(V.v, 0))))
    assert m.fn.bump_thrice().one() == 3

    # It is an ordinary grounded value, and it compares by identity.
    # `get-metatype` is the atom's own `metatype`, reached without the
    # example's `let`, which exists only because get-metatype does not reduce
    # its argument.
    #
    # Known issue, two halves. The perfect claim is
    # `assert vector.metatype == S.Grounded`, and `metatype` answers the
    # STRING 'Grounded' instead, so the comparison has to read the symbol's
    # own name back. And the design's rule is that an atom's Python class IS
    # its metatype, which would make `isinstance(vector, Grounded)` the whole
    # claim; `Handle.__mro__` is (Handle, Atom, object), so that is False
    # while the engine says Grounded [measured 2026-08-23].
    vector = m.answers(S.vector_new(1)).one()
    assert vector.metatype == S.Grounded.name
    assert m.fn["=="](vector, vector).one() is True
