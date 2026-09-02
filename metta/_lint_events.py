"""Purpose: retain source-grounded advisory lint evidence and named intents.

Assumes:
  - ``&metta`` is the process reflection space and Python source positions use
    the coordinates returned by ``code.co_positions()`` and ``ast``
Guarantees:
  - ``# metta: ok(<rule>)`` comments are tokenized, bound to one statement,
    reflected as ``lint-intent`` data, and never alter execution [tested:
    test_a_named_metta_ok_intent_suppresses_only_its_bound_rule; commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - source evidence is immutable, deduplicated per logical space, and retired
    with that space [tested: test_lint_evidence_and_intent_follow_space_clear;
    commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - operation calls under compiled loop bodies are recognized from the
    registered operation object rather than from spelling [tested:
    test_an_operation_call_inside_a_compiled_loop_is_linted; commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - emitted authorities retain every adopted audit ID and point at the
    immutable public lint catalogue [tested:
    test_lint_authorities_are_durable_public_references;
    commit=2a32acb6d254ea12085526913c7b9a1a555b8ee0]
  - each live frame call site derives its source position once and then
    resolves repeated Answers iterations in constant time without retaining
    generated code [tested:
    test_answer_iteration_benchmark_reuses_one_warmed_view,
    test_answer_position_cache_does_not_own_generated_code;
    commit=0ffac1f272c65d1c3742a2bfb824538e426c264a]
Guarded by:
  - ``_LOCK`` serializes the process registries and their reflected facts
  - ``_POSITION_LOCK`` serializes the bounded weak call-site cache
"""

from __future__ import annotations

import ast
import builtins
import inspect
import io
import re
import textwrap
import threading
import tokenize
import weakref
from collections import OrderedDict
from collections.abc import Hashable
from dataclasses import dataclass
from pathlib import Path
from types import CodeType, FrameType, FunctionType
from typing import Any

from ._ops import live_registration
from .atoms import Atom, Expression, Grounded, Symbol

# These are the adopted authorities, not implementation folklore. Keeping the
# row IDs with every emitted kind lets a finding answer which ruling it applies.
_LINT_CATALOGUE = (
    "https://github.com/MesTTo/MeTTa-Kernel/blob/"
    "7de3d32d25a7166b12f7c68c179e9cbb931ac044/website/guide/run-query.md#lint-a-space"
)
_AUTHORITIES: dict[str, str] = {
    "operation-crossing-in-loop": f"P14-14-02/GG-004; {_LINT_CATALOGUE}",
    "first-letter-role-convention": f"P14-39-05; {_LINT_CATALOGUE}",
    "interpreter-equation-shadow": f"P14-40-07/STYLE-150/GG-008; {_LINT_CATALOGUE}",
    "module-level-defined-call": f"P14-40-09; {_LINT_CATALOGUE}",
    "effectful-operation-at-construction": f"GG-013; {_LINT_CATALOGUE}",
    "operation-staged-in-law": f"GG-014; {_LINT_CATALOGUE}",
    "unordered-answers-zip": f"GG4-006/GG5-007/L9Z2-08; {_LINT_CATALOGUE}",
    "unordered-answers-reversed": f"L9Z2-09; {_LINT_CATALOGUE}",
    "sync-engine-call-in-async": f"L9Z3-03; {_LINT_CATALOGUE}",
}
_INTENT_AUTHORITY = f"L9Z1-06; {_LINT_CATALOGUE}"

_DIRECTIVE = re.compile(r"#\s*metta:\s*ok\((?P<kind>[a-z0-9-]+)\)\s*$")
_PACKAGE = Path(__file__).resolve().parent
_REFLECTION_SPACE = "&metta"
_LOCK = threading.RLock()
_CO_COROUTINE = getattr(inspect, "CO_COROUTINE", 0x0080)
_CO_ASYNC_GENERATOR = getattr(inspect, "CO_ASYNC_GENERATOR", 0x0200)
_POSITION_LOCK = threading.Lock()
_POSITION_CACHE_MAX = 4_096
_POSITION_CACHE: OrderedDict[
    tuple[int, int],
    tuple[weakref.ReferenceType[CodeType], tuple[str, int, int]],
] = OrderedDict()


