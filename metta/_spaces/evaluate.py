"""Purpose: select consumption, image, delivery, and refusal policies for eval.

Assumes: Space has prepared each target and captured its bindings.
Guarantees: ordinary eager evaluation keeps its existing kernel; explicit lazy
  consumption preserves order, multiplicity, undefined truth, and annotations
  [tested: test_evaluation_options_preserve_the_eager_kernel,
  test_evaluation_options_compose_without_losing_answers; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
  First selects a retained answer consistently across bounds while ordinary
  eager execution keeps its effects [tested:
  test_first_selects_the_first_retained_answer,
  test_evaluation_selection_preserves_eager_effects_and_bounded_demand;
  commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
Owns resources: each lazy selection owns its underlying Answers. Exhaustion,
  an error, or explicit close releases it; abandonment releases references so
  Answers' existing finalizer defers engine cleanup [tested:
  test_evaluation_selections_close_on_every_exit; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
  Cursor conversion uses the ordinary value converter and preserves both a
  conversion failure and a simultaneous cleanup failure [tested:
  test_cursor_conversion_preserves_its_failure_and_cleanup_failure;
  commit=WORKTREE].
  Stream selections enrol their cleanup with the active scope so its native
  enumerator and Python cursor retire together [tested:
  test_a_stream_selection_closes_with_its_scope; commit=WORKTREE].
"""

from __future__ import annotations

import sys
from collections import abc as _abc
from collections.abc import Iterable, Iterator
from itertools import islice
from typing import TYPE_CHECKING, Any, Self, overload

import metta._spaces.cursor as _spaces_cursor_module
import metta._spaces.execution as _spaces_execution_module
import metta._spaces.handle as _spaces_handle_module
import metta._spaces.intents as _spaces_intents_module
import metta._spaces.lifetime as _spaces_lifetime_module
import metta._spaces.results as _spaces_results_module
import metta._spaces.scope as _spaces_scope_module
import metta._spaces.source as _spaces_source_module
import metta.doors as _doors
from metta._atoms.designation import _UNSET
from metta._atoms.factories import (
    Atom,
    Expression,
    Grounded,
    Handle,
    Symbol,
    Undefined,
    Variable,
    _decode,
    _to_atom,
    ground,
    unify,
)
from metta._atoms.templates import read_targets as _read_targets
from metta._catalog.build import build
from metta._catalog.project import auto_image, project
from metta._errors.errors import EngineError, refuse
from metta._lazy import lazy
from metta.doors import AnswerForm, EvaluationAnswer
from metta.vocabularies import ArgumentDelivery, Determinism, ImageMode, OnError, RefusalKind


def _mode(enum: Any, value: Any, name: str) -> Any:
    try:
        return enum(value)
    except (TypeError, ValueError):
        raise refuse(RefusalKind.value, f"eval {name} is one of {', '.join(enum)}, got {value!r}") from None

def _image(value: Any, mode: ImageMode | None, space: Any) -> Any:
    if mode is None or not isinstance(value, Grounded) or isinstance(value, Handle):
        return value
    held = value.value
    selected = ImageMode(auto_image(held)) if mode is ImageMode.auto else mode
    if selected is ImageMode.opaque:
        return ground(held)
    projected = project(held)
    missing = tuple(declaration for declaration in projected.declarations if declaration not in space)
    if missing:
        space.transaction(lambda: space.add(*missing))
    return projected.atom

def _target_image(target: Any, mode: ImageMode | None, space: Any) -> Any:
    if mode is None:
        return target
    atom = space.parse(target) if isinstance(target, str) else target
    if not isinstance(atom, Atom):
        atom = ground(atom)
    return atom.map(lambda item: _image(item, mode, space))

def _value(value: Any, delivery: ArgumentDelivery, image: ImageMode | None, space: Any) -> Any:
    value = _image(value, image, space)
    return _decode(value) if delivery is ArgumentDelivery.values and isinstance(value, Grounded) else value

def _cardinality(count: int, determinism: Determinism) -> None:
    if determinism is Determinism.det and count != 1:
        raise refuse(RefusalKind.assertion, f"eval determinism=det expected exactly one answer, got {count}", operation="eval")
    if determinism is Determinism.semidet and count > 1:
        raise refuse(RefusalKind.assertion, f"eval determinism=semidet expected at most one answer, got {count}", operation="eval")

def _scalar_atom(values: list[Any], shape: EvaluationAnswer) -> Any:
    if len(values) != 1:
        msg = f"eval answer={shape} expected exactly one answer, got {len(values)}"
        raise EngineError(msg)
    if isinstance(values[0], Undefined):
        msg = "a scalar evaluation requires a definite answer"
        raise EngineError(msg)
    return values[0]

