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

    @m.define
    def module_helper(x: int) -> int:
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
BUDGET = 66933
