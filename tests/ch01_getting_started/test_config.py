"""Purpose: verify MeTTa's validated process-wide configuration surface.
Guarantees:
  - simultaneous writers retain their own pending mirror suspension
    [tested: test_bound_transaction_listeners_belong_to_each_writer; commit=8358dfc233bf299bb23eceddd94593a62372fe4b]
  - native configuration helpers do not enlarge the host predicate namespace
    [tested: test_native_configuration_helpers_stay_out_of_the_host_namespace;
    commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e]
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
import inspect
import os
import subprocess
import sys
from pathlib import Path

import pytest

import metta
import metta._binding.runtime as _engine
from metta import S, V
from metta._catalog.annotations import _bounded_product
from metta._catalog.bounds import Config
from metta._spaces.results import Rows


def test_native_configuration_helpers_stay_out_of_the_host_namespace(metta):
    """The exported mirror door keeps its transaction helpers private."""
    runtime = metta.runtime
    runtime.must(
        "predicate_property(metta_py_mirror_bounds, "
        "implementation_module(metta_python_bounds))"
    )
    private = runtime.must(
        "findall([_Name,_Arity], "
        "(current_predicate(metta_python_bounds:_Name/_Arity), "
        "functor(_Head,_Name,_Arity), "
        "predicate_property(metta_python_bounds:_Head, defined), "
        "\\+ predicate_property(metta_python_bounds:_Head, exported), "
        "\\+ predicate_property(metta_python_bounds:_Head, imported_from(_))), Private)"
    )["Private"]
    assert private
    for name, arity in private:
        runtime.must("\\+ current_predicate(user:Name/Arity)", Name=name, Arity=arity)


def test_setting_declaration_reaches_every_projection(metta, monkeypatch):
    """One added descriptor supplies parameters, environment, help and a row."""
    import textwrap

    from metta._catalog import bounds

    tool_path = Path(__file__).resolve().parents[2] / "tools"
    with monkeypatch.context() as patch:
        patch.syspath_prepend(str(tool_path))
        import boundsgen

    class FixtureConfig(bounds.Config):
        layout_fixture = bounds.Setting(
            3, "A bound declared by this fixture.", environment="METTA_LAYOUT_FIXTURE"
        )

    declaration = boundsgen.configure_source(FixtureConfig)
    namespace = {"_UNSET": bounds._UNSET, "_Unset": bounds._Unset}
    exec(textwrap.dedent(declaration), namespace)
    FixtureConfig.configure = namespace["configure"]
    empty = type("EmptyConfig", (Config,), dict.fromkeys(bounds.settings(Config)))
    exec(textwrap.dedent(boundsgen.configure_source(empty)), namespace)
    empty.configure = namespace["configure"]
    empty_config = empty({})
    empty_config.configure()
    assert empty_config.as_dict() == {}
    assert not inspect.signature(empty_config.configure).parameters
    configured = FixtureConfig({"METTA_LAYOUT_FIXTURE": "11"}, published=True)
    assert inspect.signature(configured.configure).parameters["layout_fixture"].kind == inspect.Parameter.KEYWORD_ONLY
    assert configured.layout_fixture == 11
    assert FixtureConfig.layout_fixture.__doc__ == "A bound declared by this fixture."
    assert "METTA_LAYOUT_FIXTURE" in boundsgen.documentation(FixtureConfig)
    assert "layout_fixture" in boundsgen.documentation(FixtureConfig)
    original = configured.as_dict()
    with pytest.raises(ValueError, match=r"layout_fixture.*positive"):
        configured.configure(display_rows=2, layout_fixture=0)
    assert configured.as_dict() == original

    runtime = metta._rt
    try:
        with monkeypatch.context() as patch:
            patch.setattr(bounds, "config", configured)
            assert bounds.publish(runtime) == 1
            assert configured.layout_fixture == 11
            configured.configure(layout_fixture=13)
            assert configured.layout_fixture == 13
            assert runtime.must(bounds._ONE_GOAL, Name="layout-fixture")["Values"] == [13]
    finally:
        for value in bounds._standing("layout_fixture"):
            runtime.apply_must("metta_py_remove", "&metta", bounds._row_atom("layout_fixture", value).to_wire())
        bounds._forget_bounds()


def test_setting_discovery_obeys_descriptor_inheritance_and_shadowing():
    """A shadowed descriptor is absent even when an ancestor declared it."""
    from metta._catalog.bounds import Setting, settings

    class Base:
        bound = Setting(3, "The inherited bound.")

    class Child(Base):
        other = Setting(5, "The child's bound.")

    class Shadow(Child):
        bound = None

    assert list(settings(Child)) == ["bound", "other"]
    assert list(settings(Shadow)) == ["other"]


@pytest.mark.parametrize("commit", [False, True])
def test_setting_publication_does_not_cache_another_threads_snapshot(metta, commit):
    """A reader between two writes sees committed rows and cannot stale the cache."""
    from concurrent.futures import ThreadPoolExecutor

    from metta._binding.runtime import engine_thread
    from metta._catalog import bounds

    original = bounds.config.display_rows

    def read():
        with engine_thread():
            return bounds.config.display_rows

    with ThreadPoolExecutor(max_workers=1) as pool:
        def change():
            bounds.config.configure(display_rows=7)
            assert pool.submit(read).result() == original
            assert bounds.config.display_rows == 7
            if not commit:
                msg = "discard the bound after the concurrent read"
                raise ValueError(msg)

        try:
            if commit:
                metta.transaction(change)
            else:
                with pytest.raises(ValueError, match="discard the bound"):
                    metta.transaction(change)
            assert not bounds._PENDING_TRANSACTIONS
            assert pool.submit(read).result() == (7 if commit else original)
            assert bounds.config.display_rows == (7 if commit else original)
        finally:
            bounds.config.configure(display_rows=original)


def test_configuration_refuses_a_false_publication_result(metta, monkeypatch):
    """A void crossing's false result is a failed setting update."""
    from metta._catalog import bounds
    from metta._errors.errors import EngineError

    original = bounds.config.display_rows
    command = metta._rt.do

    def refuse_add(predicate, *args):
        if predicate == "metta_py_add":
            return False
        return command(predicate, *args)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(metta._rt, "do", refuse_add)
            with pytest.raises(EngineError, match="engine refused setting 'display_rows'"):
                bounds.config.configure(display_rows=original + 1)
        assert bounds.config.display_rows == original
        assert not bounds._PENDING_TRANSACTIONS
    finally:
        bounds.config.configure(display_rows=original)


