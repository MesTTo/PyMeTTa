"""Purpose: MeTTa.info() answers versions and the consulted tree
from returned data, in any suite order, and never starts the PeTTa
runtime just to answer; a subprocess pins the no-start guarantee in a
fresh interpreter where it is deterministic.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import os
import re
import subprocess
import sys
import threading
from pathlib import Path

import janus_swi

import petta
from petta.parallel import engine_thread


def test_backend_info_reports_versions_and_consulted_tree():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    info = petta.engine().info()

    assert type(info) is dict
    assert set(info) == {
        "petta",
        "janus",
        "swi_prolog",
        "python",
        "petta_path",
    }
    for key in ("petta", "janus", "swi_prolog", "python"):
        assert re.fullmatch(r"\d+(?:\.\d+)+", info[key])
    assert info["python"] == ".".join(map(str, sys.version_info[:3]))
    petta_path = petta.engine().info()["petta_path"]

    assert isinstance(petta_path, str)
    runtime_tree = Path(petta_path)
    assert runtime_tree.is_dir()
    assert (runtime_tree / "engine" / "main.pl").is_file()


def test_engine_info_owns_the_runtime_it_reports():
    """The replacement is a verb on the process-default engine context."""
    program = (
        "import petta\n"
        "info = petta.engine().info()\n"
        "assert info['petta_path'], info\n"
        "assert info['janus'] and info['swi_prolog']\n"
        "print('ENGINE-INFO-OK')\n"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    done = subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    assert done.returncode == 0, done.stderr
    assert "ENGINE-INFO-OK" in done.stdout


def test_engine_thread_owns_only_its_attachment(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    observed = {}

    def work():
        observed["before"] = janus_swi.engine()
        with engine_thread():
            observed["inside"] = janus_swi.engine()
            with engine_thread():
                observed["nested"] = janus_swi.engine()
                observed["value"] = metta._one("(+ 20 22)")
            observed["after_nested"] = janus_swi.engine()
        observed["after"] = janus_swi.engine()
        try:
            with engine_thread():
                msg = "exceptional context exit"
                raise LookupError(msg)  # noqa: TRY301  -- the raised exception is the deliberate catch-path probe exercised by this test
        except LookupError:
            pass
        observed["after_exception"] = janus_swi.engine()

    thread = threading.Thread(target=work)
    thread.start()
    thread.join()

    assert observed["before"] == -1
    assert observed["inside"] >= 0
    assert observed["nested"] == observed["inside"]
    assert observed["after_nested"] == observed["inside"]
    assert observed["value"] == 42
    assert observed["after"] == -1
    assert observed["after_exception"] == -1

    home_engine = janus_swi.engine()
    with engine_thread():
        assert janus_swi.engine() == home_engine
    assert janus_swi.engine() == home_engine