class _Selection:
    """A bounded answer source that preserves each answer's caller bindings."""

    __slots__ = ("_closed", "_count", "_delivery", "_determinism", "_errors", "_image", "_iterator", "_limit", "_pending", "_prepared", "_raw", "_space")

    def __init__(self, raw: _root.Answers[Any], space: Any, *, delivery: ArgumentDelivery,
                 image: ImageMode | None, errors: OnError, determinism: Determinism,
                 limit: int | None) -> None:
        self._raw: _root.Answers[Any] | None = raw
        self._iterator: Iterator[Any] | None = raw._source
        self._space = space
        self._delivery = delivery
        self._image = image
        self._errors = errors
        self._determinism = determinism
        self._limit = limit
        self._count = 0
        self._prepared = False
        self._pending: Iterator[_spaces_results_module._AnswerItem] | None = None
        self._closed = False

    def __iter__(self) -> _Selection:
        return self

    def _next_item(self) -> _spaces_results_module._AnswerItem:
        if self._iterator is None:
            raise StopIteration
        while True:
            item = next(self._iterator)
            if not isinstance(item, _spaces_results_module._AnswerItem):
                item = _spaces_results_module._AnswerItem(item, None)
            error = _spaces_results_module.error_answer(item.value, space=self._space.name)
            if error is not None:
                if self._errors is OnError.abort:
                    raise error
                if self._errors is OnError.empty:
                    continue
            return _spaces_results_module._AnswerItem(_value(item.value, self._delivery, self._image, self._space), item.row)

    def __next__(self) -> _spaces_results_module._AnswerItem:
        if self._closed:
            raise StopIteration
        try:
            if not self._prepared:
                self._prepared = True
                if self._determinism is not Determinism.nondet:
                    pair = []
                    for _ in range(2):
                        try:
                            pair.append(self._next_item())
                        except StopIteration:
                            break
                    _cardinality(len(pair), self._determinism)
                    self._pending = iter(pair)
            if self._limit is not None and self._count >= self._limit:
                self.close()
                raise StopIteration  # noqa: TRY301 -- the common exit below releases ownership
            item = next(self._pending) if self._pending is not None else self._next_item()
            self._count += 1
            if self._limit is not None and self._count == self._limit:
                self.close()
        except StopIteration:
            self.close()
            raise
        except BaseException as error:
            try:
                self.close()
            except BaseException as cleanup:  # noqa: BLE001 -- retain both interruption and cleanup failures
                msg = "evaluation and cursor cleanup failed"
                raise BaseExceptionGroup(msg, [error, cleanup]) from None
            raise
        return item

    def close(self) -> None:
        """Release the underlying cursor; a failed release remains retryable."""
        if self._closed:
            return
        if self._raw is not None:
            self._raw.close()
        self._closed = True
        self._iterator = None
        self._raw = None
        self._pending = None

    def close_deferred(self) -> None:
        """Release ownership through Answers' existing deferred finalizer."""
        self._closed = True
        self._iterator = None
        self._raw = None
        self._pending = None

class _Stream(Iterator[Any]):
    """A closable single-pass projection of one selection."""

    __slots__ = ("_conversion", "_source")

    def __init__(self, source: _Selection) -> None:
        self._source = source
        self._conversion: tuple[Any, Any] | None = None
        _spaces_lifetime_module.own("cleanup", self.close)

    def __next__(self) -> Any:
        value = next(self._source).value
        if self._conversion is None:
            return value
        annotation, space = self._conversion
        try:
            return build(value, annotation, space=space)
        except BaseException as error:
            self.__exit__(type(error), error, None)
            raise

    def into(self, annotation: Any, *, space: Any = None) -> Self:
        """Rebuild subsequent answers through the ordinary value converter."""
        self._conversion = annotation, space
        return self

    def close(self) -> None:
        """Release the held answer cursor."""
        self._source.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, _kind: object, error: BaseException | None, _traceback: object) -> None:
        try:
            self.close()
        except BaseException as cleanup:
            if error is not None:
                msg = "evaluation scope and cursor cleanup failed"
                raise BaseExceptionGroup(msg, [error, cleanup]) from None
            raise

    def __del__(self) -> None:
        self._source.close_deferred()

def evaluate(
    space: Any, targets: tuple[Any, ...], *, answer: EvaluationAnswer | str,
    delivery: ArgumentDelivery | str, limit: int | None,
    image: ImageMode | str | None, on_error: OnError | str,
    determinism: Determinism | str, timeout: float | None,
    inferences: int | None, under: Any = _UNSET,
    theory: Any | None = None, interpreter: Any | None = None,
) -> Any:
    """Apply one policy product independently to each prepared target."""
    shape = _mode(EvaluationAnswer, answer, "answer")
    delivered = _mode(ArgumentDelivery, delivery, "delivery")
    errors = _mode(OnError, on_error, "on_error")
    promise = _mode(Determinism, determinism, "determinism")
    image_mode = None if image is None else _mode(ImageMode, image, "image")
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 0):
        raise refuse(RefusalKind.value, "eval limit is a nonnegative integer or None")
    if shape is EvaluationAnswer.atom and delivered is not ArgumentDelivery.atoms:
        raise refuse(RefusalKind.value, "eval answer=atom requires delivery=atoms")
    options = {"timeout": timeout, "inferences": inferences, "under": under,
               "theory": theory, "interpreter": interpreter}

    def one(target: Any) -> Any:
        target = _target_image(target, image_mode, space)
        # The eager cardinality spellings retain the existing one/first
        # behavior, including effects after the selected first answer.
        eager = shape.form is AnswerForm.materialised and limit is None
        if eager:
            if theory is not None or interpreter is not None or _spaces_scope_module.selected(under) is not None:
                with space.answers(target, **options) as answers:
                    values = list(answers)
            else:
                values = _spaces_execution_module.evaluate(space._rt, space._space, target, timeout, inferences)
            if errors is OnError.empty:
                values = [value for value in values if _spaces_results_module.error_answer(value, space=space.name) is None]
            if shape is EvaluationAnswer.first and promise is Determinism.nondet:
                values = values[:1]
            if errors is OnError.abort:
                _spaces_results_module.raise_error_answers(values, space=space.name, target=target)
            _cardinality(len(values), promise)
            if shape is EvaluationAnswer.all:
                return [_value(value, delivered, image_mode, space) for value in values]
            if shape is EvaluationAnswer.first:
                values = values[:1]
                if not values:
                    return None
            if delivered is ArgumentDelivery.values:
                return _spaces_execution_module.value_one(target, [_image(value, image_mode, space) for value in values])
            return _value(_scalar_atom(values, shape), delivered, image_mode, space)
        if (shape is EvaluationAnswer.count and limit is None and errors is OnError.keep
                and promise is Determinism.nondet and theory is interpreter is None
                and _spaces_scope_module.selected(under) is None):
            return _spaces_execution_module.evaluate_count(space._rt, space._space, target, timeout, inferences)
        raw = space.answers(target, **options)
        source = _Selection(raw, space, delivery=delivered, image=image_mode,
                            errors=errors, determinism=promise, limit=limit)
        if shape is EvaluationAnswer.stream:
            return _Stream(source)
        if shape.form is AnswerForm.aggregate:
            with _Stream(source) as stream:
                if shape is EvaluationAnswer.count:
                    return sum(1 for _ in stream)
                if shape is EvaluationAnswer.exists:
                    try:
                        next(stream)
                    except StopIteration:
                        return False
                    return True
                for _ in stream:
                    pass
                return None
        view: _root.Answers[Any] = _spaces_results_module.Answers(source, columns=raw.columns, space=space.name, target=target, query=raw._query)
        if shape is EvaluationAnswer.answers:
            return view
        with view:
            if shape is EvaluationAnswer.rows:
                if view.columns:
                    return _spaces_results_module.Rows(view.columns, view.rows)
                return _spaces_results_module.Rows(("value",), ((value,) for value in view))
            values = (list(islice(view, 1))
                      if shape is EvaluationAnswer.first and promise is Determinism.nondet
                      else list(view))
            if shape is EvaluationAnswer.all:
                return values
            if shape is EvaluationAnswer.first and not values:
                return None
            chosen = values[:1] if shape is EvaluationAnswer.first else values
            if delivered is ArgumentDelivery.values:
                return _spaces_execution_module.value_one(target, chosen)
            return _scalar_atom(chosen, shape)

    results = []
    try:
        for target in targets:
            results.append(one(target))  # noqa: PERF401 -- retain acquired sources for cleanup if the batch fails
    except BaseException as error:
        failures = []
        for result in results:
            if isinstance(result, (_spaces_results_module.Answers, _Stream)):
                try:
                    result.close()
                except BaseException as cleanup:  # noqa: BLE001 -- attempt all closes even after an interruption
                    failures.append(cleanup)
        if failures:
            msg = "evaluation batch and cursor cleanup failed"
            raise BaseExceptionGroup(msg, [error, *failures]) from None
        raise
    return results[0] if len(results) == 1 else results

