"""Purpose: the petta package: PeTTa's Python surface. The legacy PeTTa class
keeps its exact contract (swrite strings through helper.pl), and the rich
surface lives beside it: atoms as Python values, the MeTTa runtime class,
Python-backed MeTTa functions, structured queries and proof trees.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None

    from petta import MeTTa, S, V

    m = MeTTa()
    m.run("(= (foo) boo) !(foo)")        # [[Sym('boo')]]
    m.add(S.Parent(S.Tom, S.Bob))
    m.query(S.Parent(V.x, S.Bob))        # Rows[x](Row(x=Sym('Tom')))
"""

import logging
import sys

from . import _engine
from ._config import Config, config
from ._version import __version__

# A library stays silent until its host configures the petta logger.
logging.getLogger(__name__).addHandler(logging.NullHandler())

janus = _engine.bridge()


class PeTTa:
    """The original thin wrapper: swrite strings in, swrite strings out.

    Kept exactly as it was for existing callers; the rich surface is the
    MeTTa class beside it. Both share one consulted engine.
    """

    def __init__(self, verbose=False, petta_path=None):
        self.verbose = bool(verbose)
        self._runtime = _engine.runtime(petta_path=petta_path, verbose=self.verbose)

    def _run_helper(self, helper_name, argument):
        result = self._runtime._janus.query_once(
            "run_metta_helper(Verbose, HelperName, Argument, Results)",
            {
                "Verbose": "true" if self.verbose else "false",
                "HelperName": helper_name,
                "Argument": argument,
            },
        )
        if result is None:
            return []
        return result.get("Results", [])

    def load_metta_file(self, file_path) -> str:
        """Compile a MeTTa file to Prolog and return the results of the run."""
        return self._run_helper("load_metta_file", file_path)

    def process_metta_string(self, metta_code) -> str:
        """Compile a string of MeTTa code to Prolog and return the results of the run."""
        return self._run_helper("process_metta_string", metta_code)


from .atoms import (  # noqa: E402
    Atom,
    Expr,
    Gnd,
    S,
    Sym,
    Undefined,
    V,
    Var,
    alpha_eq,
    decode,
    encode,
    expr,
    is_ground,
    map_atoms,
    parse,
    register_object_repr,
    register_object_repr_protocol,
    sym,
    unify,
    val,
    var,
    variables,
)
from .derivation import Builtin, Derivation, Fact, Step, Truncated  # noqa: E402
from .errors import (  # noqa: E402
    DECLINE,
    CompileError,
    Decline,
    EngineError,
    InferenceLimitError,
    Interrupted,
    MettaSyntaxError,
    PettaError,
    ResourceLimitError,
    TimeLimitError,
)
from .ops import REFLECTION_SPACE  # noqa: E402
from .results import Row, Rows  # noqa: E402
from .space import Cursor, EngineProfile, MeTTa, Prepared, current_space  # noqa: E402
from . import aio, arrays, convert, das, foreign, integrate, lint, matching, measure, persistent, remote, testing, trace  # noqa: E402
from .casting import CastError, cast  # noqa: E402
from .define import Defined  # noqa: E402
from ._engine import engine_thread  # noqa: E402
from .foreign import (  # noqa: E402
    Adder,
    Clearer,
    Enumerable,
    Matcher,
    Remover,
    SpaceProvider,
)
from .subscribe import Event, Subscription, bridge  # noqa: E402

def backend_info() -> dict[str, str | None]:
    """Return backend versions and the PeTTa runtime tree in use.

    This function does not start the PeTTa runtime. The petta_path value is
    None until a MeTTa runtime exists.
    """
    janus_bridge = _engine.bridge()
    swi_version_num = janus_bridge.query_once(
        "current_prolog_flag(version, SwiVersion)"
    )["SwiVersion"]
    active = _engine.active_runtime()
    return {
        "petta": __version__,
        "janus": janus_bridge.version_str(),
        "swi_prolog": janus_bridge.version_str(swi_version_num),
        "python": (
            f"{sys.version_info.major}.{sys.version_info.minor}."
            f"{sys.version_info.micro}"
        ),
        "petta_path": (
            None if active is None else active.petta_path
        ),
    }


__all__ = [
    # the legacy surface
    "PeTTa",
    "Config",
    "config",
    # atoms
    "Atom",
    "Sym",
    "Var",
    "Gnd",
    "Expr",
    "Undefined",
    "S",
    "V",
    "sym",
    "var",
    "val",
    "expr",
    "encode",
    "decode",
    "parse",
    "alpha_eq",
    "unify",
    "variables",
    "is_ground",
    "map_atoms",
    "register_object_repr",
    "cast",
    "CastError",
    # runtime
    "MeTTa",
    "Prepared",
    "Cursor",
    "EngineProfile",
    "engine_thread",
    "Rows",
    "Row",
    "REFLECTION_SPACE",
    # diagnostics
    "backend_info",
    "Derivation",
    "Step",
    "Fact",
    "Builtin",
    "Truncated",
    # errors
    "PettaError",
    "EngineError",
    "ResourceLimitError",
    "TimeLimitError",
    "InferenceLimitError",
    "Interrupted",
    "MettaSyntaxError",
    "CompileError",
    "Decline",
    "DECLINE",
    # the general integration surface
    "integrate",
    "convert",
    "arrays",
    "foreign",
    "matching",
    "measure",
    "Matcher",
    "Enumerable",
    "Adder",
    "Remover",
    "Clearer",
    "SpaceProvider",
    "Defined",
    "register_object_repr_protocol",
    # standing queries and contexts
    "Event",
    "Subscription",
    "bridge",
    "remote",
    "aio",
    "das",
    "lint",
    "persistent",
    "testing",
    "trace",
    "current_space",
    "__version__",
]
