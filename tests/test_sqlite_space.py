"""Purpose: prove the standalone SQLite example: rows answer MeTTa
queries under the declared contract, joins cross into native atoms, the
licensed bound reaches the SQL, writes are transactional, and the
conformance kit certifies the pushdown claim.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import sys
from importlib import util as _importlib_util
from pathlib import Path

import pytest

import petta
from petta import S, testing

_MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "examples" / "integration" / "sqlite_space.py"
)


def _module():
    examples_root = str(_MODULE_PATH.parents[1])
    sys.path.insert(0, examples_root)
    try:
        specification = _importlib_util.spec_from_file_location(
            "petta_example_sqlite_space", _MODULE_PATH
        )
        module = _importlib_util.module_from_spec(specification)
        specification.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(examples_root)


@pytest.fixture
def attached(request):
    name = f"&sqlite-{request.node.name[-16:].replace('_', '')}"
    m = petta.MeTTa().fresh_space()
    provider = _module().attach_sqlite(m, name)
    try:
        yield m, name, provider
    finally:
        m.run(f"!(remove-atom &petta (bridge {name} $shape $row))")
        m.unregister_space(name)
        m.drop()


def test_rows_answer_metta_and_join_native_atoms(attached):
    m, name, _provider = attached
    m.run(f"!(add-atom {name} (edge a b))")
    m.run(f"!(add-atom {name} (edge b c))")
    m.run("(capital b beta)")
    (group,) = m.run(
        f"!(collapse (match {name} (edge a $x) (match &self (capital $x $c) $c)))"
    )
    assert [str(atom) for atom in group[0]] == ["beta"]


def test_the_licensed_bound_reaches_the_sql(attached):
    m, name, provider = attached
    for index in range(10):
        m.run(f"!(add-atom {name} (edge a t{index}))")
    (group,) = m.run(f"!(collapse (take 3 (match {name} (edge $x $y) (edge $x $y))))")
    assert len(group[0]) == 3
    assert any("LIMIT 3" in sql for sql in provider.executed), provider.executed


def test_writes_ride_the_engine_transaction(attached):
    m, name, provider = attached
    m.run(f"!(add-atom {name} (edge keep me))")
    with pytest.raises(petta.EngineError):
        m.run(
            f"!(transaction (chain (add-atom {name} (edge lost one)) $_"
            " (error boom)))"
        )
    rows = provider.connection.execute(
        "SELECT COUNT(*) FROM edges WHERE a = 'lost'"
    ).fetchone()
    assert rows[0] == 0
    (group,) = m.run(f"!(collapse (match {name} (edge $x $y) ($x $y)))")
    assert [str(atom) for atom in group[0]] == ["(keep me)"]


def test_the_kit_certifies_the_pushdown_claim(attached):
    _m, _name, provider = attached
    report = testing.check_space_provider(
        provider,
        atoms_to_store=[S.edge(S.a, S.b), S.edge(S.b, S.c), S.edge(S.d, S.d)],
    )
    assert any("patterns claimed exact, and are" in line for line in report)


def test_a_nonground_compound_downgrades_and_removal_still_unifies(attached):
    m, name, provider = attached
    m.run(f"!(add-atom {name} (edge (f 1) b))")
    m.run(f"!(add-atom {name} (edge x b))")
    pattern = m.parse("(edge (f $y) $z)")
    assert provider.pushdown(pattern) == "inexact"
    assert provider.remove(m.parse("(edge (f $y) b)")) is True
    (group,) = m.run(f"!(collapse (match {name} (edge $x $y) ($x $y)))")
    assert [str(atom) for atom in group[0]] == ["(x b)"]


def test_a_nonground_add_is_refused(attached):
    m, _name, provider = attached
    with pytest.raises(ValueError, match="ground"):
        provider.add(m.parse("(edge $x b)"))


def test_the_declaration_may_be_text(attached):
    m, _name, _provider = attached
    import sqlite3

    from petta.tables import TableBridge

    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE pairs (x TEXT, y TEXT)")
    bridge_provider = TableBridge(
        m.parse, connection, "(bridge (pair $x $y) (row pairs (x $x) (y $y)))"
    )
    bridge_provider.add(m.parse("(pair l r)"))
    assert [str(atom) for atom in bridge_provider.atoms()] == ["(pair l r)"]


def test_a_schema_is_several_shapes_answering_together(attached):
    m, _name, _provider = attached
    import sqlite3

    from petta.tables import TableBridge

    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE edges (a TEXT, b TEXT)")
    connection.execute("CREATE TABLE likes (who TEXT, what TEXT)")
    provider = TableBridge(
        m.parse,
        connection,
        [
            "(bridge (edge $a $b) (row edges (a $a) (b $b)))",
            "(bridge (likes $w $t) (row likes (who $w) (what $t)))",
        ],
    )
    provider.add(m.parse("(edge a b)"))
    provider.add(m.parse("(likes ada logic)"))
    # A variable head admits both shapes, and the answers are their union,
    # the way overlapping equations answer together.
    both = sorted(str(atom) for atom in provider.match(m.parse("($h $x $y)")))
    assert both == ["(edge a b)", "(likes ada logic)"]
    only = [str(atom) for atom in provider.match(m.parse("(likes $w $t)"))]
    assert only == ["(likes ada logic)"]
    assert provider.pushdown(m.parse("($h $x $y)")) == "exact"


def test_an_ambiguous_add_is_refused_naming_both(attached):
    m, _name, _provider = attached
    import sqlite3

    from petta.tables import TableBridge

    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE one (a TEXT, b TEXT)")
    connection.execute("CREATE TABLE two (a TEXT, b TEXT)")
    provider = TableBridge(
        m.parse,
        connection,
        [
            "(bridge (pair $a $b) (row one (a $a) (b $b)))",
            "(bridge (pair $a $b) (row two (a $a) (b $b)))",
        ],
    )
    with pytest.raises(ValueError, match="ambiguous"):
        provider.add(m.parse("(pair l r)"))


def test_metta_source_declares_its_own_schema(attached):
    m, _name, _provider = attached
    import sqlite3

    from petta.tables import TableBridge

    m.run(
        "!(add-atom &petta"
        " (bridge &src-decl (pair $x $y) (row pairs (x $x) (y $y))))"
    )
    try:
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE TABLE pairs (x TEXT, y TEXT)")
        provider = TableBridge.from_context(m, "&src-decl", connection)
        provider.add(m.parse("(pair l r)"))
        assert [str(atom) for atom in provider.atoms()] == ["(pair l r)"]
    finally:
        m.run("!(remove-atom &petta (bridge &src-decl $shape $row))")
