"""Purpose: expose an engine state cell as one typed Python handle.

Assumes:
  - ``new-state`` answers the cell symbol and ``get-state`` reads it, both
    keeping the declared ``StateMonad`` parameter; ``change-state!`` runs for
    its EFFECT and answers ``true``, the answer every operation of that family
    gives, so a write is not a way to obtain the cell [source:
    lib/lib_builtin_types/lib_builtin_types.metta, and PeTTa@ae66fa8
    src/metta.pl:265, `'change-state!'(Var, Value, true)`]
Guarantees:
  - ``State.value`` reads and writes the same engine cell, and ``__metta__``
    lets every ordinary atom boundary carry that cell [tested:
    test_state_retires_three_state_function_strings; commit=cff2e7f319bd2212f0c2d74f8d5fe5be3ac693b5]
  - the engine store is process-shared; each individual dynamic-store read
    and mutex-guarded write is thread-safe, while compound Python
    read-modify-write remains non-atomic and State emits no events, history,
    or transactions [tested:
    test_fold_into_state_updates_the_shared_engine_cell; commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
Owns resources:
  - the engine owns the state cell; this handle owns no independent resource.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from .atoms import Atom, Symbol, _decode
from .errors import EngineError

if TYPE_CHECKING:
    from ._space import Space


class State[T]:
    """A mutable engine cell whose Python type parameter is its value type."""

    __slots__ = ("_cell", "_space")

    def __init__(self, value: T, *, space: Space | None = None) -> None:
        if space is None:
            from . import engine  # noqa: PLC0415  -- the default engine is lazy

            space = engine().self
        answers = space.eval(Symbol("new-state")(value))
        if len(answers) != 1 or not isinstance(answers[0], Symbol):
            msg = f"new-state returned {answers!r}, not one state-cell symbol"
            raise EngineError(msg)
        self._space = space
        self._cell = answers[0]

    def __metta__(self) -> Atom:
        """Mention this cell at any ordinary atom-encoding boundary."""
        return self._cell

    @property
    def value(self) -> T:
        """Read the cell, requiring the engine's single state answer."""
        answers = self._space.eval(Symbol("get-state")(self._cell))
        if len(answers) != 1:
            msg = f"get-state returned {len(answers)} answers for {self._cell}"
            raise EngineError(msg)
        return cast(T, _decode(answers[0]))

    @value.setter
    def value(self, replacement: T) -> None:
        answers = self._space.eval(Symbol("change-state!")(self._cell, replacement))
        #The write answers `true`, not the cell. It answered the cell until
        #2026-08-30, which let `(get-state (change-state! ...))` compose; the
        #arbiter's write is an effect and says only that it happened.
        if len(answers) != 1 or _decode(answers[0]) is not True:
            msg = (f"change-state! returned {answers!r}, not the effect "
                   f"answer true, writing {self._cell}")
            raise EngineError(msg)

    def __repr__(self) -> str:
        return f"State({self._cell})"


__all__ = ["State"]