@overload
def eval(  # noqa: A001 -- the marked body preserves its public door name
    space: _root.Space, target: Any, /, *more: Any,
    timeout: float | None = None, inferences: int | None = None,
    under: Any = _UNSET, theory: Any | None = None,
    interpreter: Any | None = None, answer: EvaluationAnswer | str = "all",
    delivery: ArgumentDelivery | str, limit: int | None = None,
    image: ImageMode | str | None = None, on_error: OnError | str = "keep",
    determinism: Determinism | str = "nondet", **values: Any,
) -> Any: ...

@overload
def eval(  # noqa: A001 -- the marked body preserves its public door name
    space: _root.Space,
    target: Any,
    /,
    *more: Any,
    timeout: float | None=None,
    inferences: int | None=None,
    under: Any=_UNSET,
    theory: Any | None=None,
    interpreter: Any | None=None,
    answer: EvaluationAnswer | str,
    delivery: ArgumentDelivery | str = "atoms",
    limit: int | None = None,
    image: ImageMode | str | None = None,
    on_error: OnError | str = "keep",
    determinism: Determinism | str = "nondet",
    **values: Any,
) -> Any: ...

@overload
def eval(  # noqa: A001 -- the marked body preserves its public door name
    space: _root.Space,
    target: Any,
    /,
    *,
    timeout: float | None=...,
    inferences: int | None=...,
    under: Any=...,
    theory: Any | None=...,
    interpreter: Any | None=...,
    **values: Any,
) -> list[Atom | Undefined]: ...

@overload
def eval(  # noqa: A001 -- the marked body preserves its public door name
    space: _root.Space,
    target: Any,
    _second: Any,
    /,
    *more: Any,
    timeout: float | None=...,
    inferences: int | None=...,
    under: Any=...,
    theory: Any | None=...,
    interpreter: Any | None=...,
    **values: Any,
) -> list[list[Atom | Undefined]]: ...

