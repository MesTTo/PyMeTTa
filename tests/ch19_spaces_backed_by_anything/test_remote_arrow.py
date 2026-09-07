"""Purpose: a cursor's answers as Arrow record batches instead of tagged atoms.

The questions an Arrow answer has to survive are the ones a second
representation always raises: does it answer the SAME set, is its schema the
same for every chunk of one stream, does the lifecycle still end, and does a
cell a typed column cannot hold survive somewhere.

Guarantees:
  - the batches carry the answers the JSON reply carries, chunk for chunk
    [tested: test_the_batches_are_the_answers_the_json_reply_carries; commit=0fb68d75871c57f2421c335e9faef3561f8dfdd5]
  - each chunk is a COMPLETE IPC stream, ending in the end-of-stream marker
    [tested: test_every_chunk_is_a_complete_stream; commit=0fb68d75871c57f2421c335e9faef3561f8dfdd5]
  - the schema comes from what the space declares and is the same for every
    chunk; an undeclared column is canonical text marked mixed
    [tested: test_a_declared_pattern_answers_typed_columns,
    test_an_undeclared_column_is_text_marked_mixed,
    test_every_chunk_of_one_cursor_shares_one_schema; commit=0fb68d75871c57f2421c335e9faef3561f8dfdd5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import pytest

from metta import S, V, remote
from metta._arrow import _IPC_EXTRA, IPC_MEDIA_TYPE
from metta.atoms import _atom_from_wire
from metta.errors import MettaError

pytest.importorskip("pyarrow")

#: The four bytes of a continuation and the four of an empty message, which is
#: what ends an IPC stream
#: [source: https://arrow.apache.org/docs/format/Columnar.html#ipc-streaming-format].
END_OF_STREAM = b"\xff\xff\xff\xff\x00\x00\x00\x00"


@pytest.fixture()
def metta(metta):
    """Each scenario serves its own store."""
    with metta._new_space() as space:
        yield space


@pytest.fixture()
def registry(metta):
    """Five declared rows, so a chunked drain has something to chunk."""
    metta.add(*[S.users(index, f"n{index}") for index in range(5)])
    metta.run("(: users (-> Number String Bool))")
    return metta


def _table(raw):
    """One IPC stream's rows, read the way any Arrow consumer reads them."""
    import pyarrow as pa

    return pa.ipc.open_stream(pa.BufferReader(raw)).read_all()


def _drain(gateway, pattern, batch):
    """Every chunk of one Arrow cursor, as the raw streams they crossed as."""
    reply = gateway("ask", {"pattern": pattern.to_wire(), "batch": batch, "format": "arrow"})
    chunks = [reply["arrow"]]
    while reply["cursor"] is not None:
        reply = gateway(
            "next", {"cursor": reply["cursor"], "batch": batch, "format": "arrow"}
        )
        chunks.append(reply["arrow"])
    return chunks


def test_the_batches_are_the_answers_the_json_reply_carries(registry):
    """Two representations, one answer set. That is the whole contract.

    The `atom` column is the canonical text of each instantiated answer, which
    is what the JSON reply's tagged atom prints as, so the two are comparable
    without either being converted into the other's shape.
    """
    pattern = S.users(V.id, V.name)
    with remote.Gateway(registry) as gateway:
        chunks = _drain(gateway, pattern, 2)
        answered = gateway("match", {"pattern": pattern.to_wire()})
    streamed = [
        atom
        for chunk in chunks
        for atom in _table(chunk).column("atom").to_pylist()
    ]
    assert streamed == [str(_atom_from_wire(wire)) for wire in answered["atoms"]]


def test_every_chunk_is_a_complete_stream(registry):
    """A response body is what `open_stream` is handed, so it is a whole stream.

    A fragment of one stream is not readable on its own, which is why the
    chunks are one stream each rather than pieces of a single one.
    """
    with remote.Gateway(registry) as gateway:
        chunks = _drain(gateway, S.users(V.id, V.name), 2)
    assert len(chunks) == 3
    for chunk in chunks:
        assert chunk.endswith(END_OF_STREAM)
        assert _table(chunk).column_names == ["id", "name", "atom"]


