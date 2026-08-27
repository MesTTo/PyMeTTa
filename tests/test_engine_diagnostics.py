"""Purpose: the engine's own diagnostics belong to the host that embeds it. A
failing assertion is reported on stderr and never on the host's stdout.

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
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta import MeTTa
from metta.errors import AssertionFailure


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
