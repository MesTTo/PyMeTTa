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
  - a namespace refusal carries AttributeError's name and obj through the
    bracket door as well as the attribute door, where the interpreter fills
    neither [tested:
    test_the_generated_namespace_refusal_carries_both_fields,
    test_a_bracket_door_suggests_where_the_interpreter_fills_nothing;
    commit=6375a7c8f3c035b04bc9d41c8f7f22e56b42fb41]
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
from typing import Any, Final, cast

from ._atoms_core import Atom, Symbol
from ._name_mapping import (
    OperatorRecipe,
    attribute_name,
    generated_aliases,
    operator_attribute_target,
)
from .errors import Ground, Remedy, refusing

#: Both closed-namespace refusals are Python's attribute grammar: a generated
#: catalog is an object, and a name it does not carry is not an attribute.
_ATTRIBUTE_GROUND = Ground(
    "host-reference",
    "Python Language Reference section 6.3.2, Attribute references",
)

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


#The atom class a namespace mints is already the constructor's first argument,
#so making the class generic over it costs no new API and lets a type checker
#see through the attribute door: `S.foo` was `Any`, which took away the very
#reason to prefer it over the string "foo".
class _Namespace[AtomT: Atom]:
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
        "_fix",
        "_kind",
        "_label",
        "_lock",
        "_operators",
        "_remedy",
    )

    def __init__(
        self,
        kind: type[AtomT],
        *,
        allowed: frozenset[str] | None = None,
        aliases: dict[str, str] | None = None,
        documentation: dict[str, str] | None = None,
        label: str = "name",
        remedy: str = "",
        fix: Remedy | None = None,
        operators: bool = True,
    ) -> None:
        object.__setattr__(self, "_kind", kind)
        object.__setattr__(self, "_allowed", allowed)
        #: Whether Python's `operator` module words reach this namespace's
        #: atoms. True for a namespace over the ENGINE's catalog, where
        #: `fn.add` naming `+` is the point; False for one over a single
        #: library's heads, where it would name heads that library never
        #: declares and would shadow one it did.
        object.__setattr__(self, "_operators", operators)
        object.__setattr__(
            self,
            "_aliases",
            aliases
            if aliases is not None
            else generated_aliases(allowed or (), operators=operators),
        )
        object.__setattr__(self, "_label", label)
        #: What to reach for when a CLOSED namespace does not carry a name.
        #: A closed namespace is generated, so it cannot see a name registered
        #: since generation, and its refusal has to say where that name IS
        #: reachable rather than only that it is absent here.
        object.__setattr__(self, "_remedy", remedy)
        #: The same repair as data. `remedy` is the sentence a reader gets;
        #: this is what an editor offers, and both say one thing.
        object.__setattr__(self, "_fix", fix)
        object.__setattr__(self, "_documentation", documentation or {})
        object.__setattr__(self, "_cache", {})
        object.__setattr__(self, "_fast", {})
        object.__setattr__(self, "_attrs", {})
        object.__setattr__(self, "_lock", threading.RLock())

    #Declared as the atom, though ONE name in one namespace answers otherwise:
    #`S.neg` is an OperatorRecipe carrying the composite `(- 0 x)`, and the
    #operator path is reached only when the kind is Symbol, so `V.neg` is the
    #plain variable `$neg`. Every other name in every namespace is the atom.
    #
    #The union `AtomT | OperatorRecipe` was tried and taken back out. It is
    #the honest type and the wrong one to publish: it makes `Expression([S.x])`
    #an error for EVERY caller in order to be exact about a single name, so the
    #cost falls on the many to describe the one. The same trade `_fn.pyi`
    #makes, where operator words are declared explicitly rather than widening
    #the whole roster. `S['neg']` remains the exact door and answers the symbol.
    def __getattr__(self, name: str) -> AtomT:
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
        operator_target = (
            operator_attribute_target(name)
            if kind is Symbol and object.__getattribute__(self, "_operators")
            else None
        )
        if isinstance(operator_target, OperatorRecipe):
            hit = operator_target
            lock = object.__getattribute__(self, "_lock")
            with lock:
                if len(fast) >= NAMESPACE_FAST_MAX:
                    del fast[next(iter(fast))]
                fast[name] = hit
            #The one place the declared type is wider than the value: `S.neg`
            #answers an OperatorRecipe. Cast HERE, in the implementation,
            #rather than publishing a union that every caller would narrow.
            return cast("AtomT", hit)
        if operator_target is not None:
            target = operator_target
        elif object.__getattribute__(self, "_allowed") is None:
            target = attribute_name(name)
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
                raise refusing(
                    AttributeError(msg, name=name, obj=self),
                    ground=_ATTRIBUTE_GROUND,
                    remedy=object.__getattribute__(self, "_fix"),
                ) from None
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
            #`name` and `obj` are what the interpreter renders "Did you mean"
            #from, and it fills them itself for anything raised out of
            #__getattr__ [measured 2026-09-06 on CPython 3.14.4]. This is the
            #BRACKET door, which is not attribute access, so nothing fills
            #them here and a refusal carried no suggestion at all. Every
            #refusal in the package sets them rather than the ones that need
            #to: which door a caller came through is not the raise site's
            #business, and the auto-fill is an interpreter internal.
            raise refusing(
                AttributeError(msg, name=name, obj=self),
                ground=_ATTRIBUTE_GROUND,
                remedy=object.__getattribute__(self, "_fix"),
            )
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

    def __getitem__(self, name: str) -> AtomT:
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
        return list(
            generated_aliases(
                self._known(), operators=object.__getattribute__(self, "_operators")
            )
        )

    def _ipython_key_completions_(self):
        # Most engine names carry a hyphen, so S["<TAB>"] is where they live.
        return self._known()