@dataclass(frozen=True)
class LintEvent:
    """One source event that becomes a Finding only when lint is requested."""

    kind: str
    subject: str
    path: str
    line: int
    column: int
    authority: str
    effect: str | None = None
    atom: Atom | None = None

    def fact(self, space: str) -> Expression:
        """Return the queryable reflection of this evidence."""
        return Expression(
            [
                Symbol("lint-evidence"),
                Symbol(space),
                Symbol(self.kind),
                Grounded(self.subject),
                Grounded(self.path),
                Grounded(self.line),
                Grounded(self.column),
                Grounded(self.authority),
            ]
        )


@dataclass(frozen=True)
class LintIntent:
    """One named source acknowledgement and the statement it governs."""

    kind: str
    path: str
    line: int
    column: int
    target_start: int
    target_end: int

    def fact(self, space: str) -> Expression:
        """Return the intent as ordinary queryable data."""
        return Expression(
            [
                Symbol("lint-intent"),
                Symbol(space),
                Symbol(self.kind),
                Grounded(self.path),
                Grounded(self.line),
                Grounded(self.column),
                Grounded(self.target_start),
                Grounded(self.target_end),
                Grounded(_INTENT_AUTHORITY),
            ]
        )


@dataclass(frozen=True)
class LintInvocation:
    """The user source statement that requested one lint pass."""

    path: str
    line: int


_OWNER_EVENTS: dict[str, dict[Hashable, frozenset[LintEvent]]] = {}
_TRANSIENT_EVENTS: dict[str, set[LintEvent]] = {}
_INTENTS: dict[str, set[LintIntent]] = {}
_RUNTIMES: dict[str, Any] = {}
_PARSED_FILES: dict[str, tuple[int, int, tuple[LintIntent, ...]]] = {}
_SOURCE_CALLS: dict[str, tuple[int, int, dict[int, tuple[ast.Call, ...]]]] = {}


def authority_for(kind: str) -> str:
    """Return the exact adopted authority carried by one new lint kind."""
    return _AUTHORITIES[kind]


def _space_parts(space: Any) -> tuple[str, Any]:
    name = str(space.name)
    return name, space.runtime


def _runtime_for_name(space: str) -> Any:
    runtime = _RUNTIMES.get(space)
    if runtime is not None:
        return runtime
    from ._engine import (  # noqa: PLC0415 -- Answers imports before engine
        runtime as current_runtime,
    )

    return current_runtime()


def _retain(runtime: Any, fact: Expression) -> None:
    runtime.must("metta_py_add(Space, W)", Space=_REFLECTION_SPACE, W=fact.to_wire())


def _release(runtime: Any, fact: Expression) -> None:
    runtime.once(
        "metta_py_remove(Space, W, _)", Space=_REFLECTION_SPACE, W=fact.to_wire()
    )


def _all_events(space: str) -> set[LintEvent]:
    owned = _OWNER_EVENTS.get(space, {})
    return set().union(*owned.values(), _TRANSIENT_EVENTS.get(space, set()))


def _replace_owner(
    space: Any, owner: Hashable, current: set[LintEvent] | frozenset[LintEvent]
) -> None:
    name, runtime = _space_parts(space)
    with _LOCK:
        _RUNTIMES[name] = runtime
        before = _all_events(name)
        _OWNER_EVENTS.setdefault(name, {})[owner] = frozenset(current)
        after = _all_events(name)
        for event in before - after:
            _release(runtime, event.fact(name))
        for event in after - before:
            _retain(runtime, event.fact(name))


def _record(space: Any, event: LintEvent) -> None:
    name, runtime = _space_parts(space)
    with _LOCK:
        _RUNTIMES[name] = runtime
        events = _TRANSIENT_EVENTS.setdefault(name, set())
        if event in events or event in _all_events(name):
            return
        events.add(event)
        _retain(runtime, event.fact(name))