def test_bound_transaction_listeners_belong_to_each_writer(metta):
    """One writer finishing cannot remove another writer's completion listener."""
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from metta._binding.runtime import engine_thread
    from metta._catalog import bounds

    original = bounds.config.as_dict()
    both_changed = threading.Barrier(2)
    first_finished = threading.Event()

    def first():
        with engine_thread():
            def change():
                bounds.config.configure(display_rows=7)
                both_changed.wait()
                msg = "discard the first writer"
                raise ValueError(msg)

            try:
                with pytest.raises(ValueError, match="discard the first writer"):
                    metta.transaction(change)
            except BaseException:
                both_changed.abort()
                raise
            finally:
                first_finished.set()

    def second():
        with engine_thread():
            def change():
                bounds.config.configure(chunk_cap=8)
                both_changed.wait()
                first_finished.wait()
                assert set(bounds._PENDING_TRANSACTIONS) == {threading.get_ident()}
                assert bounds.config.chunk_cap == 8

            try:
                metta.transaction(change)
            except BaseException:
                both_changed.abort()
                raise

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(first), pool.submit(second)]
            for future in futures:
                future.result()
        assert not bounds._PENDING_TRANSACTIONS
        assert bounds.config.display_rows == original["display_rows"]
        assert bounds.config.chunk_cap == 8
    finally:
        bounds.config.configure(
            display_rows=original["display_rows"], chunk_cap=original["chunk_cap"]
        )


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


@pytest.mark.usefixtures("metta")
def test_configuration_publication_failure_restores_every_setting(monkeypatch):
    """A refused second row leaves both the rows and the local defaults intact."""
    from metta._catalog import bounds

    original = bounds.config.as_dict()
    local = bounds.config._values.copy()
    write = bounds._write_row

    def refuse_second(setting, value):
        if setting == "display_rows":
            msg = "injected setting publication failure"
            raise ValueError(msg)
        write(setting, value)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(bounds, "_write_row", refuse_second)
            with pytest.raises(ValueError, match="injected setting publication failure"):
                bounds.config.configure(declaration_limit=19, display_rows=7)
        assert bounds.config.as_dict() == original
        assert bounds.config._values == local
    finally:
        bounds.config.configure(
            declaration_limit=original["declaration_limit"],
            display_rows=original["display_rows"],
        )


def test_configuration_rows_and_mirror_follow_outer_rollback(metta):
    """An inner setting commit remains owned by the enclosing transaction."""
    from metta._catalog import bounds

    original = bounds.config.display_rows

    def change():
        bounds.config.configure(display_rows=7)
        assert bounds.config.display_rows == 7
        msg = "discard the enclosing transaction"
        raise ValueError(msg)

    try:
        with pytest.raises(ValueError, match="discard the enclosing transaction"):
            metta.transaction(change)
        assert bounds.config.display_rows == original
    finally:
        bounds.config.configure(display_rows=original)


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
    from metta._catalog.bounds import _ROW_BACKED, _STARTUP_SETTINGS

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
        "from metta._catalog.bounds import _MIRROR, _ROW_BACKED\n"
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
    from metta._catalog.bounds import _MIRROR

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
    from metta._catalog.bounds import _MIRROR

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