def test_a_declared_pattern_answers_typed_columns(registry):
    """A declared `Number` is a float64 column and a `String` is utf8.

    This is what the type table buys the wire: the columns arrive typed rather
    than as text a consumer has to parse back.
    """
    with remote.Gateway(registry) as gateway:
        table = _table(_drain(gateway, S.users(V.id, V.name), 10)[0])
    assert [str(field.type) for field in table.schema] == ["double", "string", "string"]
    assert table.column("id").to_pylist() == [0.0, 1.0, 2.0, 3.0, 4.0]
    assert table.column("name").to_pylist() == ["n0", "n1", "n2", "n3", "n4"]
    assert table.schema.field("id").metadata[b"metta.type"] == b"Number"
    assert b"metta.kind" not in table.schema.field("id").metadata


def test_an_undeclared_column_is_text_marked_mixed(metta):
    """No declaration is no promise, so the column carries canonical text.

    Every atom has canonical text, so nothing is lost and no cell has to be
    dropped; the field says `metta.kind=mixed` rather than leaving a consumer to
    infer why a column of numbers arrived as strings.
    """
    metta.add(S.thing(1, "a"), S.thing("b", 2))
    with remote.Gateway(metta) as gateway:
        table = _table(_drain(gateway, S.thing(V.a, V.b), 10)[0])
    assert [str(field.type) for field in table.schema] == ["string", "string", "string"]
    assert table.column("a").to_pylist() == ["1", '"b"']
    assert table.schema.field("a").metadata[b"metta.kind"] == b"mixed"
    assert table.schema.field("a").metadata[b"metta.type"] == b"%Undefined%"


def test_every_chunk_of_one_cursor_shares_one_schema(registry):
    """The schema is fixed when the cursor opens, not derived per chunk.

    A kind read off the cells of the first chunk can be contradicted by the
    second, and an IPC stream has no way to change its mind, so the schema comes
    from the space's declaration instead.
    """
    with remote.Gateway(registry) as gateway:
        schemas = [_table(chunk).schema for chunk in _drain(gateway, S.users(V.id, V.name), 2)]
    assert all(schema.equals(schemas[0]) for schema in schemas)


def test_a_bound_of_zero_still_answers_a_readable_stream(registry):
    """No rows is still a schema, so a consumer reads one either way."""
    with remote.Gateway(registry) as gateway:
        reply = gateway(
            "ask",
            {
                "pattern": S.users(V.id, V.name).to_wire(),
                "bound": 0,
                "format": "arrow",
            },
        )
    assert reply["cursor"] is None
    table = _table(reply["arrow"])
    assert table.num_rows == 0
    assert table.column_names == ["id", "name", "atom"]


def test_stop_still_releases_an_arrow_cursor(registry):
    """The lifecycle is the protocol's own whatever the chunks look like."""
    with remote.Gateway(registry) as gateway:
        reply = gateway(
            "ask",
            {"pattern": S.users(V.id, V.name).to_wire(), "batch": 1, "format": "arrow"},
        )
        assert reply["cursor"] is not None
        assert gateway("stop", {"cursor": reply["cursor"]}) == {"stopped": True}
        assert gateway("stop", {"cursor": reply["cursor"]}) == {"stopped": False}


def test_a_json_cursor_refuses_a_later_arrow_chunk(registry):
    """One stream, one representation: the schema is fixed at the ask.

    Asking for Arrow on `next` after a JSON `ask` has no schema to write at, and
    the refusal names where a schema is decided rather than inventing one.
    """
    with remote.Gateway(registry) as gateway:
        opened = gateway(
            "ask", {"pattern": S.users(V.id, V.name).to_wire(), "batch": 1}
        )
        with pytest.raises(MettaError, match="opened for JSON answers"):
            gateway("next", {"cursor": opened["cursor"], "format": "arrow"})


def test_an_unknown_format_refuses_by_name(registry):
    """A client that asked for something is owed that or a sentence."""
    with remote.Gateway(registry) as gateway, pytest.raises(MettaError, match="format must be"):
        gateway("ask", {"pattern": S.users(V.id, V.name).to_wire(), "format": "parquet"})


