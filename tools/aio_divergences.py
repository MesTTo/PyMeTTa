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