def _record_for_name(space: str, event: LintEvent) -> None:
    runtime = _runtime_for_name(space)
    with _LOCK:
        _RUNTIMES[space] = runtime
        events = _TRANSIENT_EVENTS.setdefault(space, set())
        if event in events or event in _all_events(space):
            return
        events.add(event)
        _retain(runtime, event.fact(space))


def _position(frame: FrameType) -> tuple[str, int, int]:
    # CPython's inspect._get_code_position reaches instruction N with
    # islice(code.co_positions(), N), a linear walk on every call. Deriving a
    # call site once changes I repeated positions after B bytecode entries
    # from Theta(I*B) to Theta(B+I).
    # Source: https://github.com/python/cpython/blob/f6842ddae6b0c744b89c33b9bb088d7c4b3eb8d3/Lib/inspect.py#L1566-L1571
    code = frame.f_code
    key = (id(code), frame.f_lasti)
    with _POSITION_LOCK:
        cached = _POSITION_CACHE.get(key)
        if cached is not None and cached[0]() is code:
            _POSITION_CACHE.move_to_end(key)
            return cached[1]

    path = code.co_filename
    if not (path.startswith("<") and path.endswith(">")):
        path = str(Path(path).resolve())
    info = inspect.getframeinfo(frame, context=0)
    positions = info.positions
    column = (
        0
        if positions is None or positions.col_offset is None
        else positions.col_offset
    )
    result = (path, frame.f_lineno, column)

    def retire(reference: weakref.ReferenceType[CodeType]) -> None:
        with _POSITION_LOCK:
            current = _POSITION_CACHE.get(key)
            if current is not None and current[0] is reference:
                del _POSITION_CACHE[key]

    reference = weakref.ref(code, retire)
    with _POSITION_LOCK:
        _POSITION_CACHE[key] = (reference, result)
        _POSITION_CACHE.move_to_end(key)
        while len(_POSITION_CACHE) > _POSITION_CACHE_MAX:
            _POSITION_CACHE.popitem(last=False)
    return result


def external_caller(frame: FrameType | None = None) -> FrameType | None:
    """Find the first caller outside the package implementation."""
    current = frame or inspect.currentframe()
    current = None if current is None else current.f_back
    while current is not None:
        filename = current.f_code.co_filename
        if filename.startswith("<") and filename.endswith(">"):
            return current
        try:
            resolved = Path(filename).resolve()
            resolved.relative_to(_PACKAGE)
        except ValueError:
            return current
        current = current.f_back
    return None


def _statement_targets(tree: ast.AST) -> list[ast.stmt]:
    return [node for node in ast.walk(tree) if isinstance(node, ast.stmt)]


def _target_for_comment(
    statements: list[ast.stmt], line: int, column: int, *, inline: bool
) -> tuple[int, int]:
    if inline:
        return line, line
    exact = [
        node
        for node in statements
        if node.lineno > line and node.col_offset == column
    ]
    candidates = exact or [node for node in statements if node.lineno > line]
    if not candidates:
        return line, line
    target = min(candidates, key=lambda node: (node.lineno, node.col_offset))
    return target.lineno, target.end_lineno or target.lineno


