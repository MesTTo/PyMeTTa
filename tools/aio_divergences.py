"""Purpose: record exclusions and signature divergences in the async surface.

`aiogen.py` generates mechanical counterparts from Space. A handwritten
counterpart still conforms to Space or MeTTa, unless this ledger states the
worker mechanism that requires a different parameter shape.

The ledger exists because the divergences were REAL and UNRECORDED. Measured
2026-08-31 over the 66 hand-written mirrors: 15 carried a signature different
from the sync method's, 16 weakened its return type, and 64 of 66 paraphrased
its docstring, while the section comment above them said the synchronous
docstrings applied verbatim. Two of the fifteen were runtime refusals rather
than annotations: `await am.type(atom=x)` raised TypeError where
`m.type(atom=x)` answers, because the async method had made the parameter
positional-only, and `await am.pure()` raised where `m.pure()` returns a
decorator. None of the 66 docstrings said why.

Assumes:
  - a reason names the MECHANISM that makes the sync shape impossible across
    the worker, not a preference. "Simpler" is not one.
Guarantees:
  - every name here resolves to a synchronous method; generated counterparts
    carry its signature, return annotation and docstring verbatim except for
    the DIVERGENT replacement signatures, while
    handwritten counterparts obey the parameter-name parity gate or the
    replacement parameter shape below [tested:
    test_every_async_counterpart_has_the_sync_parameters; commit=d263b1f05e3ca3a0621122c1fc60d295b87692b0]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

#: Space methods with NO async counterpart, and why the async surface omits them.
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
    "self": (
        "the space a receiver's doors work in, which for a space IS the "
        "receiver: mirroring it would give the async tier a property whose "
        "answer is the SYNCHRONOUS space, which is the one thing the async "
        "surface exists not to hand out. AsyncMeTTa answers its own home "
        "through the context tier, and an async space is already itself"
    ),
}

#: Methods whose async signature CANNOT be the sync one, with the mechanism that
#: forbids it and the replacement parameter list.
_DECORATOR_ACROSS_THE_WORKER = (
    "the sync method's fn=None form returns a DECORATOR, and a decorator "
    "handed back across the worker would register on the caller's thread "
    "rather than the engine's. Only the applied form crosses"
)

DIVERGENT: dict[str, tuple[str, str]] = dict.fromkeys(
    ("pure", "reads", "writes", "io"),
    ("self, fn: Callable, /, **options: Any", _DECORATOR_ACROSS_THE_WORKER),
)

#: `define` and `op` carry the same mechanism and were not recorded, because
#: the parameter gate compared NAMES and flattened positional-only together
#: with positional-or-keyword. `m.define(fn=f)` answers and
#: `await am.define(fn=f)` raises TypeError, which is the shape this file was
#: written for: one of the two runtime refusals measured 2026-08-31 was exactly
#: that, on `type`. Separating the kinds in the gate surfaced both.
DIVERGENT["define"] = (
    "self, fn: Callable | None = None, /, *, prolog: Any = None, "
    "name: Any = None, accessors: bool = True, methods: bool = True",
    _DECORATOR_ACROSS_THE_WORKER,
)
DIVERGENT["op"] = (
    "self, fn: Callable, /, *, effect: Any, name: Any = None, "
    "transport: Any = 'encoded', declarations: Any = (), arities: Any = None, "
    "inverse: Any = None",
    _DECORATOR_ACROSS_THE_WORKER,
)

DIVERGENT["subscribe"] = (
    'self, pattern: Any, *, on: str = "add", where: Any | None = None, '
    'queue_max: int = SUBSCRIPTION_QUEUE_MAX',
    "the synchronous callback runs during delivery on the engine worker, "
    "while async consumers resume on their event loop. A caller callback "
    "cannot run on both threads; the async event stream is the delivery "
    "across that boundary and therefore has no callback parameter",
)

#: Methods reached through a private Space method: the public name is the async
#: one, and the sync surface uses a different method name.
PRIVATE_TARGET: dict[str, str] = {"one": "_one", "first": "_first"}

#: The module tier: metta.run(...) and its siblings, each one delegation to
#: the same method on the default context's self space. Membership here is a
#: DESIGN decision rather than a derivation, because the module level carries
#: only the everyday verbs; the pair maps the module name to the Space method
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
    ("debug", "debug"),
    ("record", "record"),
)

#: The context's PROTOCOL methods, mirrored from Space the way the named methods
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
