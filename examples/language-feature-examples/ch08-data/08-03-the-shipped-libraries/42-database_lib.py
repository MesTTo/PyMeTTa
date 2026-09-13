"""Purpose: persist metagraph syntax and compose selection and reconstruction.

Guarantees: the same claims as 42-database_lib.metta.
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/42-database_lib.metta; commit=24b9b7ee948564963a5c3455cd5b412d05afdd2c].
Owns resources: explicit handles close below and in finally; scoped handles
close when their answer streams end. Finally removes the temporary directory.
"""

from metta import Expression, G, S, V, lib
from metta._errors.errors import MettaError


def twin(m):
    """Match passive snapshots, join relations and reconstruct stored equations."""
    m += lib.file
    m += lib.database
    fn = m.fn
    atoms = fn.database_atoms
    add, remove = fn["database-add!"], fn["database-remove!"]
    close, scoped = fn["database-close!"], fn.with_database

    def selected(rows, pattern, template):
        """Compose Python atom bindings with substitution over an ordered snapshot."""
        if isinstance(template, tuple):
            template = Expression(template)
        return tuple(template.subs(bindings) for row in rows
                     if (bindings := pattern.unify(row)) is not None)

    def query(handle, pattern, template):
        """Read a snapshot before selecting its passive values."""
        return [selected(atoms(handle)[0], pattern, template)]

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
        assert query(first, S.item(S.pear, V.price), V.price) == [(5,)]

        assert query(second, V.value, V.value) == [()]
        assert add(second, S.item(S.banana, 8)) == [True]
        assert query(second, S.item(V.name, V.price), (V.name, V.price)) == [((S.banana, 8),)]
        assert query(first, S.item(V.name, V.price), (V.name, V.price)) == [((S.pear, 5), (S.apple, 3))]

        assert add(first, S["+"](1, 2)) == [True]
        assert query(first, S["+"](1, V.value), V.value) == [(2,)]
        assert add(first, S.number(1)) == [True]
        assert add(first, S.number(1.0)) == [True]
        assert [S.hit for row in atoms(first)[0]
                if row == S.number(1) or row == S.number(1.0)] == [S.hit, S.hit]
        assert remove(first, S.number(1)) == [True]
        assert query(first, S.number(V.value), V.value) == [(1.0,)]
        nul_text = fn.string_from_codes((97, 0, 98)).one()
        assert fn.string_codes(nul_text) == [(97, 0, 98)]
        assert add(first, S.text(G("café"), nul_text, ())) == [True]
        assert query(first, S.text(V.left, V.right, ()), (V.left, V.right)) == [((G("café"), G("a\0b")),)]
        assert add(first, S.path(S.a, S.b, S.c)) == [True]
        path = next(row.children[1:] for row in atoms(first)[0]
                    if isinstance(row, Expression) and row[0] == S.path)
        assert [(path[:index], path[index:]) for index in range(len(path) + 1)] == [((), (S.a, S.b, S.c)), ((S.a,), (S.b, S.c)), ((S.a, S.b), (S.c,)), ((S.a, S.b, S.c), ())]
        assert add(first, ()) == [True]
        assert query(first, Expression(()), S.empty_value) == [(S.empty_value,)]
        assert add(first, S.unbound(V.value)) == [True]
        assert remove(first, S.unbound(V.renamed)) == [True]
        assert refused(S["database-add!"](first, second))

        assert add(first, S["="](S.stored_twice(V.x), V.x + V.x)) == [True]
        assert add(first, S["="](S.stored_twice(V.x), (V.x + V.x) + 1)) == [True]
        assert list(m.match(S["="](S.stored_twice(V.x), V.body))) == []
        assert add(first, S.edge(S.e1, S.alice, S.bob)) == [True]
        assert add(first, S.edge(S.e2, S.bob, S.carol)) == [True]
        assert add(first, S.supports(S.e1, S.e2)) == [True]
        graph = atoms(first)[0]
        joined = []
        for left, right in selected(graph, S.supports(V.left, V.right), (V.left, V.right)):
            for source, middle in selected(graph, S.edge(left, V.source, V.middle), (V.source, V.middle)):
                joined.extend((source, middle, target)
                              for target in selected(graph, S.edge(right, middle, V.target), V.target))
        assert joined == [(S.alice, S.bob, S.carol)]

        assert fn["database-sync!"](first) == [True]
        assert fn.file_exists(fn.path_join(first_path, G("journal.pl")).one()) == [True]
        assert refused(S["database-open!"](first_path, S.close))
        assert add(first, S.after_sync) == [True]
        assert close(first) == [True]
        assert close(first) == [True]
        assert close(second) == [True]
        assert refused(S.database_atoms(first))

        reopened = fn["database-open!"](first_path, S.flush)[0]
        handles.append(reopened)
        assert query(reopened, S.item(V.name, V.price), (V.name, V.price)) == [((S.pear, 5), (S.apple, 3))]
        assert query(reopened, S.text(V.left, V.right, ()), (V.left, V.right)) == [((G("café"), G("a\0b")),)]
        assert query(reopened, S.after_sync, S.present) == [(S.present,)]
        recipes = selected(atoms(reopened)[0], S["="](S.stored_twice(V.parameter), V.body),
                           S["|->"]((V.parameter,), V.body))
        assert [answer for recipe in recipes
                for answer in m.eval((m.eval(recipe)[0], 7))] == [14, 15]
        bodies = selected(atoms(reopened)[0], S["="](S.stored_twice(9), V.body), V.body)
        assert [answer for body in bodies for answer in m.eval(body)] == [18, 19]
        parameters = selected(atoms(reopened)[0], S["="](S.stored_twice(V.parameter), V.body), V.parameter)
        assert [bool(parameter.vars) for parameter in parameters] == [True, True]
        assert remove(reopened, S["="](S.stored_twice(V.fresh), V.fresh + V.fresh)) == [True]
        bodies = selected(atoms(reopened)[0], S["="](S.stored_twice(4), V.body), V.body)
        assert [answer for body in bodies for answer in m.eval(body)] == [9]
        assert close(reopened) == [True]

        snapshot = S["|->"]((V.store,), S.database_atoms(V.store))
        assert selected(scoped(first_path, S.flush, snapshot)[0],
                        S.item(V.name, V.price), (V.name, V.price)) == ((S.pear, 5), (S.apple, 3))
        assert list(scoped(first_path, S.none, S["|->"]((V.store,), S.superpose((S.left, S.right))))) == [S.left, S.right]
        assert list(scoped(first_path, S.none, S["|->"]((V.store,), S.superpose(())))) == []
        assert refused(S.with_database(first_path, S.none, S["|->"]((V.store,), S["database-add!"](V.store, S.bad(V.store)))))
        assert scoped(first_path, S.close, S["|->"]((V.store,), S["database-close!"](V.store))) == [True]
        assert scoped(second_path, S.close, snapshot) == [((S.item, S.banana, 8),)]
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


#: MEASURED: all 71 claims cover snapshots, variable rules, joins and ownership.
#: The example pays 244929; both notations import File before Database.
#: [measured 2026-09-13: 226128 inferences, minimum of three fresh serial processes;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/42-database_lib.metta;
#: fixture=lib_database with engine/lib QLF artifacts purged; commit=24b9b7ee948564963a5c3455cd5b412d05afdd2c].
BUDGET = 226128