def _parse_intents(path: str) -> tuple[LintIntent, ...]:
    source_path = Path(path)
    try:
        stat = source_path.stat()
    except OSError:
        return ()
    cached = _PARSED_FILES.get(path)
    if cached is not None and cached[:2] == (stat.st_mtime_ns, stat.st_size):
        return cached[2]
    try:
        with tokenize.open(source_path) as source_file:
            source = source_file.read()
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
        tree = ast.parse(source, filename=path)
    except (OSError, SyntaxError, tokenize.TokenError, UnicodeError):
        return ()
    statements = _statement_targets(tree)
    significant = {
        token.start[0]
        for token in tokens
        if token.type
        not in (
            tokenize.COMMENT,
            tokenize.ENCODING,
            tokenize.ENDMARKER,
            tokenize.INDENT,
            tokenize.DEDENT,
            tokenize.NEWLINE,
            tokenize.NL,
        )
    }
    intents: list[LintIntent] = []
    for token in tokens:
        if token.type != tokenize.COMMENT or (match := _DIRECTIVE.fullmatch(token.string)) is None:
            continue
        line, column = token.start
        target_start, target_end = _target_for_comment(
            statements, line, column, inline=line in significant
        )
        intents.append(
            LintIntent(
                match.group("kind"),
                path,
                line,
                column,
                target_start,
                target_end,
            )
        )
    result = tuple(intents)
    _PARSED_FILES[path] = (stat.st_mtime_ns, stat.st_size, result)
    return result


def _source_calls(path: str, line: int) -> tuple[ast.Call, ...]:
    """Return calls covering one line, indexed once per source revision."""
    source_path = Path(path)
    try:
        stat = source_path.stat()
    except OSError:
        return ()
    cached = _SOURCE_CALLS.get(path)
    if cached is not None and cached[:2] == (stat.st_mtime_ns, stat.st_size):
        return cached[2].get(line, ())
    try:
        with tokenize.open(source_path) as source_file:
            tree = ast.parse(source_file.read(), filename=path)
    except (OSError, SyntaxError, UnicodeError):
        return ()
    by_line: dict[int, list[ast.Call]] = {}
    for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
        for covered in range(call.lineno, (call.end_lineno or call.lineno) + 1):
            by_line.setdefault(covered, []).append(call)
    frozen = {covered: tuple(calls) for covered, calls in by_line.items()}
    _SOURCE_CALLS[path] = (stat.st_mtime_ns, stat.st_size, frozen)
    return frozen.get(line, ())


def frame_calls_builtin(frame: FrameType, name: str) -> bool:
    """Whether the caller's current expression calls one exact builtin.

    Resolving a plain-name alias through locals/globals is what lets
    ``pairs = zip; pairs(a, b)`` retain the same lint semantics without
    treating every ordinary Answers iteration as a zip.
    """
    path, line, _column = _position(frame)
    expected = getattr(builtins, name)
    for node in _source_calls(path, line):
        if isinstance(node.func, ast.Name):
            value = frame.f_locals.get(
                node.func.id,
                frame.f_globals.get(node.func.id, getattr(builtins, node.func.id, None)),
            )
            if value is expected:
                return True
        elif (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.attr == name
        ):
            owner = frame.f_locals.get(
                node.func.value.id, frame.f_globals.get(node.func.value.id)
            )
            if owner is builtins:
                return True
    return False


def _retain_file_intents(
    space: Any,
    path: str,
    *,
    targets: tuple[tuple[str, int], ...] = (),
    invocation_line: int | None = None,
) -> None:
    """Reflect only directives reached by an event or this lint statement."""
    name, runtime = _space_parts(space)
    selected = (
        intent
        for intent in _parse_intents(path)
        if (
            invocation_line is not None
            and intent.target_start <= invocation_line <= intent.target_end
        )
        or any(
            intent.kind == kind and intent.target_start <= line <= intent.target_end
            for kind, line in targets
        )
    )
    with _LOCK:
        _RUNTIMES[name] = runtime
        recorded = _INTENTS.setdefault(name, set())
        for intent in selected:
            if intent not in recorded:
                recorded.add(intent)
                _retain(runtime, intent.fact(name))


def _retain_file_intents_for_name(
    space: str, path: str, *, targets: tuple[tuple[str, int], ...]
) -> None:
    runtime = _runtime_for_name(space)

    class _Space:
        name = space

        @property
        def runtime(self) -> Any:
            return runtime

    _retain_file_intents(_Space(), path, targets=targets)


