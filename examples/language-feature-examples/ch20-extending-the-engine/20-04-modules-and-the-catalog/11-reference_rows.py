"""Purpose: reference_rows.metta in Python through stored rows and shared claims.

from_ is sugar over adding a from row. get_property reads the same engine
claims as the MeTTa head and the library card.
Guarantees: the twin checks homes, metadata, occurrence bags and withdrawal
[tested: examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/11-reference_rows.metta; commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].
"""

from metta import S, V, ground


def twin(m):
    """Reference a changing home and withdraw exactly that reference."""
    home = m.metta.space(S.reference_home)
    home += S.internal(S.module_helper)

    @home.define
    def module_helper(x: int) -> int:
        return x + 1

    @home.define
    def module_answer(x: int) -> int:
        return module_helper(x)

    home += S["@doc"](S.module_answer, S["@desc"](ground("Add one at home")))
    home += S.home_data(S.kept)
    m += S.internal(S.module_helper)

    # The same head defined here as at home, so the Python name says which:
    # `name=` opts this definition in to the head the home already carries.
    @m.define(name="module-helper")
    def module_helper_here(x: int) -> int:
        return x + 100

    m.from_(home)
    assert m.fn.module_answer(2) == [3]
    assert m.fn.module_helper(2) == [102]
    assert m[S.home_data(V.x)] == []
    assert m[S["="](S.module_answer(V.x), V.body)] == []
    assert m[S[":"](S.module_answer, V.type)].type == [S["->"](S.Number, S.Number)]
    assert S.visibility(S.public) in m.get_property(S.module_answer)
    assert S.visibility(S.internal) in m.get_property(S.module_helper)
    origins = [p for p in m.get_property(S.module_answer) if p.head == S.origin]
    assert len(origins) == 1
    assert origins[0].args[0] == home and origins[0].args[2] == -1
    assert home.fn.module_helper(2) == [3]

    later = S["="](S.module_later(), 9)
    home += later
    home += later
    assert m.fn.module_later() == [9, 9]
    home -= later
    assert m.fn.module_later() == [9]
    m.remove(S["from"](home))
    assert m.eval(S.module_answer(2)) == [S.module_answer(2)]
    assert m[S[":"](S.module_answer, V.type)] == []


#: Initial reference-row price includes defining both homes, checking claims,
#: observing new duplicate occurrences, and withdrawing their reference.
#: [measured: 67053 inferences, min-of-3 fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3 examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/11-reference_rows.metta;
#: fixture=built native engine; commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427]
#: RE-PINNED 2026-09-10, 67053 to 66933 (-120), The reference, visibility and
#: property declarations add six heads to the cold-import census. Partial
#: catalog reads now sort occurrence tokens; source-scoped claims and cache
#: reservations change first translation work. The explicitly revised lib_he
#: examples load upstream equations. Warm imports save nine inferences through
#: one rollback collection; ordinary call and row slopes stay unchanged
#: [measured 2026-09-10: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].
#: RE-PINNED 2026-09-11, 66933 to 65601 (-1332), end-of-wave re-pin on the
#: merged tree after FROM's reference rows and four engine units, the closed-
#: set derivations and two host services, BINDING's one native evaluation entry
#: and boot import, W-OBSERVE's observer guard, PERF's receipts batching and
#: cursor retirement, and the three REDS repairs (derived runtime resources and
#: the shared loader, the tool-lane repairs, the corpus example); serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-11: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=57f84148ba2684015f052d533f3197eca07b1f7b].
#: RE-PINNED 2026-09-11, 65601 to 65786 (+185), engine/metta/limits.pl
#: (docs/host-workarounds.md: swi-autoload-cut-installs-the-undefined-
#: supervisor, swi-findall-bag-push-window): every first-use resolution of an
#: undefined predicate pays one inference for the catch around the trap query,
#: and a twin that bounds pays one inference per findall under the bound plus
#: the first bound of its process installing the findall scope [measured
#: 2026-09-11: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 65786
