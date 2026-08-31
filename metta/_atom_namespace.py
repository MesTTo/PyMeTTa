"""Purpose: provide bounded attribute and exact-item atom namespaces.
Guarantees:
  - repeated recent names preserve identity and cache growth is bounded
    [tested test_namespace_cache_is_bounded,
    test_the_subscription_queue_is_bounded_and_load_takes_a_budget]
  - a name touched every round survives any amount of churn past it, which
    a FIFO does not deliver [measured 2026-08-19: over 2048 touches of one
    hot name, insertion-age eviction re-minted it 5 times and two tiers
    minted it once; hit rate at 512 with 200 hot names, 82.4% against
    88.4%]
  - the lock-free cache-hit read uses 1.99% fewer instructions than locking
    every hit [measured 2026-08-14: minimum 1177503701 versus 1201380616]
  - engine completion failures surface instead of returning partial names
    [tested test_namespace_completion_surfaces_engine_errors]
  - the cache bound is marked immutable to type checkers [tested
    test_policy_constants_are_final]
  - attributes use the total underscore-to-hyphen map while item access
    preserves exact target spelling [tested:
    test_attribute_factories_apply_the_total_map_and_brackets_stay_exact;
    commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
  - Symbol attributes consult the operator word table before transliteration,
    including composite ``neg``, while exact item access remains unchanged
    [tested: test_operator_words_precede_the_mechanical_name_map;
    commit=8ec44dec3cafba5981e7cf712749cca0e1bdcc45]
  - hot attribute spellings reuse a separate bounded cache, so the name map
    stays within the established term-building budget [measured: 659673847
    instructions; date=2026-08-23; command=cd extensions/python && ../../../../.venv-pypetta/bin/python -m benchmarks.check_instructions term-operators; fixture=20000 term-operators terms; commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
  - generated Symbol mentions can carry inert per-instance documentation while
    retaining Symbol equality and hashing [tested: test_generated_fn_help_is_offline;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
Guarded by:
  - each namespace lock protects its target and attribute cache tiers; each
    fast-tier hit path reads one dict and takes no lock [tested
    test_atom_identity_caches_are_thread_safe]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import importlib
import threading
from typing import Any, Final

from ._atoms_core import Symbol
from ._name_mapping import OperatorRecipe, generated_aliases, operator_attribute_target

NAMESPACE_CACHE_MAX: Final[int] = 512
#: The fast tier in front of it, read without the lock and without
#: reordering. Same ratio as CPython's re cache, 512 over 256.
NAMESPACE_FAST_MAX: Final[int] = 256


class _DocumentedSymbol(Symbol):
    # An inert generated mention; its instance doc powers offline help().
    __slots__ = ("__doc__",)

    def __init__(self, name: str, documentation: str) -> None:
        super().__init__(name)
        object.__setattr__(self, "__doc__", documentation)


class _Namespace:
    """Mint atoms by attribute access: S.likes is the symbol likes, V.x is $x.

    The Python binding is the name itself, so nothing is spelled twice.
    S["car-atom"] reaches names that are not identifiers.
    """

    __slots__ = (
        "_aliases",
        "_allowed",
        "_attrs",
        "_cache",
        "_documentation",
        "_fast",
        "_kind",
        "_label",
        "_lock",
        "_remedy",
    )

    def __init__(
        self,
        kind: type,
        *,
        allowed: frozenset[str] | None = None,
        aliases: dict[str, str] | None = None,
        documentation: dict[str, str] | None = None,
        label: str = "name",
        remedy: str = "",
    ) -> None:
        object.__setattr__(self, "_kind", kind)
        object.__setattr__(self, "_allowed", allowed)
        object.__setattr__(
            self,
            "_aliases",
            aliases if aliases is not None else generated_aliases(allowed or ()),
        )
        object.__setattr__(self, "_label", label)
        #: What to reach for when a CLOSED namespace does not carry a name.
        #: A closed namespace is generated, so it cannot see a name registered
        #: since generation, and its refusal has to say where that name IS
        #: reachable rather than only that it is absent here.
        object.__setattr__(self, "_remedy", remedy)
        object.__setattr__(self, "_documentation", documentation or {})
        object.__setattr__(self, "_cache", {})
        object.__setattr__(self, "_fast", {})
        object.__setattr__(self, "_attrs", {})
        object.__setattr__(self, "_lock", threading.RLock())

    def __getattr__(self, name: str) -> Any:
        """Two tiers, copied from _atoms_core._wire_intern, which took them
        from CPython's own re module cache.

        Returning on a hit without touching the cache made this a FIFO: a
        name used in every line of a program aged out on the same schedule
        as one used once, so `repeated recent names preserve identity` was
        not true of it. The main tier is an LRU, `cache.pop` then reinsert,
        which is the plain-dict spelling of OrderedDict.move_to_end. The
        small fast tier in front of it keeps the hit lock-free and
        reorder-free, which is why the LRU costs nothing on the hot path.

        Simulated 2026-08-19 at the shipped 512, a small hot set
        interleaved with fresh names: FIFO 82.4% against 88.4% at 200 hot
        and 70.4% against 82.4% at 400, and over 2048 touches of one hot
        name FIFO re-minted it five times where two tiers minted it once.

        This keeps `del cache[next(iter(cache))]`, which _atoms_core no
        longer does, and the difference is the bound. That eviction is
        O(bound) because a dict's iterator skips the tombstones previous
        evictions left, so it costs 170 ns at 256 entries and 2,257 ns at
        262,144. At 512 it is the small end of that curve, and the names
        here come from hand-written source rather than a peer, so the cache
        rarely evicts at all. Paying an OrderedDict for it instead costs
        every LOOKUP: dict.get 23.5 ns against OrderedDict.get 24.8 ns, and
        term-operators, which is three namespace lookups per term over
        20,000 terms, measured +0.132% [measured 2026-08-19, minimum of
        three instructions:u runs]. Deliberate, not an oversight.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if name.startswith("__"):
            raise AttributeError(name)
        fast = object.__getattribute__(self, "_attrs")
        try:
            return fast[name]
        except KeyError:
            pass
        aliases = object.__getattribute__(self, "_aliases")
        kind = object.__getattribute__(self, "_kind")
        operator_target = operator_attribute_target(name) if kind is Symbol else None
        if isinstance(operator_target, OperatorRecipe):
            hit = operator_target
            lock = object.__getattribute__(self, "_lock")
            with lock:
                if len(fast) >= NAMESPACE_FAST_MAX:
                    del fast[next(iter(fast))]
                fast[name] = hit
            return hit
        if operator_target is not None:
            target = operator_target
        elif object.__getattribute__(self, "_allowed") is None:
            target = name
            if name != "_" and "_" in name:
                target = name.replace("_", "-")
        else:
            try:
                target = aliases[name]
            except KeyError:
                label = object.__getattribute__(self, "_label")
                remedy = object.__getattribute__(self, "_remedy")
                msg = (
                    f"no {label} attribute named {name!r} exists in the "
                    f"generated catalog{remedy}"
                )
                raise AttributeError(msg) from None
        hit = self._resolve(target)
        lock = object.__getattribute__(self, "_lock")
        with lock:
            if len(fast) >= NAMESPACE_FAST_MAX:
                del fast[next(iter(fast))]
            fast[name] = hit
        return hit

    def _resolve(self, name: str) -> Any:
        """Mint one resolved target name through the bounded cache."""
        allowed = object.__getattribute__(self, "_allowed")
        if allowed is not None and name not in allowed:
            label = object.__getattribute__(self, "_label")
            remedy = object.__getattribute__(self, "_remedy")
            msg = (
                f"no {label} named {name!r} exists in the generated "
                f"catalog{remedy}"
            )
            raise AttributeError(msg)
        fast = object.__getattribute__(self, "_fast")
        try:
            return fast[name]
        except KeyError:
            pass
        lock = object.__getattribute__(self, "_lock")
        cache = object.__getattribute__(self, "_cache")
        with lock:
            hit = fast.get(name)
            if hit is not None:
                return hit
            hit = cache.pop(name, None)
            if hit is None:
                kind = object.__getattribute__(self, "_kind")
                documentation = object.__getattribute__(self, "_documentation")
                hit = (
                    _DocumentedSymbol(name, documentation[name])
                    if kind is Symbol and name in documentation
                    else kind(name)
                )
                if len(cache) >= NAMESPACE_CACHE_MAX:
                    del cache[next(iter(cache))]
            cache[name] = hit
            if len(fast) >= NAMESPACE_FAST_MAX:
                del fast[next(iter(fast))]
            fast[name] = hit
            return hit

    def __getitem__(self, name: str) -> Any:
        if not isinstance(name, str):
            msg = f"an exact namespace name is a string, got {type(name).__name__}"
            raise TypeError(msg)
        return self._resolve(name)

    def __setattr__(self, *_: Any) -> None:
        msg = "namespaces are read-only"
        raise AttributeError(msg)

    def _known(self) -> list[str]:
        allowed = object.__getattribute__(self, "_allowed")
        if allowed is not None:
            return sorted(allowed)
        lock = object.__getattribute__(self, "_lock")
        with lock:
            names = set(object.__getattribute__(self, "_cache"))
        if object.__getattribute__(self, "_kind") is Symbol:
            engine = importlib.import_module(f"{__package__}._engine")

            if engine.started():
                names.update(engine.runtime().builtins())
        return sorted(names)

    def __dir__(self):
        if object.__getattribute__(self, "_allowed") is not None:
            return list(object.__getattribute__(self, "_aliases"))
        return list(generated_aliases(self._known()))

    def _ipython_key_completions_(self):
        # Most engine names carry a hyphen, so S["<TAB>"] is where they live.
        return self._known()
