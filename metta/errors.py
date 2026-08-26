"""Purpose: define PeTTa errors and the operation non-reduction signal.

Guarantees:
  - Timeout is both the PeTTa coordination miss and a builtin TimeoutError,
    so callers may catch at either abstraction [tested:
    test_the_coordination_family_is_python_shaped; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - every PettaError carries atom, space, operation and capability
    attributes, None by default, the message unchanged for their presence
    [tested test_base_fields_default_to_none]
  - MettaOperationError.operation is the base field, not a shadow
    [tested test_operation_error_operation_is_the_base_field]
  - AssertionFailure is a PettaError and NOT an EngineError, so a harness
    separates a false claim from a broken engine by type [tested
    test_a_failing_assertion_is_a_different_exception_from_an_engine_fault]
  - SpaceCapabilityError carries the refused space, operation, and capability
    as fields [tested:
    test_a_restricted_space_cannot_reach_what_its_base_does_not_publish;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - semantic refusals carry a structured Python-reference or MeTTa-law ground,
    and every CompileError derives one from its construct [tested:
    bindings/python/tests/test_refusal_grounds.py,
    tests/check_refusal_grounds.py;
    commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - a reified-world effect refusal carries the named EffectSafety law as its
    machine-readable ground [tested:
    test_an_uncovered_world_refuses_before_creating_scratch_or_running_the_operation;
    commit=WORKTREE]
  - CompileError can render a source path, function, line and exact caret span
    while retaining its machine-readable construct and coordinates [tested:
    test_unknown_host_callee_refusal_has_file_caret_and_both_remedies;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "AssertionFailure",
    "CompileError",
    "EngineError",
    "InferenceLimitError",
    "Interrupted",
    "MettaOperationError",
    "MettaResultError",
    "MettaSyntaxError",
    "NotReducible",
    "PettaError",
    "ResourceLimitError",
    "SourceNotFound",
    "SpaceCapabilityError",
    "StrictError",
    "SubscriberError",
    "TimeLimitError",
    "Timeout",
    "TransportFailure",
    "is_transport_failure",
]


@dataclass(frozen=True)
class _RefusalGround:
    """The semantics that requires one refusal, carried beside its prose."""

    kind: str
    citation: str

    def __post_init__(self) -> None:
        if self.kind not in ("python-reference", "metta-law"):
            msg = f"unknown refusal-ground kind {self.kind!r}"
            raise ValueError(msg)
        if not self.citation.strip():
            msg = "a refusal ground requires a nonempty citation"
            raise ValueError(msg)

    def __str__(self) -> str:
        return f"{self.kind}: {self.citation}"


_PYTHON_COMPARISON_GROUND = _RefusalGround(
    "python-reference",
    "Python Language Reference section 6.10, Comparisons",
)
_PYTHON_RICH_COMPARISON_GROUND = _RefusalGround(
    "python-reference",
    "Python Language Reference section 3.3.1, Basic customization",
)
_EFFECT_SAFETY_GROUND = _RefusalGround(
    "metta-law",
    "LeaTTa EffectSafety: a reified world admits only an effect plan covered by its handlers",
)

_COMPILE_REFERENCE_BY_CONSTRUCT = (
    (("match", "pattern", "case"), "Python Language Reference section 8.6, The match statement"),
    (("loop", "for", "while"), "Python Language Reference section 8.2-8.3, while and for statements"),
    (("with",), "Python Language Reference section 8.5, The with statement"),
    (("yield", "generator"), "Python Language Reference section 6.2.9, Yield expressions"),
    (("call", "callee", "keyword", "function", "def", "twin"), "Python Language Reference section 6.3.4, Calls"),
    (("attribute",), "Python Language Reference section 6.3.2, Attribute references"),
    (("subscript", "slice"), "Python Language Reference section 6.3.3, Subscriptions"),
    (("comparison", "boolean"), "Python Language Reference section 6.10-6.11, Comparisons and Boolean operations"),
    (("arithmetic", "floor", "binary", "reduce"), "Python Language Reference section 6.7, Binary arithmetic operations"),
    (("name", "ambiguous"), "Python Language Reference section 4.2, Naming and binding"),
)


def _compile_ground(construct: str | None) -> _RefusalGround:
    lowered = "" if construct is None else construct.lower()
    citation = next(
        (
            reference
            for terms, reference in _COMPILE_REFERENCE_BY_CONSTRUCT
            if any(term in lowered for term in terms)
        ),
        "Python Language Reference section 6, Expressions",
    )
    return _RefusalGround("python-reference", citation)


class _GroundedTypeError(TypeError):
    """A Python-shaped TypeError whose semantic ground is machine-readable."""

    def __init__(self, message: str, *, ground: _RefusalGround):
        super().__init__(message)
        self.ground = ground


def _grounded_type_error(message: str, *, ground: _RefusalGround) -> TypeError:
    """Construct a TypeError without exposing a second public exception name."""
    return _GroundedTypeError(message, ground=ground)


class PettaError(Exception):
    """Base class for everything this library raises on purpose.

    Machine-readable parts ride beside the message, the way
    AttributeError.name and OSError.errno do: `atom` is the MeTTa atom
    the error is about, an `(Error ...)` answer or the offending term;
    `space` is the space name involved; `operation` the operation that
    refused; `capability` the capability that was missing; `ground` the
    Python-reference or named MeTTa law that requires a semantic refusal.
    Each defaults to None, and the message never changes for their presence, so a
    program reacts to the part where it used to parse the sentence.
    """

    def __init__(  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self,
        *args: object,
        atom: object | None = None,
        space: str | None = None,
        operation: str | None = None,
        capability: str | None = None,
        ground: _RefusalGround | None = None,
    ):
        super().__init__(*args)
        self.atom = atom
        self.space = space
        self.operation = operation
        self.capability = capability
        self.ground = ground


class Timeout(PettaError, TimeoutError):  # noqa: N818 -- a timeout is the public outcome, not an implementation error suffix
    """A bounded coordination wait ended before anything arrived."""


class MettaSyntaxError(PettaError):
    """The reader refused the source. Carries the engine's own message."""


