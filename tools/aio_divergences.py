"""Purpose: the async surface's exclusions and its one signature divergence,
each with the reason it is not simply Space's door awaited. `aiogen.py`
generates every other mirrored door from `Space` verbatim and reads these for
the cases that cannot be.

The ledger exists because the divergences were REAL and UNRECORDED. Measured
2026-08-31 over the 66 hand-written mirrors: 15 carried a signature different
from the sync door's, 16 weakened its return type, and 64 of 66 paraphrased
its docstring, while the section comment above them said the synchronous
docstrings applied verbatim. Two of the fifteen were runtime refusals rather
than annotations: `await am.type(atom=x)` raised TypeError where
`m.type(atom=x)` answers, because the async door had made the parameter
positional-only, and `await am.pure()` raised where `m.pure()` returns a
decorator. None of the 66 docstrings said why.

Assumes:
  - a reason names the MECHANISM that makes the sync shape impossible across
    the worker, not a preference. "Simpler" is not one.
Guarantees:
  - every name here is a live Space method, and every mirrored door not here
    carries Space's signature, return annotation and docstring verbatim
    [tested: test_the_async_mirror_is_generated_from_the_sync_surface]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

#: Space methods with NO async door, and why the async surface omits them.
EXCLUDED: dict[str, str] = {
    "pool": (
        "asyncio's fan-out is N workers and asyncio.gather; a pool of engine "
        "threads is the synchronous spelling of the same thing"
    ),
    "prolog": "an interactive Prolog toplevel belongs to a terminal thread",
    "transactional": (
        "a transaction body is a closed synchronous goal, SWI's transaction/1 "
        "takes one; transaction() is the async spelling, and there is no "
        "decorator because decoration cannot await"
    ),
    "answers": (
        "Answers is a synchronous replayable iterator; AsyncMeTTa's stream is "
        "the awaitable pull protocol rather than a cross-thread iterator"
    ),
    "metatype": "Space's Atom/Handle operand protocol, not an engine call",
    "to_wire": "Space's Atom/Handle operand protocol, not an engine call",
}

#: Doors whose async signature CANNOT be the sync one, with the mechanism that
#: forbids it and the replacement parameter list.
DIVERGENT: dict[str, tuple[str, str]] = dict.fromkeys(
    ("pure", "reads", "writes", "io"),
    (
        "self, fn: Callable, /, **options: Any",
        "the sync door's fn=None form returns a DECORATOR, and a decorator "
        "handed back across the worker would register on the caller's thread "
        "rather than the engine's. Only the applied form crosses",
    ),
)

#: Doors reached through a private Space method: the public name is the async
#: one, and the sync surface spells its own door differently.
PRIVATE_TARGET: dict[str, str] = {"one": "_one", "first": "_first"}

#: The module tier: metta.run(...) and its siblings, each one delegation to
#: the same door on the default context's self space. Membership here is a
#: DESIGN decision rather than a derivation, because the module level carries
#: only the everyday verbs; the pair maps the module name to the Space door
#: it reaches, and only `speculate` differs, Space's noun being
#: `speculative()`.
MODULE_DOORS: tuple[tuple[str, str], ...] = (
    ("run", "run"),
    ("load", "load"),
    ("match", "match"),
    ("add", "add"),
    ("remove", "remove"),
    ("eval", "eval"),
    ("solve", "solve"),
    ("doc", "doc"),
    ("define", "define"),
    ("op", "op"),
    ("pure", "pure"),
    ("reads", "reads"),
    ("writes", "writes"),
    ("io", "io"),
    ("stats", "stats"),
    ("limits", "limits"),
    ("speculate", "speculative"),
    ("trace", "trace"),
)

#: The context's PROTOCOL faces, mirrored from Space the way the named doors
#: are: the process home's handle speaks the same container and write
#: protocols its space speaks, which is the MeTTa()~dict() reading the
#: surface promises. The in-place trio returns the CONTEXT (the operator
#: protocol rebinds the left operand to the return value, and delegating the
#: return would silently swap a MeTTa for its Space); the rest delegate
#: plainly. __bool__ MUST ride along with __len__: Space's own bool is
#: always True (a handle, not a value that dwindles), and without the
#: mirror bool() falls through to the mirrored __len__ and an empty
#: context turns falsy, the datetime-midnight bug class Space's docstring
#: names. Deliberately absent, each for a reason and not an oversight:
#: __eq__/__hash__ and __enter__/__exit__ (the context's own identity and
#: lifecycle, hand-written beside __init__), __repr__ (the context's own
#: identity face, hand-written), __str__,
#: __setattr__/__delattr__/__reduce__/__deepcopy__ (space-handle mechanics).
CONTEXT_DUNDERS: tuple[str, ...] = (
    "__bool__",
    "__iadd__",
    "__isub__",
    "__ior__",
    "__contains__",
    "__iter__",
    "__len__",
    "__getitem__",
    "__delitem__",
)

#: The in-place subset of CONTEXT_DUNDERS whose rendered body must
#: `return self` after delegating.
INPLACE_DUNDERS: frozenset[str] = frozenset({"__iadd__", "__isub__", "__ior__"})

