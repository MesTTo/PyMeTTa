"""Purpose: a keyboard interrupt reaches a running evaluation. The runtime
installs janus's heartbeat at startup, so SIGINT during a long engine goal
raises KeyboardInterrupt promptly instead of queueing until the goal ends.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import os
import signal
import subprocess
import sys
import textwrap
import time


def test_sigint_interrupts_a_running_evaluation():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The spin would run for minutes; the test passes only because the
    # heartbeat lets the signal through in well under the timeout.
    program = textwrap.dedent(
        """
        import sys

        from metta import MeTTa

        m = MeTTa().space("&sigint-probe")
        m.run("(= (spin $n) (if (== $n 0) done (spin (- $n 1))))")
        print("READY", flush=True)
        try:
            m.run(
                "!(with-pragma! ((max-stack-depth 4000000000)) "
                "(spin 1000000000))"
            )
            print("FINISHED", flush=True)
        except KeyboardInterrupt:
            print("INTERRUPTED", flush=True)
            sys.exit(42)
        """
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    proc = subprocess.Popen(
        [sys.executable, "-c", program],
        stdout=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        assert proc.stdout.readline().strip() == "READY"
        time.sleep(0.5)  # well inside the engine goal by now
        proc.send_signal(signal.SIGINT)
        out, _ = proc.communicate(timeout=30)
    finally:
        if proc.poll() is None:
            proc.kill()
    assert proc.returncode == 42, out
    assert "INTERRUPTED" in out
