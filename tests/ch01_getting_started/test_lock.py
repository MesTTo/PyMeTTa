"""Purpose: pin `metta.lock` and `run --locked`.

What a program loaded is recorded by digest, and the refusal fires when the
tree no longer matches.

A lock is only worth having if the check is exact in both directions. It has
to stay silent when nothing changed, including across a write and a read back,
and it has to name EXACTLY what changed when one byte of one source moved.
Both directions are held here, along with the two refusals a lock can raise on
its own: a lock taken while a load is in flight, and one whose format this
build cannot read.

Guarantees:
  - a lock written and read back describes the same artefacts and its file is
    a fixed point [tested: test_a_lock_round_trips_through_its_file]
  - editing one source flips exactly one Drift
    [tested: test_editing_one_source_flips_exactly_one_drift]
  - a lock names the libraries a program imported, by the digest of both
    halves [tested: test_a_lock_pins_the_libraries_a_program_imported]
  - `run --locked` refuses on drift with a nonzero exit and runs on agreement
    [tested: test_a_locked_run_refuses_on_drift_and_runs_on_agreement]
  - the engine digest follows the engine's own sources
    [tested: test_the_engine_digest_follows_the_engines_sources]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

import metta
from metta import MeTTa, S, lib
from metta.errors import LockDrift, MettaError

_PACKAGE_ROOT = str(Path(__file__).resolve().parents[2])


def _program(directory: Path, text: str = "(= (answer) 1)\n!(answer)\n") -> Path:
    """One tiny program to load and pin."""
    path = directory / "facts.metta"
    path.write_text(text, encoding="utf-8")
    return path


def test_a_lock_round_trips_through_its_file(tmp_path):
    """A written lock reads back equal, and rewriting it beside itself is a fixed point."""
    program = _program(tmp_path)
    with MeTTa() as m:
        m.load(str(program))
        taken = m.lock()
        written = taken.write(tmp_path / "metta.lock")
        read = metta.Lock.read(written)

        assert read.engine == taken.engine
        assert [(Path(row.path).name, row.space, row.digest) for row in read.sources] == [
            (Path(row.path).name, row.space, row.digest) for row in taken.sources
        ]
        assert read.libraries == taken.libraries and read.pins == taken.pins
        assert read.text(base=tmp_path) == written.read_text(encoding="utf-8")
        assert m.check(read) == []


def test_a_lock_is_readable_toml_with_the_documented_tables(tmp_path):
    """The file is TOML anything reads, with the four tables the design names."""
    program = _program(tmp_path)
    with MeTTa() as m:
        m.load(str(program))
        written = m.lock().write(tmp_path / "metta.lock")

    document = tomllib.loads(written.read_text(encoding="utf-8"))

    assert document["lock-version"] == 1
    assert document["created-by"].startswith("metta ")
    assert set(document["engine"]) == {"metta", "swi-prolog", "sources"}
    assert document["engine"]["sources"].startswith("sha256:")
    # By NAME rather than by position: a lock pins what the PROCESS loaded, so
    # a suite that loaded other programs first has their rows here too.
    rows = [row for row in document["source"] if row["path"] == "facts.metta"]
    assert len(rows) == 1
    assert rows[0]["digest"].startswith("sha256:")
    assert set(rows[0]) == {"path", "space", "digest"}


def test_editing_one_source_flips_exactly_one_drift(tmp_path):
    """One edited byte names one entry and leaves every other agreeing."""
    program = _program(tmp_path)
    second = tmp_path / "other.metta"
    second.write_text("(= (other) 2)\n", encoding="utf-8")
    with MeTTa() as m:
        m.load(str(program))
        m.load(str(second))
        lock = m.lock()
        # A lock pins what the PROCESS loaded, so a suite that ran other
        # programs first carries their rows too; the claim is about what this
        # edit ADDS, which is the difference between the two checks.
        before = m.check(lock)

        program.write_text("(= (answer) 2)\n!(answer)\n", encoding="utf-8")
        added = [drift for drift in m.check(lock) if drift not in before]

    assert not [drift for drift in before if drift.name.endswith(("facts.metta", "other.metta"))]
    assert len(added) == 1
    assert added[0].kind == "source"
    assert added[0].name.endswith("facts.metta")
    assert added[0].expected != added[0].actual
    assert str(added[0]).endswith(" here")


def test_a_removed_source_drifts_as_not_present(tmp_path):
    """A locked file that is gone drifts with no digest rather than a wrong one."""
    program = _program(tmp_path)
    with MeTTa() as m:
        m.load(str(program))
        lock = m.lock()
        before = m.check(lock)
        program.unlink()
        added = [drift for drift in m.check(lock) if drift not in before]

    assert [drift.actual for drift in added] == [None]
    assert added[0].name.endswith("facts.metta")
    assert "not present here" in str(added[0])


def test_a_lock_pins_the_libraries_a_program_imported(tmp_path):
    """An imported library is one `[[library]]` row, by the digest of both halves."""
    program = _program(
        tmp_path, "!(import! &self (library lib_memo))\n(= (answer) 1)\n"
    )
    with MeTTa() as m:
        m.load(str(program))
        lock = m.lock()

    names = {row.name for row in lock.libraries}
    assert "lib_memo" in names
    assert {row.digest for row in lock.libraries} == {
        f"sha256:{metta.library.digest(name)}" for name in names
    }
    assert any(row.path.endswith("facts.metta") for row in lock.sources)
    # A library's files are covered by its [[library]] row and never repeated
    # as [[source]] rows, whichever half of it the import happened to read.
    assert not any("lib_memo" in row.path for row in lock.sources)


def test_a_lock_refuses_while_a_load_is_in_flight(tmp_path):
    """A lock taken during a load would record a half-loaded program.

    The probe runs from inside the load, which is the only moment the engine's
    load table is mid-write, and it reports the refusal it got rather than a
    lock it should never have been given.
    """
    taken: list[object] = []
    reported: list[str] = []

    with MeTTa() as m:

        @m.io
        def probe_lock() -> str:
            try:
                taken.append(m.lock())
            except MettaError as error:
                reported.append(str(error))
                return "refused"
            return "taken"

        program = _program(tmp_path, "!(probe-lock)\n")
        m.load(str(program))

    assert taken == []
    assert reported and "loading right now" in reported[0]


def test_a_newer_lock_version_is_refused_by_number(tmp_path):
    """A lock this build cannot read is refused by version, never read in part."""
    path = tmp_path / "metta.lock"
    path.write_text('lock-version = 99\ncreated-by = "metta 9.9"\n', encoding="utf-8")

    with pytest.raises(MettaError, match="lock-version 99"):
        metta.Lock.read(path)


def test_a_malformed_lock_is_refused_by_name(tmp_path):
    """A file that is not TOML is refused naming the file and the reason."""
    path = tmp_path / "metta.lock"
    path.write_text("this is not toml = = =\n", encoding="utf-8")

    with pytest.raises(MettaError, match="not readable as TOML"):
        metta.Lock.read(path)

    with pytest.raises(MettaError, match="cannot be read as a lock"):
        metta.Lock.read(tmp_path / "absent.lock")


def test_the_engine_digest_follows_the_engines_sources(tmp_path):
    """A planted engine tree's digest changes when one of its sources does."""
    from metta._lock import engine_digest

    first = tmp_path / "one"
    second = tmp_path / "two"
    for root, body in ((first, "a(1).\n"), (second, "a(2).\n")):
        (root / "engine").mkdir(parents=True)
        (root / "engine" / "unit.pl").write_text(body, encoding="utf-8")
        (root / "engine" / "prelude.pl").write_text("x(1).\n", encoding="utf-8")

    assert engine_digest(str(first)).startswith("sha256:")
    assert engine_digest(str(first)) != engine_digest(str(second))
    assert engine_digest(str(first)) == engine_digest(str(first))


