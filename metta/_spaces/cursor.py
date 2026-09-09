"""Purpose: consume an engine-held query as a Python iterator.

Owns resources: Cursor._finish closes an opened query on exhaustion or close;
Cursor._reap defers abandonment cleanup to the engine
[source: extensions/python/metta/_spaces/cursor.py:374, Cursor._reap; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
"""

from __future__ import annotations

import logging
import warnings
import weakref
from collections import deque
from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Any, Self, cast

import metta._spaces.results as _spaces_results_module
import metta._spaces.scope as _spaces_scope_module
from metta._atoms.factories import (
    TRUE,
    Atom,
    Expression,
    Grounded,
    Variable,
    _atom_from_wire,
    _to_atom,
    _variables,
    and_,
)
from metta._binding.runtime import Runtime, defer_engine_call
from metta._catalog.bounds import config
from metta._errors.errors import EngineError, MettaError
from metta._lazy import lazy

logger = logging.getLogger(__name__)

def _require_vocabulary(
    value: Any, vocabulary: Any, called: str, *, because: str = ""
) -> Any:
    """One of a closed vocabulary's members, or a refusal naming them all.

    Thirteen declaration methods wrote this check longhand, each rebuilding the
    same sentence. Naming the whole vocabulary is the part that matters and the
    part a hand-written check drops first: a caller who wrote the wrong word
    needs to see the right ones, not that theirs is unknown.

    ``because`` is the clause a method adds when the refusal needs its ground --
    `handles` says the fidelity is the claim the router acts on, so an unknown
    word would declare nothing silently.
    """
    if value not in vocabulary:
        msg = f"{called} is one of {', '.join(vocabulary)}, not {value!r}"
        if because:
            msg = f"{msg}: {because}"
        raise ValueError(msg)
    return value

def _require_bound(value: Any, called: str, kinds: tuple[type, ...], reads: str) -> None:
    """Check one per-call bound, type before magnitude.

    Comparing first reports a wrong type as "'>' not supported between
    instances of 'str' and 'int'", which names neither the argument nor the
    call the user made.
    """
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, kinds):
        msg = f"{called} must be {reads} or None, got {value!r}"
        raise TypeError(msg)
    # isinstance against a variable tuple narrows value to object, so the
    # comparison needs the type the check just established.
    if not cast(float, value) > 0:
        msg = f"{called} must be positive, got {value!r}"
        raise ValueError(msg)

def _validate_limit(limit: int | None) -> None:
    """Require the one public query-limit vocabulary before an engine call."""
    if limit is None:
        return
    if isinstance(limit, bool) or not isinstance(limit, int):
        msg = f"limit must be a positive int or None, got {limit!r}"
        raise TypeError(msg)
    if limit <= 0:
        msg = f"limit must be positive, got {limit}"
        raise ValueError(msg)

def require_deadline(deadline: Any) -> None:
    """Check one quiet-deadline: a nonnegative number of seconds, or None.

    One definition because three methods take the same argument and mean the
    same thing by it: peek(), take() and watch(), across both surfaces. It
    was written out twice in _space.py and the async watch had no check at
    all, which is how the two surfaces came to disagree about whether a
    deadline was even a parameter.
    """
    if deadline is None:
        return
    if isinstance(deadline, bool) or not isinstance(deadline, (int, float)) or deadline < 0:
        msg = f"deadline is a nonnegative number of seconds, not {deadline!r}"
        raise ValueError(msg)

def guard_atom(where: Any | None) -> Atom | None:
    """Convert a where= guard, refusing one that can never answer a truth.

    A grounded non-boolean is the trap: it converts to a perfectly good
    atom, the engine evaluates it per row, nothing is ever true, and the
    query answers empty as though the data were wrong. why() then blames
    the guard, which is honest but sends the reader to the data.
    """
    if where is None:
        return None
    if isinstance(where, Sequence) and not isinstance(
        where, (str, bytes, bytearray, Atom)
    ):
        guards: list[Atom] = []
        for index, item in enumerate(where):
            guard = guard_atom(item)
            if guard is None:
                msg = (
                    f"where= guard sequence item {index} is None; omit it or "
                    f"pass an actual guard"
                )
                raise TypeError(msg)
            guards.append(guard)
        if not guards:
            return TRUE
        if len(guards) == 1:
            return guards[0]
        return and_(*guards)
    guard = _to_atom(where)
    # An expression is the guard proper; a variable is one a pattern bound to
    # a truth; a grounded bool is trivially one. A grounded value or a bare
    # symbol is neither a call nor a truth, so it can never be true.
    if isinstance(guard, (Expression, Variable)):
        return guard
    if isinstance(guard, Grounded) and isinstance(guard.value, bool):
        return guard
    msg = (
        f"a where= guard is a term the engine evaluates per row, as in "
        f"V.age.ge(18); {where!r} can never answer true"
    )
    raise TypeError(
        msg
    )

