"""Purpose: launch the bundled PeTTa runtime through SWI-Prolog.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

# A launcher runs a program, which is the job rather than a risk; the call
# below says why the specific one is safe.
import subprocess  # nosec B404
import sys
from pathlib import Path

from ._config import config
from ._engine import _resolve_petta_path


def main(argv=None):
    """Run PeTTa's SWI-Prolog entry point and return its exit status."""
    if argv is None:
        argv = sys.argv[1:]

    runtime_root = Path(_resolve_petta_path())
    main_file = runtime_root / "src" / "main.pl"
    command = [
        "swipl",
        f"--stack_limit={config.stack_limit}",
        "-q",
        "-s",
        str(main_file),
        "--",
        *argv,
    ]

    # Every native backend that is built, and this launcher names none of them.
    # It used to test for MORK's shared library and LD_PRELOAD it, so a second
    # backend needed a second branch in a file that has nothing to do with
    # backends; whether one is usable is now that backend's own business, in
    # backends/*.pl. The preload was never load-bearing either: the backend
    # opens its own library with global visibility.
    command.append("backends")

    try:
        # The list form and never shell=True, so nothing here is parsed by a
        # shell. What B603 asks you to check is untrusted input, and the input
        # is the caller's own argv forwarded to the program they invoked. The
        # only element this file chooses is "swipl", resolved on PATH the way
        # every launcher resolves the interpreter it wraps.
        return subprocess.call(command)  # noqa: S603  # nosec B603
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            "PeTTa's command-line launcher needs the SWI-Prolog 'swipl' binary on PATH"
        ) from exc