def test_a_drifted_engine_names_the_field_that_moved(tmp_path):
    """An engine entry that no longer matches is one Drift naming its key."""
    program = _program(tmp_path)
    with MeTTa() as m:
        m.load(str(program))
        lock = m.lock()
        before = m.check(lock)
        moved = type(lock)(
            engine={**lock.engine, "metta": "0.0.1"},
            libraries=lock.libraries,
            sources=lock.sources,
            pins=lock.pins,
            base=lock.base,
        )
        added = [drift for drift in m.check(moved) if drift not in before]

    assert [(drift.kind, drift.name, drift.expected) for drift in added] == [
        ("engine", "metta", "0.0.1")
    ]


def test_a_lock_drift_refusal_names_every_entry_and_its_repair(tmp_path):
    """LockDrift carries the rows AND spells both repairs in its message."""
    from metta._lock import Drift, require

    program = _program(tmp_path)
    with MeTTa() as m:
        m.load(str(program))
        lock = m.lock()
        program.write_text("(= (answer) 3)\n", encoding="utf-8")
        with pytest.raises(LockDrift) as raised:
            require(m.runtime, lock, "metta.lock")
        assert any(drift.name.endswith("facts.metta") for drift in raised.value.drifts)

    assert "metta.lock no longer describes this tree" in str(raised.value)
    assert "re-pin with `metta lock -o <lock>`" in str(raised.value)
    assert raised.value.remedy is not None
    assert all(isinstance(drift, Drift) for drift in raised.value.drifts)


