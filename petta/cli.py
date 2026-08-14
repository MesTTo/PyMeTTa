"""Purpose: launch the bundled PeTTa runtime through SWI-Prolog.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import os
import subprocess
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

    mork_library = runtime_root / "mork_ffi" / "target" / "release" / "libmork_ffi.so"
    env = None
    if mork_library.is_file():
        env = os.environ.copy()
        inherited = env.get("LD_PRELOAD")
        env["LD_PRELOAD"] = (
            os.pathsep.join((str(mork_library), inherited))
            if inherited
            else str(mork_library)
        )
        command.append("mork")

    try:
        return subprocess.call(command, env=env)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            "PeTTa's command-line launcher needs the SWI-Prolog 'swipl' binary on PATH"
        ) from exc