def _column_names(atoms: Iterable[Atom]) -> list[str]:
    """Distinct non-anonymous variables in first-appearance order."""
    return list(dict.fromkeys(name for atom in atoms for name in _variables(atom) if name != "_"))

def _forward_window(window: slice) -> tuple[int, int | None]:
    """A cursor slice's bounds, refusing the ones that need the whole stream.

    Both refusals are the design. A step still PULLS the rows it skips, and a
    negative bound means knowing where the end is, so accepting either would
    quietly buy the full scan the cursor exists to avoid, in the spelling that
    looks cheapest.
    """
    if window.step is not None and window.step != 1:
        msg = (
            "a cursor slice takes no step: skipping rows still pulls them, "
            "so [::2] costs what taking them all costs"
        )
        raise ValueError(
            msg
        )
    start = 0 if window.start is None else window.start
    if start < 0 or (window.stop is not None and window.stop < 0):
        msg = (
            "a cursor slice counts from the start only: a negative bound "
            "needs the whole stream, which is what the cursor exists to avoid"
        )
        raise ValueError(
            msg
        )
    return start, window.stop

def _explain_text(rt: Runtime, space_name: str, patterns: list, where) -> str:
    """The engine's own decisions for one conjunction, rendered. Pure
    reflection through metta_py_explain: nothing runs, no row is pulled,
    and the engine answers claimed/rest as indexes so the caller's own
    atoms, variable names included, do the rendering.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    kind, detail, claimed, rest = rt.apply_must(
        "metta_py_explain", space_name, [p.to_wire() for p in patterns]
    )
    shown = ", ".join(str(p) for p in patterns)
    lines = [f"query over {space_name}: {shown}"]
    if kind == "stored":
        lines.append("  stored atoms: engine unification joins the conjunction left to right")
    elif kind == "refused":
        lines.append(f"  REFUSED: the declared entry {detail[0]} answers Refuse for this conjunction")
    else:
        width = max(len(str(p)) for p in patterns)
        for pattern, (klass, origin) in zip(patterns, detail, strict=True):
            lines.append(f"  {pattern!s:<{width}}  {klass:<8}  {origin}")
        if claimed:
            names = ", ".join(str(patterns[i]) for i in claimed)
            lines.append(f"  conjunction: the provider claimed {names}")
            if rest:
                joined = ", ".join(str(patterns[i]) for i in rest)
                lines.append(f"  the engine joins the rest: {joined}")
            else:
                lines.append("  the engine joins nothing further")
        elif len(patterns) > 1:
            lines.append("  conjunction: no provider claim; the engine joins left to right")
        if any(k == "exact" for k, _ in detail):
            lines.append("  a bound reaches the provider only where the class is exact")
    if where is not None:
        lines.append(f"  guard {where}: runs in the engine over each row")
    return "\n".join(lines)

_CURSOR_LENGTH_REFUSAL = (
    "a cursor has no len(): counting its rows means pulling all of them, "
    "which is what it exists to avoid. Use len(space.match(pattern)) for the "
    "count, or match() if you want the rows"
)

class Cursor:
    """Private streaming answers pulled from an engine-held query in doubling
    chunks, one janus crossing per chunk. Iterate it, close() it, or leave its with-block. Exhaustion reaps
    the engine and remains ordinary iterator exhaustion; explicit close is a
    separate state that refuses further pulls. A cursor dropped unclosed is
    reaped by its finalizer. Rows carry the query's variable names as columns,
    exactly as match()'s rows do.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    __slots__ = (
        "__weakref__",
        "_annotation",
        "_atoms",
        "_buffer",
        "_cap",
        "_capture",
        "_chunk",
        "_closed",
        "_drained",
        "_exhausted",
        "_finalizer",
        "_handle",
        "_open_arguments",
        "_open_predicate",
        "_policy",
        "_row_cls",
        "_rt",
        "_space_name",
        "_stack",
        "_timeout",
        "_under",
        "_where_atom",
        "columns",
    )

    def __init__(
        self,
        space: _root.Space,
        patterns: tuple,
        where: Any | None,
        timeout: float | None,
        inferences: int | None,
        *,
        limit: int | None = None,
        context: _spaces_scope.EvaluationContext | None = None,
        capture: Any = None,
    ) -> None:
        if context is not None:
            limit = context.limit
        under = None if context is None else context.algebra
        order = None if context is None else context.order
        _validate_limit(limit)
        atoms = [_to_atom(p) for p in patterns]
        columns = _column_names(atoms)
        self.columns = tuple(columns)
        self._row_cls = _spaces_results_module._row_class(self.columns)
        limits = _spaces_scope_module._limits(timeout, inferences)
        # The inference budget rides inside the engine, because the engine's
        # work is its own counter's and a per-pull wrapper cannot see it.
        # Placement alone is not the whole of it: SWI bounds inferences per
        # SOLUTION, so the engine-side wrapper also reads that counter against
        # a base and stops on the answer that passes the budget. The wall bound
        # goes INSIDE the engine beside it, against what this comment used to
        # say: a time limit in this thread cannot interrupt a goal running
        # inside an engine, so wrapping each pull outside left the caller's
        # timeout inert [measured 2026-09-05, plain SWI:
        # `call_with_time_limit(2, engine_next(E, _))` over a non-terminating
        # engine goal ran ninety seconds without firing]. Idle time between
        # pulls counts now, because the deadline is absolute from the engine's
        # start, which is what a caller passing timeout= to a query means.
        self._timeout = None if limits is None or limits[0] < 0 else limits[0]
        steps = -1 if limits is None else limits[1]
        self._stack = -1 if limits is None else limits[2]
        self._rt = space.runtime
        self._atoms = atoms
        self._space_name = space.name
        wires = [a.to_wire() for a in atoms]
        checked = guard_atom(where)
        self._where_atom = checked
        guard = [] if checked is None else checked.to_wire()
        self._under = under
        self._capture = capture
        self._annotation: Atom | None = None
        predicate = "metta_py_cursor_open"
        arguments = [space.name, wires, guard, columns.copy(), limit or 0, steps]
        if under is not None:
            predicate = "metta_py_cursor_open_under"
            arguments.extend((under, order or "none"))
        # Appended last, so the `under` variant's existing positions stay put.
        arguments.append(-1.0 if self._timeout is None else float(self._timeout))
        self._open_predicate = predicate
        self._open_arguments = arguments
        self._handle: Any | None = None
        self._policy: Any = None
        self._closed = False
        self._exhausted = False
        self._buffer: deque = deque()
        self._chunk = 1
        # The doubling ceiling, read ONCE per cursor rather than per refill,
        # which is the granularity a chunk sequence can honour: a cap that
        # moved mid-drain would make one cursor's own doubling incoherent. A
        # program that rewrites the `(limit chunk-cap ...)` row therefore
        # reaches every cursor opened after the write. The read is the seat's
        # mirror of that row and costs no crossing; the engine announces the
        # write instead [source: extensions/python/metta/_catalog/bounds.py:404, _MIRROR; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
        self._cap = config.chunk_cap
        self._drained = False
        # The finalizer is the last guard, not the contract: it destroys
        # the engine if a cursor is dropped unclosed, from whichever
        # thread collection runs on (cross-thread destroy is probed).
        self._finalizer: weakref.finalize | None = None

    @staticmethod
    def _reap(runtime: Runtime, handle: Any) -> None:
        """The weakref.finalize callback: HAND OVER the close, never make it.

        This runs from the collector, at a point no caller chose, possibly
        while this thread is already inside a crossing. Closing the cursor here
        is a crossing, and one taken that way aborted the process inside SWI's
        copy_record [source:
        docs/journal/2026-09-06-finalisers-must-not-call-prolog.md;
        commit=2421d06e697daffb0797c307a798131616ebdd8e]. _finish() disarms this and closes
        directly, so the
        explicit path still reports its failures to the caller that asked.
        [tested: test_a_dropped_cursor_defers_its_close_instead_of_crossing;
        commit=2421d06e697daffb0797c307a798131616ebdd8e]
        """
        del runtime  # the drain makes the call on its own runtime
        defer_engine_call("metta_py_cursor_close", handle)

    def __iter__(self) -> Self:
        return self

    def _open(self) -> None:
        """Create the held engine at the first pull, under that pull's policy."""
        if self._handle is not None:
            return
        # The policy module imports this object's limit helpers, so the edge
        # is intentionally lazy after both modules have initialized.
        from metta._spaces.execution import (  # noqa: PLC0415 -- execution imports cursor during initialization
            _controlled_run,
            _execution_policy,
        )

        self._policy = _execution_policy()
        self._handle = _controlled_run(
            self._rt,
            self._open_predicate,
            self._open_arguments,
            None,
            policy=self._policy,
        )
        self._finalizer = weakref.finalize(
            self, Cursor._reap, self._rt, self._handle
        )

    def _finish(self) -> None:
        """Reap an opened engine; an inert, never-pulled cursor owns none.

        Every caller of this is explicit -- exhaustion and close() -- so the
        close is made here and now. detach() disarms the finalizer first, so
        the collector cannot later defer a close of the same handle, and
        returns None when it has already run, which keeps this idempotent.
        """
        finalizer, self._finalizer = self._finalizer, None
        if finalizer is None or finalizer.detach() is None:
            return
        try:
            self._rt.do("metta_py_cursor_close", self._handle)
        except EngineError:
            # Explicit close still reports failures through iteration; this
            # arm is the exhaustion path, which has nothing to report to.
            logger.debug("cursor close found an unavailable engine", exc_info=True)

    def _refill(self) -> None:
        """Cross once, for as many answers as this cursor has earned.

        A crossing costs 2.55us against 2.55us of engine work for a plain
        enumeration, so a cursor that crosses per answer spends half its time
        in the boundary: 27.9x the eager method at ten thousand answers, and the
        gap is per-crossing rather than a warm-up [tested:
        test_draining_amortises_the_crossing].

        The chunk starts at one and doubles, which is the same policy TCP
        opens a connection with and a vector grows by, and it is here for the
        same reason: a caller who takes one answer of an infinite stream must
        pay for one, and a caller who drains ten thousand should not pay ten
        thousand crossings. Taking k answers computes fewer than 2k, so
        stream()'s promise of work proportional to answers pulled holds with
        a constant rather than exactly.

        Nothing here asks what the query does. A producer with effects the
        developer did not declare is a wrong declaration, and effect classes
        exist so this layer does not second-guess them.

        Bounded cursors chunk too (user ruling, 2026-08-31). A budget that
        trips mid-chunk discards that chunk's collected prefix, so a spent
        cursor may deliver fewer answers than the budget's work computed:
        measured, a 3000-inference budget delivered 210 answers one at a time
        and 191 chunked. That is the accepted price; per-answer accounting at
        a trip is not worth a crossing per answer, and the diagnosis path is
        raising the budget, which delivers more. The wall bound consequently
        covers a chunk's worth of work per crossing rather than one answer's.
        """
        self._open()
        from metta._spaces.execution import _controlled_run  # noqa: PLC0415

        want = self._chunk
        limits = (
            None
            if self._timeout is None and self._stack < 0
            else (
                -1.0 if self._timeout is None else self._timeout,
                -1,
                self._stack,
            )
        )
        answers = _controlled_run(
            self._rt,
            "metta_py_cursor_chunk",
            [self._handle, want],
            limits,
            policy=self._policy,
        )
        self._buffer = deque(answers)
        # A SHORT chunk is the whole of the exhaustion signal, so no pull ever
        # looks past the last answer it was asked for.
        if len(answers) < want:
            self._drained = True
        self._chunk = min(want * 2, self._cap)

    def __next__(self):
        if self._closed:
            msg = "this cursor is closed"
            raise MettaError(msg)
        if not self._buffer:
            if self._exhausted or self._drained:
                self._exhausted = True
                self._finish()
                raise StopIteration
            self._refill()
        if not self._buffer:
            self._exhausted = True
            self._finish()
            raise StopIteration
        payload = self._buffer.popleft()
        if self._under is not None:
            row_wires, annotation_wire = payload
            self._annotation = _atom_from_wire(annotation_wire)
        else:
            row_wires = payload
        row = self._row_cls(_atom_from_wire(v) for v in row_wires)
        # An algebra cursor answers what match(under=) answers. Without this
        # the SAME word meant two things: a folded algebra answer through
        # match, and a bare row with a separate .annotation through stream
        # [measured 2026-08-31].
        if self._capture is not None:
            return self._capture(row, self._annotation)
        return row

    @property
    def annotation(self) -> Atom:
        """The annotation paired with the row most recently pulled."""
        if self._annotation is None:
            msg = "this cursor has not pulled an algebra-annotated row"
            raise RuntimeError(msg)
        return self._annotation

    def explain(self) -> str:
        """The query's plan, reflected rather than run: which provider
        decisions the engine already made for this conjunction. See
        Prepared.explain for the whole story; a cursor explains the same
        way, and explaining does not pull a row.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return _explain_text(self._rt, self._space_name, self._atoms, self._where_atom)

    def __getitem__(self, index: int | slice):
        """`cursor[:3]` and `cursor[0]`, pulling only what is asked for.

        This is the one convenience worth adding here, because it changes the
        SPELLING and not the plan. Measured over 2,000 stored atoms, wanting
        the first three: `match(pat)[:3]` costs 26,049 inferences because
        slicing trims after computing everything, `match(pat, limit=3)` costs
        94, and pulling three from a cursor costs 13. The cheapest route was
        the only one that could not be spelled naturally.

        A negative index or a step is REFUSED, not supported. Both need the
        whole stream, so accepting them would quietly buy the 26,049
        inferences this exists to avoid, in the spelling that looks cheapest.
        """
        if isinstance(index, slice):
            return self._take_slice(index)
        if not isinstance(index, int):
            msg = (
                f"a cursor is indexed by an int or a slice, not "
                f"{type(index).__name__}"
            )
            raise TypeError(
                msg
            )
        if index < 0:
            msg = (
                "a cursor cannot be indexed from the end: it does not know "
                "where the end is without pulling every row, which is what "
                "the cursor exists to avoid. Use match() if you want them all"
            )
            raise IndexError(
                msg
            )
        for position, row in enumerate(self):
            if position == index:
                return row
        msg = f"the cursor answered fewer than {index + 1} rows"
        raise IndexError(msg)

    def _take_slice(self, window: slice) -> list:
        start, stop = _forward_window(window)
        if stop is not None and stop <= start:
            return []
        taken = []
        for position, row in enumerate(self):
            if position >= start:
                taken.append(row)
            if stop is not None and position + 1 >= stop:
                break
        return taken

    def __len__(self) -> int:
        """Refused, and the refusal is the design.

        A length cannot be known without consuming the cursor, so answering
        one would silently materialise the very thing the cursor exists to
        avoid.
        """
        raise TypeError(_CURSOR_LENGTH_REFUSAL)

    def first(self, *, default: Any = _spaces_results_module._MISSING) -> Any:
        """Return the first row, or the caller's explicit default.

        Rows.first() and Answers.first() already spell this, with this
        contract and this message; a cursor is the third view of one lazy row
        source and had only ``next(cursor)`` plus a StopIteration to catch.
        Taking the first row is also the whole reason a stream exists, so it
        was the method most worth having and the one that was missing.

        This PULLS: the cursor is one-shot, so the row is gone from it. The
        cursor stays open, since a caller who wants the second row wants it
        from here.
        """
        row = next(self, _spaces_results_module._MISSING)
        if row is not _spaces_results_module._MISSING:
            return row
        if default is not _spaces_results_module._MISSING:
            return default
        msg = "first() found no rows; pass default= for absence"
        raise EngineError(msg)

    def one(self, *, default: Any = _spaces_results_module._MISSING) -> Any:
        """THE row, when the stream is asserted to have exactly one.

        Rows.one()'s contract on a cursor: none or several raise naming what
        was found, so a lookup that silently took an arbitrary row cannot
        hide. Proving "exactly one" costs the SECOND pull, which is what
        exactness means on a source that cannot be looked at twice, and the
        cursor is closed either way because nothing can follow the answer it
        just asserted is alone.
        """
        row = next(self, _spaces_results_module._MISSING)
        if row is _spaces_results_module._MISSING:
            self.close()
            if default is not _spaces_results_module._MISSING:
                return default
            msg = "one() expected exactly one row, got 0; use first() for row-or-default"
            raise EngineError(msg)
        extra = next(self, _spaces_results_module._MISSING)
        self.close()
        if extra is not _spaces_results_module._MISSING:
            msg = (
                "one() expected exactly one row, got at least 2; "
                "use first() for the first row, or iterate for all"
            )
            raise EngineError(msg)
        return row

    def close(self) -> None:
        """Destroy the held engine; idempotent and distinct from exhaustion."""
        if self._closed or self._exhausted:
            return
        self._closed = True
        self._finish()  # runs the reap exactly once; later GC is a no-op

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __del__(self) -> None:
        if not getattr(self, "_closed", True) and not getattr(self, "_exhausted", True):
            warnings.warn(
                "an open metta Cursor was discarded; use a with-block or close()",
                ResourceWarning,
                source=self,
                stacklevel=2,
            )

    def __repr__(self) -> str:
        state = "closed" if self._closed else "exhausted" if self._exhausted else "open"
        return f"<cursor {state} -> {', '.join(self.columns)}>"

# Resolve annotations after definitions so peer imports can finish.
if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
import metta._spaces.scope as _spaces_scope  # noqa: E402 -- deferred annotation bindings
