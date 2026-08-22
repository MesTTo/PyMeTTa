"""examples/integration/c_space/c_space.metta in Python: a space whose atoms live in C.

`cstore.c` holds the atoms and `cstore.pl` puts four clauses on the foreign-space
seam, so `&cstore` is a space like any other and nothing above it knows there is
a C backend. That is exactly why this twin reads like the spaces twins: the
store is a handle, `store += atom` writes, `store[pattern]` matches, and
`store -= atom` takes one unifying occurrence away, which is what `remove-atom`
means everywhere.

The provider file is consulted through `m.register_prolog(path=)`, the Python
door for what the example spells `(let "cstore.pl" (consult_global) provider)`.

Two things do not dissolve. `check-space-provider` is the seam's own proof
harness and the Python compliance kit beside it, `petta.testing`, reaches only
Python providers, so the C provider is checkable only through the MeTTa door,
which names the space as a symbol. And the concurrent-writer form is DECLINED:
`hyperpose` runs its branches on real threads and the completion schedule moves
the inference count, which the residue records against P14.14.
"""

from pathlib import Path

from petta import S, V, val

#: The space the imports write, and the C-backed space they are for.
SELF = S["&self"]  # rung: no import door hangs off the space handle
CSTORE = S["&cstore"]  # rung: check-space-provider takes the space as a symbol; petta.testing's kit reaches only Python providers

#: The build artefact and the provider that loads it. Marked data because a
#: twin may not write a bare string; `.value` is the path a Python door takes.
CSTORE_SO = Path(val("examples/integration/c_space/cstore.so").value)
CSTORE_PL = Path(val("examples/integration/c_space/cstore.pl").value)

#: What a healthy provider reports about itself.
REPORT = [
    val("enumerate: declared, seam:foreign_atoms/2 has clauses"),
    val("add: declared, seam:foreign_add/2 has clauses"),
    val("remove: declared, seam:foreign_remove/3 has clauses"),
    val("clear: declared, seam:foreign_clear/1 has clauses"),
    val("match: over-approximation holds over 1 atoms"),
    val("pushdown: 0 of 1 patterns claimed exact, and are"),
    val("plan: not declared, so a conjunction takes the engine's split"),
]

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 141295 to 132196, -9099 (-6.44%), by the twin
#: contract change: five `if`/`file-exists` guards, six `test` wrappers, eight
#: `collapse`/`match` pairs and three `size-atom` calls left the engine for
#: Python's own `if`, `Path.exists()`, `assert`, the space handle's `[...]` and
#: `len()`. The writes, the removals and the C crossings under them did not
#: move. Against the example's 174913 the ratio is 0.7558, and the
#: concurrent-writer form stays declined [measured 2026-08-22 min-of-3:
#: `twin_coverage.py --measure examples/integration/c_space/c_space.metta`].
#: Prior: ADDED 2026-08-22 at 141295 by the wave-3 twin baseline, which priced
#: a transliteration.
BUDGET = 132196


def twin(m):
    """Write into C, read back out of it, and prove the provider."""
    for library in (S.lib_import, S.lib_file, S.lib_conformance):
        m.eval(S["import!"](SELF, S.library(library)))

    if not CSTORE_SO.exists():
        # The example prints its skip here. A twin has no door for prose.
        return

    m.register_prolog(path=CSTORE_PL)
    store = m.space(CSTORE.name)

    # Writes and reads cross into C; the engine keeps unification for itself.
    store += S.edge(S.a, S.b)
    store += S.edge(S.a, S.c)
    store += S.edge(S.b, S.c)
    assert list(store[S.edge(S.a, V.x)]["x"]) == [S.b, S.c]

    # Removal is multiset subtraction: two atoms match `(edge a $any)`, so
    # clearing them takes two removals rather than one.
    store -= S.edge(S.a, V.any)
    assert len(store[S.edge(V.x, V.y)]) == 2
    store -= S.edge(S.a, V.other)
    assert [(row.x, row.y) for row in store[S.edge(V.x, V.y)]] == [(S.b, S.c)]

    # Identical copies are where the reading matters most: the count walks
    # down one at a time rather than clearing to nothing.
    for _ in range(3):
        store += S.dup(1)
    store -= S.dup(1)
    assert len(store[S.dup(V.n)]) == 2
    store -= S.dup(1)
    store -= S.dup(1)
    assert len(store[S.dup(V.n)]) == 0

    # Every declared capability has clauses behind it, match over-approximates,
    # and no pushdown claim overreaches. It raises on a violation.
    assert list(m.one(S["check-space-provider"](CSTORE))) == REPORT
