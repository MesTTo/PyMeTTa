"""Purpose: verify PeTTa's validated process-wide configuration surface.
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

import pytest

import metta
from metta import _engine
from metta._config import Config
from metta._type_annotations import _bounded_product
from metta.results import Rows


def test_configuration_reads_and_validates_environment():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    configured = Config(
        {
            "PETTA_STACK_LIMIT": "64000000",
            "PETTA_HEARTBEAT_INTERVAL": "25000",
            "PETTA_DECLARATION_LIMIT": "64",
            "PETTA_DISPLAY_ROWS": "7",
        }
    )
    assert configured.as_dict() == {
        "stack_limit": 64_000_000,
        "heartbeat_interval": 25_000,
        "declaration_limit": 64,
        "display_rows": 7,
    }
    with pytest.raises(ValueError, match=r"PETTA_STACK_LIMIT.*positive integer"):
        Config({"PETTA_STACK_LIMIT": "eight gigabytes"})
    with pytest.raises(ValueError, match=r"PETTA_DISPLAY_ROWS.*positive"):
        Config({"PETTA_DISPLAY_ROWS": "0"})


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


def test_backend_startup_does_not_change_process_working_directory(monkeypatch, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    runtime_root = tmp_path / "runtime"
    main_file = runtime_root / "engine" / "main.pl"
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

    def refuse_chdir(path):
        msg = f"engine startup changed directory to {path}"
        raise AssertionError(msg)

    monkeypatch.setattr(_engine.os, "chdir", refuse_chdir)
    runtime = _engine.Runtime.__new__(_engine.Runtime)
    consulted = runtime._consult_engine(str(runtime_root), 64_000_000)

    assert "set_prolog_flag(stack_limit, 64000000)" in bridge.queries
    # Every native backend that is built, naming none of them: the embedding
    # host used to test for MORK's shared library and pass `mork`.
    assert "set_prolog_flag(argv, ['backends'])" in bridge.queries
    assert bridge.consulted == [str(main_file)]
    assert consulted is bridge
