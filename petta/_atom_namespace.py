"""Purpose: provide bounded attribute and item builders for symbols and variables.
Guarantees:
  - repeated recent names preserve identity and cache growth is bounded
    [tested test_namespace_cache_is_bounded]
  - the lock-free cache-hit read uses 1.99% fewer instructions than locking
    every hit [measured 2026-08-14: minimum 1177503701 versus 1201380616]
  - engine completion failures surface instead of returning partial names
    [tested test_namespace_completion_surfaces_engine_errors]
  - the cache bound is marked immutable to type checkers [tested
    test_policy_constants_are_final]
Guarded by:
  - each namespace lock protects its recency cache [tested
    test_atom_identity_caches_are_thread_safe]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import importlib
import threading
from typing import Any, Final

from ._atoms_core import Sym

NAMESPACE_CACHE_MAX: Final[int] = 512


class _Namespace:
    """Mint atoms by attribute access: S.likes is the symbol likes, V.x is $x.

    The Python binding is the name itself, so nothing is spelled twice.
    S["car-atom"] reaches names that are not identifiers.
    """

    __slots__ = ("_cache", "_kind", "_lock")

    def __init__(self, kind: type) -> None:
        object.__setattr__(self, "_kind", kind)
        object.__setattr__(self, "_cache", {})
        object.__setattr__(self, "_lock", threading.RLock())

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__"):
            raise AttributeError(name)
        cache = object.__getattribute__(self, "_cache")
        try:
            return cache[name]
        except KeyError:
            pass
        lock = object.__getattribute__(self, "_lock")
        with lock:
            hit = cache.get(name)
            if hit is None:
                hit = object.__getattribute__(self, "_kind")(name)
                cache[name] = hit
                if len(cache) > NAMESPACE_CACHE_MAX:
                    del cache[next(iter(cache))]
            return hit

    def __getitem__(self, name: str) -> Any:
        return self.__getattr__(name)

    def __call__(self, name: str) -> Any:
        return self.__getattr__(name)

    def __setattr__(self, *_: Any) -> None:
        raise AttributeError("namespaces are read-only")

    def _known(self) -> list[str]:
        lock = object.__getattribute__(self, "_lock")
        with lock:
            names = set(object.__getattribute__(self, "_cache"))
        if object.__getattribute__(self, "_kind") is Sym:
            engine = importlib.import_module(f"{__package__}._engine")

            if engine.started():
                names.update(engine.runtime().builtins())
        return sorted(names)

    def __dir__(self):
        return [n for n in self._known() if n.isidentifier()]

    def _ipython_key_completions_(self):
        # Most engine names carry a hyphen, so S["<TAB>"] is where they live.
        return self._known()
