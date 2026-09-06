"""Purpose: the engine's messages as ``metta.engine`` log records.

A warning and an error the engine prints both arrive as records at the level
their SWI kind maps to, carrying that kind and the source location SWI's own
prefix would have shown. The bridge ADDS a reader: SWI still writes its own
line to stderr, because a hook that succeeded would silence it. A library that
nobody configured stays quiet, and a broken handler cannot reach the engine.

Assumes:
  - capfd, not capsys. The engine writes through SWI's streams onto file
    descriptors 1 and 2, so the fd-level fixture is the only one that sees it
    [source: extensions/python/tests/ch10_errors_and_refusals/test_engine_diagnostics.py]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import logging

import pytest

from metta.errors import EngineError

#: A Prolog registration claims its name for the whole process, so each
#: scenario writes its own predicate rather than racing a sibling for one.
_SINGLETON = "{name}(X, 1).\n"
_BROKEN = "{name}(1) :- .\n"


@pytest.fixture()
def m(metta):
    """An isolated space carrying the door that consults a Prolog source."""
    with metta._new_space() as space:
        space.run("!(import! &self (library lib_import))")
        yield space


def _prolog(tmp_path, head, template):
    path = tmp_path / f"{head}.pl"
    path.write_text(template.format(name=head), encoding="utf-8")
    return path


def _engine_records(caplog):
    return [r for r in caplog.records if r.name == "metta.engine"]


def test_an_engine_warning_becomes_a_warning_record(m, tmp_path, caplog):
    """Carry SWI's ``warning`` kind and the file the message names.

    A singleton variable in a consulted Prolog source is that kind, and it
    is emitted with a source location, so the record has both halves.
    """
    head = "wrn_singleton"
    path = _prolog(tmp_path, head, _SINGLETON)
    with caplog.at_level(logging.DEBUG, logger="metta.engine"):
        m.run(f'!(import_prolog_functions_from_file "{path}" ({head}))')

    warnings = [r for r in _engine_records(caplog) if r.levelno == logging.WARNING]
    assert warnings, f"no warning record arrived: {caplog.records}"
    record = warnings[-1]
    assert "Singleton variables" in record.getMessage()
    assert record.metta_kind == "warning"
    assert record.metta_file == str(path)
    assert record.metta_line == 1


def test_an_engine_error_becomes_an_error_record(m, tmp_path, caplog):
    """A syntax error in a consulted source is SWI's ``error`` kind.

    The engine still raises its own refusal: the bridge reads the message,
    it does not take it.
    """
    head = "wrn_broken"
    path = _prolog(tmp_path, head, _BROKEN)
    with caplog.at_level(logging.DEBUG, logger="metta.engine"):
        with pytest.raises(EngineError):
            m.run(f'!(import_prolog_functions_from_file "{path}" ({head}))')

    errors = [r for r in _engine_records(caplog) if r.levelno == logging.ERROR]
    assert errors, f"no error record arrived: {caplog.records}"
    assert "Syntax error" in errors[-1].getMessage()
    assert errors[-1].metta_kind == "error"


def test_the_engine_still_prints_its_own_message(m, tmp_path, capfd, caplog):
    """The hook fails after recording, so SWI prints as it always did.

    A thread_message_hook that SUCCEEDS is read as "handled": SWI calls
    neither message_hook/3 nor the printer. Reading a message must not
    silence it, and this is the assertion that would fail if the hook ever
    stopped failing.
    """
    head = "wrn_printed"
    path = _prolog(tmp_path, head, _SINGLETON)
    capfd.readouterr()
    with caplog.at_level(logging.DEBUG, logger="metta.engine"):
        m.run(f'!(import_prolog_functions_from_file "{path}" ({head}))')
    seen = capfd.readouterr()

    assert "Singleton variables" in seen.err, (
        f"the engine stopped printing its own warning: {seen.err!r}"
    )
    assert _engine_records(caplog), "and the record was not delivered either"


def test_a_broken_handler_cannot_poison_the_crossing(m, tmp_path, caplog):
    """A handler that raises is logging's own problem, not the engine's.

    Nothing raised on the Python side of the hook may cross back, because it
    would land in whichever engine call happened to be running.
    """

    class Broken(logging.Handler):
        def emit(self, record):
            msg = f"broken on purpose while emitting {record.levelname}"
            raise RuntimeError(msg)

    head = "wrn_handler"
    path = _prolog(tmp_path, head, _SINGLETON)
    logger = logging.getLogger("metta.engine")
    broken = Broken()
    raising = logging.raiseExceptions
    logging.raiseExceptions = False
    logger.addHandler(broken)
    try:
        with caplog.at_level(logging.DEBUG, logger="metta.engine"):
            m.run(f'!(import_prolog_functions_from_file "{path}" ({head}))')
        assert m.run("!(+ 1 2)")[0][0] == 3, "the engine survived the handler"
    finally:
        logger.removeHandler(broken)
        logging.raiseExceptions = raising


def test_the_package_root_carries_the_library_null_handler():
    """Keep an unconfigured record off ``logging.lastResort``.

    That handler prints at WARNING, so without a NullHandler on the package
    root an engine warning would print a second time from Python after SWI
    had already written it to stderr.
    """
    handlers = logging.getLogger("metta").handlers
    assert any(isinstance(handler, logging.NullHandler) for handler in handlers)


def test_the_kind_map_covers_swis_own_levels():
    """Map every SWI kind that reaches Python to a level.

    `silent` is dropped engine-side, and a kind with no row is INFO rather
    than absent.
    """
    from metta._engine import _MESSAGE_LEVELS, engine_message

    assert _MESSAGE_LEVELS["error"] == logging.ERROR
    assert _MESSAGE_LEVELS["warning"] == logging.WARNING
    assert _MESSAGE_LEVELS["informational"] == logging.INFO
    # `information` is SWI's other informational kind, the one time/1 prints
    # at, rather than a misspelling of the first.
    assert _MESSAGE_LEVELS["information"] == logging.INFO
    assert _MESSAGE_LEVELS["debug"] == logging.DEBUG
    assert "silent" not in _MESSAGE_LEVELS
    assert engine_message("banner", "a kind with no row", "", -1) is True
