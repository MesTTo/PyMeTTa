"""Purpose: petta.backend_info() answers versions and the consulted tree
from returned data, in any suite order, and never starts the PeTTa
runtime just to answer; a subprocess pins the no-start guarantee in a
fresh interpreter where it is deterministic.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import os
import re
import subprocess
import sys
import threading
from pathlib import Path

import petta
from petta import _engine


def test_backend_info_reports_versions_and_consulted_tree():
    fresh = not _engine.started()

    info = petta.backend_info()

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
    if fresh:
        # Answering did not start the runtime, so there is no tree yet.
        assert info["petta_path"] is None
        assert not _engine.started()

    petta.MeTTa()
    petta_path = petta.backend_info()["petta_path"]

    assert isinstance(petta_path, str)
    runtime_tree = Path(petta_path)
    assert runtime_tree.is_dir()
    assert (runtime_tree / "src" / "main.pl").is_file()


def test_backend_info_never_starts_the_runtime():
    """The no-start guarantee, pinned where it is deterministic: a fresh
    interpreter answers every version and still has no runtime."""
    program = (
        "import petta\n"
        "from petta import _engine\n"
        "info = petta.backend_info()\n"
        "assert info['petta_path'] is None, info\n"
        "assert not _engine.started()\n"
        "assert info['janus'] and info['swi_prolog']\n"
        "print('NO-START-OK')\n"
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
    assert "NO-START-OK" in done.stdout


def test_engine_thread_owns_only_its_attachment(metta):
    observed = {}

    def work():
        observed["before"] = petta.janus.engine()
        with petta.engine_thread():
            observed["inside"] = petta.janus.engine()
            with petta.engine_thread():
                observed["nested"] = petta.janus.engine()
                observed["value"] = metta.value("(+ 20 22)")
            observed["after_nested"] = petta.janus.engine()
        observed["after"] = petta.janus.engine()
        try:
            with petta.engine_thread():
                raise LookupError("exceptional context exit")
        except LookupError:
            pass
        observed["after_exception"] = petta.janus.engine()

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

    home_engine = petta.janus.engine()
    with petta.engine_thread():
        assert petta.janus.engine() == home_engine
    assert petta.janus.engine() == home_engine