@_doors.door(
    kind=_doors.Kind.evaluation,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.nondet,
    tiers=(_doors.Tier.sync, _doors.Tier.async_, _doors.Tier.module, _doors.Tier.context),
    evidence=('extensions/python/tests/ch05_equations_and_evaluation/test_evaluation_options.py::test_evaluation_options_preserve_the_eager_kernel', 'extensions/python/tests/ch05_equations_and_evaluation/test_evaluation_options.py::test_evaluation_options_compose_without_losing_answers'),
    alias='eval',
    binding=_doors.Binding('metta_py_evaluate', _doors.Wire.goal, _doors.EvaluationOptions()),
    refuses=(_doors.Refusal(_doors.RefusalKind.assertion, 'extensions/python/tests/ch05_equations_and_evaluation/test_evaluation_options.py::test_evaluation_options_check_cardinality_before_truncation'), _doors.Refusal(_doors.RefusalKind.inference_limit, 'extensions/python/tests/ch05_equations_and_evaluation/test_evaluation_options.py::test_evaluation_options_preserve_bounds_and_capture'), _doors.Refusal(_doors.RefusalKind.value, 'extensions/python/tests/ch05_equations_and_evaluation/test_evaluation_options.py::test_evaluation_options_refuse_invalid_values')),
)
def eval(  # noqa: A001 -- the marked body preserves its public door name
    space: _root.Space,
    target: Any,
    /,
    *more: Any,
    timeout: float | None=None,
    inferences: int | None=None,
    under: Any=_UNSET,
    theory: Any | None=None,
    interpreter: Any | None=None,
    answer: EvaluationAnswer | str = "all",
    delivery: ArgumentDelivery | str = "atoms",
    limit: int | None = None,
    image: ImageMode | str | None = None,
    on_error: OnError | str = "keep",
    determinism: Determinism | str = "nondet",
    **values: Any,
) -> Any:
    """Evaluate a term, returning every answer.

    This is what !(...) runs, minus the printing: the engine's
    translate_expr over the term, then its goals. Nondeterminism means
    the list can hold any number of answers, including none.

    Variadic, and that is how evaluation BATCHES: several terms ride
    one engine crossing and the answer is one group per term in call
    order, run()'s own grouping carried to the term form. One term
    keeps its flat list, so the scalar reading never changes shape.

    Every answer carries its truth: an answer that is undefined under
    Well Founded Semantics (a tabled loop through tnot, reachable via
    translatePredicate or injected Prolog) arrives as an Undefined
    holding the answer and the delay condition that makes it
    undefined, never as an ordinary-looking value. A term to which no
    rule applies is the ordinary answer itself; `eval_status()` names
    that path `not-reducible`. run() does not carry the third truth
    value; evaluate through eval() when it matters.

    A text target may carry HOLES, exactly as run()'s source may:
    `m.eval(t"(decide {tensor})")` and `m.eval("(decide {x})", x=tensor)`
    hand the object itself to the rule, by identity. One call's holes are
    numbered together, so a batch and a nested template cannot collide.

    `bind()` binds named host values into the term before it evaluates,
    exactly as it does for run(): inside `with m.bind({"x": tensor})`,
    `m.eval("(decide x)")` hands the tensor itself to the rule, by
    identity, rather than a printed form of it. The name is the SYMBOL x
    and not the variable $x, in this call and the source form alike. The
    evaluation calls take the same vocabulary as the source form, so using
    a term instead of source text costs no change of spelling.

    A key may be a NAME or an ATOM. A name means the symbol of that name,
    which is what the engine's own substitution matches and what run()
    takes. An atom means exactly that atom, so `bind({V.x: 5})` fills a
    VARIABLE hole -- the one substitution `unify` reports and the one no
    evaluation call could apply, because a variable crosses the wire as ['v', 'x']
    where a symbol crosses as ['s', 'x'] and the engine matches names.

    `timeout` (seconds) and `inferences` (engine steps) bound the call,
    raising TimeLimitError or InferenceLimitError when hit. A surrounding
    `capture()` scope collects printed text without changing the list.

    `under`, `theory` and `interpreter` are answers()' three, and mean
    exactly what they mean there; `eval()` materialises that query as a list. A
    surrounding `with metta.under(carrier)` reaches here too, which it did
    not before: match() and answers() both honoured such a scope while
    eval() ignored it in silence.

    The answer, delivery, limit, image, on_error and determinism options
    select one evaluation contract. answer=answers retains a replayable
    cursor; answer=stream returns a closable single-pass stream. count,
    exists and none consume only the requested shape. A determinism
    promise is checked before a limit truncates the answers. Image
    projection publishes the type declarations its values require.
    """
    _spaces_intents_module.record_sync_engine_call(space, "eval", sys._getframe(1))
    grouped, holes = _read_targets(
        (target, *more), values, called="eval", reserved=_spaces_execution_module._TERM_KEYWORDS
    )
    if (answer != "all" or delivery != "atoms" or limit is not None
            or image is not None or on_error != "keep" or determinism != "nondet"):

        prepared = [_prepared_ask(space, _spaces_source_module._held(each, holes, handed_on=True), None) for each in grouped]
        targets = tuple(_spaces_handle_module._substituted(each, using) if using else each for each, using in prepared)
        # Capture bindings once before a cursor can outlive their scope.
        # Applying an alias chain twice would turn a -> b into a -> c.
        token = _spaces_scope_module._RUN_BINDINGS.set(None)
        try:
            return evaluate(
                space, targets, answer=answer, delivery=delivery, limit=limit,
                image=image, on_error=on_error, determinism=determinism,
                timeout=timeout, inferences=inferences, under=under,
                theory=theory, interpreter=interpreter,
            )
        finally:
            _spaces_scope_module._RUN_BINDINGS.reset(token)
    handed_on = (
        theory is not None
        or interpreter is not None
        or _spaces_scope_module.selected(under) is not None
    )
    target, more = grouped[0], grouped[1:]
    if more:
        # The batched face: the delegating knobs stay per-term through
        # answers(); the plain lane crosses once for the lot.
        if handed_on:
            return [
                list(
                    space.answers(
                        _spaces_source_module._held(each, holes, handed_on=True),
                        timeout=timeout,
                        inferences=inferences,
                        under=under,
                        theory=theory,
                        interpreter=interpreter,
                    )
                )
                for each in grouped
            ]
        prepared = [_prepared_ask(space, each, holes) for each in grouped]
        scope = next((using for _, using in prepared if using), None)
        return _spaces_execution_module.evaluate_many(
            space._rt,
            space._space,
            tuple(each for each, _ in prepared),
            timeout,
            inferences,
            using=scope,
        )
    # Atom-keyed bindings are applied here whichever branch runs below, so
    # the eager path and the delegating one agree on what a binding means.
    target, using = _prepared_ask(
        space, _spaces_source_module._held(target, holes, handed_on=handed_on),
        None if handed_on else holes,
    )
    # The two methods are NOT one mechanism, which was measured rather than
    # assumed: eval() uses metta_py_evaluate/4's eager collector and
    # answers() opens a cursor, and routing eval() through the cursor
    # unconditionally left a memoized definition's call keys unrecorded
    # where the eager method records them [measured 2026-08-31: a memoized
    # fib(12) reached through the handle then run() stored 13 entries on
    # the eager path and 0 through the cursor]. So the delegation is for
    # what answers() uniquely OWNS -- the carrier, the theory and the
    # interpreter -- and the eager path stays the eager path.
    if handed_on:
        return list(
            space.answers(
                target,
                timeout=timeout,
                inferences=inferences,
                under=under,
                theory=theory,
                interpreter=interpreter,
            )
        )
    return _spaces_execution_module.evaluate(
        space._rt, space._space, target, timeout, inferences, using=using
    )

