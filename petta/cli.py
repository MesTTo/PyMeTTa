"""Purpose: launch the bundled PeTTa runtime through SWI-Prolog.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import os
import subprocess
import sys

from . import _resolve_petta_path
from ._config import config


def main(argv=None):
    """Run PeTTa's SWI-Prolog entry point and return its exit status."""
    if argv is None:
        argv = sys.argv[1:]

    runtime_root = _resolve_petta_path()
    main_file = os.path.join(runtime_root, "src", "main.pl")
    command = [
        "swipl",
        f"--stack_limit={config.stack_limit}",
        "-q",
        "-s",
        main_file,
        "--",
        *argv,
    ]

    mork_library = os.path.join(
        runtime_root, "mork_ffi", "target", "release", "libmork_ffi.so"
    )
    env = None
    if os.path.isfile(mork_library):
        env = os.environ.copy()
        inherited = env.get("LD_PRELOAD")
        env["LD_PRELOAD"] = (
            os.pathsep.join((mork_library, inherited))
            if inherited
            else mork_library
        )
        command.append("mork")

    try:
        return subprocess.call(command, env=env)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            "PeTTa's command-line launcher needs the SWI-Prolog 'swipl' "
            "binary on PATH"
        ) from exc
