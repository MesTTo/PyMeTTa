"""Purpose: keep Prolog-backed definition registration on the async owner.

Guarantees:
  - an unapplied synchronous decorator cannot escape AsyncMeTTa.define
    [tested: test_async_prolog_define_requires_the_reference_function; commit=089bc6036ae5039bce3963d8b4e80ecaf04dfb49]
"""

import asyncio
import threading

import pytest

import metta.aio as _aio_surface
from metta import MeTTa, Space


def test_async_prolog_define_requires_the_reference_function(tmp_path):
    """No callable may escape that registers after its worker has closed."""
    async def run():
        with MeTTa() as context:
            async with _aio_surface.AsyncMeTTa(metta=context.self) as am:
                with pytest.raises(TypeError, match="reference function"):
                    await am.define(prolog=tmp_path / "not-read.pl")

    asyncio.run(run())


def test_async_prolog_define_registers_and_applies_on_its_worker(tmp_path, monkeypatch):
    """The applied form keeps its Python twin and calls the actual Prolog body."""
    source = tmp_path / "async_twin.pl"
    source.write_text('''
:- metta_extension(async_lifecycle_twin, [version('0.1.0')]).
:- metta_export("(: async-lifecycle-twin (-> Number Number))").
'async-lifecycle-twin'(X, Y) :- Y is X + 1.
''')
    registered_on = []
    original = Space.register_prolog

    def register(space, *args, **kwargs):
        registered_on.append(threading.get_ident())
        return original(space, *args, **kwargs)

    monkeypatch.setattr(Space, "register_prolog", register)

    def reference(value):
        return value + 1

    async def run():
        with MeTTa() as context:
            async with _aio_surface.AsyncMeTTa(metta=context.self) as am:
                worker = await am.call(lambda _space: threading.get_ident())
                twin = await am.define(reference, prolog=source, name="async-lifecycle-twin")
                assert twin.py(4) == 5
                assert await am.eval("(async-lifecycle-twin 4)") == [5]
                assert registered_on == [worker]
                assert worker != threading.get_ident()

    asyncio.run(run())
