"""Purpose: prove the standalone SQLite example: rows answer MeTTa
queries under the declared contract, joins cross into native atoms, the
licensed bound reaches the SQL, writes are transactional, and the
conformance kit certifies the pushdown claim. The BLOB worked instance proves
that a context image controls whether a binary value crosses whole.
Guarantees:
  - the opaque BLOB image keeps the binary object as a handle, a lazy path
    reaches one field [tested:
    test_an_opaque_blob_column_is_reached_by_a_lazy_path_without_crossing;
    commit=24532816d8f3987cc56059fadf3666a387ae1156]
  - the transparent image costs more engine inferences than the opaque image
    for the same 4,096-byte value [measured: minimum of three counter samples;
    command=python -m pytest bindings/python/tests/test_sqlite_space.py -q;
    fixture=SQLite documents.payload containing bytes(range(256)) repeated 16;
    commit=24532816d8f3987cc56059fadf3666a387ae1156]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import sys
from importlib import util as _importlib_util
from pathlib import Path

import pytest
from hypothesis import example, given
from hypothesis import strategies as st

import petta
from petta import S, testing
from petta.tables import TableBridge

_MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "examples" / "integration" / "sqlite_space.py"
)


class _OneRow:
    """The DB-API slice needed to expose one generated driver row."""

    def __init__(self, value):
        self.value = value

    def execute(self, _sql, _parameters=()):
        return [(self.value,)]

    def commit(self):
        return None

    def rollback(self):
        return None


@example(None)
@example("None")
@example("space here")
@example("(")
@example('say "hello"')
@example("λ雪")
@given(
    st.one_of(
        st.none(),
        st.text(),
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
    )
)
def test_a_row_value_becomes_an_atom_without_being_reparsed(value):
    """Map a database row value directly into one atom without parsing text."""
    m = petta.MeTTa()
    provider = TableBridge(
        m.parse,
        _OneRow(value),
        "(bridge (value $x) (row generated (cell $x)))",
    )
    (atom,) = tuple(provider.atoms())
    expected = petta.Sym(value) if isinstance(value, str) else petta.encode(value)
    assert atom == petta.Expr([S.value, expected])


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
def attached(request):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    name = f"&sqlite-{request.node.name[-16:].replace('_', '')}"
    m = petta.MeTTa().new_space()
    provider = _module().attach_sqlite(m, name)
    try:
        yield m, name, provider
    finally:
        m.run(f"!(remove-atom &petta (bridge {name} $shape $row))")
        m.run(f"!(remove-atom &petta (image {name} $type $setting))")
        m.unregister_space(name)
        m.drop()


def test_rows_answer_metta_and_join_native_atoms(attached):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m, name, _provider = attached
    m.run(f"!(add-atom {name} (edge a b))")
    m.run(f"!(add-atom {name} (edge b c))")
    m.run("(capital b beta)")
    (group,) = m.run(
        f"!(collapse (match {name} (edge a $x) (match &self (capital $x $c) $c)))"
    )
    assert [str(atom) for atom in group[0]] == ["beta"]


def test_the_licensed_bound_reaches_the_sql(attached):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m, name, provider = attached
    for index in range(10):
        m.run(f"!(add-atom {name} (edge a t{index}))")
    (group,) = m.run(f"!(collapse (take 3 (match {name} (edge $x $y) (edge $x $y))))")
    assert len(group[0]) == 3
    assert any("LIMIT 3" in sql for sql in provider.executed), provider.executed


def test_an_opaque_blob_column_is_reached_by_a_lazy_path_without_crossing(
    attached, monkeypatch
):
    """Keep the opaque BLOB behind a handle and reach one field by a lazy path."""
    import sqlite3

    from petta import S, V, path

    m, name, opaque_provider = attached
    image = m.parse(f"(image {name} Blob opaque)")
    assert image in m.space("&petta")
    assert m.space("&petta").run(f"!(get-type {image})") == [
        [m.parse("ImageDecl")]
    ]
    payload = bytes(range(256)) * 16
    opaque_provider.connection.execute(
        "INSERT INTO documents VALUES (?, ?)",
        ("manual", sqlite3.Binary(payload)),
    )
    opaque_space = m.space(name)

    def measured_crossing(space):
        samples = []
        rows = None
        for _sample in range(3):
            with space.stats() as counted:
                rows = space.query(S.document(S.manual, V.blob))
            samples.append(counted.inferences)
        assert rows is not None
        return min(samples), rows

    opaque_inferences, opaque_rows = measured_crossing(opaque_space)
    opaque_blob = opaque_rows[0].blob.value
    assert type(opaque_blob).__name__ == "Blob"
    assert opaque_blob.data == payload

    def refuse_whole_projection(_blob):
        msg = "the opaque BLOB crossed whole"
        raise AssertionError(msg)

    with monkeypatch.context() as image_guard:
        image_guard.setattr(
            type(opaque_blob), "__metta__", refuse_whole_projection
        )
        rows = opaque_space.query(
            S.document(S.manual, path("data", 17, to=V.byte))
        )
    assert rows.to_dicts() == [{"byte": 17}]

    m.unregister_space(name)
    transparent_image = m.declare_image(name, "Blob", "transparent")
    assert image not in m.space("&petta")
    assert transparent_image in m.space("&petta")
    transparent_provider = petta.tables.TableBridge.from_context(
        m, name, opaque_provider.connection
    )
    m.register_space(transparent_provider, name)
    transparent_inferences, transparent_rows = measured_crossing(m.space(name))
    assert str(transparent_rows[0].blob).startswith("(Blob 0 1 2 3 ")
    assert transparent_inferences > opaque_inferences


def test_writes_ride_the_engine_transaction(attached):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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


def test_the_kit_certifies_the_pushdown_claim(attached):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    _m, _name, provider = attached
    report = testing.check_space_provider(
        provider,
        atoms_to_store=[S.edge(S.a, S.b), S.edge(S.b, S.c), S.edge(S.d, S.d)],
    )
    assert any("patterns claimed exact, and are" in line for line in report)


def test_a_nonground_compound_downgrades_and_removal_still_unifies(attached):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m, name, provider = attached
    m.run(f"!(add-atom {name} (edge (f 1) b))")
    m.run(f"!(add-atom {name} (edge x b))")
    pattern = m.parse("(edge (f $y) $z)")
    assert provider.pushdown(pattern) == "inexact"
    assert provider.remove(m.parse("(edge (f $y) b)")) is True
    (group,) = m.run(f"!(collapse (match {name} (edge $x $y) ($x $y)))")
    assert [str(atom) for atom in group[0]] == ["(x b)"]


def test_a_nonground_add_is_refused(attached):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m, _name, provider = attached
    with pytest.raises(ValueError, match="ground"):
        provider.add(m.parse("(edge $x b)"))


def test_the_declaration_may_be_text(attached):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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


def test_a_schema_is_several_shapes_answering_together(attached):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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


def test_an_ambiguous_add_is_refused_naming_both(attached):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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


def test_metta_source_declares_its_own_schema(attached):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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
