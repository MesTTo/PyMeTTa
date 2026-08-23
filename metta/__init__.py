"""Purpose: expose PeTTa's narrow Python core and lazily load satellites.

Assumes:
  - ``metta._space.MeTTa`` owns runtime context and ``metta._space.Space``
    owns storage and query verbs [source:
    bindings/python/metta/_space.py:306 and :3090; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Guarantees:
  - the R5 root exports the term builders, relational solve, and lazy State
    handle while ``record`` and atom-specialist ``order_key`` stay absent
    [tested: test_m7_narrow_core_surface,
    test_solve_retires_the_five_relational_let_workarounds,
    test_keyword_builders_retire_53_raw_if_mentions, and
    test_state_retires_three_state_function_strings; commit=cff2e7f319bd2212f0c2d74f8d5fe5be3ac693b5]
  - ``dir(metta)`` is exactly the curated public surface and loads no
    satellites [tested: test_m7_narrow_core_surface; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - satellite modules are imported only by attribute access, following PEP
    562 with their real module identity intact [tested:
    test_m7_satellites_are_lazy_and_identity_stable; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - ``space()`` is the only space-creation door and cannot be overwritten by
    an implementation submodule [tested: test_m7_space_factory_keeps_identity;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - ``space()`` accepts both text and a space-name Symbol returned by the
    engine [tested: test_space_factory_accepts_a_name_symbol; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - ``fn`` is an inert, generated, statically typed mention namespace and
    importing it never starts the engine [tested:
    test_the_fn_namespace_is_generated; commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
  - package ``match`` reads the default space while ``superpose`` evaluates
    its expression form; compiled definitions lower their syntactic match
    calls before either Python function executes [tested:
    test_module_tier_exposes_the_mode_and_definition_family; commit=b2527d32dc851615e6cf1e11c94ac017d4e78c86]
  - ``view`` lazily opens a live provider space over Python mappings, sets,
    and sequences [tested: test_view_is_a_live_queryable_space;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - the root exports ``seg``, the named segment builder, beside the ``...``
    spelling Python already has [tested: test_seg_builds_a_named_segment;
    commit=WORKTREE]
  - coordination functions are lazy satellite exports and Timeout remains
    catchable as builtin TimeoutError [tested:
    test_the_coordination_family_is_python_shaped; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - module define/cache/stats/limits/strict/trace verbs defer engine creation
    until called and target the default self space [tested:
    test_module_tier_exposes_the_mode_and_definition_family; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import functools as _functools
import importlib as _importlib
import os as _os
from typing import Any as _Any

from ._config import Config, config
from ._fn import fn
from ._version import __version__
from .atoms import (
    FALSE,
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
    and_,
    arrow,
    ground,
    if_,
    in_,
    not_,
    or_,
    parse,
    seg,
    typed,
    unify,
)
from .errors import NotReducible, PettaError, Timeout

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
    "State": ("_state", "State"),
    "boot": ("manifest", "boot"),
    "equation": ("_rules", "equation"),
    "rules": ("_rules", "rules"),
    "channel": ("parallel", "channel"),
    "every": ("parallel", "every"),
    "par_map": ("parallel", "par_map"),
    "race": ("parallel", "race"),
    "spawn": ("parallel", "spawn"),
    "view": ("spaces", "view"),
}

_HIDDEN_IMPLEMENTATION_MODULES = {
    "answer",
    "atoms",
    "define",
    "errors",
    "ops",
    "results",
}

_OMITTED = object()


def _path_exists(path: str) -> bool:
    """Check a runtime path without importing pathlib into the narrow root."""
    return _os.path.exists(path)  # noqa: FURB141 -- pathlib adds eager imports to plain ``import metta``


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
    _rehide_implementation_modules()
    globals()[name] = value
    return value


def _rehide_implementation_modules() -> None:
    """Restore each root verb an implementation-module import shadowed.

    Importing a submodule writes it onto its parent package, so any import
    that pulls in ``metta.define`` and its siblings replaces the root VERB
    with the module object. This puts the verb back. A name with no verb is
    removed. During partial package initialization the verbs table is not
    bound yet; popping then would delete the verb with nothing to restore
    it, which is how ``metta.define`` once vanished for the life of the
    process, so the pass defers to the end-of-init sweep instead.
    """
    verbs = globals().get("_ROOT_IMPLEMENTATION_VERBS")
    if verbs is None:
        return
    for implementation_name in _HIDDEN_IMPLEMENTATION_MODULES:
        replacement = verbs.get(implementation_name)
        if replacement is None:
            globals().pop(implementation_name, None)
        else:
            globals()[implementation_name] = replacement


def __dir__() -> list[str]:
    """Return only the designed public surface without resolving it."""
    return sorted(__all__)


@_functools.cache
def engine():
    """Return the process-default runtime context, creating it on first use."""
    return __getattr__("MeTTa")()


def space(
    name: str | Atom | None = None,
    backing: _Any = None,
    *,
    journal: str | None = None,
    **options: _Any,
):
    """Create or open a space; the backing value selects its implementation."""
    return engine().space(name, backing, journal=journal, **options)


def attach(name: str | Symbol, backing: _Any, **options: _Any):
    """Attach a provider or remote URL through the unified creation door."""
    return space(name, backing=backing, **options)


def current_space():
    """Return the ambient space selected by an enclosing space context."""
    space_api = _importlib.import_module(f"{__name__}._space")
    value = space_api.current_space()
    _rehide_implementation_modules()
    return value


def forms(source: str) -> list[Atom]:
    """Parse every top-level form without evaluating any of them."""
    source_forms = _importlib.import_module(f"{__name__}._source_forms")
    return [parse(form.text) for form in source_forms.positioned_forms(source)]


def run(source: str, **kwargs: _Any):
    """Run source in the default context's self space."""
    return engine().self.run(source, **kwargs)