@_doors.door(
    kind=_doors.Kind.evaluation,
    answers=_doors.AnswersAs.answers,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.nondet,
    tiers=(_doors.Tier.sync,),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_answers_scalar_doors_raise_error_atoms_but_iteration_retains_them', 'extensions/python/tests/ch04_spaces_and_matching/test_arrow_doors.py::test_term_answers_refuse_the_arrow_doors', 'extensions/python/tests/ch04_spaces_and_matching/test_results.py::test_term_answers_never_render_as_a_binding_table'),
    binding=_doors.Binding('metta_py_evaluate', _doors.Wire.goal, _doors.EvaluationOptions(answers=_doors.EvaluationCollection.cursor)),
    sugar_of=_doors.Sugar('space:eval', (('answer', 'answers'),)),
    async_excluded="Answers is a synchronous replayable iterator; AsyncMeTTa's stream is the awaitable pull protocol rather than a cross-thread iterator",
)
def answers(
    space: _root.Space,
    target: Any,
    /,
    *,
    timeout: float | None = None,
    inferences: int | None = None,
    under: Any = _UNSET,
    theory: Any | None = None,
    interpreter: Any | None = None,
    **values: Any,
) -> _root.Answers[Any]:
    """Evaluate as an immutable, cached and replayable view.

    Creating the view performs no engine work. The first demand opens
    its cursor. Outside a transaction, existence pulls at most one
    answer, ``one()`` at most two, and ordinary iteration resumes the
    same lazy evaluation [tested:
    test_function_calls_pull_engine_answers_only_as_demanded;
    commit=2d4d4583c2d82e90bb21a7e8671842f126edd4f4].

    Inside a transaction, opening the cursor evaluates all answers
    eagerly on that transaction's thread, so its reads see earlier
    writes and its own writes commit or roll back with the transaction.
    Holding costs memory proportional to the answer bag. Budgets apply
    during that enumeration; captured output arrives with the first
    pull. Unread rows survive commit and disappear on rollback. Step
    the cursor from the transaction's thread, or open it outside the
    transaction to step it from another thread [tested:
    extensions/python/tests/ch15_writing_transactions_and_worlds/test_cursor_transaction.py;
    commit=ea2c1bde39a7b002b1e5948cf6c53bc469dac084].

    ``under=`` has the same carrier semantics as ``match``. In
    particular, ``space.answers(call, under=counting).one()`` returns one
    ``TaggedAnswer`` whose annotation counts the call's answer
    derivations inside the engine, and ordered carriers
    order their annotated ``TaggedAnswer`` values before a slice pulls
    its prefix. A surrounding ``metta.under(carrier)`` is used only when
    this call does not pass an explicit carrier.

    ``theory=`` treats an atom or iterable of atoms as the theory value for
    this ask. That value replaces the receiver's own equational program.
    Engine builtins and the shared ``&self`` session space remain in scope
    exactly as they are for every space, and names the theory defines
    shadow inherited ones. It installs the theory in an isolated scratch
    space on the first pull, evaluates there, and drops the space when the
    view is exhausted or abandoned. The receiver is unchanged. This
    mirrors reflective descent functions whose inputs are a reified module
    and term [source:
    https://maude.cs.illinois.edu/maude1/manual/maude-manual-html/maude-manual_24.html;
    commit=0d49980b03d507f9bae0354786ab826a146c20df].

    ``interpreter=`` instead evaluates the explicit full-interpreter
    application ``(interpreter target %Undefined% space)`` for this ask,
    which is the shape MeTTa's own evaluation function has: it says
    "reduce with YOURS rather than the engine's".

    The two COMPOSE, and are the head and the third argument of one
    application rather than rival answers to one question: with both, the
    interpreter is handed the theory's space, so it interprets the theory
    [measured 2026-08-31: an interpreter tracing its delegate answered
    `(Traced base)` alone and `(Traced left), (Traced right)` over a
    two-equation theory]. They used to refuse together.

    The INTERPRETER must declare its first parameter `Atom`, MeTTa's own
    way to receive an argument unevaluated, or the engine reduces the
    target before the interpreter ever sees it; and its RETURN metatype
    `%Undefined%`, or the interpreter's own answer is not reduced either.
    `(: e (-> Atom Atom Atom %Undefined%))` is the declaration.

    A text target may carry HOLES, as run()'s source may:
    `m.answers(t"(near {point})")`. A theory, an interpreter or a carrier
    makes this view ask through another door, so the holes are read into
    the term itself there rather than sent as pairs a hand-off would drop.
    """
    _spaces_intents_module.record_sync_engine_call(space, "answers", sys._getframe(1))
    (target,), holes = _read_targets(
        (target,), values, called="answers", reserved=_spaces_execution_module._TERM_KEYWORDS
    )
    carrier = _spaces_scope_module.selected(under)
    handed_on = theory is not None or interpreter is not None or carrier is not None
    target, using = _prepared_ask(
        space, _spaces_source_module._held(target, holes, handed_on=handed_on),
        None if handed_on else holes,
        theory,
        interpreter,
    )
    if theory is not None:
        return _answers_with_theory(
            space, target,
            theory,
            timeout=timeout,
            inferences=inferences,
            carrier=carrier,
            interpreter=interpreter,
        )
    if carrier is None:
        return _spaces_execution_module.evaluate_answers(
            space._rt,
            space._space,
            target,
            timeout,
            inferences,
            using=using,
        )
    algebra_api = lazy('metta.algebra')
    declaration = algebra_api.resolve(space, carrier)
    context = _spaces_scope_module.EvaluationContext(declaration.name, order=declaration.order)
    tagged_target = (
        _spaces_handle_module._substituted(target, using)
        if using
        else (_to_atom(target))
    )
    if declaration.name == "counting":
        def counted() -> Iterator[Any]:
            if algebra_api.has_tagged_program(space, tagged_target):
                yield algebra_api.count_tagged(
                    space,
                    tagged_target,
                    timeout=timeout,
                    inferences=inferences,
                )
            else:
                # This scalar IS the whole evaluation: the counting view
                # holds no answer cursor beside it, so the engine counts
                # once and one integer crosses. Asking the repeatability
                # question here instead sent an effect-bearing goal
                # through a materializing pass that encoded and crossed
                # every answer to reach an aggregate nobody kept.
                yield algebra_api.counting_answer(
                    space,
                    _spaces_execution_module.evaluate_count(
                        space._rt,
                        space._space,
                        target,
                        timeout,
                        inferences,
                        using=using,
                        under=declaration.name,
                    ),
                    declaration.name,
                )

        return _spaces_results_module.Answers(counted(), space=space._space, target=target)
    columns = tuple(_spaces_cursor_module._column_names((tagged_target,)))

    def annotated() -> Iterator[Any]:
        if algebra_api.has_tagged_program(space, tagged_target):
            evaluation = algebra_api.evaluate(
                space,
                tagged_target,
                algebra=declaration,
                context=context,
                timeout=timeout,
                inferences=inferences,
            )
            if not columns:
                yield from evaluation.answers
                return
            row_cls = _spaces_results_module._row_class(columns)
            for answer in evaluation.answers:
                bindings = unify(tagged_target, answer.value)
                if bindings is None:
                    continue
                row = row_cls(bindings[Variable(name)] for name in columns)
                yield _spaces_results_module._AnswerItem(answer, row)
            return
        ordinary = _spaces_execution_module.evaluate_answers(
            space._rt,
            space._space,
            target,
            timeout,
            inferences,
            using=using,
            context=context,
            annotation_factory=(
                lambda value, annotation: algebra_api.captured_answer(
                    space, value, annotation, declaration, context=context
                )
            ),
        )
        yield from ordinary._items()

    return _spaces_results_module.Answers(
        annotated(),
        columns=columns,
        space=space._space,
        target=target,
    )

