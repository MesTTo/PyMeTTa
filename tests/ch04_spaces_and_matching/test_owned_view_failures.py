"""Purpose: preserve body and cleanup failures on owned result exit."""

import asyncio
from types import SimpleNamespace

import pytest

from metta._spaces.evaluate import _Stream
from metta._spaces.results import Answers, _raise_exit_errors
from metta.aio._evaluation import EvaluationView
from metta.remote import Gateway, Server
from metta.remote._client import RemoteCursor


@pytest.mark.parametrize("body", [ValueError("body"), KeyboardInterrupt("cancelled body")])
def test_owned_views_preserve_body_and_cleanup_errors(body):
    """A failed close cannot replace the failure that caused unwinding."""
    cleanup = RuntimeError("cleanup")

    class Source:
        def __iter__(self):
            return self

        def __next__(self):
            raise StopIteration

        def close(self):
            raise cleanup

    answers = Answers(Source())
    try:
        with pytest.raises(BaseExceptionGroup) as failure, answers:
            raise body
        assert failure.value.exceptions == (body, cleanup)
    finally:
        answers._source = iter(())
        answers.close()


def test_failed_answer_exit_retains_its_source_for_retry():
    """A grouped exit failure leaves the same source available to close again."""
    body, cleanup = ValueError("body"), RuntimeError("cleanup")

    class Source:
        closes = 0

        def __iter__(self):
            return self

        def __next__(self):
            raise StopIteration

        def close(self):
            self.closes += 1
            if self.closes == 1:
                raise cleanup

    source = Source()
    answers = Answers(source)
    with pytest.raises(ExceptionGroup) as caught, answers:
        raise body
    assert caught.value.exceptions == (body, cleanup)
    answers.close()
    assert source.closes == 2


@pytest.mark.parametrize("body", [ValueError("body"), KeyboardInterrupt("cancelled body")])
def test_async_owned_view_preserves_body_and_cleanup_errors(body):
    """The asynchronous exit retains cancellation and its failed release."""
    cleanup = RuntimeError("cleanup")

    class Group:
        async def close(self, _index):
            raise cleanup

    async def run():
        with pytest.raises(BaseExceptionGroup) as failure:
            async with EvaluationView(Group(), 0):
                raise body
        assert failure.value.exceptions == (body, cleanup)
    asyncio.run(run())


@pytest.mark.parametrize("count", [0, 1, 3])
@pytest.mark.parametrize("body", [None, KeyboardInterrupt("body")])
def test_exit_aggregation_retains_any_number_of_cleanup_failures(count, body):
    """Independent cleanup outcomes remain visible in their original order."""
    failures = [RuntimeError(f"cleanup {index}") for index in range(count)]
    if not failures:
        assert _raise_exit_errors("exit failed", body, iter(failures)) is None
    elif body is None and count == 1:
        with pytest.raises(RuntimeError) as caught:
            _raise_exit_errors("exit failed", body, iter(failures))
        assert caught.value is failures[0]
    else:
        with pytest.raises(BaseExceptionGroup) as caught:
            _raise_exit_errors("exit failed", body, iter(failures))
        assert caught.value.exceptions == tuple(([body] if body is not None else []) + failures)


@pytest.mark.parametrize("owner", [Gateway, Server])
def test_remote_owned_view_preserves_body_and_cleanup_errors(monkeypatch, owner):
    """Gateway and server context exit use the same failure contract."""
    body, cleanup = ValueError("body"), RuntimeError("cleanup")

    def fail(_self):
        raise cleanup

    monkeypatch.setattr(owner, "close", fail)
    with pytest.raises(BaseExceptionGroup) as failure, object.__new__(owner):
        raise body
    assert failure.value.exceptions == (body, cleanup)


@pytest.mark.parametrize("owner,make", [
    (Answers, lambda: Answers(())),
    (_Stream, lambda: _Stream(SimpleNamespace(close_deferred=lambda: None))),
    (RemoteCursor, lambda: object.__new__(RemoteCursor)),
    (Gateway, lambda: object.__new__(Gateway)),
    (Server, lambda: object.__new__(Server)),
])
@pytest.mark.parametrize("body_fails", [False, True])
@pytest.mark.parametrize("close_fails", [False, True])
def test_owned_exit_zero_one_or_two_failures(monkeypatch, owner, make, body_fails, close_fails):
    """Normal exit and single failures retain the same ownership and identity."""
    body = ValueError("body") if body_fails else None
    cleanup = RuntimeError("cleanup") if close_fails else None
    calls = []

    def close(self):
        calls.append(self)
        if cleanup is not None:
            raise cleanup

    monkeypatch.setattr(owner, "close", close)
    view = make()
    caught = None
    try:
        with view:
            if body is not None:
                raise body  # noqa: TRY301 -- the test must fail inside the owned context
    except BaseException as error:
        caught = error
    if body is not None and cleanup is not None:
        assert isinstance(caught, BaseExceptionGroup)
        assert caught.exceptions == (body, cleanup)
    else:
        assert caught is (body or cleanup)
    assert calls == [view]


@pytest.mark.parametrize("body_fails", [False, True])
@pytest.mark.parametrize("close_fails", [False, True])
def test_async_exit_preserves_cancellation_and_normal_exit(body_fails, close_fails):
    """Cancellation is retained with cleanup failure and propagated unchanged alone."""
    body = asyncio.CancelledError("body") if body_fails else None
    cleanup = RuntimeError("cleanup") if close_fails else None
    calls = []

    class Group:
        async def close(self, index):
            calls.append(index)
            if cleanup is not None:
                raise cleanup

    async def run():
        caught = None
        try:
            async with EvaluationView(Group(), 0):
                if body is not None:
                    raise body  # noqa: TRY301 -- the test must cancel inside the owned context
        except BaseException as error:
            caught = error
        if body is not None and cleanup is not None:
            assert isinstance(caught, BaseExceptionGroup)
            assert caught.exceptions == (body, cleanup)
        else:
            assert caught is (body or cleanup)
        assert calls == [0]

    asyncio.run(run())
