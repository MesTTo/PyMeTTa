"""Purpose: verify version-pinned fast cache save and load, text auto-detection,
equation recompilation, batched program analysis, live-object refusal, and
corrupt-cache failures.
Guarantees:
  - restoring recursive program content reconciles its call graph once per
    image while preserving every atom and a callable equation [tested:
    test_fast_restore_batches_content_dependent_program_analysis;
    commit=d2279ea320e54790dab4484421a168e93755b185]
  - fast caches rebase and restore translator rules, bound equation-world
    spaces, and repeat-load ownership while retaining the root atom count
    [tested: test_fast_cache_restores_translator_rules_and_bound_spaces;
    commit=d2279ea320e54790dab4484421a168e93755b185]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import gzip
import re
import uuid
from contextlib import contextmanager
from pathlib import Path

import pytest

from metta import (
    TRUE,
    MeTTa,
    S,
    V,
    engine,
    ground,
)
from metta import _space_persistence as persistence_module
from metta.errors import EngineError


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as space:
        yield space


def test_fast_save_load_round_trip_recompiles_equations(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    path = tmp_path / "knowledge.metta-fast"
    with metta._new_space() as source, metta._new_space() as loaded:
        source.run("(fast-io-fact alpha) (fast-io-fact beta) (= (fast-io-next $x) (+ $x 1))")
        assert source.save(path, format="fast") == 3
        assert loaded.load(path) == []
        assert [row.x for row in loaded.match(S["fast-io-fact"](V.x))] == [
            S.alpha,
            S.beta,
        ]
        assert loaded.run("!(fast-io-next 41)") == [[42]]


def test_fast_restore_batches_content_dependent_program_analysis(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    path = tmp_path / "recursive-program.fast"
    size = 40
    forms = []
    for index in range(size):
        name = f"fast-restore-recursive-{index}"
        forms.append(
            f"(= ({name} $n) (if (== $n 0) 0 "
            f"(+ ({name} (- $n 1)) ({name} (- $n 1)))))"
        )

    with metta._new_space() as source, metta._new_space() as restored:
        source.run("\n".join(forms))
        assert source.save(path, format="fast") == size
        with metta.stats() as spent:
            restored.load(path)

        assert len(restored) == size
        assert restored.run("!(fast-restore-recursive-39 2)") == [[0]]
        assert spent.inferences < 100_000


def test_fast_cache_restores_translator_rules_and_bound_spaces(tmp_path, capfd):
    """The cache is a program image, not only the receiver's atom list.

    The child gets a fresh runtime name, while both aliases, its atoms, and
    the translator rule keep their logical identity. Loading the same image
    again replaces every source-owned component instead of accumulating it.
    """
    source = tmp_path / "translator-world.metta"
    cache = tmp_path / "translator-world.fast"
    source.write_text(
        "(: pick (-> Atom Atom Atom Atom Atom %Undefined%))\n"
        "(= (pick $expression $head $tail $body $otherwise)\n"
        "   (quote (if (== $expression ())\n"
        "              $otherwise\n"
        "              (let ($head $tail)\n"
        "                   (decons-atom $expression) $body))))\n"
        "!(add-translator-rule! pick)\n"
    )

    with MeTTa() as donor:
        donor.self.load(source)
        donor.run("!(bind! &kept (new-space))")
        donor.run("!(bind! &also &kept)")
        donor.run("!(add-atom &kept (a 1))")
        donor.run("!(add-atom &kept (a 2))")
        old_child = donor.runtime.once("metta_token('&kept', Child)")["Child"]
        assert donor.self.save(cache, format="fast") == 2

    with MeTTa() as restored:
        for _ in range(2):
            restored.self.load(cache)
            home = str(restored.self.name)
            module = restored.runtime.once(
                "space_module(Space, Module)", Space=home
            )["Module"]
            child = restored.runtime.once("metta_token('&kept', Child)")["Child"]
            alias = restored.runtime.once("metta_token('&also', Child)")["Child"]
            children = list(
                restored.runtime.iter(
                    "spaces:space_equation_home(Child, Home)", Home=home
                )
            )

            assert child == alias
            assert [row["Child"] for row in children] == [child]
            assert len(restored.self) == 2
            assert restored.run("!(space-atom-count &kept)") == [[2]]
            assert restored.run("!(pick (1 2) $head $tail $head empty)") == [[1]]
            assert restored.runtime.once(
                "translator_rules:translator_rule(pick, _, Home), Home == Module",
                Module=module,
            )
            assert child != old_child

        assert "Illegal UTF-8 start" not in capfd.readouterr().err

        # A caller-owned binding cannot be discarded to make a replacement
        # fit. The refusal rolls the provisional withdrawal back, including
        # the old child module and translator registry.
        restored.runtime.must(
            "space_module(Space, Module), "
            "with_metta_module(Module, register_metta_token('&kept', 99))",
            Space=home,
        )
        with pytest.raises(EngineError, match="metta_fast_token_conflict"):
            restored.self.load(cache)
        alias = restored.runtime.once("metta_token('&also', Child)")["Child"]
        assert alias == child
        assert restored.runtime.once("metta_token('&kept', Value)")["Value"] == 99
        assert restored.run("!(space-atom-count &also)") == [[2]]
        assert restored.run("!(pick (1 2) $head $tail $head empty)") == [[1]]
        assert restored.runtime.once(
            "spaces:space_equation_home(Child, Home)", Child=child, Home=home
        )


def test_fast_cache_rebases_nested_space_graph_references(tmp_path):
    """Every edge and term reference is relocated through one identity map."""
    cache = tmp_path / "nested-world.fast"
    grand_name = f"&cache-grand-{uuid.uuid4().hex}"

    with MeTTa() as donor:
        donor.run("!(bind! &kept (new-space))")
        donor.run("!(bind! &sibling (new-space))")
        old_child = donor.runtime.once("metta_token('&kept', Child)")["Child"]
        donor.runtime.must(
            "metta_py_declare_space(scoped, Grand, Child)",
            Grand=grand_name,
            Child=old_child,
        )
        donor.run(f"!(bind! &deep {grand_name})")
        donor.run("!(add-atom &kept (shallow fact))")
        donor.run("!(add-atom &deep (deep fact))")
        donor.run("!(add-atom &sibling (side fact))")
        donor.run("(points &kept &deep &sibling)")
        assert donor.self.save(cache, format="fast") == 1

    with MeTTa() as restored:
        restored.self.load(cache)
        home = str(restored.self.name)
        child = restored.runtime.once("metta_token('&kept', Child)")["Child"]
        deep = restored.runtime.once("metta_token('&deep', Deep)")["Deep"]
        sibling = restored.runtime.once("metta_token('&sibling', Side)")["Side"]
        edge = restored.runtime.once(
            "spaces:space_equation_home(Deep, Child)", Child=child, Deep=deep
        )
        side_edge = restored.runtime.once(
            "spaces:space_equation_home(Side, Home)", Side=sibling, Home=home
        )
        stored = restored.runtime.once(
            "'get-atoms'(Home, [points, Child, Deep, Side])", Home=home
        )

        assert edge
        assert side_edge
        assert child != old_child
        assert deep != grand_name
        assert stored["Child"] == child
        assert stored["Deep"] == deep
        assert stored["Side"] == sibling
        assert restored.run("!(space-atom-count &kept)") == [[1]]
        assert restored.run("!(space-atom-count &deep)") == [[1]]
        assert restored.run("!(space-atom-count &sibling)") == [[1]]


def test_fast_cache_restores_bidirectional_rule_ownership(tmp_path):
    """A restored generated inverse remains one removable derived equation."""
    source = tmp_path / "bidirectional-world.metta"
    cache = tmp_path / "bidirectional-world.fast"
    source.write_text(
        "(: unpack (-> Atom %Undefined%))\n"
        "(= (unpack (wrap (box $x))) (noeval (twin $x $x)))\n"
        "!(add-translator-rule! unpack ((direction bidirectional)))\n"
    )

    with MeTTa() as donor:
        donor.self.load(source)
        assert donor.self.save(cache, format="fast") == 3

    with MeTTa() as restored:
        restored.self.load(cache)
        home = str(restored.self.name)

        assert str(restored.run("!(unpack (wrap (box 1)))")[0][0]) == "(twin 1 1)"
        assert str(restored.run("!(twin (a b c) (a b c))")[0][0]) == (
            "(unpack (wrap (box (a b c))))"
        )
        assert restored.runtime.once(
            "aggregate_all(count, "
            "translator_rules:translator_rule_derived(unpack, Space, _), Count)",
            Space=home,
        )["Count"] == 1

        assert restored.run("!(remove-translator-rule! unpack)") == [[TRUE]]
        assert not restored.runtime.once(
            "translator_rules:translator_rule(twin, _, _)"
        )
        assert not restored.runtime.once(
            "'get-atoms'(Space, ['=', [twin|_], _])", Space=home
        )


def test_load_auto_detects_text_and_fast_files(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    text_path = tmp_path / "knowledge.metta"
    fast_path = tmp_path / "knowledge.fast"
    with (
        metta._new_space() as source,
        metta._new_space() as from_text,
        metta._new_space() as from_fast,
    ):
        source.add(S["auto-fact"](S.one), S["auto-fact"](S.two))
        source.save(text_path)
        source.save(fast_path, format="fast")
        assert text_path.read_text() == "(auto-fact one)\n(auto-fact two)\n"
        assert from_text.load(text_path) == []
        assert from_fast.load(fast_path) == []
        expected = [S.one, S.two]
        assert [row.x for row in from_text.match(S["auto-fact"](V.x))] == expected
        assert [row.x for row in from_fast.match(S["auto-fact"](V.x))] == expected


def test_escaped_quote_round_trips_through_text_save_and_load(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    path = tmp_path / "escaped-quote.metta"
    with metta._new_space() as source, metta._new_space() as loaded:
        source.add(S.h('a"b'))
        assert source.save(path) == 1
        assert path.read_text() == '(h "a\\"b")\n'
        assert loaded.load(path) == []
        assert loaded.match(S.h(V.value))[0].value.value == 'a"b'


@pytest.mark.parametrize("suffix", [".metta", ".metta.gz"])
def test_text_save_uses_utf8_for_plain_and_gzip_files(metta, tmp_path, suffix):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    path = tmp_path / f"unicode{suffix}"
    with metta._new_space() as source:
        source.add(S.text("é字"))
        assert source.save(path) == 1

    raw = gzip.decompress(path.read_bytes()) if suffix.endswith(".gz") else path.read_bytes()
    assert raw == b'(text "\xc3\xa9\xe5\xad\x97")\n'


def test_escaped_quote_runs_directly(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as space:
        assert space.run('(= (quote-id $x) $x)\n!(quote-id "a\\"b")') == [['a"b']]


def test_comments_remain_outside_escaped_string_state(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as space:
        assert space.run(
            '; leading comment\n(escaped-text "a\\"; ) b") ; trailing comment\n!(+ 1 2)'
        ) == [[3]]
        assert space.match(S["escaped-text"](V.value))[0].value.value == 'a"; ) b'


def test_fast_save_refuses_live_objects_exactly_like_text(m, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.add(S.holds(ground(object())))
    with pytest.raises(ValueError) as text_error:
        m.save(tmp_path / "object.metta")
    with pytest.raises(ValueError) as fast_error:
        m.save(tmp_path / "object.fast", format="fast")
    assert str(fast_error.value) == str(text_error.value)
    assert "live Python object" in str(fast_error.value)
    assert not (tmp_path / "object.fast").exists()


@pytest.mark.parametrize(
    "name",
    ['bad"quote', "bad(paren", "bad)paren", "bad name", "$notvar", "semi;colon", "42", "True"],
)
@pytest.mark.parametrize("format", ["metta", "fast"])
def test_save_refuses_symbols_without_round_trip_text(m, tmp_path, name, format):  # noqa: A002, D103  -- pytest parameterization names the public save-format argument exercised here; pytest discovers or injects this callable; its descriptive name states the contract
    path = tmp_path / f"unsafe-{format}"
    m.add(S.container(S[name]))
    with pytest.raises(ValueError, match=r"cannot write symbol"):
        m.save(path, format=format)
    assert not path.exists()


@pytest.mark.parametrize("format", ["metta", "fast"])
@pytest.mark.parametrize("suffix", [".data", ".data.gz"])
def test_save_failure_preserves_existing_file(m, tmp_path, monkeypatch, format, suffix):  # noqa: A002, D103  -- pytest parameterization names the public save-format argument exercised here; pytest discovers or injects this callable; its descriptive name states the contract
    target = tmp_path / f"knowledge{suffix}"
    target.write_bytes(b"old data stays\n")
    m.add(S.new(S.data))

    def fail_replace(source, destination):
        assert Path(source).parent == target.parent
        assert Path(source) != target
        assert Path(destination) == target
        msg = "injected replacement failure"
        raise OSError(msg)

    monkeypatch.setattr(persistence_module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected replacement failure"):
        m.save(target, format=format)

    assert target.read_bytes() == b"old data stays\n"
    assert list(tmp_path.glob(".metta-save-*")) == []


@pytest.mark.parametrize("format", ["metta", "fast"])
def test_save_validation_preserves_existing_file(m, tmp_path, format):  # noqa: A002, D103  -- pytest parameterization names the public save-format argument exercised here; pytest discovers or injects this callable; its descriptive name states the contract
    target = tmp_path / "knowledge.data"
    target.write_bytes(b"old data stays\n")
    m.add(S.holds(ground(object())))

    with pytest.raises(ValueError, match="live Python object"):
        m.save(target, format=format)

    assert target.read_bytes() == b"old data stays\n"
    assert list(tmp_path.glob(".metta-save-*")) == []


def test_text_save_write_failure_preserves_existing_file(m, tmp_path, monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    target = tmp_path / "knowledge.metta"
    target.write_text("old data stays\n")
    m.add(S.first(S.value), S.second(S.value))
    real_open = persistence_module._open_maybe_gz

    @contextmanager
    def failing_open(path, mode):
        assert Path(path) != target
        with real_open(path, mode) as handle:
            writes = 0

            class FailingHandle:
                def write(self, text):
                    nonlocal writes
                    writes += 1
                    if writes == 2:
                        msg = "injected write failure"
                        raise OSError(msg)
                    return handle.write(text)

            yield FailingHandle()

    monkeypatch.setattr(persistence_module, "_open_maybe_gz", failing_open)
    with pytest.raises(OSError, match="injected write failure"):
        m.save(target)

    assert target.read_text() == "old data stays\n"
    assert list(tmp_path.glob(".metta-save-*")) == []


def test_save_syncs_before_replacing(m, tmp_path, monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    target = tmp_path / "knowledge.metta"
    m.add(S.synced(S.value))
    events = []
    real_replace = persistence_module.os.replace

    def record_fsync(descriptor):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        events.append("fsync")

    def record_replace(source, destination):
        events.append("replace")
        real_replace(source, destination)

    monkeypatch.setattr(persistence_module.os, "fsync", record_fsync)
    monkeypatch.setattr(persistence_module.os, "replace", record_replace)
    assert m.save(target) == 1

    assert events[0:2] == ["fsync", "replace"]
    assert target.read_text() == "(synced value)\n"


def test_fast_load_refuses_a_different_swi_version_before_payload(m, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    path = tmp_path / "wrong-swi.fast"
    m.save(path, format="fast")
    header = path.read_bytes().split(b"\n", 1)[0]
    fields = header.split(b"\t")
    fields[3] = b"0.0.0"
    path.write_bytes(b"\t".join(fields) + b"\n")

    with pytest.raises(EngineError) as error:
        m.load(path)
    message = str(error.value)
    assert str(path) in message
    assert "SWI-Prolog version" in message
    assert "re-save" in message


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [(1, b"METTA-NOT-FAST", "magic tag"), (2, b"999", "format version")],
)
def test_fast_load_refuses_other_incompatible_headers(m, tmp_path, field, replacement, message):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    path = tmp_path / f"wrong-header-{field}.fast"
    m.save(path, format="fast")
    header = path.read_bytes().split(b"\n", 1)[0]
    fields = header.split(b"\t")
    fields[field] = replacement
    path.write_bytes(b"\t".join(fields) + b"\n")

    with pytest.raises(EngineError, match=message) as error:
        m.load(path)
    assert "re-save" in str(error.value)


def test_fast_load_reports_a_truncated_payload(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    path = tmp_path / "truncated.fast"
    with metta._new_space() as source, metta._new_space() as target:
        source.add(*(S.payload(i, S.value) for i in range(20)))
        source.save(path, format="fast")
        data = path.read_bytes()
        path.write_bytes(data[:-3])

        with pytest.raises(EngineError) as error:
            target.load(path)
        message = str(error.value)
        assert str(path) in message
        assert "corrupt or incomplete" in message
        assert "re-save" in message
        assert len(target) == 0


def test_gz_round_trips_both_formats_and_import(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    text_gz = tmp_path / "corpus.metta.gz"
    fast_gz = tmp_path / "corpus.fast.gz"
    with (
        metta._new_space() as source,
        metta._new_space() as from_text,
        metta._new_space() as from_fast,
        metta._new_space() as imported,
    ):
        source.run("(gz-fact one) (gz-fact two) (= (gz-next $x) (+ $x 1))")
        assert source.save(text_gz) == 3
        assert source.save(fast_gz, format="fast") == 3
        raw = text_gz.read_bytes()
        assert raw[:2] == b"\x1f\x8b"  # really gzip on disk
        assert b"gz-fact" not in raw  # compressed, not plain text
        assert from_text.load(text_gz) == []
        assert from_fast.load(fast_gz) == []
        for target in (from_text, from_fast):
            assert [row.x for row in target.match(S["gz-fact"](V.x))] == [
                S.one,
                S.two,
            ]
            assert target.run("!(gz-next 41)") == [[42]]
        # import! answers the unit value, the way add-atom and pragma! do.
        assert imported.run(f'!(import! (context-space) "{text_gz}")') == [[TRUE]]
        assert [row.x for row in imported.match(S["gz-fact"](V.x))] == [
            S.one,
            S.two,
        ]


def test_corrupt_gz_is_loud_and_names_the_file(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    bad = tmp_path / "broken.metta.gz"
    bad.write_bytes(b"\x1f\x8bnot really gzip")
    with metta._new_space() as target, pytest.raises(EngineError) as caught:
        target.load(bad)
    assert str(bad) in str(caught.value)


def test_fast_file_starts_with_the_magic_header(m, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    path = tmp_path / "header.fast"
    m.add(S.header(S.fact))
    m.save(path, format="fast")
    data = path.read_bytes()
    assert data.startswith(b"METTA-CACHE\tMETTA-FAST\t3\t")
    header = data.split(b"\n", 1)[0] + b"\n"
    assert re.fullmatch(rb"METTA-CACHE\tMETTA-FAST\t3\t\d+\.\d+\.\d+\t[0-9a-f]{64}\n", header)
    assert header[:-1].split(b"\t")[3].decode() == engine().info()["swi_prolog"]


def test_flipped_payload_byte_refuses_before_reading(metta, tmp_path):
    """The header's sha256 gates the payload: a single flipped byte, size
    unchanged, refuses on integrity before fast_read sees any byte.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    path = tmp_path / "flipped.fast"
    with metta._new_space() as source, metta._new_space() as target:
        source.add(*(S.payload(i, S.value) for i in range(20)))
        source.save(path, format="fast")
        data = bytearray(path.read_bytes())
        data[-1] ^= 0xFF
        path.write_bytes(bytes(data))

        with pytest.raises(EngineError) as error:
            target.load(path)
        message = str(error.value)
        assert str(path) in message
        assert "integrity" in message
        assert "corrupt or incomplete" in message
        assert len(target) == 0


try:
    from hypothesis import HealthCheck, given, settings
    from hypothesis import strategies as st
except ModuleNotFoundError:
    pass
else:

    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(st.lists(st.integers(-1_000_000, 1_000_000), max_size=40, unique=True))
    def test_fast_round_trip_preserves_generated_fact_lists(metta, tmp_path, values):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
        path = tmp_path / "generated.fast"
        with metta._new_space() as source, metta._new_space() as target:
            source.add(*(S["generated-value"](value) for value in values))
            assert source.save(path, format="fast") == len(values)
            assert target.load(path) == []
            assert [int(row.value) for row in target.match(S["generated-value"](V.value))] == values
