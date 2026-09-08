"""Purpose: verify MeTTa's validated process-wide configuration surface.
Guarantees:
  - startup settings freeze after a successful consult while presentation
    settings remain live [tested: test_runtime_settings_freeze_after_startup,
    test_live_limits_control_declarations_and_rows; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - MORK startup never changes the host process working directory [tested
    test_backend_startup_does_not_change_process_working_directory;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

import metta
from metta import S, V, _engine
from metta._config import Config
from metta._type_annotations import _bounded_product
from metta.results import Rows


def test_configuration_reads_and_validates_environment():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    configured = Config(
        {
            "METTA_STACK_LIMIT": "64000000",
            "METTA_HEARTBEAT_INTERVAL": "25000",
            "METTA_DECLARATION_LIMIT": "64",
            "METTA_DISPLAY_ROWS": "7",
        }
    )
    # A bound with no METTA_* variable of its own keeps its shipped value:
    # it is set through configure() or through its own `(limit ...)` row.
    assert configured.as_dict() == {
        "stack_limit": 64_000_000,
        "heartbeat_interval": 25_000,
        "declaration_limit": 64,
        "display_rows": 7,
        "chunk_cap": 64,
        "subscription_queue": 10_000,
        "repr_items": 4,
    }
    with pytest.raises(ValueError, match=r"METTA_STACK_LIMIT.*positive integer"):
        Config({"METTA_STACK_LIMIT": "eight gigabytes"})
    with pytest.raises(ValueError, match=r"METTA_DISPLAY_ROWS.*positive"):
        Config({"METTA_DISPLAY_ROWS": "0"})


def test_configuration_updates_are_atomic():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    configured = Config({})
    before = configured.as_dict()
    with pytest.raises(ValueError, match=r"heartbeat_interval.*positive"):
        configured.configure(display_rows=3, heartbeat_interval=0)
    assert configured.as_dict() == before

    configured.configure(display_rows=3, declaration_limit=20)
    assert configured.display_rows == 3
    assert configured.declaration_limit == 20

    with pytest.raises(TypeError, match=r"stack_limit.*positive integer"):
        configured.stack_limit = True


def test_runtime_settings_freeze_after_startup():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    configured = Config({})
    with configured._startup() as startup:
        assert startup == (8_000_000_000, 100_000)

    configured.configure(stack_limit=8_000_000_000)
    with pytest.raises(RuntimeError, match=r"stack_limit.*runtime has started"):
        configured.stack_limit = 64_000_000
    configured.display_rows = 5
    assert configured.display_rows == 5

    retryable = Config({})
    with pytest.raises(RuntimeError, match="injected consult failure"), retryable._startup():
        msg = "injected consult failure"
        raise RuntimeError(msg)
    retryable.stack_limit = 64_000_000
    assert retryable.stack_limit == 64_000_000


def test_live_limits_control_declarations_and_rows():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    original = metta.config.as_dict()
    try:
        metta.config.configure(declaration_limit=3, display_rows=2)
        with pytest.raises(TypeError, match="over 3 superposed combinations"):
            list(_bounded_product([[1, 2], [3, 4]], "test declaration"))

        rows = Rows(("n",), [(1,), (2,), (3,)])
        assert "1 more rows" in repr(rows)
        assert rows._repr_html_().count("<tr>") == 4
    finally:
        metta.config.configure(
            declaration_limit=original["declaration_limit"],
            display_rows=original["display_rows"],
        )


def test_the_bounds_are_rows_a_program_can_read_and_replace(metta):
    """Every row-backed bound is a `(limit ...)` row, and the row is the source.

    The two startup settings are absent from the rows on purpose: they are
    arguments to the boot that creates the space the rows live in.
    """
    import metta as package
    from metta._config import _ROW_BACKED, _STARTUP_SETTINGS

    catalog = package.catalog
    rows = {
        str(answer.name).replace("-", "_"): answer.value.value
        for answer in catalog.match(S.limit(V.name, V.value))
    }
    assert set(rows) == set(_ROW_BACKED)
    assert not set(rows) & _STARTUP_SETTINGS
    assert rows["chunk_cap"] == package.config.chunk_cap

    original = package.config.display_rows
    try:
        metta.run("!(add-atom &metta (limit display-rows 3))")
        assert package.config.display_rows == 3
        rows_2 = Rows(("n",), [(1,), (2,), (3,), (4,)])
        assert "1 more rows" in repr(rows_2)
    finally:
        package.config.configure(display_rows=original)
    assert package.config.display_rows == original
    # configure() leaves exactly one row behind, so the override and the
    # setting cannot say different things afterwards.
    standing = list(catalog.match(S.limit(S["display-rows"], V.value)))
    assert len(standing) == 1


def test_a_bound_read_after_the_first_costs_no_crossing(metta):
    """A bound is a row AND costs what the constant it replaced cost.

    A cursor reads its chunk cap when it opens, so a crossing per read is a
    crossing per cursor: 21 inferences, and 3.2 of the 35 microseconds a
    one-answer `match` takes [measured 2026-09-08; command=python
    extensions/python/benchmarks/probes/bound_row_cost.py --read;
    fixture=a 50-atom space, 20,000 matches per arm, min of five]. The
    engine announces every `(limit ...)` write through
    `seam:catalog_row_changed/2` instead, and this seat mirrors what it read,
    so the cost does not grow with the number of reads. Two block sizes rather
    than a number: what has to hold is that reading a hundred times costs what
    reading ten times costs.
    """
    import metta as package

    space = metta.self
    space.add(S.n(1))
    assert package.config.chunk_cap
    space.match(S.n(V.x)).close()

    with metta.stats() as few:
        for _ in range(10):
            _ = package.config.chunk_cap
    with metta.stats() as many:
        for _ in range(1000):
            _ = package.config.chunk_cap
    assert many.inferences == few.inferences

    with metta.stats() as few_cursors:
        for _ in range(10):
            space.match(S.n(V.x)).close()
    with metta.stats() as many_cursors:
        for _ in range(100):
            space.match(S.n(V.x)).close()
    assert many_cursors.inferences == few_cursors.inferences


def test_the_first_bound_read_in_a_process_costs_no_crossing(tmp_path):
    """Boot seeds the mirror, so a program's OWN first read is a hit too.

    A read that fills the mirror costs three times a steady one, because its
    goal is also crossing for the first time, and the first `match` in a
    process was paying all of it: 96 inferences against a control's 35, where
    the second and third cost 33 either way. `publish` already reads the whole
    table to decide which rows to write, so it seeds every bound from that
    read and nothing is left to pay [measured 2026-09-08: 62 inferences either
    way for a one-match twin, against 123 before the seed; command=python
    extensions/python/tools/twin_coverage.py --measure
    examples/ch03-atoms-and-expressions/05-parse.metta; fixture=one twin in a
    fresh process; commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58].

    A fresh interpreter is the only place a FIRST read exists, so this takes
    one, the way the wall-bound probe in ch18 does.
    """
    probe = tmp_path / "first_bound_probe.py"
    probe.write_text(
        "import sys\n"
        "import metta\n"
        "from metta import MeTTa\n"
        "from metta._config import _MIRROR, _ROW_BACKED\n"
        "with MeTTa() as m:\n"
        "    with m.stats() as once:\n"
        "        first = metta.config.chunk_cap\n"
        "    with m.stats() as thousand:\n"
        "        for _ in range(1000):\n"
        "            _ = metta.config.chunk_cap\n"
        "    if once.inferences != thousand.inferences:\n"
        "        print(f'the first read crossed: {once.inferences} against "
        "{thousand.inferences} for a thousand', file=sys.stderr)\n"
        "        sys.exit(1)\n"
        "    seeded = {name: _MIRROR.get(name) for name in _ROW_BACKED}\n"
        "    if any(value is None for value in seeded.values()):\n"
        "        print(f'boot left a bound unseeded: {seeded}', file=sys.stderr)\n"
        "        sys.exit(1)\n"
        "    if first != seeded['chunk_cap']:\n"
        "        print(f'{first} is not the seeded {seeded}', file=sys.stderr)\n"
        "        sys.exit(1)\n"
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    spec = importlib.util.find_spec("metta")
    package_root = str(Path(spec.origin).resolve().parents[1])
    finished = subprocess.run(
        [sys.executable, str(probe)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env={**os.environ, "PYTHONPATH": package_root},
    )
    assert finished.returncode == 0, finished.stdout + finished.stderr


def test_a_bound_a_program_rewrites_reaches_the_next_read(metta):
    """The engine invalidates the mirror, so `add-atom` is the whole override.

    Both directions: a row landing beside the shipped one makes the new value
    the bound, and taking it away again leaves the shipped one standing. A
    removal cannot be applied as an update -- only the catalog knows what row
    was underneath -- so the announcement drops the entry and the next read
    asks.
    """
    import metta as package
    from metta._config import _MIRROR

    assert package.config.chunk_cap == 64
    try:
        metta.run("!(add-atom &metta (limit chunk-cap 8))")
        assert "chunk_cap" not in _MIRROR
        assert package.config.chunk_cap == 8
    finally:
        metta.run("!(remove-atom &metta (limit chunk-cap 8))")
    assert package.config.chunk_cap == 64


def test_a_bound_this_seat_does_not_know_forgets_every_mirrored_bound(metta):
    """A library's own bound, or an open position, forgets the whole mirror.

    The announcement carries a name, and a name outside this seat's table
    cannot be mapped to an entry to drop. Forgetting everything is the
    conservative answer: it costs one re-read per bound and can never leave a
    stale one behind.
    """
    import metta as package
    from metta._config import _MIRROR

    assert package.config.chunk_cap == 64
    assert _MIRROR
    try:
        metta.run("!(add-atom &metta (limit a-library-bound 3))")
        assert _MIRROR == {}
        assert package.config.chunk_cap == 64
    finally:
        metta.run("!(remove-atom &metta (limit a-library-bound 3))")


def test_backend_startup_does_not_change_process_working_directory(monkeypatch, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    runtime_root = tmp_path / "runtime"
    main_file = runtime_root / "engine" / "qlf_boot.pl"
    main_file.parent.mkdir(parents=True)
    main_file.touch()

    class Bridge:
        def __init__(self):
            self.queries = []
            self.consulted = []

        def query_once(self, goal):
            self.queries.append(goal)

        def consult(self, path):
            self.consulted.append(path)

    bridge = Bridge()
    monkeypatch.setattr(_engine.importlib, "import_module", lambda _name: bridge)
    # _consult_engine reaches janus through bridge(), which CACHES what it
    # imports in the process-wide _STATE so a missing engine is refused with
    # one diagnostic wherever it is first noticed. That cache would outlive
    # this test and hand every later one this stub, whose query_once takes no
    # inputs: setting it through monkeypatch is what puts it back.
    monkeypatch.setattr(_engine._STATE, "janus", None)

    def refuse_chdir(path):
        msg = f"engine startup changed directory to {path}"
        raise AssertionError(msg)

    monkeypatch.setattr(_engine.os, "chdir", refuse_chdir)
    runtime = _engine.Runtime.__new__(_engine.Runtime)
    consulted = runtime._consult_engine(str(runtime_root), 64_000_000)

    assert "set_prolog_flag(stack_limit, 64000000)" in bridge.queries
    # Every native backend that is built, naming none of them: the embedding
    # host used to test for MORK's shared library and pass `mork`.
    assert "set_prolog_flag(argv, ['extensions'])" in bridge.queries
    assert bridge.consulted == [str(main_file)]
    assert "metta_qlf_boot:qlf_load_engine" in bridge.queries
    assert consulted is bridge
