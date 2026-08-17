"""Purpose: the petta package: PeTTa's Python surface. The legacy PeTTa class
keeps its exact contract (swrite strings through helper.pl), and the rich
surface lives beside it: atoms as Python values, the MeTTa runtime class,
Python-backed MeTTa functions, structured queries and proof trees.
Guarantees:
  - importing petta and petta.cli does not require janus_swi until an
    engine-backed API is used [tested test_package_import_does_not_require_janus]
  - optional integration modules load only when requested [tested
    test_optional_surfaces_load_only_when_requested]
  - contextual name and save-format types are available at package level
    [tested test_public_context_types_are_distinct]
  - atom formatter registrations have public removal counterparts [tested
    test_object_repr_registrations_can_be_removed_exactly]
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

import functools
import importlib
import logging
import sys

from . import _engine
from ._api_types import MettaName, SaveFormat, SpaceName
from ._config import Config, config
from ._version import __version__

# A library stays silent until its host configures the petta logger.
logging.getLogger(__name__).addHandler(logging.NullHandler())

_LAZY_MODULES = frozenset(
    {
        "aio",
        "arrays",
        "das",
        "parallel",
        "persistent",
        "remote",
        "spaces",
        "structures",
        "testing",
    }
)


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


def __getattr__(name: str):
    """Resolve optional modules and the Janus bridge only when requested."""
    if name == "janus":
        return _engine.bridge()
    if name in _LAZY_MODULES:
        module = importlib.import_module(f".{name}", __name__)
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Include lazy public modules in package discovery."""
    return sorted(globals().keys() | _LAZY_MODULES | {"janus"})


from . import (  # noqa: E402
    convert,
    foreign,
    integrate,
    lint,
    trace,
)
from ._engine import engine_thread  # noqa: E402
from .answer import Answer, Bindings  # noqa: E402
from .atoms import (  # noqa: E402
    Atom,
    Expr,
    Gnd,
    Handle,
    S,
    Sym,
    Undefined,
    V,
    Var,
    alpha_eq,
    atom_from_wire,
    decode,
    encode,
    expr,
    is_ground,
    map_atoms,
    order_key,
    parse,
    register_object_repr,
    register_object_repr_protocol,
    sym,
    unify,
    unregister_object_repr,
    unregister_object_repr_protocol,
    val,
    var,
    variables,
)
from .casting import CastError, cast  # noqa: E402
from .define import Defined  # noqa: E402
from .derivation import Builtin, Derivation, Fact, Step, Truncated  # noqa: E402
from .errors import (  # noqa: E402
    DECLINE,
    CompileError,
    Decline,
    EngineError,
    InferenceLimitError,
    Interrupted,
    MettaOperationError,
    MettaResultError,
    MettaSyntaxError,
    PettaError,
    ResourceLimitError,
    SourceNotFound,
    StrictError,
    TimeLimitError,
)
from .foreign import (  # noqa: E402
    Adder,
    Clearer,
    CustomMatch,
    Enumerable,
    Matcher,
    Remover,
    SpaceProvider,
)
from .ops import REFLECTION_SPACE, record  # noqa: E402
from .results import Row, Rows  # noqa: E402
from .space import Cursor, EngineProfile, MeTTa, Prepared, current_space  # noqa: E402
from .subscribe import Event, Subscription, bridge  # noqa: E402

# ------------------------------------------------------ the module-level tier
# Tier 1 of the ladder: one lazily created default engine behind module
# functions, random's and logging's own shape. The hidden instance is fine
# because the sugar is thin, named, and escapable: every function below is
# one line over MeTTa(), and default_engine() hands the instance over the
# moment control is wanted. There is deliberately no module-level space():
# petta.space is the space MODULE, a public import target, and a function
# would clobber it; spell it default_engine().space(name).

@functools.cache
def default_engine() -> MeTTa:
    """The engine behind the module-level functions, created on first
    use: escape hatch and inspection point in one. Construct MeTTa()
    yourself for isolation; there is one engine per process either way,
    so this is about who holds the handle, not about capacity.
    functools.cache carries the once-and-locked semantics."""
    return MeTTa()


