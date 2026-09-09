"""Purpose: plan and decode eager conjunctive queries for one named space.
Guarantees:
  - relational solve answers retain variable columns and expose one-answer
    attribute projection [tested:
    test_solve_retires_the_five_relational_let_workarounds,
    test_solve_projects_variables_from_the_winning_pattern; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - conjunctive patterns preserve first-appearance column order [tested
    test_query_surfaces_share_column_order]
  - guards and limits are sent to the engine rather than applied after
    decoding [tested test_query_where_guard_and_limit]
  - non-positive limits fail before an engine call [tested
    test_limit_validation_refuses_nonsense]
  - eager Rows retain normalized query context for why() [tested
    test_query_rows_explain_empty_results]
  - query_count returns one integer from an engine-side aggregate rather than
    crossing answer rows [tested:
    test_query_answers_complete_the_lazy_projection_protocol; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - the same aggregate accepts a per-ask algebra without opening a row cursor
    [tested:
    test_counting_counts_match_bag_duplicates_without_opening_a_row_cursor;
    commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
  - the scalar stays this module's return type whatever the carrier, so the
    tagged-answer protocol is put on it by Space, one layer up, and nothing
    here reaches the algebra satellite [tested:
    test_counting_counts_match_bag_duplicates_without_opening_a_row_cursor,
    imports; commit=2e627a593413191cda3170f2eb716835f7f62543]
  - eager and prepared queries carry a scoped stack bound through the shared
    limited-call selector [tested:
    test_stack_limit_is_carried_to_the_limited_six_seam; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - query guards inherit the same atomic and speculative execution policy as
    term evaluation [tested:
    test_every_public_execution_door_honours_speculative_policy;
    commit=1262dd20ada9d5c799d9bdc4bdf5d2b859ca7a98]
  - a query count hint runs only when its match and guard are repeatable, so
    list() cannot execute a guard write once for the hint and again for rows
    [tested: test_a_guarded_query_length_hint_executes_its_write_once;
    commit=1262dd20ada9d5c799d9bdc4bdf5d2b859ca7a98]
  - a solution-row refusal carries the asked name and the row, so the
    interpreter suggests from the same variables the message lists [tested:
    test_a_solution_row_offers_its_own_variables; commit=6375a7c8f3c035b04bc9d41c8f7f22e56b42fb41]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import builtins as _builtins
import sys
from collections.abc import Iterable, Iterator
from dataclasses import replace
from typing import TYPE_CHECKING, Any, cast

import metta._spaces.cursor as _spaces_cursor_module
import metta._spaces.evaluate as _spaces_evaluate_module
import metta._spaces.execution as _spaces_execution_module
import metta._spaces.intents as _spaces_intents_module
import metta._spaces.results as _spaces_results_module
import metta._spaces.scope as _spaces_scope_module
import metta.doors as _doors
from metta._atoms.designation import _UNSET
from metta._atoms.factories import (
    Atom,
    Expression,
    Grounded,
    Symbol,
    Variable,
    _atom_from_wire,
    _decode,
    _to_atom,
    unify,
)
from metta._atoms.names import resolve_known_name
from metta._atoms.templates import apply as _apply_holes
from metta._atoms.templates import read_targets as _read_targets
from metta._binding.runtime import Runtime
from metta._lazy import lazy


class SolveRows(_spaces_results_module.Rows):
    """Bindings produced by relational solve, with one-answer projection."""

    def __getattr__(self, name: str) -> Any:
        # One resolver rule everywhere: attribute access carries the factories'
        # total underscore-to-hyphen map, so row.async_x reads column async-x
        # exactly as V.async_x wrote it. Bracket access stays exact.
        resolved = resolve_known_name(name, self.columns.__contains__, allow_bang=False)
        if resolved is None:
            msg = f"no solution variable {name!r}; variables are {list(self.columns)}"
            raise AttributeError(msg, name=name, obj=self)
        values = self._column(resolved)
        return values[0] if len(values) == 1 else values

def solve_rows(columns: tuple[str, ...], answers: list[Atom]) -> SolveRows:
    """Shape evaluated answer templates back into caller-named bindings."""
    rows: list[tuple[Atom, ...]]
    if len(columns) == 1:
        rows = [(answer,) for answer in answers]
    else:
        rows = []
        for answer in answers:
            if not isinstance(answer, Expression) or len(answer) != len(columns):
                msg = f"solve answer {answer!r} does not carry {len(columns)} bindings"
                raise TypeError(msg)
            rows.append(tuple(answer))
    return SolveRows(columns, rows)

def query_count(
    rt: Runtime,
    space: str,
    patterns: tuple[Any, ...],
    *,
    where: Any | None,
    limit: int | None,
    timeout: float | None,
    inferences: int | None,
    under: str | None = None,
) -> int:
    """Count one query wholly inside the engine."""
    predicate = "metta_py_query_count"
    if under is not None:
        predicate = "metta_py_query_count_under"
    output = _query_count_call(
        rt,
        space,
        patterns,
        where=where,
        limit=limit,
        timeout=timeout,
        inferences=inferences,
        predicate=predicate,
        extra=[] if under is None else [under],
    )
    return int(output)

def query_count_if_repeatable(
    rt: Runtime,
    space: str,
    patterns: tuple[Any, ...],
    *,
    where: Any | None,
    limit: int | None,
    timeout: float | None,
    inferences: int | None,
) -> int | None:
    """Count only when opening the row cursor cannot repeat an effect."""
    output = _query_count_call(
        rt,
        space,
        patterns,
        where=where,
        limit=limit,
        timeout=timeout,
        inferences=inferences,
        predicate="metta_py_query_count_if_repeatable",
        extra=[],
    )
    return int(output[0]) if output else None

def _query_count_call(
    rt: Runtime,
    space: str,
    patterns: tuple[Any, ...],
    *,
    where: Any | None,
    limit: int | None,
    timeout: float | None,
    inferences: int | None,
    predicate: str,
    extra: list[Any],
) -> Any:
    """Encode the shared query-count wire once for both count policies."""
    _spaces_cursor_module._validate_limit(limit)
    atoms = [_to_atom(pattern) for pattern in patterns]
    guard = _spaces_cursor_module.guard_atom(where)
    columns = _spaces_cursor_module._column_names(atoms)
    inputs = [
        space,
        [atom.to_wire() for atom in atoms],
        [] if guard is None else guard.to_wire(),
        columns,
        limit or 0,
        *extra,
    ]
    return _execute_query(rt, predicate, inputs, _spaces_scope_module._limits(timeout, inferences))

def _execute_query(
    rt: Runtime,
    predicate: str,
    inputs: list[Any],
    limits: tuple[float, int, int] | None,
) -> Any:
    # Imported at the call boundary because _space_execution owns policy
    # handling and imports the shared query objects during module initialization.
    from metta._spaces.execution import _controlled_run  # noqa: PLC0415

    return _controlled_run(rt, predicate, inputs, limits)

class Prepared:
    """A prepared query: pattern wires and columns built once, solved many
    times, optionally with per-call facts. It follows clingo's progression from
    assumptions per solve, to inputs per session, to added rules, and includes
    the capability clingo lacks: removing rules, since this engine erases
    clauses whole.

        route = m.prepare(S.path(V.a, V.b))
        route.solve()
        route.solve(given=[S.edge(S.a, S.b)])   # facts for this call only
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    __slots__ = ("_guard", "_patterns", "_space", "_where", "_wires", "columns")

    def __init__(self, space: _root.Space, patterns: list[Atom], where: Atom | None) -> None:
        self._space = space
        self._patterns = patterns
        self._where = where
        self._wires = [p.to_wire() for p in patterns]
        self._guard = None if where is None else where.to_wire()
        self.columns = tuple(_spaces_cursor_module._column_names(patterns))

    def solve(
        self,
        given: list | None = None,
        limit: int | None = None,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> _root.Rows:
        """Answers now, with `given` facts present for this call alone.
        `timeout` and `inferences` bound this solve exactly as they bound
        MeTTa.match().
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        _spaces_cursor_module._validate_limit(limit)
        if not given:
            return self._run(limit, timeout, inferences)
        with self._space.assuming(*given):
            return self._run(limit, timeout, inferences)

    def _run(self, limit: int | None, timeout: float | None, inferences: int | None) -> _root.Rows:
        rt = self._space.runtime
        space = self._space.name
        names = list(self.columns)
        if self._guard is not None:
            pred = "metta_py_query_guarded_all"
            ins = [space, self._wires, self._guard, names, limit or 0]
        elif limit is not None:
            pred, ins = "metta_py_query_limit_all", [space, self._wires, names, limit]
        else:
            pred, ins = "metta_py_query_all", [space, self._wires, names]
        from metta._spaces.execution import _controlled_run  # noqa: PLC0415

        answered = _controlled_run(
            rt, pred, ins, _spaces_scope_module._limits(timeout, inferences)
        )
        decoded = [tuple(_atom_from_wire(v) for v in r) for r in answered]
        return _spaces_results_module.Rows(self.columns, decoded)

    def explain(self) -> str:
        """The query's plan, reflected rather than run: polars'
        LazyFrame.explain and SQL's EXPLAIN, from decisions the engine has
        already made. For a Python-backed space, each pattern's line says
        whether its candidates push down exact (the provider's answers
        are trusted as instantiations, a bound may reach it) or inexact
        (candidates re-unify in the engine), and which rule decided:
        a declared (handles ...) entry, the provider's own pushdown
        method, or silence. A conjunction line names what a planning
        provider claimed whole and what the engine joins. Stored spaces
        answer the one true line: engine unification. No row is pulled
        and no provider match is called; the provider's plan hook is
        consulted exactly as a real query would consult it, since the
        claim is the provider's to make.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return _spaces_cursor_module._explain_text(self._space.runtime, self._space.name, self._patterns, self._where)

    def __repr__(self) -> str:
        shown = ", ".join(str(p) for p in self._patterns)
        return f"<prepared {shown} -> {', '.join(self.columns)}>"

@_doors.door(
    kind=_doors.Kind.query,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.nondet,
    tiers=(_doors.Tier.sync, _doors.Tier.async_, _doors.Tier.module, _doors.Tier.context),
    evidence=('extensions/python/tests/ch03_atoms_and_expressions/test_identity_wire.py::test_store_and_match_preserve_python_object_identity', 'extensions/python/tests/ch04_spaces_and_matching/test_algebra_lifecycle.py::test_drop_retires_algebra_before_redeclaration', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_a_recorded_session_replays_verbatim'),
    alias='match',
)
def match(
    space: _root.Space,
    *patterns: Any,
    where: Any | None = None,
    limit: int | None = None,
    timeout: float | None = None,
    inferences: int | None = None,
    under: Any = _UNSET,
    into: _builtins.type | None = None,
    **values: Any,
) -> Any:
    """Lazily match patterns against this space as one conjunction.

    Variables shared between patterns join, the engine's own match/4
    doing the joining. Columns are the variable names in first
    appearance order. `where` is a guard term over the same variables,
    evaluated per join and required true, so restrictions a pattern
    cannot spell (an inequality) compose onto the match:

        m.match(S.person(V.name, V.age), where=V.age.ge(18))

    `limit` bounds the answers, the engine stopping at the count
    rather than trimming afterwards. `timeout` (seconds) and
    `inferences` (engine steps) bound the whole call, raising
    TimeLimitError or InferenceLimitError when hit, for joins whose
    size is not known in advance.

    The returned Answers view pulls only what Python observes. ``bool``
    pulls one row, exact-one operations pull at most two, and slicing
    retains an Answers view. ``len`` uses an engine-side aggregate when
    no row has yet been pulled.

    ``under=`` interprets the same ask through an annotation algebra.
    ``under=counting`` answers one ``TaggedAnswer`` whose annotation is
    the engine-computed count, including duplicate derivations without
    crossing their rows into Python. Ordered carriers sort in their
    declared direction before slicing, so
    ``m.match(q, under=ranked)[:3]`` is top-k and
    ``under=tropical`` puts the cheapest annotation first. Other carriers
    answer ``TaggedAnswer`` values with ``annotation``, ``why()`` and
    ``under(other)``; the latter two reuse the retained derivation rather
    than querying the space again. ``with metta.under(carrier)`` supplies
    the carrier when this call has no explicit ``under=``.

    `into=Rows` explicitly chooses the eager Rows face. Other `into=`
    values shape each row into a dataclass, NamedTuple, or
    TypedDict matched by field name, sqlite3's row_factory reading:
    `m.match(S.edge(V.a, V.b), into=Edge)` answers `list[Edge]`,
    and Rows stays the default so nothing is lost. A one-variable query
    whose column holds complete constructor expressions rebuilds those
    expressions instead: `m.match(V.edge, into=Edge)`.

        m.match(S.Edge(V.x, V.y), S.Edge(V.y, V.z))

    A text pattern may carry HOLES, as run()'s source may:
    `m.match(t"(person {name} $age)")` matches the value itself, so a name
    holding a space stays one String atom rather than reading as two
    symbols. Keyword values apply across every pattern of the call.
    """
    _spaces_intents_module.record_sync_engine_call(space, "match", sys._getframe(1))
    patterns, holes = _read_targets(
        patterns, values, called="match", reserved=_spaces_execution_module._MATCH_KEYWORDS
    )
    if holes:
        # A cursor opens through metta_py_cursor_open, which carries no
        # bindings, so a pattern's holes go into the pattern here. The
        # values are already atoms, which is what keeps this agreeing with
        # the engine path: _to_atom PARSES a str where encode makes it a
        # String, so an unencoded value would mean two different things at
        # the two doors.
        patterns = tuple(
            _apply_holes(_to_atom(pattern), holes) for pattern in patterns
        )
    _spaces_cursor_module._validate_limit(limit)
    carrier = _spaces_scope_module.selected(under)
    if carrier is not None:
        return _match_under(
            space, patterns,
            where=where,
            limit=limit,
            timeout=timeout,
            inferences=inferences,
            under=carrier,
            into=into,
        )
    cursor = _spaces_cursor_module.Cursor(space, patterns, where, timeout, inferences, limit=limit)

    def source() -> Iterator[_spaces_results._AnswerItem]:
        pulled = 0
        try:
            while limit is None or pulled < limit:
                try:
                    row = next(cursor)
                except StopIteration:
                    return
                pulled += 1
                yield _spaces_results_module._AnswerItem(row, row)
        finally:
            cursor.close()

    query_context = _spaces_results_module._QueryContext(
        space._space,
        tuple(_to_atom(pattern) for pattern in patterns),
        _spaces_cursor_module.guard_atom(where),
    )

    def count_answers(*, values_wanted: bool) -> int | None:
        if values_wanted:
            return None
        return query_count_if_repeatable(
            space._rt,
            space._space,
            patterns,
            where=where,
            limit=limit,
            timeout=timeout,
            inferences=inferences,
        )

    answers: _root.Answers[Any] = _spaces_results_module.Answers(
        source(),
        columns=cursor.columns,
        space=space._space,
        target=patterns,
        query=query_context,
        # A bare len asks the engine to admit a repeatable second query.
        # list has already asked for an iterator, so its length hint
        # materializes the one cursor it is about to consume.
        count=count_answers,
    )
    if into is None:
        return answers
    eager = _spaces_results_module.Rows(
        cursor.columns,
        answers,
        _query=query_context,
    )
    if into is _spaces_results_module.Rows:
        return eager
    return _spaces_results_module.rows_into(eager, into)

def _match_under(
    space: _root.Space,
    patterns: tuple[Any, ...],
    *,
    where: Any | None,
    limit: int | None,
    timeout: float | None,
    inferences: int | None,
    under: Any,
    into: _builtins.type | None,
) -> Any:
    """Build one lazy carrier view over tagged or ordinary engine rows."""
    algebra_api = lazy('metta.algebra')
    declaration = algebra_api.resolve(space, under)
    context = _spaces_scope_module.EvaluationContext(declaration.name, limit, declaration.order)
    if declaration.name == "counting":
        return _match_counting_under(
            space, patterns,
            where=where,
            limit=limit,
            timeout=timeout,
            inferences=inferences,
            algebra_api=algebra_api,
            declaration=declaration,
            into=into,
        )

    atoms = tuple(_to_atom(pattern) for pattern in patterns)
    columns = tuple(_spaces_cursor_module._column_names(atoms))
    query_context = _spaces_results_module._QueryContext(
        space._space,
        atoms,
        _spaces_cursor_module.guard_atom(where),
    )
    tagged_route: bool | None = None

    def has_tagged_program() -> bool:
        nonlocal tagged_route
        if tagged_route is None:
            tagged_route = len(patterns) == 1 and algebra_api.has_tagged_program(
                space, patterns[0]
            )
        return tagged_route

    def tagged_source() -> Iterator[_spaces_results._AnswerItem]:
        if len(patterns) != 1:
            msg = "a tagged algebra query takes one proposition pattern"
            raise algebra_api.AlgebraEvaluationError(msg)
        evaluation = algebra_api.evaluate(
            space,
            patterns[0],
            algebra=declaration,
            context=context,
            timeout=timeout,
            inferences=inferences,
        )
        row_cls = _spaces_results_module._row_class(columns)
        # Built ONCE: the guard term does not depend on the answer, only
        # its substitution does.
        guard_template = None if where is None else _spaces_cursor_module.guard_atom(where)
        yielded = 0
        for answer in evaluation.answers:
            bindings = unify(atoms[0], answer.value)
            if bindings is None:
                continue
            if guard_template is not None:
                guard, using = _spaces_evaluate_module._prepared_ask(space, guard_template.subs(bindings), None)
                guard_answers = _spaces_execution_module.evaluate(
                    space._rt, space._space, guard, timeout, inferences,
                    using=using, context=context,
                )
                if not any(
                    isinstance(value, Grounded) and _decode(value) is True
                    for value in guard_answers
                ):
                    continue
            if limit is not None and yielded >= limit:
                return
            row = row_cls(bindings[Variable(name)] for name in columns)
            yielded += 1
            yield _spaces_results_module._AnswerItem(answer, row)

    def engine_source(
        *, evaluation_context: _spaces_scope.EvaluationContext = context
    ) -> Iterator[_spaces_results._AnswerItem]:
        cursor = _spaces_cursor_module.Cursor(
            space,
            patterns,
            where,
            timeout,
            inferences,
            context=evaluation_context,
        )
        try:
            for row in cursor:
                answer = algebra_api.captured_answer(
                    space,
                    row,
                    cursor.annotation,
                    declaration,
                    context=evaluation_context,
                )
                yield _spaces_results_module._AnswerItem(answer, row)
        finally:
            cursor.close()

    def bounded_engine_source(
        stop: int, shared: Iterable[_spaces_results._AnswerItem]
    ) -> Iterable[_spaces_results._AnswerItem]:
        if (
            len(patterns) != 1
            or where is not None
            or declaration.order is None
            or limit == 0
        ):
            return shared
        bounded_limit = stop if limit is None else min(stop, limit)

        def bounded() -> Iterator[_spaces_results._AnswerItem]:
            promises = space._rt.once(
                "seam:foreign_space(Space), metta_source(Space, Kind)",
                Space=space._space,
            )
            if (
                not promises
                or str(promises["Kind"]) == "linear"
                or has_tagged_program()
            ):
                yield from shared
                return
            yield from engine_source(
                evaluation_context=replace(context, limit=bounded_limit),
            )

        return bounded()

    def source() -> Iterator[_spaces_results._AnswerItem]:
        if has_tagged_program():
            yield from tagged_source()
        else:
            yield from engine_source()

    answers: _root.Answers[Any] = _spaces_results_module.Answers(
        source(),
        columns=columns,
        space=space._space,
        target=patterns,
        query=query_context,
        bound_source=bounded_engine_source,
    )
    if into is None:
        return answers
    eager = _spaces_results_module.Rows(columns, answers.rows, _query=query_context)
    if into is _spaces_results_module.Rows:
        return eager
    return _spaces_results_module.rows_into(eager, into)

def _match_counting_under(
    space: _root.Space,
    patterns: tuple[Any, ...],
    *,
    where: Any | None,
    limit: int | None,
    timeout: float | None,
    inferences: int | None,
    algebra_api: Any,
    declaration: Any,
    into: _builtins.type | None,
) -> _root.Answers[Any]:
    """Build the protocol-shaped engine-side counting view."""
    if into is not None:
        msg = "under=counting answers one aggregate and cannot use into="
        raise TypeError(msg)

    def counted() -> Iterator[Any]:
        if len(patterns) == 1 and algebra_api.has_tagged_program(
            space, patterns[0]
        ):
            if where is not None:
                msg = (
                    "tagged under=counting does not accept where=; "
                    "put the restriction in the tagged rule"
                )
                raise algebra_api.AlgebraEvaluationError(msg)
            yield algebra_api.count_tagged(
                space,
                patterns[0],
                limit=limit,
                timeout=timeout,
                inferences=inferences,
            )
            return
        yield algebra_api.counting_answer(
            space,
            query_count(
                space._rt,
                space._space,
                patterns,
                where=where,
                limit=limit,
                timeout=timeout,
                inferences=inferences,
                under=declaration.name,
            ),
            declaration.name,
        )

    return _spaces_results_module.Answers(
        counted(),
        space=space._space,
        target=patterns,
    )

@_doors.door(
    kind=_doors.Kind.query,
    answers=_doors.AnswersAs.stream,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.nondet,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_wide_query_projection_is_identical_through_every_answer_door', 'extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_nonpositive_limits_are_refused_by_match_stream_and_prepared'),
    refuses=(_doors.Refusal(_doors.RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:stream]'),),
)
def stream(
    space: _root.Space,
    *patterns: Any,
    where: Any | None = None,
    limit: int | None = None,
    timeout: float | None = None,
    inferences: int | None = None,
    under: Any = _UNSET,
) -> _spaces_cursor.Cursor:
    """match(), pulled: the same conjunction and guard, answered one
    row at a time through a cursor the engine holds open.

        with m.stream(S.edge(V.a, V.b), S.edge(V.b, V.c)) as rows:
            for row in rows:
                if wanted(row):
                    break            # nothing further is even joined

    The join's state lives inside an SWI engine between pulls, each
    pull is one ordinary call, and unrelated calls interleave freely,
    so a huge join costs one row of work per row actually taken where
    match() computes and decodes every answer up front. `timeout`
    bounds each pull's wall time; `inferences` is one budget for the
    cursor's whole engine work, spent across pulls, and the cursor
    stops on the answer that passes it. Because the budget counts the
    cursor's own engine, it is not the number ``stats()`` reports for
    the same work: ``stats()`` reads the calling thread's counters,
    which see the pull loop rather than the engine. The cursor
    enumerates under the engine's logical update view: writes made
    after the first pull are not seen by this cursor.

    `limit` and `under` mean what they mean on match(), because this is
    match() and the cursor underneath already carried both: a tagging
    algebra (ranked, tropical, prov) answers one TaggedAnswer per pull,
    the same value match() answers. `under='counting'` is refused by
    name, because a counting fold is ONE aggregate over the whole answer
    set and a cursor exists not to have one.

    What this method does NOT take is match()'s `into=`, the same kind of
    difference: `into` builds a container out of every row.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    carrier = _spaces_scope_module.selected(under)
    if carrier is None:
        return _spaces_cursor_module.Cursor(space, patterns, where, timeout, inferences, limit=limit)
    algebra_api = lazy('metta.algebra')
    declaration = algebra_api.resolve(space, carrier)
    if declaration.name == "counting":
        # A counting fold is ONE aggregate over the whole answer set,
        # which is the thing a cursor exists not to have. Answering
        # per-row would make under= mean a fold through match() and
        # something else here.
        msg = (
            "under='counting' folds every answer into one aggregate, so "
            "it has nothing to stream; use match(under='counting'), "
            "which answers a TaggedAnswer carrying that count, or "
            "stream under a tagging algebra "
            "(ranked, tropical, prov) for one tagged answer per pull"
        )
        raise TypeError(msg)
    context = _spaces_scope_module.EvaluationContext(declaration.name, limit, declaration.order)
    return _spaces_cursor_module.Cursor(
        space,
        patterns,
        where,
        timeout,
        inferences,
        context=context,
        capture=lambda row, annotation: algebra_api.captured_answer(
            space, row, annotation, declaration, context=context
        ),
    )

@_doors.door(
    kind=_doors.Kind.evaluation,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.nondet,
    tiers=(_doors.Tier.sync, _doors.Tier.async_, _doors.Tier.module, _doors.Tier.context),
    evidence=('extensions/python/tests/ch11_python_as_a_notation/test_library_fixes.py::test_solve_projects_variables_from_the_winning_pattern', 'extensions/python/tests/ch11_python_as_a_notation/test_r5_unbuilt_doors.py::test_set_is_the_unique_image_of_solve_answers', 'extensions/python/tests/ch11_python_as_a_notation/test_r5_unbuilt_doors.py::test_solve_refuses_an_anonymous_only_subject'),
    alias='solve',
    refuses=(_doors.Refusal(_doors.RefusalKind.value, 'extensions/python/tests/repository/test_door_refusals.py::test_door_value_refusals[space:solve]'),),
)
def solve(space: _root.Space, pattern: Any, subject: Any) -> Any:
    """Run relational ``let`` and return bindings keyed by its variables.

    ``solve(4, V.x - 1).x`` places the known value on let's pattern side,
    lets the arithmetic relation solve backwards, and projects ``x``.
    The answer template is derived from the pattern's variables followed
    by any new subject variables, so either relational direction can
    introduce the bindings and the third hand-written ``let`` argument
    disappears.
    """
    pattern_atom = _to_atom(pattern)
    subject_atom = _to_atom(subject)
    columns = tuple(_spaces_cursor_module._column_names([pattern_atom, subject_atom]))
    if not columns:
        msg = "solve needs at least one variable in its pattern or subject"
        raise ValueError(msg)
    template: Atom = (
        Variable(columns[0])
        if len(columns) == 1
        else Expression([Variable(name) for name in columns])
    )
    answers = space.eval(
        Expression([Symbol("let"), pattern_atom, subject_atom, template])
    )
    return solve_rows(columns, cast(list[Atom], answers))

@_doors.door(
    kind=_doors.Kind.query,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.readOnlyLookup,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_nonpositive_limits_are_refused_by_match_stream_and_prepared', 'extensions/python/tests/ch11_python_as_a_notation/test_adoptions.py::test_prepared_query_with_given', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_limits_on_query_eval_value_and_prepared'),
)
def prepare(space: _root.Space, *patterns: Any, where: Any | None = None) -> Prepared:
    """A query whose shape is fixed and whose facts are not: the wire
    form and columns build once, and each solve() may bring per-call
    facts (given=) that leave nothing behind.

        route = m.prepare(S.path(V.a, V.b), where=V.a != ...)
        route.solve()
        route.solve(given=[S.edge(S.x, S.y)])
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return Prepared(
        space,
        [_to_atom(p) for p in patterns],
        _spaces_cursor_module.guard_atom(where),
    )

# Resolve annotations after definitions so peer imports can finish.
if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
import metta._spaces.cursor as _spaces_cursor  # noqa: E402 -- deferred annotation bindings
import metta._spaces.results as _spaces_results  # noqa: E402 -- deferred annotation bindings
import metta._spaces.scope as _spaces_scope  # noqa: E402 -- deferred annotation bindings
