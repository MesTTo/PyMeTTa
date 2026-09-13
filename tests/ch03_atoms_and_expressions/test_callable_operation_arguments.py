"""Purpose: retain lexical programs when native callbacks enter host operations.

Guarantees:
  - native callable arguments use the caller's space, including nested values
    and scheduled operations, and retain that home after the call [tested:
    test_operation_callbacks_keep_the_calling_program; commit=WORKTREE]
  - an explicit callable home takes precedence over the calling space [tested:
    test_operation_callbacks_preserve_an_explicit_home; commit=WORKTREE]
  - inverse operations receive the same lexical callback conversion [tested:
    test_inverse_operations_receive_native_callbacks; commit=WORKTREE]
"""

from collections.abc import Callable

import pytest

from metta import Expression, MeTTa, S, Space, V


@pytest.mark.parametrize("name", ("&operation-callback-home", S["operation-callback-home"](1)))
@pytest.mark.parametrize("kind", ("det", "many", "async"))
@pytest.mark.parametrize("nested", (False, True))
def test_operation_callbacks_keep_the_calling_program(name, kind, nested):
    """Conversion carries the program that gave a function symbol its meaning."""
    with MeTTa() as context:
        home = Space(name)
        operation = S[f"invoke-callback-{kind}"]
        try:
            original = S["="](S["callback-add"](V.value), S["+"](V.value, 4))
            home.add(S[":"](S["callback-add"], S["->"](S.Number, S.Number)), original)
            held = []
            annotation = list[Callable[[int], int]] if nested else Callable[[int], int]

            def answer(value):
                callback = value[0] if nested else value
                held.append(callback)
                return callback(3)

            def once(value: annotation) -> int:
                return answer(value)

            def choices(value: annotation):
                yield answer(value)

            async def deferred(value: annotation) -> int:
                return answer(value)

            producer = {"det": once, "many": choices, "async": deferred}[kind]
            context.self.op(producer, name=operation.name, effect="readOnlyLookup")
            value = S.noeval(Expression([S["callback-add"]])) if nested else S["callback-add"]
            results = home.eval(operation(value))
            if kind == "async":
                results = list(results[0].wait())
            assert results == [7]
            home.remove(original)
            home.add(S["="](S["callback-add"](V.value), S["+"](V.value, 10)))
            assert held[0](5) == 15
        finally:
            try:
                context.self.unregister_op(operation.name)
            finally:
                home.drop()


@pytest.mark.parametrize("quoted", (False, True))
def test_operation_callbacks_preserve_an_explicit_home(quoted):
    """A carried lambda retains its own program across a different caller."""
    with MeTTa() as context:
        caller = context.self
        with caller._new_space() as home:
            home.run("(= (callback-add $value) (+ $value 10))")
            caller.run("(= (callback-add $value) (+ $value 100))")

            @caller.op(effect="readOnlyLookup")
            def invoke_lexical(callback: Callable[[int], int]) -> int:
                return callback(3)

            value = S["|->"](Expression([V.value]), S.evalc(S["callback-add"](V.value), home))
            try:
                assert caller.eval(S["invoke-lexical"](S.noeval(value) if quoted else value)) == [13]
            finally:
                caller.unregister_op("invoke-lexical")


@pytest.mark.parametrize("stream", (False, True))
def test_inverse_operations_receive_native_callbacks(stream):
    """The output-side converter resolves a function in the inverse caller."""
    with MeTTa() as context:
        caller = context.self
        with caller._new_space() as home:
            home.run("(: callback-add (-> Number Number)) (= (callback-add $value) (+ $value 4))")

            def forward(_value: int) -> Callable[[int], int]:
                msg = "the inverse query must not execute the forward body"
                raise AssertionError(msg)

            def once(callback):
                return callback(3)

            def choices(callback):
                yield callback(3)

            operation = "inverse-callback-choices" if stream else "inverse-callback-once"
            caller.op(forward, name=operation, inverse=choices if stream else once, effect="readOnlyLookup")
            try:
                assert home.run(f"!(let ({operation} $value) callback-add $value)") == [[7]]
            finally:
                caller.unregister_op(operation)