def _prepared_ask(
    space: _root.Space,
    target: Any,
    using: dict[Any, Any] | None,
    theory: Any = None,
    interpreter: Any = None,
) -> tuple[Any, dict[str, Any] | None]:
    """Everything a term ask does to its target before the engine sees it.

    Two things, both of which every method taking a target owes its caller.

    ``interpreter=`` is a TERM rewrite and nothing more, so it costs the
    same three lines wherever it is offered; ``theory=`` needs a scratch
    space and stays with the method that owns its lifetime, which is why the
    rewrite is skipped here when a theory is also present: the application
    has to name the SCRATCH as its space, and the scratch does not exist
    yet.

    And an ATOM-keyed binding from the ``bind()`` scope is applied here
    rather than sent on. The engine's metta_host_substitute/3 matches an
    atom by NAME [source: engine/filereader.pl:579-584], so it can reach a
    symbol and cannot reach a variable at all -- measured 2026-08-31,
    neither ``{"x": 5}`` nor ``{"$x": 5}`` fills the hole in
    ``(dbl $x)``. A variable hole is exactly what ``unify`` reports, so
    the one substitution the library could produce was the one no method
    could apply. An atom key says which atom it means, so it is applied by
    ``Atom.subs`` here and a name key keeps meaning the symbol it always
    meant, to the same engine predicate as before.
    """
    using = {**(_spaces_scope_module._RUN_BINDINGS.get() or {}), **(using or {})} or None
    if using:
        keyed = {key: value for key, value in using.items() if isinstance(key, Atom)}
        if keyed:
            target = (
                _to_atom(target)
            ).subs(keyed)
            using = {
                key: value
                for key, value in using.items()
                if not isinstance(key, Atom)
            } or None
    if interpreter is not None and theory is None:
        target = _interpreted(space, target, interpreter, space)
    return target, using

def _interpreted(_space: _root.Space, target: Any, interpreter: Any, space: _root.Space) -> Expression:
    """The explicit interpreter application, over one space.

    ``(interpreter target %Undefined% space)`` is the shape MeTTa's own
    evaluation function has -- `!(test (metta (+ 1 2) %Undefined% &self) 3)`
    is in the corpus -- so this says "reduce with YOURS instead of the
    engine's". The space argument is what makes it compose with ``theory=``:
    the interpreter reads the space it is handed, and the theory decides
    which space that is.

    The INTERPRETER must declare its first parameter `Atom`, or MeTTa
    reduces the target before it ever arrives and the interpreter sees an
    answer rather than a term
    [measured 2026-08-31: an ordinary define answered `(Saw base)` where
    `(: e (-> Atom Atom Atom %Undefined%))` answered `(Saw (choice))`].
    The return metatype is the other half: `%Undefined%` there so the
    interpreter's own answer reduces, `Atom` so it does not.
    """
    interpreted = _to_atom(target)
    return Expression(
        [_to_atom(interpreter), interpreted, Symbol("%Undefined%"), space]
    )

def _in_theory(space: _root.Space, theory: Any) -> _abc.Iterator[_root.Space]:
    """A scratch space holding one theory, dropped when the block ends.

    The receiver is unchanged; names the theory defines shadow inherited
    ones, and engine builtins and &self stay in scope as they do for every
    space.
    """
    scratch = space._new_space()
    try:
        atoms = _theory_atoms(theory)
        if atoms:
            scratch.add(*atoms)
        yield scratch
    finally:
        scratch.drop()

def _answers_with_theory(
    space: _root.Space,
    target: Any,
    theory: Any,
    *,
    timeout: float | None,
    inferences: int | None,
    carrier: Any | None,
    interpreter: Any | None = None,
) -> _root.Answers[Any]:
    """Defer an isolated theory ask and own its scratch-space lifetime."""
    columns = () if isinstance(target, str) else tuple(_spaces_cursor_module._column_names((_to_atom(target),)))

    def source() -> Iterator[_spaces_results_module._AnswerItem]:
        scratch = space._new_space()
        inner: _root.Answers[Any] | None = None
        try:
            atoms = _theory_atoms(theory)
            if atoms:
                scratch.add(*atoms)
            # With an interpreter, the application names the SCRATCH and is
            # asked of the RECEIVER: the interpreter's own definition lives
            # here, and the space it reads is the theory's. Asking the
            # scratch instead leaves the interpreter unresolved, and naming
            # the receiver leaves the theory unread
            # [measured 2026-08-31, both ways round].
            asked, ask_of = (
                (target, scratch)
                if interpreter is None
                else (_interpreted(space, target, interpreter, scratch), space)
            )
            if carrier is None:
                inner = ask_of.answers(
                    asked,
                    timeout=timeout,
                    inferences=inferences,
                )
            else:
                inner = ask_of.answers(
                    asked,
                    timeout=timeout,
                    inferences=inferences,
                    under=carrier,
                )
            yield from inner._items()
        finally:
            if inner is not None:
                close = getattr(inner._source, "close", None)
                if callable(close):
                    close()
            scratch.drop()

    return _spaces_results_module.Answers(source(), columns=columns, space=space._space, target=target)

def _theory_atoms(theory: Any) -> tuple[Atom, ...]:
    """Normalize one data-valued theory without accepting source text."""
    if isinstance(theory, lazy('metta._faces.space').Space):
        values: Iterable[Any] = theory.atoms()
    elif isinstance(theory, Atom):
        values = (theory,)
    elif isinstance(theory, str) or not isinstance(theory, Iterable):
        msg = (
            "theory= needs an atom, Space, or iterable of atoms as data; "
            "source text belongs at run()"
        )
        raise TypeError(msg)
    else:
        values = theory
    try:
        return tuple(_to_atom(value) for value in values)
    except (TypeError, ValueError) as error:
        msg = f"theory= contains a value that is not an atom: {error}"
        raise TypeError(msg) from error

