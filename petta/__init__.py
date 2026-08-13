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

import os
import threading
import importlib

CONSULTED = False
CONSULT_LOCK = threading.Lock()
janus = None
DEFAULT_STACK_LIMIT = 8_000_000_000

# Whether shim.pl has been consulted; owned by petta._engine.
_SHIM_LOADED = False


def _resolve_petta_path():
    """Locate the PeTTa runtime tree (src/, lib/, python/helper.pl).

    Prefers PETTA_PATH, then the runtime bundled in the installed package,
    then the source-tree root (editable installs and checkouts).
    """
    env_path = os.environ.get("PETTA_PATH")
    if env_path:
        return os.path.abspath(env_path)

    here = os.path.dirname(os.path.abspath(__file__))
    bundled = os.path.join(here, "_runtime")
    if os.path.exists(os.path.join(bundled, "src", "main.pl")):
        return bundled

    return os.path.abspath(os.path.join(here, os.pardir, os.pardir))


class PeTTa:
    """The original thin wrapper: swrite strings in, swrite strings out.

    Kept exactly as it was for existing callers; the rich surface is the
    MeTTa class beside it. Both share one consulted engine.
    """

    def __init__(self, verbose=False, petta_path=None):
        global CONSULTED, janus
        self.verbose = bool(verbose)
        if not CONSULTED:
            with CONSULT_LOCK:
                if not CONSULTED:
                    if petta_path is None:
                        petta_path = _resolve_petta_path()
                    morklib_file = os.path.join(petta_path, "mork_ffi", "target", "release", "libmork_ffi.so")
                    if os.path.exists(morklib_file):
                        orig_dir = os.getcwd()
                        os.chdir(petta_path)
                        janus = importlib.import_module("janus_swi")
                        janus.query_once(f"set_prolog_flag(stack_limit, {DEFAULT_STACK_LIMIT})")
                        os.chdir(orig_dir)
                        janus.query_once("set_prolog_flag(argv, ['mork'])")
                    else:
                        janus = importlib.import_module("janus_swi")
                        janus.query_once(f"set_prolog_flag(stack_limit, {DEFAULT_STACK_LIMIT})")
                    main_file = os.path.join(petta_path, "src", "main.pl")
                    helper_file = os.path.join(petta_path, "python", "helper.pl")
                    if not os.path.exists(main_file):
                        raise FileNotFoundError(
                            f"PeTTa runtime not found under {petta_path!r} "
                            f"(expected {main_file!r}). Set the PETTA_PATH "
                            "environment variable or pass petta_path to point at "
                            "a PeTTa checkout."
                        )
                    janus.consult(main_file)
                    janus.consult(helper_file)
                    CONSULTED = True

    def _run_helper(self, helper_name, argument):
        result = janus.query_once(
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
    V,
    Var,
    alpha_eq,
    decode,
    encode,
    expr,
    is_ground,
    parse,
    register_object_repr,
    register_object_repr_protocol,
    sym,
    unify,
    val,
    var,
    variables,
)
from .derivation import Builtin, Derivation, Fact, Step  # noqa: E402
from .errors import (  # noqa: E402
    DECLINE,
    CompileError,
    Decline,
    EngineError,
    MettaSyntaxError,
    PettaError,
)
from .ops import REFLECTION_SPACE  # noqa: E402
from .results import Row, Rows  # noqa: E402
from .space import MeTTa, Prepared, current_space  # noqa: E402
from . import (  # noqa: E402
    arrays,
    convert,
    foreign,
    integrate,
    matching,
    measure,
    multishot,
    soft,
    web,
)
from .define import Defined  # noqa: E402
from .foreign import SpaceProvider  # noqa: E402
from .subscribe import Event, Subscription  # noqa: E402

__version__ = "0.2.0"

__all__ = [
    # the legacy surface
    "PeTTa",
    # atoms
    "Atom",
    "Sym",
    "Var",
    "Gnd",
    "Expr",
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
    "register_object_repr",
    # runtime
    "MeTTa",
    "Prepared",
    "Rows",
    "Row",
    "REFLECTION_SPACE",
    # diagnostics
    "Derivation",
    "Step",
    "Fact",
    "Builtin",
    # errors
    "PettaError",
    "EngineError",
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
    "multishot",
    "soft",
    "web",
    "SpaceProvider",
    "Defined",
    "register_object_repr_protocol",
    # standing queries and context
    "Event",
    "Subscription",
    "current_space",
    "__version__",
]