def make_event(
    kind: str,
    subject: str,
    *,
    path: str,
    line: int,
    column: int,
    effect: str | None = None,
    atom: Atom | None = None,
) -> LintEvent:
    """Build one pending event with its immutable authority citation."""
    return LintEvent(
        kind,
        subject,
        path,
        line,
        column,
        authority_for(kind),
        effect,
        atom,
    )


def event_at_frame(
    kind: str,
    subject: str,
    frame: FrameType,
    *,
    effect: str | None = None,
    atom: Atom | None = None,
) -> LintEvent:
    """Build a pending event at one known user frame."""
    path, line, column = _position(frame)
    return make_event(
        kind,
        subject,
        path=path,
        line=line,
        column=column,
        effect=effect,
        atom=atom,
    )


def record_event_at_frame(
    space: Any,
    kind: str,
    subject: str,
    frame: FrameType,
    *,
    effect: str | None = None,
    atom: Atom | None = None,
) -> None:
    """Retain a runtime event and every named intent in its source file."""
    event = event_at_frame(kind, subject, frame, effect=effect, atom=atom)
    _retain_file_intents(space, event.path, targets=((event.kind, event.line),))
    _record(space, event)


def record_event_for_name(
    space: str,
    kind: str,
    subject: str,
    frame: FrameType,
) -> None:
    """Answers' variant for a view carrying a space name but no handle."""
    event = event_at_frame(kind, subject, frame)
    _retain_file_intents_for_name(
        space, event.path, targets=((event.kind, event.line),)
    )
    _record_for_name(space, event)


def record_sync_engine_call(
    space: Any, subject: str, frame: FrameType | None = None
) -> None:
    """Record a synchronous driving call made directly by an async body."""
    frame = external_caller() if frame is None else frame
    if frame is None or not (
        frame.f_code.co_flags & (_CO_COROUTINE | _CO_ASYNC_GENERATOR)
    ):
        return
    record_event_at_frame(
        space,
        "sync-engine-call-in-async",
        subject,
        frame,
    )


def prepare_lint(space: Any) -> LintInvocation | None:
    """Record intents at the user's lint call, enabling atom-wide suppression."""
    frame = external_caller()
    if frame is None:
        return None
    path, line, _column = _position(frame)
    _retain_file_intents(space, path, invocation_line=line)
    return LintInvocation(path, line)


def events_for(space: Any) -> tuple[LintEvent, ...]:
    """Return this logical space's retained evidence in source order."""
    name = str(space.name)
    with _LOCK:
        return tuple(
            sorted(
                _all_events(name),
                key=lambda event: (event.path, event.line, event.column, event.kind, event.subject),
            )
        )


def is_suppressed(
    space: Any,
    kind: str,
    *,
    path: str | None,
    line: int | None,
    invocation: LintInvocation | None,
) -> bool:
    """Whether an exact named intent governs the finding or this lint call."""
    name = str(space.name)
    with _LOCK:
        intents = tuple(_INTENTS.get(name, ()))
    return any(
        intent.kind == kind
        and (
            (
                path == intent.path
                and line is not None
                and intent.target_start <= line <= intent.target_end
            )
            or (
                invocation is not None
                and invocation.path == intent.path
                and intent.target_start <= invocation.line <= intent.target_end
            )
        )
        for intent in intents
    )


def clear(space: Any) -> None:
    """Retire every lint event and intent owned by one space life."""
    name, runtime = _space_parts(space)
    with _LOCK:
        for event in _all_events(name):
            _release(runtime, event.fact(name))
        for intent in _INTENTS.get(name, set()):
            _release(runtime, intent.fact(name))
        _OWNER_EVENTS.pop(name, None)
        _TRANSIENT_EVENTS.pop(name, None)
        _INTENTS.pop(name, None)
        _RUNTIMES.pop(name, None)


