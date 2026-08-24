"""examples/integration/c_space/c_space.metta in Python: a space whose atoms live in C.

`cstore.c` holds the atoms and `cstore.pl` puts four clauses on the
foreign-space seam, so `&cstore` is a space like any other and nothing above it
knows there is a C backend. That is exactly why this twin reads like the spaces
twins: the store is a handle named by an ATOM rather than by text, `store +=
atom` writes, `store[pattern]` matches, and `store -= atom` takes one unifying
occurrence away, which is what `remove-atom` means everywhere.
`check-space-provider` takes that handle too, as a grounded operand, so nothing
here names a space as a symbol.

The provider file is consulted through `m.register_prolog(path=)`, the Python
door for what the example spells `(let "cstore.pl" (consult_global) provider)`.

Two things do not dissolve. The Python compliance kit, `metta.testing`, reaches
only Python providers, so a provider whose clauses live in Prolog and whose
store lives in C is checkable only through the engine's own
`check-space-provider`. And the concurrent-writer form is DECLINED: `hyperpose`
runs its branches on real threads and the completion schedule moves the
inference count, which the residue records against P14.14.
"""

from pathlib import Path

import metta
from metta import S, V, ground

#: The three engine libraries the example opens, spelled with their real
#: underscores: `S.lib_file` would name `lib-file`, which the tree does not ship.
LIBRARIES = (S["lib_import"], S["lib_file"], S["lib_conformance"])

#: The build artefact and the provider that loads it, as host paths for a
#: Python door.
CSTORE_SO = Path("examples/integration/c_space/cstore.so")
CSTORE_PL = Path("examples/integration/c_space/cstore.pl")

#: What a healthy provider reports about itself, in the engine's own prose.
REPORT = [
    ground("enumerate: declared, seam:foreign_atoms/2 has clauses"),
    ground("add: declared, seam:foreign_add/2 has clauses"),
    ground("remove: declared, seam:foreign_remove/3 has clauses"),
    ground("clear: declared, seam:foreign_clear/1 has clauses"),
    ground("match: over-approximation holds over 1 atoms"),
    ground("pushdown: 0 of 1 patterns claimed exact, and are"),
    ground("plan: not declared, so a conjunction takes the engine's split"),
]

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=e70eaeba6b6c0afc9081239041b8459eb8bb1b92].
BUDGET = 1


def twin(m):
    """Write into C, read back out of it, and prove the provider."""
    # Known issue: `import!` has no Python door on the handle. The perfect
    # spelling is `m.import_(target)`, or `m += lib.<name>` for a shipped
    # library (appendix stamp 1), and neither exists yet, so the directive is
    # reached by its own bang name, which performs it where it is written.
    for library in LIBRARIES:
        m.fn["import!"](m, S.library(library))

    if not CSTORE_SO.exists():
        # The example prints its skip here. A twin has no door for prose.
        return

    m.register_prolog(path=CSTORE_PL)
    # Known issue: `metta.space(name)` rides the process-DEFAULT context, not
    # the one holding `m`; the two reach the same store only because the SWI
    # runtime is process-wide. A creation door on the handle's own context is
    # the perfect spelling [measured 2026-08-24].
    store = metta.space(S.cstore)

    # Writes and reads cross into C; the engine keeps unification for itself.
    store += [(S.edge, S.a, S.b), (S.edge, S.a, S.c), (S.edge, S.b, S.c)]
    assert [row.x for row in store[S.edge(S.a, V.x)]] == [S.b, S.c]

    # Removal is multiset subtraction: two atoms match `(edge a $any)`, so
    # clearing them takes two removals rather than one.
    store -= S.edge(S.a, V.any)
    assert len(store[S.edge(V.x, V.y)]) == 2
    store -= S.edge(S.a, V.other)
    assert [(row.x, row.y) for row in store[S.edge(V.x, V.y)]] == [(S.b, S.c)]

    # Identical copies are where the reading matters most: the count walks down
    # one at a time rather than clearing to nothing.
    store += [(S.dup, 1)] * 3
    store -= S.dup(1)
    assert len(store[S.dup(V.n)]) == 2
    store -= S.dup(1)
    store -= S.dup(1)
    assert len(store[S.dup(V.n)]) == 0

    # Every declared capability has clauses behind it, match over-approximates,
    # and no pushdown claim overreaches. It raises on a violation.
    #
    # Known issue: the perfect spelling is the Python compliance kit,
    # `metta.testing.check_space_provider(provider)`, and it takes a Python
    # `SpaceProvider` OBJECT, so a provider whose clauses live in Prolog and
    # whose store lives in C cannot reach it. The engine's own function is the
    # only route, and it does take the handle.
    assert list(m.answers(S.check_space_provider(store)).one()) == REPORT
