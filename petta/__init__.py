"""Purpose: expose PeTTa's narrow Python core and lazily load satellites.

Assumes:
  - ``petta._space.MeTTa`` owns runtime context and ``petta._space.Space``
    owns storage and query verbs [source:
    bindings/python/petta/_space.py:306 and :3090; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Guarantees:
  - ``dir(petta)`` is exactly the curated public surface and loads no
    satellites [tested: test_m7_narrow_core_surface; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - satellite modules are imported only by attribute access, following PEP
    562 with their real module identity intact [tested:
    test_m7_satellites_are_lazy_and_identity_stable; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - ``space()`` is the only space-creation door and cannot be overwritten by
    an implementation submodule [tested: test_m7_space_factory_keeps_identity;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - ``PeTTa`` retains the upstream source-string wrapper for a legacy
    ``src/main.pl`` tree without widening the curated root [tested:
    test_upstream_python_package_path_is_canonical and
    test_upstream_source_wrapper_binds_verbose_atom; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - ``fn`` is an inert, generated, statically typed mention namespace and
    importing it never starts the engine [tested:
    test_the_fn_namespace_is_generated; commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
Decides:
  - ``DEFAULT_STACK_LIMIT`` preserves the upstream wrapper's 8 GB Prolog
    stack policy [source: PeTTa-base/python/petta/__init__.py:8;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import _thread
import functools as _functools
import importlib as _importlib
import os as _os
from typing import Any as _Any

from ._config import Config, config
from ._fn import fn
from ._version import __version__
from .atoms import (
    FALSE,
    HERE,
    TRUE,
    UNIT,
    Atom,
    Expression,
    G,
    Grounded,
    Handle,
    S,
    Symbol,
    Undefined,
    V,
    Variable,
    ground,
    parse,
    unify,
)
from .errors import NotReducible, PettaError

_SATELLITES = frozenset(
    {
        "aio",
        "algebra",
        "arrays",
        "casting",
        "convert",
        "derivation",
        "events",
        "foreign",
        "integrate",
        "lint",
        "manifest",
        "parallel",
        "paths",
        "remote",
        "spaces",
        "structures",
        "subscribe",
        "tables",
        "testing",
        "trace",
        "vocabularies",
        "wire",
    }
)

_LAZY_ATTRIBUTES = {
    "Answer": ("answer", "Answer"),
    "Bindings": ("answer", "Bindings"),
    "Defined": ("define", "Defined"),
    "MeTTa": ("_space", "MeTTa"),
    "Space": ("_space", "Space"),
    "SpaceProvider": ("foreign", "SpaceProvider"),
    "boot": ("manifest", "boot"),
    "equation": ("_rules", "equation"),
    "record": ("ops", "record"),
    "rules": ("_rules", "rules"),
}

_HIDDEN_IMPLEMENTATION_MODULES = {
    "answer",
    "atoms",
    "define",
    "errors",
    "ops",
    "results",
}

# These four names are the retained upstream package state. Exact ``__dir__``
# keeps them out of the designed PeTTa-library surface, but the original
# ``python.petta`` wrapper and its tests access them directly.
CONSULTED = False
CONSULT_LOCK = _thread.allocate_lock()
janus: _Any = None
DEFAULT_STACK_LIMIT = 8_000_000_000


def _path_exists(path: str) -> bool:
    """Check a runtime path without importing pathlib into the narrow root."""
    return _os.path.exists(path)  # noqa: FURB141 -- pathlib adds eager imports to plain ``import petta``


def _resolve_petta_path() -> str:
    """Locate either the upstream or current bundled/source runtime tree."""
    env_path = _os.environ.get("PETTA_PATH")
    if env_path:
        return _os.path.abspath(env_path)

    here = _os.path.dirname(_os.path.abspath(__file__))
    bundled = _os.path.join(here, "_runtime")
    if _path_exists(_os.path.join(bundled, "src", "main.pl")) or _path_exists(
        _os.path.join(bundled, "engine", "main.pl")
    ):
        return bundled

    return _os.path.abspath(_os.path.join(here, _os.pardir, _os.pardir, _os.pardir))


def _is_upstream_runtime(petta_path: str | None) -> bool:
    """Recognize the retained upstream layout without consulting either engine."""
    if petta_path is None:
        if CONSULTED:
            return True
        petta_path = _resolve_petta_path()
    return _os.path.isfile(_os.path.join(petta_path, "src", "main.pl"))


def _consult_upstream(petta_path: str | None) -> None:
    """Consult the original ``src/main.pl`` and ``python/helper.pl`` pair once."""
    global CONSULTED, janus  # pylint: disable=global-statement

    if CONSULTED:
        return
    with CONSULT_LOCK:
        if CONSULTED:
            return
        if petta_path is None:
            petta_path = _resolve_petta_path()
        mork_library = _os.path.join(
            petta_path,
            "mork_ffi",
            "target",
            "release",
            "libmork_ffi.so",
        )
        if _path_exists(mork_library):
            original_dir = _os.getcwd()  # noqa: FURB104 -- pathlib stays outside the narrow import graph
            try:
                _os.chdir(petta_path)
                janus = _importlib.import_module("janus_swi")
                janus.query_once(
                    f"set_prolog_flag(stack_limit, {DEFAULT_STACK_LIMIT})"
                )
            finally:
                _os.chdir(original_dir)
            janus.query_once("set_prolog_flag(argv, ['mork'])")
        else:
            janus = _importlib.import_module("janus_swi")
            janus.query_once(f"set_prolog_flag(stack_limit, {DEFAULT_STACK_LIMIT})")
        main_file = _os.path.join(petta_path, "src", "main.pl")
        helper_file = _os.path.join(petta_path, "python", "helper.pl")
        if not _path_exists(main_file):
            msg = (
                f"PeTTa runtime not found under {petta_path!r} "
                f"(expected {main_file!r}). Set the PETTA_PATH environment "
                "variable or pass petta_path to point at a PeTTa checkout."
            )
            raise FileNotFoundError(msg)
        janus.consult(main_file)
        janus.consult(helper_file)
        CONSULTED = True


class PeTTa:
    """The upstream-compatible thin wrapper: source strings in and out."""

    def __init__(self, verbose=False, petta_path=None):  # noqa: FBT002 -- upstream constructor signature is the retained compatibility boundary
        """Open the upstream-compatible source-string runner."""
        self.verbose = bool(verbose)
        self._upstream = _is_upstream_runtime(petta_path)
        if self._upstream:
            _consult_upstream(petta_path)
            self._runtime = None
        else:
            _engine = _importlib.import_module(f"{__name__}._engine")
            self._runtime = _engine.runtime(
                petta_path=petta_path,
                verbose=self.verbose,
            )

    def _run_helper(self, helper_name, argument):
        if self._upstream:
            bridge = janus
        else:
            runtime = self._runtime
            if runtime is None:
                msg = "current runtime was not initialized"
                raise RuntimeError(msg)
            bridge = runtime._janus
        result = bridge.query_once(
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
        """Compile a MeTTa file to Prolog and return the run results."""
        return self._run_helper("load_metta_file", file_path)

    def process_metta_string(self, metta_code) -> str:
        """Compile MeTTa source and return the run results."""
        return self._run_helper("process_metta_string", metta_code)


def __getattr__(name: str) -> _Any:
    """Load one advertised satellite or lazy core object on first access."""
    if name in _SATELLITES:
        value = _importlib.import_module(f".{name}", __name__)
    elif name in _LAZY_ATTRIBUTES:
        module_name, attribute = _LAZY_ATTRIBUTES[name]
        module = _importlib.import_module(f".{module_name}", __name__)
        value = getattr(module, attribute)
    elif name == "reflection":
        value = engine().space("&petta")
    else:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)
    for implementation_name in _HIDDEN_IMPLEMENTATION_MODULES:
        globals().pop(implementation_name, None)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return only the designed public surface without resolving it."""
    return sorted(__all__)