@_doors.door(
    kind=_doors.Kind.evaluation,
    answers=_doors.AnswersAs.sequence,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.nondet,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_hyperpose_is_parallel_under_the_languages_name', 'extensions/python/tests/ch14_seeing_your_program/test_engine_pool.py::test_pool_composes_with_in_engine_parallel', 'extensions/python/tests/ch17_concurrency_and_the_loop/test_parallel.py::test_parallel_accepts_text_and_atoms'),
)
def parallel(
    space: _root.Space,
    *targets: Any,
    timeout: float | None = None,
) -> list[Atom | Undefined]:
    """Evaluate every target concurrently, answering every branch's answers.

    This is the engine's `hyperpose`, the parallel twin of `superpose`:
    one SWI thread per branch through concurrent_and/2, so independent
    branches cost about one branch's wall clock rather than their sum.

        m.run("(= (sq $x) (* $x $x))")
        m.parallel(S.sq(1), S.sq(2), S.sq(3))    # 1, 4 and 9, in any order

    This is the **in-engine** fan-out: one janus call, the branches split
    below it. The other route is `pool()`, the **Python-side** fan-out
    across several engines. Reach for this one when the fan-out is a MeTTa
    expression, and for `pool()` when it is a Python loop. They compose,
    so a pool worker may itself evaluate a `parallel()`.

    (Before 2026-08-15 this docstring said in-engine fan-out was the only
    route to a second core, because every janus call took one process-wide
    lock. That lock is now per-engine, and Python threads holding their own
    engine measured 1.94x, 3.90x and 7.26x at 2, 4 and 8 threads.)

    **Answers arrive in completion order, not argument order**, because
    the branches race. Compare sets rather than sequences, and evaluate a
    `superpose` instead when order carries meaning.

    Each target is a term or its source text, as everywhere else. No
    targets answers nothing without calling the engine.

    `timeout` bounds the call and is the bound to use here. There is
    deliberately no `inferences=`: the engine's inference limit counts
    the calling thread, and `concurrent_and/2` runs every branch in a
    worker, so a limit of 50,000 does not stop two branches spending six
    million [measured 2026-08-15]. An unenforceable bound is worse than
    an absent one, so eval() over a `superpose` is the way to bound this
    work by inferences, at the cost of running it on one core.
    """
    if not targets:
        return []
    branches = Expression([_to_atom(target) for target in targets])
    return _spaces_execution_module.evaluate(
        space._rt,
        space._space,
        Expression([Symbol("hyperpose"), branches]),
        timeout,
        None,
    )

@_doors.door(
    kind=_doors.Kind.provider,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync,),
    evidence=('extensions/python/tests/ch14_seeing_your_program/test_engine_pool.py::test_metta_pool_is_the_same_pool', 'extensions/python/tests/ch14_seeing_your_program/test_engine_pool.py::test_several_failures_raise_together_one_raises_plain'),
    async_excluded="asyncio's fan-out is N workers and asyncio.gather; a pool of engine threads is the synchronous spelling of the same thing",
)
def pool(_space: _root.Space, workers: int | None = None) -> Any:
    """A pool of worker threads that each hold their own Prolog engine.

    The Python-side twin of `parallel()`. Each worker attaches its own
    engine, so the process lock that serialises the home engine does not
    apply to it and the calls genuinely run at once [measured 2026-08-15:
    1.94x, 3.90x and 7.26x at 2, 4 and 8 workers].

        m.run("(= (sq $x) (* $x $x))")
        with m.pool(workers=4) as p:
            list(p.map(lambda n: m.eval(S.sq(n))[0], range(64)))

    Use it as a context manager so every engine is released. `workers`
    defaults to os.cpu_count(). This handle stays usable from the workers:
    a MeTTa is a space name over the process runtime, not thread-owned.

    Reach for `parallel()` instead when the fan-out is a MeTTa expression
    rather than a Python loop; the two compose.
    """
    return lazy('metta.parallel').EnginePool(workers)

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.boolean,
    effect=_doors.EffectClass.readOnlyLookup,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch05_equations_and_evaluation/test_nothing_outcomes.py::test_reducible_asks_the_question_without_running_the_term',),
    binding=_doors.Binding('metta_py_reducible', _doors.Wire.goal),
)
def reducible(space: _root.Space, target: Any) -> bool:
    """Whether a head reduces here, asked without evaluating anything.

        m.reducible(S.double(4))     # True
        m.reducible(S.Point(1, 2))   # False, nothing applies to that head

    The same head test eval_status() uses, published on its own because a
    caller who wants to DECIDE about an unreduced term should not have to
    run the term to find out. That decision is the caller's: a term
    nothing applies to is its own answer, which is ordinary MeTTa and how
    `!(hello world)` works, so there is no scope here that refuses one.

    The Node extension has had m.reducible() since it existed; Python had
    only eval_status(), which evaluates to tell you [measured 2026-08-31].
    """
    # The engine call answers the ATOM true or false, which crosses as the string
    # of that name; bool("false") is True, so the comparison is explicit,
    # the same way algebra.py reads its own boolean result.
    return (
        space._rt.apply_must(
            "metta_py_reducible", space._space, _to_atom(target).to_wire()
        )
        == "true"
    )