def run(source: str, **kwargs):
    """Run MeTTa source. Sugar for MeTTa().run(...); construct your own
    engine for isolation."""
    return default_engine().run(source, **kwargs)


def query(*patterns, **kwargs):
    """Query patterns as one conjunction. Sugar for MeTTa().query(...);
    construct your own engine for isolation."""
    return default_engine().query(*patterns, **kwargs)


def add(*atoms):
    """Add atoms. Sugar for MeTTa().add(...); construct your own engine
    for isolation."""
    return default_engine().add(*atoms)


def remove(atom):
    """Remove every copy of an atom. Sugar for MeTTa().remove(...);
    construct your own engine for isolation."""
    return default_engine().remove(atom)


def eval(target, **kwargs):
    """Evaluate a term, every answer. Sugar for MeTTa().eval(...);
    construct your own engine for isolation."""
    return default_engine().eval(target, **kwargs)


def fn(name: str):
    """An engine function as a Python callable. Sugar for
    MeTTa().fn(...); construct your own engine for isolation."""
    return default_engine().fn(name)


def backend_info() -> dict[str, str | None]:
    """Return backend versions and the PeTTa runtime tree in use.

    This function does not start the PeTTa runtime. The petta_path value is
    None until a MeTTa runtime exists.
    """
    janus_bridge = _engine.bridge()
    version_row = janus_bridge.query_once("current_prolog_flag(version, SwiVersion)")
    if version_row is None or not isinstance(version_row.get("SwiVersion"), int):
        raise EngineError("janus did not report the running SWI-Prolog version")
    swi_version_num = version_row["SwiVersion"]
    active = _engine.active_runtime()
    return {
        "petta": __version__,
        "janus": janus_bridge.version_str(),
        "swi_prolog": janus_bridge.version_str(swi_version_num),
        "python": (
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        ),
        "petta_path": (None if active is None else active.petta_path),
    }


__all__ = [
    "DECLINE",
    "REFLECTION_SPACE",
    "Adder",
    "Answer",
    "Atom",
    "Bindings",
    "Builtin",
    "CastError",
    "Clearer",
    "CompileError",
    "Config",
    "Cursor",
    "CustomMatch",
    "Decline",
    "Defined",
    "Derivation",
    "EngineError",
    "EngineProfile",
    "Enumerable",
    "Event",
    "Expr",
    "Fact",
    "Gnd",
    "Handle",
    "InferenceLimitError",
    "Interrupted",
    "Matcher",
    "MeTTa",
    "MettaName",
    "MettaOperationError",
    "MettaResultError",
    "MettaSyntaxError",
    "PeTTa",
    "PettaError",
    "Prepared",
    "Remover",
    "ResourceLimitError",
    "Row",
    "Rows",
    "S",
    "SaveFormat",
    "SourceNotFound",
    "SpaceName",
    "SpaceProvider",
    "Step",
    "StrictError",
    "Subscription",
    "Sym",
    "TimeLimitError",
    "Truncated",
    "Undefined",
    "V",
    "Var",
    "__version__",
    "add",
    "aio",
    "alpha_eq",
    "arrays",
    "atom_from_wire",
    "backend_info",
    "bridge",
    "cast",
    "config",
    "convert",
    "current_space",
    "das",
    "decode",
    "default_engine",
    "encode",
    "engine_thread",
    "eval",
    "expr",
    "fn",
    "foreign",
    "integrate",
    "is_ground",
    "lint",
    "map_atoms",
    "order_key",
    "parallel",
    "parse",
    "persistent",
    "query",
    "record",
    "register_object_repr",
    "register_object_repr_protocol",
    "remote",
    "remove",
    "run",
    "sym",
    "testing",
    "trace",
    "unify",
    "unregister_object_repr",
    "unregister_object_repr_protocol",
    "val",
    "var",
    "variables",
]