class SourceNotFound(PettaError, FileNotFoundError):  # noqa: N818  -- the exception name is a domain outcome in the public protocol, not an implementation error suffix
    """A file this library was asked to load is not there.

    Both bases on purpose. A caller reaching for a source file writes
    `except FileNotFoundError`, and a caller wrapping a whole registration
    writes `except PettaError`; one exception answering to both is what
    stops the second reading from silently missing this case, which is what
    a plain FileNotFoundError did.
    """


class EngineError(PettaError):
    """A Prolog-side exception crossed the boundary.

    The original janus exception rides along as __cause__, so nothing is
    hidden; the message here is the engine's, trimmed of janus framing.
    """


class SpaceCapabilityError(EngineError):
    """A restricted space tried an operation its creation grants omit."""

    def __init__(
        self,
        message: str,
        *,
        space: str,
        operation: str,
        capability: str,
    ):
        """Carry the refusing space, operation, and missing capability as data."""
        super().__init__(
            message,
            space=space,
            operation=operation,
            capability=capability,
        )


class MettaOperationError(EngineError):
    """A builtin refused a value, naming the operation the source wrote.

    The engine keeps the ISO formal term and adds the written operation, so
    the parts arrive as data: `operation` is what to look for in the source,
    `kind` is the formal's functor, and `expected` and `culprit` carry the
    type and the offending value when the formal is a type error. Catching
    EngineError still catches this.
    """

    def __init__(  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self,
        message: str,
        *,
        operation: str,
        kind: str,
        expected: object | None = None,
        culprit: object | None = None,
    ):
        super().__init__(message, operation=operation)
        self.kind = kind
        self.expected = expected
        self.culprit = culprit