def test_a_locked_run_refuses_on_drift_and_runs_on_agreement(tmp_path):
    """`metta run --locked` gates the run on the lock, before the program runs."""
    program = _program(tmp_path)
    environment = {
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": _PACKAGE_ROOT,
        "HOME": str(tmp_path),
    }
    written = subprocess.run(
        [sys.executable, "-m", "metta", "lock", "facts.metta", "-o", "metta.lock"],
        check=True,
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
    )
    del written
    agreeing = subprocess.run(
        [sys.executable, "-m", "metta", "run", "--locked", "metta.lock", "facts.metta"],
        check=False,
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
    )

    program.write_text("(= (answer) 7)\n!(answer)\n", encoding="utf-8")
    drifted = subprocess.run(
        [sys.executable, "-m", "metta", "run", "--locked", "metta.lock", "facts.metta"],
        check=False,
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
    )

    assert agreeing.returncode == 0, agreeing.stderr
    assert agreeing.stdout.strip() == "1"
    assert drifted.returncode != 0
    assert "no longer describes this tree" in drifted.stderr
    assert "7" not in drifted.stdout


def test_the_cli_prints_a_card_and_a_lock(tmp_path):
    """`metta card` and `metta lock` are the shell faces of the two doors."""
    _program(tmp_path)
    environment = {
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": _PACKAGE_ROOT,
        "HOME": str(tmp_path),
    }
    card = subprocess.run(
        [sys.executable, "-m", "metta", "card", "lib_memo"],
        check=True,
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
    )
    printed = subprocess.run(
        [sys.executable, "-m", "metta", "lock", "facts.metta"],
        check=True,
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
    )

    assert card.stdout.startswith("lib_memo ")
    assert "memoize" in card.stdout
    assert f"digest sha256:{metta.library.digest('lib_memo')}" in card.stdout
    assert tomllib.loads(printed.stdout)["source"][0]["path"] == "facts.metta"


def test_a_library_handle_and_a_card_name_the_same_library():
    """`lib.memo` and `card("lib_memo")` are the same library, two doors."""
    assert lib.memo.form == S.library(S["lib_memo"])
    assert library_name_of(lib.memo.form) == metta.library.card("lib_memo").name


def library_name_of(form) -> str:
    """The library name inside a `(library name)` module form."""
    return form.children[1].name
