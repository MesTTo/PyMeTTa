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
"""

from __future__ import annotations

from collections.abc import Iterator
from itertools import islice
from typing import Any, Self

from ._convert_project import auto_image, project
from ._space_execution import evaluate as evaluate_eager
from ._space_execution import evaluate_count, value_one
from ._under import _UNSET, selected
from .atoms import Atom, Grounded, Handle, Undefined, _decode, ground
from .doors import AnswerForm, EvaluationAnswer
from .errors import EngineError, refuse
from .results import Answers, Rows, _AnswerItem, error_answer, raise_error_answers
from .vocabularies import ArgumentDelivery, Determinism, ImageMode, OnError, RefusalKind


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

    def __init__(self, raw: Answers[Any], space: Any, *, delivery: ArgumentDelivery,
                 image: ImageMode | None, errors: OnError, determinism: Determinism,
                 limit: int | None) -> None:
        self._raw: Answers[Any] | None = raw
        self._iterator: Iterator[Any] | None = raw._source
        self._space = space
        self._delivery = delivery
        self._image = image
        self._errors = errors
        self._determinism = determinism
        self._limit = limit
        self._count = 0
        self._prepared = False
        self._pending: Iterator[_AnswerItem] | None = None
        self._closed = False

    def __iter__(self) -> _Selection:
        return self

    def _next_item(self) -> _AnswerItem:
        if self._iterator is None:
            raise StopIteration
        while True:
            item = next(self._iterator)
            if not isinstance(item, _AnswerItem):
                item = _AnswerItem(item, None)
            error = error_answer(item.value, space=self._space.name)
            if error is not None:
                if self._errors is OnError.abort:
                    raise error
                if self._errors is OnError.empty:
                    continue
            return _AnswerItem(_value(item.value, self._delivery, self._image, self._space), item.row)

    def __next__(self) -> _AnswerItem:
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
        else:
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

    __slots__ = ("_source",)

    def __init__(self, source: _Selection) -> None:
        self._source = source

    def __next__(self) -> Any:
        return next(self._source).value

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
        # The eager cardinality spellings retain the existing _one/_first
        # behavior, including effects after the selected first answer.
        eager = shape.form is AnswerForm.materialised and limit is None
        if eager:
            if theory is not None or interpreter is not None or selected(under) is not None:
                with space._door_answers(target, **options) as answers:
                    values = list(answers)
            else:
                values = evaluate_eager(space._rt, space._space, target, timeout, inferences)
            if errors is OnError.empty:
                values = [value for value in values if error_answer(value, space=space.name) is None]
            if shape is EvaluationAnswer.first and promise is Determinism.nondet:
                values = values[:1]
            if errors is OnError.abort:
                raise_error_answers(values, space=space.name, target=target)
            _cardinality(len(values), promise)
            if shape is EvaluationAnswer.all:
                return [_value(value, delivered, image_mode, space) for value in values]
            if shape is EvaluationAnswer.first:
                values = values[:1]
                if not values:
                    return None
            if delivered is ArgumentDelivery.values:
                return value_one(target, [_image(value, image_mode, space) for value in values])
            return _value(_scalar_atom(values, shape), delivered, image_mode, space)
        if (shape is EvaluationAnswer.count and limit is None and errors is OnError.keep
                and promise is Determinism.nondet and theory is None and interpreter is None
                and selected(under) is None):
            return evaluate_count(space._rt, space._space, target, timeout, inferences)
        raw = space._door_answers(target, **options)
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
        view: Answers[Any] = Answers(source, columns=raw.columns, space=space.name, target=target, query=raw._query)
        if shape is EvaluationAnswer.answers:
            return view
        with view:
            if shape is EvaluationAnswer.rows:
                if view.columns:
                    return Rows(view.columns, view.rows)
                return Rows(("value",), ((value,) for value in view))
            values = (list(islice(view, 1))
                      if shape is EvaluationAnswer.first and promise is Determinism.nondet
                      else list(view))
            if shape is EvaluationAnswer.all:
                return values
            if shape is EvaluationAnswer.first and not values:
                return None
            chosen = values[:1] if shape is EvaluationAnswer.first else values
            if delivered is ArgumentDelivery.values:
                return value_one(target, chosen)
            return _scalar_atom(chosen, shape)

    results = []
    try:
        for target in targets:
            results.append(one(target))  # noqa: PERF401 -- retain acquired sources for cleanup if the batch fails
    except BaseException as error:
        failures = []
        for result in results:
            if isinstance(result, (Answers, _Stream)):
                try:
                    result.close()
                except BaseException as cleanup:  # noqa: BLE001 -- attempt all closes even after an interruption
                    failures.append(cleanup)
        if failures:
            msg = "evaluation batch and cursor cleanup failed"
            raise BaseExceptionGroup(msg, [error, *failures]) from None
        raise
    return results[0] if len(results) == 1 else results