def match(*patterns: _Any, **kwargs: _Any):
    """Match patterns against the default context's self space."""
    return engine().self.match(*patterns, **kwargs)


def _ambient_space():
    """Open the space selected by the active Python or engine context."""
    return engine().space(current_space())


def superpose(*alternatives: _Any):
    """Evaluate expression-position alternatives in the ambient space.

    With no alternatives this evaluates ``(empty)``. Inside a compiled
    definition the compiler lowers this same function spelling directly to
    ``(superpose (...))``.
    """
    target = S.empty() if not alternatives else S.superpose(Expression(alternatives))
    return _ambient_space().answers(target)


def accept(atom: _Any = _OMITTED) -> Expression:
    """Build a pre-add verdict that keeps or replaces the offered atom."""
    return S.accept() if atom is _OMITTED else S.accept(atom)


def refuse(words: _Any) -> Expression:
    """Build a pre-add verdict that rejects a write with the judge's words."""
    return S.refuse(words)


def drop() -> Expression:
    """Build a pre-add verdict that silently skips the offered atom."""
    return S.drop()


def add(*atoms: _Any):
    """Add atoms to the default context's self space."""
    return engine().self.add(*atoms)


def remove(atom: _Any):
    """Remove one exact atom from the default context's self space."""
    return engine().self.remove(atom)


def eval(target: _Any, **kwargs: _Any):  # noqa: A001 -- eval is the ruled public verb and its atom type stays behind the lazy handle seam
    """Evaluate one term in the default context's self space."""
    return engine().self.eval(target, **kwargs)


def solve(pattern: _Any, subject: _Any):
    """Solve a relation backwards in the default context."""
    return engine().self.solve(pattern, subject)


def define(*args: _Any, **kwargs: _Any):
    """Define a function or record in the default self space."""
    return engine().self.define(*args, **kwargs)


def cache(*args: _Any, **kwargs: _Any):
    """Define and memoize a function in the default self space."""
    return engine().self.cache(*args, **kwargs)


def stats():
    """Measure engine counters across a default-context block."""
    return engine().self.stats()


def limits(
    *,
    timeout: float | None = None,
    inferences: int | None = None,
    stack: int | None = None,
):
    """Scope default time, inference, and stack-byte bounds."""
    return engine().self.limits(
        timeout=timeout,
        inferences=inferences,
        stack=stack,
    )


def strict():
    """Refuse unreduced default-context directives within the block."""
    return engine().self.strict()


def trace(source: str, *, max_events: int = 10_000):
    """Trace source in the default self space."""
    return engine().self.trace(source, max_events=max_events)


_ROOT_IMPLEMENTATION_VERBS = {
    "define": define,
    "trace": trace,
}


__all__ = [
    "FALSE",
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
    "PettaError",
    "S",
    "Space",
    "SpaceProvider",
    "State",
    "Symbol",
    "Timeout",
    "Undefined",
    "V",
    "Variable",
    "__version__",
    "accept",
    "add",
    "aio",
    "algebra",
    "and_",
    "arrays",
    "arrow",
    "attach",
    "boot",
    "cache",
    "casting",
    "channel",
    "config",
    "convert",
    "current_space",
    "define",
    "derivation",
    "drop",
    "engine",
    "equation",
    "eval",
    "events",
    "every",
    "fn",
    "foreign",
    "forms",
    "ground",
    "if_",
    "in_",
    "integrate",
    "limits",
    "lint",
    "manifest",
    "match",
    "not_",
    "or_",
    "par_map",
    "parallel",
    "parse",
    "paths",
    "race",
    "reflection",
    "refuse",
    "remote",
    "remove",
    "rules",
    "run",
    "seg",
    "solve",
    "space",
    "spaces",
    "spawn",
    "stats",
    "strict",
    "structures",
    "subscribe",
    "superpose",
    "tables",
    "testing",
    "trace",
    "typed",
    "unify",
    "view",
    "vocabularies",
    "wire",
]

# Importing a submodule writes it onto its parent package. These concrete
# modules remain explicitly importable, but they are implementation modules,
# not root attributes. The verbs table is bound by here, so this is the
# end-of-init sweep the partial-init guard in the helper defers to.
_rehide_implementation_modules()
