"""Purpose: launch the bundled PeTTa runtime through SWI-Prolog.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

# A launcher runs a program, which is the job rather than a risk; the call
# below says why the specific one is safe.
import subprocess  # nosec B404
import sys
from pathlib import Path

from ._config import config
from ._engine import _resolve_petta_path

#: The two flags the launcher answers itself. Everything else is forwarded,
#: because this command keeps UPSTREAM'S LAUNCHER CONTRACT: it runs a file
#: through swipl directly, and the subcommand surface is `python -m petta`
#: (website/guide/getting-started.md states the split deliberately). These two
#: are answered here only because forwarding them produced
#: `source_sink '--version' does not exist`, an engine error about a missing
#: FILE, which is not an answer a released command may give to the one flag
#: every installed tool is asked first. They are answered ONLY as the whole
#: command line, so a program taking its own `--help` still receives it
#: [tested: test_the_launcher_answers_version_and_help_without_booting].
SELF_ANSWERED = ("--version", "-V", "--help", "-h")

USAGE = """usage: petta [FILE ...]

Run a MeTTa program on the bundled PeTTa engine, through swipl.
Every other argument is passed to the program.

  petta program.metta     run a program
  petta --version         print the version

The subcommand surface is `python -m petta` (run, repl, serve, boot, lint,
doc). The Python surface is `import petta`."""


def main(argv=None):
    """Run PeTTa's SWI-Prolog entry point and return its exit status."""
    if argv is None:
        argv = sys.argv[1:]

    if len(argv) == 1 and argv[0] in SELF_ANSWERED:
        # Deferred, so answering a flag boots nothing.
        from ._version import __version__  # noqa: PLC0415

        print(f"petta {__version__}" if argv[0] in ("--version", "-V") else USAGE)
        return 0

    runtime_root = Path(_resolve_petta_path())
    main_file = runtime_root / "engine" / "main.pl"
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
        msg = "PeTTa's command-line launcher needs the SWI-Prolog 'swipl' binary on PATH"
        raise FileNotFoundError(
            msg
        ) from exc
