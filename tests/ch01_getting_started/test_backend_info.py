"""Purpose: MeTTa.info() answers versions and the consulted tree
from returned data, in any suite order, and never starts the MeTTa
runtime just to answer; a subprocess pins the no-start guarantee in a
fresh interpreter where it is deterministic.
Guarantees:
  - a bare thread whose recycled identifier equals the runtime's boot-thread
    identifier is still classified by its live Janus attachment [tested:
    test_a_recycled_thread_identifier_never_selects_the_janus_fast_path;
    commit=af5821f5ffb7ce186e516706f003d02f5c1d3b4a]
  - booted() becomes true only after both the Python prelude and contract
    ontology finish, and either install retries after a one-off failure
    [tested: test_a_failed_python_runtime_install_retries_whole;
    commit=7f1b7a27ed5044c1df8885f4cdf831654dff25fc]
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
import pytest

import metta
from metta.parallel import engine_thread


@pytest.mark.parametrize("module_name", ["_prelude", "_contract"])
def test_a_failed_python_runtime_install_retries_whole(repo_root, module_name):
    """A completion flag cannot publish a prelude or ontology torn in half."""
    program = f"""
import metta
from metta import _contract, _engine, _prelude, parse

module = {module_name}
real_install = module.install
calls = []

def fail_once(runtime):
    calls.append(1)
    if len(calls) == 1:
        raise RuntimeError("one-off {{}} install failure".format(module.__name__))
    return real_install(runtime)

module.install = fail_once
try:
    metta.MeTTa(metta_path=".")
except RuntimeError as failure:
    assert "one-off" in str(failure)
else:
    raise AssertionError("the injected install failure did not leave boot")

assert not _engine.booted()
assert _engine._STATE.runtime is None

runtime = metta.MeTTa(metta_path=".")
assert calls == [1, 1]
assert _engine.booted()
assert runtime.run('!(py-len "abcd")') == [[4]]
assert runtime.runtime.do(
    "metta_py_contains", "&metta", parse("(: Declaration Type)").to_wire()
)
assert runtime.runtime.do(
    "metta_py_contains", "&metta", parse("(: nondet Determinism)").to_wire()
)
print("PYTHON-RUNTIME-INSTALL-RETRIED")
"""
    environment = os.environ | {
        "PYTHONPATH": str(repo_root / "extensions" / "python")
    }
    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=repo_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout.strip() == "PYTHON-RUNTIME-INSTALL-RETRIED"


def test_backend_info_reports_versions_and_consulted_tree():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    info = metta.engine().info()

    assert type(info) is dict
    assert set(info) == {
        "metta",
        "janus",
        "swi_prolog",
        "python",
        "metta_path",
    }
    for key in ("metta", "janus", "swi_prolog", "python"):
        assert re.fullmatch(r"\d+(?:\.\d+)+", info[key])
    assert info["python"] == ".".join(map(str, sys.version_info[:3]))
    metta_path = metta.engine().info()["metta_path"]

    assert isinstance(metta_path, str)
    runtime_tree = Path(metta_path)
    assert runtime_tree.is_dir()
    assert (runtime_tree / "engine" / "main.pl").is_file()


def test_engine_info_owns_the_runtime_it_reports():
    """The replacement is a verb on the process-default engine context."""
    program = (
        "import metta\n"
        "info = metta.engine().info()\n"
        "assert info['metta_path'], info\n"
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


def test_a_recycled_thread_identifier_never_selects_the_janus_fast_path():
    """A stale numeric identifier cannot stand in for an attached engine."""
    program = (
        "import threading\n"
        "import metta\n"
        "context = metta.MeTTa()\n"
        "runtime = context.runtime\n"
        "failure = []\n"
        "def cross():\n"
        "    runtime._home_thread = threading.get_ident()\n"
        "    try:\n"
        "        assert runtime._janus.engine() == -1\n"
        "        assert context.eval('( + 1 2 )') == [3]\n"
        "    except BaseException as exc:\n"
        "        failure.append(exc)\n"
        "worker = threading.Thread(target=cross)\n"
        "worker.start()\n"
        "worker.join()\n"
        "assert not failure, failure\n"
        "print('RECYCLED-THREAD-ID-SAFE')\n"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    done = subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        env=env,
    )

    assert done.returncode == 0, (done.returncode, done.stdout, done.stderr)
    assert "RECYCLED-THREAD-ID-SAFE" in done.stdout