class _LoopCrossings(ast.NodeVisitor):
    def __init__(self, fn: FunctionType, path: str, first_line: int, atom: Atom) -> None:
        self.fn = fn
        self.path = path
        self.first_line = first_line
        self.atom = atom
        self.bindings = {**vars(builtins), **fn.__globals__}
        for name, cell in zip(fn.__code__.co_freevars, fn.__closure__ or (), strict=True):
            try:
                self.bindings[name] = cell.cell_contents
            except ValueError:
                # A recursive nested function's own closure cell is empty
                # until its decorator returns. It cannot be a registered op.
                continue
        self.depth = 0
        self.events: set[LintEvent] = set()

    def _operation(self, node: ast.expr) -> Any | None:
        if not isinstance(node, ast.Name):
            return None
        return live_registration(self.bindings.get(node.id))

    def _emit(self, node: ast.expr, operation: Any) -> None:
        line = self.first_line + node.lineno - 1
        self.events.add(
            make_event(
                "operation-crossing-in-loop",
                str(operation.name),
                path=self.path,
                line=line,
                column=node.col_offset,
                effect=operation.effect.value,
                atom=self.atom,
            )
        )

    def visit_Call(self, node: ast.Call) -> None:
        if self.depth and (operation := self._operation(node.func)) is not None:
            self._emit(node, operation)
        if (
            isinstance(node.func, ast.Name)
            # policy-inventory-exempt: mechanism-internal; reason=map and filter are the two eager Python builtins that repeatedly invoke their first argument while consuming the iterable; evidence=extensions/python/metta/_lint_events.py:_LoopCrossings.visit_Call
            and node.func.id in {"map", "filter"}
            and node.args
            and (operation := self._operation(node.args[0])) is not None
        ):
            self._emit(node.args[0], operation)
        self.generic_visit(node)

    def _visit_for(self, node: ast.For | ast.AsyncFor) -> None:
        self.visit(node.iter)
        self.visit(node.target)
        self.depth += 1
        for statement in (*node.body, *node.orelse):
            self.visit(statement)
        self.depth -= 1

    def visit_For(self, node: ast.For) -> None:
        self._visit_for(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._visit_for(node)

    def visit_While(self, node: ast.While) -> None:
        self.depth += 1
        self.visit(node.test)
        for statement in (*node.body, *node.orelse):
            self.visit(statement)
        self.depth -= 1

    def _visit_comprehension(
        self,
        node: ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp,
    ) -> None:
        generators = node.generators
        for generator in generators:
            self.visit(generator.iter)
        self.depth += 1
        if isinstance(node, ast.DictComp):
            self.visit(node.key)
            self.visit(node.value)
        else:
            self.visit(node.elt)
        for generator in generators:
            self.visit(generator.target)
            for condition in generator.ifs:
                self.visit(condition)
        self.depth -= 1

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension(node)


def register_definition_crossings(
    space: Any, fn: FunctionType, atom: Atom, metta_name: str
) -> None:
    """Replace one definition source's loop-crossing evidence."""
    try:
        lines, first_line = inspect.getsourcelines(fn)
        source = textwrap.dedent("".join(lines))
        tree = ast.parse(source)
        definition = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == fn.__code__.co_name
        )
        path = inspect.getsourcefile(fn) or inspect.getfile(fn)
    except (OSError, TypeError, SyntaxError, StopIteration):
        return
    if not (path.startswith("<") and path.endswith(">")):
        path = str(Path(path).resolve())
    visitor = _LoopCrossings(fn, path, first_line, atom)
    for statement in definition.body:
        visitor.visit(statement)
    targets = tuple((event.kind, event.line) for event in visitor.events)
    _retain_file_intents(space, path, targets=targets)
    owner = ("define", metta_name, path, first_line)
    _replace_owner(space, owner, visitor.events)


def register_rule_events(space: Any, bundle: Any) -> None:
    """Publish construction evidence only after a Rules bundle lands."""
    pending = frozenset(bundle.lint_events)
    path = bundle.source_path
    if path is not None:
        targets = tuple((event.kind, event.line) for event in pending)
        _retain_file_intents(space, path, targets=targets)
    owner = ("rules", bundle.name, path, bundle.source_line)
    _replace_owner(space, owner, pending)