@_doors.door(
    kind=_doors.Kind.evaluation,
    answers=_doors.AnswersAs.sequence,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.nondet,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_eval_status_reports_the_four_outcomes', 'extensions/python/tests/ch05_equations_and_evaluation/test_per_ask_evaluation.py::test_eval_status_selects_the_same_relations_answers_does', 'extensions/python/tests/ch05_equations_and_evaluation/test_nothing_outcomes.py::test_eager_eval_keeps_empty_and_not_reducible_distinct'),
    binding=_doors.Binding('metta_py_evaluate', _doors.Wire.goal, _doors.EvaluationOptions(answers=_doors.EvaluationCollection.status)),
)
def eval_status(
    space: _root.Space,
    target: Any,
    /,
    *,
    timeout: float | None = None,
    inferences: int | None = None,
    theory: Any | None = None,
    interpreter: Any | None = None,
    **values: Any,
) -> list[tuple[str, Atom | Undefined | None]]:
    """Evaluate a term, pairing each answer with how it was produced.

        m.eval_status(S.double(4))       # [("value", Grounded(8))]
        m.eval_status(S.Point(1, 2))     # [("not-reducible", Expression(...))]
        m.eval_status(S.empty())         # [("empty", None)]

    `value` means an equation, builtin or special form applied.
    `not-reducible` means no rule applied, so the answer is the term
    itself, which is what MeTTa does with any head it cannot call.
    `empty` means the goal produced no answer at all, and its atom is
    None. Reading the last two as the same thing is the mistake this
    exists to prevent: an unevaluated term and a pruned branch look
    alike from the answers alone. An error is not a status here,
    because it arrives as an exception.

    A `bind()` scope binds host values into the term exactly as it
    does for eval(), and it has to: the substitution lands BEFORE the
    reducibility question, so the status of an evaluation that binds
    anything was unaskable without it. Name keys mean symbols and atom
    keys mean themselves, so `bind({V.x: 5})` fills a variable hole.

    `theory` and `interpreter` are eval()'s own, and mean the same here.
    This is the method that says which evaluation path produced an answer, so
    being unable to point it at an alternative evaluation relation was the
    sharpest form of the gap: `m.eval_status(target, interpreter=my_eval)`
    is how you see whether an explicit interpreter reduced a term or handed
    it back. `under=` is deliberately NOT here: a carrier annotates every
    answer with an algebra value, so it would make a status row a triple
    rather than the pair it is, which is a question about what a status IS.
    """
    (target,), holes = _read_targets(
        (target,), values, called="eval_status", reserved=_spaces_execution_module._STATUS_KEYWORDS
    )
    target, using = _prepared_ask(space, target, holes, theory, interpreter)
    if theory is None:
        return _spaces_execution_module.evaluate_status(
            space._rt, space._space, target, timeout, inferences, using=using
        )
    for scratch in _in_theory(space, theory):
        # With an interpreter, the application names the SCRATCH and is
        # asked of the RECEIVER, the same way answers() composes them: the
        # interpreter's definition lives here and the space it reads is
        # the theory's.
        if interpreter is None:
            return scratch.eval_status(
                target, timeout=timeout, inferences=inferences
            )
        return space.eval_status(
            _interpreted(space, target, interpreter, scratch),
            timeout=timeout,
            inferences=inferences,
        )
    raise AssertionError  # pragma: no cover -- _in_theory always yields once

@_doors.door(
    kind=_doors.Kind.evaluation,
    answers=_doors.AnswersAs.sequence,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.nondet,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_run_status_registers_signatures_before_any_form_runs', 'extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_run_status_reports_each_directive', 'extensions/python/tests/ch11_python_as_a_notation/test_template_holes.py::test_run_status_refuses_program_text_with_holes'),
)
def run_status(
    space: _root.Space,
    source: str,
    *,
    timeout: float | None = None,
    inferences: int | None = None,
) -> list[list[tuple[str, Atom | Undefined | None]]]:
    """run(), with each directive's answers paired with how they arose.

    The grouping and the answers are run()'s own; see eval_status() for
    what the three paths mean.
    """
    _spaces_source_module._require_source(source, "run_status")
    return _spaces_execution_module.run_status(space._rt, space._space, source, timeout, inferences)

@_doors.door(
    kind=_doors.Kind.evaluation,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.async_,),
    evidence=('extensions/python/tests/ch10_errors_and_refusals/test_error_answers.py::test_one_raises_a_structured_error_on_an_error_answer', 'extensions/python/tests/ch10_errors_and_refusals/test_error_answers.py::test_one_still_answers_plain_values', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_value_answers_the_one_answer'),
    sugar_of=_doors.Sugar('space:eval', (('answer', 'one'), ('delivery', 'values'), ('on_error', 'abort'))),
)
def one(
    space: _root.Space,
    target: Any,
    *,
    timeout: float | None = None,
    inferences: int | None = None,
) -> Any:
    """Return the sole answer as a plain Python value for internal callers.

        m.eval(S.fact(5))[0]         # Grounded(120)

    Exactly one answer is the contract: none or several raise naming
    the count, because a caller asking for the value has asserted
    there is one. Grounded answers unwrap to their Python values;
    symbols and structure stay atoms.

    This is one point on the answer-cardinality axis, spelled the
    same everywhere it appears: eval() takes every answer (MeTTa's
    collapse), while this private helper demands exactly one. The same
    timeout/inferences bounds apply throughout.

    An `(Error ...)` answer raises MettaResultError carrying the
    atom: an error among the answers is the evaluation reporting
    failure, and failure outranks the count. eval() is the method
    that keeps errors as data.
    """
    return space.eval(
        target, timeout=timeout, inferences=inferences,
        answer="one", delivery="values", on_error="abort",
    )

@_doors.door(
    kind=_doors.Kind.evaluation,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.async_,),
    evidence=('extensions/python/tests/ch10_errors_and_refusals/test_error_answers.py::test_first_raises_on_an_error_first_answer_only', 'extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_the_three_families_share_the_tolerant_member'),
    sugar_of=_doors.Sugar('space:eval', (('answer', 'first'), ('delivery', 'values'), ('on_error', 'abort'))),
)
def first(
    space: _root.Space,
    target: Any,
    *,
    timeout: float | None = None,
    inferences: int | None = None,
) -> Any:
    """The first answer as a plain Python value, or None for no answers.

    The tolerant member of one()'s family: one() asserts exactly
    one, eval() answers all, first() answers the first or nothing,
    decoded by the same rule as one(). An Undefined first answer
    still raises, since None here MEANS no answers. Tolerance is
    about cardinality, not content: a first answer that is an
    `(Error ...)` atom raises MettaResultError exactly as one()
    does, because None must keep meaning "no answers" and an error
    used as a value is the silent kind of wrong.
    """
    return space.eval(
        target, timeout=timeout, inferences=inferences,
        answer="first", delivery="values", on_error="abort",
    )

# Resolve annotations after definitions so peer imports can finish.
if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