@_functools.cache
def engine():
    """Return the process-default runtime context, creating it on first use."""
    return __getattr__("MeTTa")()


def space(
    name: str | None = None,
    backing: _Any = None,
    *,
    journal: str | None = None,
    **options: _Any,
):
    """Create or open a space; the backing value selects its implementation."""
    return engine().space(name, backing, journal=journal, **options)


def attach(name: str, backing: _Any, **options: _Any):
    """Attach a provider or remote URL through the unified creation door."""
    return space(name, backing=backing, **options)


def current_space():
    """Return the ambient space selected by an enclosing space context."""
    space_api = _importlib.import_module(f"{__name__}._space")
    value = space_api.current_space()
    for implementation_name in _HIDDEN_IMPLEMENTATION_MODULES:
        globals().pop(implementation_name, None)
    return value


def forms(source: str) -> list[Atom]:
    """Parse every top-level form without evaluating any of them."""
    source_forms = _importlib.import_module(f"{__name__}._source_forms")
    return [parse(form.text) for form in source_forms.positioned_forms(source)]


def run(source: str, **kwargs: _Any):
    """Run source in the default context's self space."""
    return engine().self.run(source, **kwargs)


def query(*patterns: _Any, **kwargs: _Any):
    """Query the default context's self space."""
    return engine().self.query(*patterns, **kwargs)


def add(*atoms: _Any):
    """Add atoms to the default context's self space."""
    return engine().self.add(*atoms)


def remove(atom: _Any):
    """Remove one exact atom from the default context's self space."""
    return engine().self.remove(atom)


def eval(target: _Any, **kwargs: _Any):  # noqa: A001 -- eval is the ruled public verb and its atom type stays behind the lazy handle seam
    """Evaluate one term in the default context's self space."""
    return engine().self.eval(target, **kwargs)


__all__ = [
    "FALSE",
    "HERE",
    "TRUE",
    "UNIT",
    "Answer",
    "Atom",
    "Bindings",
    "Config",
    "Defined",
    "Expression",
    "G",
    "Grounded",
    "Handle",
    "MeTTa",
    "NotReducible",
    "PeTTa",
    "PettaError",
    "S",
    "Space",
    "SpaceProvider",
    "Symbol",
    "Undefined",
    "V",
    "Variable",
    "__version__",
    "add",
    "aio",
    "algebra",
    "arrays",
    "attach",
    "boot",
    "casting",
    "config",
    "convert",
    "current_space",
    "derivation",
    "engine",
    "equation",
    "eval",
    "events",
    "fn",
    "foreign",
    "forms",
    "ground",
    "integrate",
    "lint",
    "manifest",
    "parallel",
    "parse",
    "paths",
    "query",
    "record",
    "reflection",
    "remote",
    "remove",
    "rules",
    "run",
    "space",
    "spaces",
    "structures",
    "subscribe",
    "tables",
    "testing",
    "trace",
    "unify",
    "vocabularies",
    "wire",
]

# Importing a submodule writes it onto its parent package. These concrete
# modules remain explicitly importable, but they are implementation modules,
# not root attributes.
for _implementation_name in _HIDDEN_IMPLEMENTATION_MODULES:
    globals().pop(_implementation_name, None)
del _implementation_name
