"""Purpose: the engine's own diagnostics and its verbosity belong to the host
that embeds it. A failing assertion is reported on stderr and never on the
host's stdout, and verbosity is set through published engine surface rather
than through a setter each binding writes for itself.

Assumes:
  - capfd, not capsys. The engine writes through SWI's own streams onto file
    descriptors 1 and 2; nothing it prints passes through Python's
    sys.stdout, so the fd-level fixture is the only one that sees it
    [source: bindings/python/tests/test_p2b_matching_core.py, which reads
    engine annotations the same way]
Guarantees:
  - a failing assertEqual leaves the embedding process's stdout carrying only
    that process's own writes, while the report itself is on stderr
    [tested: test_a_failing_assertion_stays_off_the_hosts_stdout]
  - MeTTa(verbose=...) reaches engine/filereader.pl's metta_host_set_silent/1
    and the engine's trace follows it, with no binding-private setter left in
    the process and no binding source writing silent/1 itself
    [tested: test_verbosity_is_a_published_engine_door,
    test_no_binding_carries_its_own_verbosity_setter]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import re

import pytest

from metta import MeTTa
from metta.errors import AssertionFailure

# Any binding writing the engine's print-suppression flag for itself. Built
# from parts so this file is not its own first offender: the pattern's source
# text spells the parenthesis escaped, and the thing being looked for does not.
_WRITES_THE_FLAG = re.compile(r"assertz\(\s*silent\(")

_BINDING_SOURCE = ("*.pl", "*.py", "*.c", "*.h", "*.ts", "*.mjs", "*.js")


@pytest.fixture
def _verbosity_restored(metta):
    """Put the process-wide verbosity back, whatever the test did to it.

    One engine per process and one flag in it, so a test that turns the
    engine's trace on and leaves it on makes every later output-reading test
    in the same worker read compiled goals it never asked for.
    """
    was = metta.runtime.verbose
    yield
    MeTTa(verbose=was)


def test_a_failing_assertion_stays_off_the_hosts_stdout(metta, capfd,
                                                        _verbosity_restored):
    """assert/2 reports through print_message/2, so the report is on stderr.

    It used to be a bare format/2, which writes to current_output: for a host
    that embeds SWI in its own process that is the HOST's stdout, and no
    binding can suppress it without redirecting output the host owns (CeTTa
    C12 filed exactly that, from C).
    """
    MeTTa(verbose=False)
    capfd.readouterr()

    # The beacon makes the stdout claim below falsifiable. Without it an
    # engine that had stopped writing to stdout and a capture that was never
    # reading it would look exactly the same from here.
    metta.run('!(println! "petta-stdout-beacon")')
    with pytest.raises(AssertionFailure):
        metta.run("!(assertEqual 1 2)")
    seen = capfd.readouterr()

    assert "petta-stdout-beacon" in seen.out, (
        "the beacon never reached stdout, so this test cannot tell a clean "
        "stdout from one it is not reading"
    )
    assert "MeTTa assertion failed" in seen.err, (
        "the assertion failure was not reported at all; moving it off stdout "
        "must not mean losing it"
    )
    assert "assertion failed" not in seen.out.lower(), (
        f"the engine wrote its assertion report to the host's stdout: "
        f"{seen.out!r}"
    )
    assert "collapse 1" not in seen.out, (
        f"the failing form reached the host's stdout: {seen.out!r}"
    )


def test_verbosity_is_a_published_engine_door(metta, capfd, _verbosity_restored):
    """MeTTa(verbose=...) sets the engine's flag and the trace follows it.

    The flag is decided from argv at load time, which an embedded host has
    none of, so this is the only route a library caller has. It runs through
    the engine's metta_host_set_silent/1; the two seats that each wrote that
    setter privately are gone.
    """
    MeTTa(verbose=True)
    capfd.readouterr()
    metta.run("!(+ 1 2)")
    loud = capfd.readouterr().out

    MeTTa(verbose=False)
    metta.run("!(+ 1 2)")
    quiet = capfd.readouterr().out

    assert "metta runnable" in loud, (
        f"asking for verbosity produced no engine trace: {loud!r}"
    )
    assert "metta runnable" not in quiet, (
        f"the engine kept tracing after verbosity was turned off: {quiet!r}"
    )


def test_no_binding_carries_its_own_verbosity_setter(metta, repo_root):
    """One writer for the flag, and it is the engine's.

    bindings/python and bindings/cetta each carried the identical
    retract-then-assert under a private name, and engine/filereader.pl's own
    export comment named the first of them, so the engine depended on a
    binding's internals. The scoreboard in test_shim_surface.py pins that the
    replacement is DECLARED; this pins that the copies are gone and that a
    third binding cannot quietly grow one.
    """
    runtime = metta.runtime
    assert runtime.once("current_predicate(metta_host_set_silent/1)"), (
        "the published door is not defined in the running engine"
    )
    for private in ("petta_py_set_silent/1", "petta_c_set_silent/1"):
        assert runtime.once(f"current_predicate({private})") == {}, (
            f"{private} is still defined; the binding-private setter it "
            f"replaces was supposed to leave with the door's arrival"
        )

    bindings = repo_root / "bindings"
    offenders = sorted(
        str(path.relative_to(repo_root))
        for pattern in _BINDING_SOURCE
        for path in bindings.rglob(pattern)
        if "node_modules" not in path.parts
        and _WRITES_THE_FLAG.search(path.read_text(encoding="utf-8", errors="ignore"))
    )
    assert not offenders, (
        f"these binding sources set the engine's silent/1 themselves rather "
        f"than through metta_host_set_silent/1: {offenders}"
    )