def test_the_accept_header_asks_for_arrow_over_http(registry):
    """HTTP's own way of asking for a representation, and its cursor header."""
    import urllib.request

    from metta import _json

    with remote.serve(registry) as server:
        request = urllib.request.Request(
            f"{server.url}/ask",
            data=_json.dumps(
                {"space": registry.name, "pattern": S.users(V.id, V.name).to_wire(), "batch": 2}
            ),
            headers={"content-type": "application/json", "accept": IPC_MEDIA_TYPE},
        )
        with urllib.request.urlopen(request) as reply:
            assert reply.headers["content-type"] == IPC_MEDIA_TYPE
            token = reply.headers["x-metta-cursor"]
            raw = reply.read()
    assert token
    assert _table(raw).num_rows == 2


def test_a_client_cursor_drains_to_one_table(registry):
    """`to_arrow()` is the ask/next/stop lifecycle drained into one table."""
    with remote.serve(registry) as server:
        transport = remote.connect(server.url)
        space = remote.RemoteSpace(transport, registry.name)
        with space.stream(S.users(V.id, V.name), batch=2, arrow=True) as answers:
            table = answers.to_arrow()
    assert table.num_rows == 5
    assert table.column_names == ["id", "name", "atom"]
    assert table.column("name").to_pylist() == ["n0", "n1", "n2", "n3", "n4"]


def test_a_client_cursor_answers_the_capsule_protocol(registry):
    """A consumer that dispatches on the protocol reaches the same batches."""
    import pyarrow as pa

    with remote.serve(registry) as server:
        transport = remote.connect(server.url)
        space = remote.RemoteSpace(transport, registry.name)
        with space.stream(S.users(V.id, V.name), batch=2, arrow=True) as answers:
            through_capsule = pa.table(answers)
    assert through_capsule.num_rows == 5


def test_the_two_cursor_modes_refuse_each_others_doors(registry):
    """Each refusal names the other mode, because converting would lose exactness.

    An Arrow batch's `atom` column is canonical TEXT, and reading atoms back out
    of it would go through the parser rather than through the tagged wire, which
    carries a grounded value the text cannot spell.
    """
    with remote.serve(registry) as server:
        transport = remote.connect(server.url)
        space = remote.RemoteSpace(transport, registry.name)
        with space.stream(S.users(V.id, V.name), arrow=True) as batches:
            with pytest.raises(MettaError, match="no atoms to iterate"):
                next(iter(batches))
        with space.stream(S.users(V.id, V.name)) as atoms:
            with pytest.raises(MettaError, match="open it with arrow=True"):
                atoms.to_arrow()


def test_the_ipc_doors_name_the_extra_when_pyarrow_is_absent(registry, monkeypatch):
    """The refusal says which package writes the format, and which extra has it."""
    monkeypatch.setattr("metta._optional.import_module", _no_pyarrow)
    with remote.Gateway(registry) as gateway, pytest.raises(ImportError) as refusal:
        gateway("ask", {"pattern": S.users(V.id, V.name).to_wire(), "format": "arrow"})
    assert "pymetta[arrow]" in str(refusal.value)
    assert _IPC_EXTRA == str(refusal.value)


def test_an_arrow_answer_carries_its_cursor_in_a_header(registry):
    """The transport reads the token off the reply, which the body cannot hold."""
    with remote.serve(registry) as server:
        transport = remote.connect(server.url)
        reply = transport(
            "ask",
            {
                "space": registry.name,
                "pattern": S.users(V.id, V.name).to_wire(),
                "batch": 2,
                "format": "arrow",
            },
        )
    assert isinstance(reply["arrow"], bytes)
    assert isinstance(reply["cursor"], str)
    assert _table(reply["arrow"]).num_rows == 2


def _no_pyarrow(name, *arguments, **options):
    """importlib.import_module with pyarrow taken out of the installation."""
    import importlib

    if name.split(".")[0] == "pyarrow":
        absent = "No module named 'pyarrow'"
        raise ModuleNotFoundError(absent, name="pyarrow")
    return importlib.import_module(name, *arguments, **options)