class MettaResultError(PettaError):
    """The evaluation ANSWERED an `(Error ...)` atom, at a door that
    answers a single value.

    In MeTTa an error is a result: `(Error culprit reason)` is one
    element of the answer multiset, which is why the aggregation doors,
    eval(), run(), function iteration and the streams, keep it as data. A door
    that answers exactly one value has no multiset for the error to be
    data in, so one(), first() and calling a function raise it instead.
    `atom` carries the whole `(Error ...)` expression, `culprit` the
    term it blames, `reason` the explanation beside it. Not an
    EngineError on purpose: the engine did not throw, the program
    answered an error value.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self,
        message: str,
        *,
        atom: object,
        culprit: object | None = None,
        reason: object | None = None,
        space: str | None = None,
    ):
        super().__init__(message, atom=atom, space=space)
        self.culprit = culprit
        self.reason = reason


class AssertionFailure(PettaError):  # noqa: N818  -- the exception name is a domain outcome in the public protocol, not an implementation error suffix
    """A MeTTa `(test ...)` or `(assert ...)` said something false.

    Deliberately NOT an EngineError: the engine worked, the program's claim
    did not hold. A harness runs a suite and has to tell "this file's
    assertion is red" from "the interpreter under it broke", and those two
    call for opposite responses, so they are opposite types. Both are still
    PettaError, so a caller wrapping a whole run keeps catching both.

    `operation` is the form that failed, "test" or "assert"; `actual` is what
    the expression produced and `expected` what the source asked for, each
    None where the form carries no such value (a failed `assert` has a goal
    and no pair, and a `test` with no answer at all has no actual).
    """

    def __init__(  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self,
        message: str,
        *,
        operation: str,
        actual: object | None = None,
        expected: object | None = None,
    ):
        super().__init__(message, operation=operation, atom=actual)
        self.actual = actual
        self.expected = expected


class SubscriberError(PettaError):
    """A watcher raised, and the write it was watching had already landed.

    A subscription callback runs inside the write that triggered it, so its
    exception comes back out through the writer. Told apart from a refused
    write only by reading the message, the two invited opposite responses to
    the same sentence: retry a refused write, never retry an applied one.
    A space is a multiset, so the second copy the retry stores is permanent.

    `subscription` is the standing query whose callback raised, `atom` and
    `space` are what was written and where, `action` is "add" or "remove",
    and `__cause__` is what the callback actually raised.

    The write is applied when this is raised. An enclosing atomic run or
    `(transaction ...)` scope is the one thing that undoes it, and it does
    so as this error leaves the scope.
    """

    def __init__(  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self,
        message: str,
        *,
        subscription: object,
        action: str,
        atom: object | None = None,
        space: str | None = None,
    ):
        super().__init__(message, atom=atom, space=space)
        self.subscription = subscription
        self.action = action


class ResourceLimitError(EngineError):
    """A per-call resource guard stopped the evaluation.

    The guard is the caller's own timeout= or inferences= bound. Whatever
    the goal completed before the stop, writes included, stands; that is
    what stopping a computation mid-way means everywhere.
    """


class TimeLimitError(ResourceLimitError):
    """timeout= seconds elapsed before the call finished."""


class InferenceLimitError(ResourceLimitError):
    """inferences= engine steps were spent before the call finished."""


class Interrupted(EngineError):  # noqa: N818  -- the exception name is a domain outcome in the public protocol, not an implementation error suffix
    """interrupt() stopped the evaluation mid-goal.

    The sqlite3 and DuckDB reading of interrupt: whatever the goal
    completed before the stop, writes included, stands.
    """


class StrictError(PettaError):
    """An opt-in strict run or eval refused an answer nothing reduced.

    Strict means every directive must reduce. `term` is the answer the
    engine handed back unevaluated, and `directive` is its 1-based position
    in the source. An empty answer is NOT a violation: a pruned branch is
    what (empty) and a match with no candidates produce, and refusing it
    would refuse ordinary MeTTa.
    """

    def __init__(self, message: str, *, term: object = None, directive: int | None = None):  # noqa: D107  -- the enclosing class documents construction and the object invariants
        where = f"directive {directive}: " if directive is not None else ""
        super().__init__(f"{where}{message}")
        self.term = term
        self.directive = directive


class CompileError(PettaError):
    """A Python construct the define compiler refuses, with the reason.

    Refusals are the contract: every one names the construct, the line, and
    what to write instead, so the message teaches the subset rather than
    hiding it. Never a silent fallback.
    """

    def __init__(  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self,
        message: str,
        *,
        construct: str | None = None,
        line: int | None = None,
        ground: _RefusalGround | None = None,
        path: str | None = None,
        source_line: str | None = None,
        column: int | None = None,
        end_column: int | None = None,
        function: str | None = None,
        annotation: str | None = None,
    ):
        if path is not None and line is not None and source_line is not None:
            headline, *detail = message.splitlines()
            place = f"  --> {path}:{line}"
            if function is not None:
                place += f" in {function}"
            place += f" (line {line})"
            start = max(column or 0, 0)
            stop = max(end_column or start + 1, start + 1)
            caret = " " * start + "^" * (stop - start)
            if annotation is not None:
                caret += f" {annotation}"
            rendered = "\n".join(
                [
                    headline,
                    place,
                    "   |",
                    f"{line:>3} | {source_line.rstrip()}",
                    f"   | {caret}",
                    *detail,
                ]
            )
        else:
            where = f" (line {line})" if line is not None else ""
            rendered = f"{message}{where}"
        super().__init__(rendered, ground=ground or _compile_ground(construct))
        self.construct = construct
        self.line = line
        self.path = path
        self.column = column
        self.end_column = end_column


class TransportFailure(PettaError):  # noqa: N818  -- the exception name is a domain outcome in the public protocol, not an implementation error suffix
    """The backend is ABSENT rather than wrong: a connection, a timeout, a
    closed stream. The seam's error trichotomy treats these differently
    from application errors: a declared keep or empty mode never applies,
    transport always aborts, because retrying or giving up is the caller's
    decision and an absent backend has said nothing about the data.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose


def is_transport_failure(error: BaseException) -> bool:
    """Whether an error is the backend being ABSENT rather than wrong.

    The obvious test does not separate them: a socket timeout raises
    OSError, but websocket-client's own timeout does NOT subclass it, so
    "is the cause an OSError" misses exactly the shape a broken event
    stream takes under load. Hoisted from the DAS surface to the seam,
    because every remote backend needs the same trichotomy.
    """
    from ._optional import optional_module  # noqa: PLC0415  optional probe

    cause = error.__cause__ if isinstance(error, PettaError) else error
    if isinstance(error, TransportFailure):
        return True
    if isinstance(cause, (OSError, TimeoutError)):
        return True
    module = optional_module("websocket")
    if module is None:
        return False
    return isinstance(
        cause,
        (module.WebSocketTimeoutException, module.WebSocketConnectionClosedException),
    )


class NotReducible(Exception):  # noqa: N818  -- the exception name is a domain outcome in the public protocol, not an implementation error suffix
    """Raised inside an operation to answer nothing at all.

    A deterministic operation that raises NotReducible makes the call fail rather
    than error, which is how a semi-deterministic MeTTa function says no. A
    generator operation needs no signal: yielding nothing already is one.
    """
