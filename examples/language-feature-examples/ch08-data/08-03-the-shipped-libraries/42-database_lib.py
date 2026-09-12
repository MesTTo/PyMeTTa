"""Purpose: persist independent stores and query their native values.

Guarantees: the same claims as 42-database_lib.metta.
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/42-database_lib.metta; commit=WORKTREE].
Owns resources: explicit handles close below and in finally; scoped handles
close when their answer streams end. Finally removes the temporary directory.
"""

from metta import G, S, V, lib
from metta._errors.errors import MettaError


def twin(m):
    """Keep duplicate rows, match held patterns and reopen independent stores."""
    m += lib.file
    m += lib.database
    fn = m.fn
    query = fn.database_query
    add, remove = fn["database-add!"], fn["database-remove!"]
    close, scoped = fn["database-close!"], fn.with_database

    def refused(call):
        """Observe a native refusal through the public evaluation door."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    assert fn.path_join(G("store"), G("journal.pl")) == [G("store/journal.pl")]
    work = fn["temp-dir!"](G("database-lib")).one()
    handles = []
    try:
        first_path = fn.path_join(work, G("first")).one()
        second_path = fn.path_join(work, G("second")).one()
        first = fn["database-open!"](first_path, S.none)[0]
        handles.append(first)
        second = fn["database-open!"](second_path, S.close)[0]
        handles.append(second)
        assert query(first, V.value, V.value) == [()]
        assert refused(S["database-open!"](first_path, S.flush))

        assert add(first, S.item(S.apple, 3)) == [True]
        assert add(first, S.item(S.pear, 5)) == [True]
        assert add(first, S.item(S.apple, 3)) == [True]
        assert query(first, S.item(V.name, V.price), (V.name, V.price)) == [((S.apple, 3), (S.pear, 5), (S.apple, 3))]
        assert query(first, S.item(V.name, 3), V.name) == [(S.apple, S.apple)]
        assert remove(first, S.item(S.apple, 3)) == [True]
        assert query(first, S.item(V.name, V.price), (V.name, V.price)) == [((S.pear, 5), (S.apple, 3))]
        assert remove(first, S.item(S.missing, 0)) == [False]
        assert query(first, S.missing(V.value), V.value) == [()]
        assert query(first, S.item(S[":="](S.pear), V.price), V.price) == [(5,)]

        assert query(second, V.value, V.value) == [()]
        assert add(second, S.item(S.banana, 8)) == [True]
        assert query(second, S.item(V.name, V.price), (V.name, V.price)) == [((S.banana, 8),)]
        assert query(first, S.item(V.name, V.price), (V.name, V.price)) == [((S.pear, 5), (S.apple, 3))]

        assert add(first, S["+"](1, 2)) == [True]
        assert query(first, S["+"](1, V.value), V.value) == [(2,)]
        assert add(first, S.number(1)) == [True]
        assert add(first, S.number(1.0)) == [True]
        assert query(first, S.number(1), S.hit) == [(S.hit, S.hit)]
        assert remove(first, S.number(1)) == [True]
        assert query(first, S.number(V.value), V.value) == [(1.0,)]
        nul_text = fn.string_from_codes((97, 0, 98)).one()
        assert fn.string_codes(nul_text) == [(97, 0, 98)]
        assert add(first, S.text(G("café"), nul_text, ())) == [True]
        assert query(first, S.text(V.left, V.right, ()), (V.left, V.right)) == [((G("café"), G("a\0b")),)]
        assert add(first, S.path(S.a, S.b, S.c)) == [True]
        assert query(first, S.path(S[":seg"](V.left), S[":seg"](V.right)), (V.left, V.right)) == [(((), (S.a, S.b, S.c)), ((S.a,), (S.b, S.c)), ((S.a, S.b), (S.c,)), ((S.a, S.b, S.c), ()))]
        assert add(first, ()) == [True]
        assert query(first, (), S.empty_value) == [(S.empty_value,)]
        assert refused(S["database-add!"](first, S.unbound(V.value)))
        assert refused(S["database-add!"](first, second))

        assert fn["database-sync!"](first) == [True]
        assert fn.file_exists(fn.path_join(first_path, G("journal.pl")).one()) == [True]
        assert refused(S["database-open!"](first_path, S.close))
        assert add(first, S.after_sync) == [True]
        assert close(first) == [True]
        assert close(first) == [True]
        assert close(second) == [True]
        assert refused(S.database_query(first, V.value, V.value))

        reopened = fn["database-open!"](first_path, S.flush)[0]
        handles.append(reopened)
        assert query(reopened, S.item(V.name, V.price), (V.name, V.price)) == [((S.pear, 5), (S.apple, 3))]
        assert query(reopened, S.text(V.left, V.right, ()), (V.left, V.right)) == [((G("café"), G("a\0b")),)]
        assert query(reopened, S.after_sync, S.present) == [(S.present,)]
        assert close(reopened) == [True]

        items = S["|->"]((V.store,), S.database_query(V.store, S.item(V.name, V.price), (V.name, V.price)))
        assert scoped(first_path, S.flush, items) == [((S.pear, 5), (S.apple, 3))]
        assert list(scoped(first_path, S.none, S["|->"]((V.store,), S.superpose((S.left, S.right))))) == [S.left, S.right]
        assert list(scoped(first_path, S.none, S["|->"]((V.store,), S.superpose(())))) == []
        assert refused(S.with_database(first_path, S.none, S["|->"]((V.store,), S["database-add!"](V.store, S.bad(V.unbound)))))
        assert scoped(first_path, S.close, S["|->"]((V.store,), S["database-close!"](V.store))) == [True]
        assert scoped(second_path, S.close, S["|->"]((V.store,), S.database_query(V.store, V.value, V.value))) == [((S.item, S.banana, 8),)]
        invalid_path = fn.path_join(work, G("invalid")).one()
        assert refused(S["database-open!"](invalid_path, S.invented))
        assert fn.dir_exists(invalid_path) == [False]

        bad_path = fn.path_join(work, G("bad")).one()
        assert scoped(bad_path, S.close, S["|->"]((V.store,), S["database-add!"](V.store, S.original))) == [True]
        journal = fn.path_join(bad_path, G("journal.pl")).one()
        damaged = G("created(0).\nassert(row(original)).\ninvented(corruption).\n")
        assert fn["write-file!"](journal, damaged) == [True]
        assert refused(S["database-open!"](bad_path, S.flush))
        assert fn["read-file!"](journal) == [damaged]
    finally:
        for handle in handles:
            close(handle).one()
        assert fn["delete-tree!"](work) == [True]


#: MEASURED: all 58 claims cover multiset queries, reopening and owned scopes.
#: The example pays 223237; both notations import File before Database.
#: [measured 2026-09-13: 222382 inferences, minimum of three fresh serial processes;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/42-database_lib.metta;
#: fixture=lib_database with engine/lib QLF artifacts purged; commit=WORKTREE].
BUDGET = 222382
