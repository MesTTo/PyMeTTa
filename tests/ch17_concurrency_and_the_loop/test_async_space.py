"""Purpose: verify async space construction through the synchronous context door.

Guarantees:
  - journal replay, validation, failed acquisition cleanup, and equation-home
    resolution agree across MeTTa.space and AsyncMeTTa.space [tested:
    test_a_journaled_async_space_round_trips_a_fact,
    test_async_sync_without_journal_has_the_sync_refusal,
    test_a_failed_async_space_construction_leaks_nothing,
    test_an_anonymous_async_space_resolves_equations_through_its_home;
    commit=d263b1f05e3ca3a0621122c1fc60d295b87692b0]
  - the async factory reaches a journal's one-open schema migration, so the
    sync door's rename keyword is not a synchronous-only spelling [tested:
    test_the_async_space_factory_exposes_replay_rename; commit=694dff934a11dbc2ee99267b60f39564053baf87]
"""

import asyncio

import pytest

import metta.aio as _aio_surface
from metta import MeTTa, S, Space, V
from metta.foreign import SpaceProvider


def test_a_journaled_async_space_round_trips_a_fact(tmp_path):
    """Drop closes the owned journal so another async handle can replay it."""
    async def go():
        with MeTTa() as context:
            async with _aio_surface.AsyncMeTTa(metta=context.self) as am:
                journal = tmp_path / "explicit-schema.jnl"
                stored = await am.space(journal=journal, schema={"edge": 2}, sync="close")
                try:
                    await stored.add(S.edge(S.a, S.b))
                    # Transaction failure must discard the provider's staged write.
                    with pytest.raises(RuntimeError, match="abort journal write"):
                        await stored.call(lambda space: space.transaction(lambda: abort(space)))
                    assert await stored.atoms() == [S.edge(S.a, S.b)]
                finally:
                    await stored.drop()
                reopened = await am.space(journal=journal, schema={"edge": 2})
                try:
                    assert await reopened.atoms() == [S.edge(S.a, S.b)]
                finally:
                    await reopened.drop()

    def abort(space):
        space.add(S.edge(S.discarded, S.write))
        msg = "abort journal write"
        raise RuntimeError(msg)

    asyncio.run(go())


def test_async_sync_without_journal_has_the_sync_refusal():
    """The same invalid request reaches the same synchronous validation."""
    async def go():
        with MeTTa() as context:
            with pytest.raises(TypeError) as sync_error:
                context.space("&async-no-journal", sync="batch")
            async with _aio_surface.AsyncMeTTa(metta=context.self) as am:
                with pytest.raises(TypeError) as async_error:
                    await am.space("&async-no-journal", sync="batch")
            assert str(async_error.value) == str(sync_error.value)

    asyncio.run(go())


def test_async_schema_mapping_backing_matches_sync(tmp_path):
    """A mapping backing supplies the journal schema on both surfaces."""
    async def go():
        with MeTTa() as context:
            journal = tmp_path / "mapping-schema.jnl"
            with context.space(backing={"edge": 2}, journal=journal) as sync_space:
                sync_space.add(S.edge(S.a, S.b))
            async with _aio_surface.AsyncMeTTa(metta=context.self) as am:
                stored = await am.space(backing={"edge": 2}, journal=journal)
                try:
                    assert await stored.atoms() == [S.edge(S.a, S.b)]
                    await stored.add(S.edge(S.b, S.c))
                finally:
                    await stored.drop()
            with context.space(backing={"edge": 2}, journal=journal) as sync_space:
                assert sync_space.atoms() == [S.edge(S.a, S.b), S.edge(S.b, S.c)]

    asyncio.run(go())


def test_the_async_space_factory_exposes_replay_rename(tmp_path):
    """The async door migrates a journal the sync door wrote under old heads."""
    async def go():
        journal = tmp_path / "async-rename.jnl"
        with MeTTa() as context:
            with context.space(backing={"old": 1}, journal=journal, sync="close") as old:
                old.add(S.old(S.value))
            async with _aio_surface.AsyncMeTTa(metta=context.self) as am:
                migrated = await am.space(
                    backing={"new": 1},
                    journal=journal,
                    sync="close",
                    rename={"old": "new"},
                )
                try:
                    assert await migrated.atoms() == [S.new(S.value)]
                finally:
                    await migrated.drop()
                # The migration is one-open: the next open must not repeat it.
                reopened = await am.space(backing={"new": 1}, journal=journal)
                try:
                    assert await reopened.atoms() == [S.new(S.value)]
                finally:
                    await reopened.drop()

    asyncio.run(go())


def test_async_bare_transport_has_the_sync_refusal():
    """Refusal names RemoteSpace composition instead of provider internals."""
    async def go():
        with MeTTa() as context:
            transport = lambda _operation, _payload: None  # noqa: E731
            with pytest.raises(TypeError) as sync_error:
                context.space(backing=transport)
            async with _aio_surface.AsyncMeTTa(metta=context.self) as am:
                names_before = set(await am.space_names())
                with pytest.raises(TypeError) as async_error:
                    await am.space(backing=transport)
                try:
                    assert str(async_error.value) == str(sync_error.value)
                finally:
                    # The baseline leaked its anonymous mint on this refusal.
                    for name in set(await am.space_names()) - names_before:
                        await am.call(lambda _space, name=name: Space(name).drop())

    asyncio.run(go())


@pytest.mark.parametrize("stage", ["validation", "provider", "journal", "registration"])
def test_a_failed_async_space_construction_leaks_nothing(tmp_path, monkeypatch, stage):
    """Validation, provider failure, and owned acquisition release their resources."""
    from metta import foreign

    async def go():
        with MeTTa() as context:
            async with _aio_surface.AsyncMeTTa(metta=context.self) as am:
                before = set(await am.space_names())
                journal = tmp_path / "failed-construction.jnl"
                if stage == "validation":
                    options = {"journal": journal}
                    expected = TypeError
                    message = "needs schema"
                elif stage == "provider":
                    options = {"backing": object()}
                    expected = TypeError
                    message = "provider answers"
                elif stage == "journal":
                    options = {"journal": journal, "schema": {"edge": -1}}
                    expected = ValueError
                    message = "schema arity"
                else:
                    options = {"journal": journal, "schema": {"edge": 2}}
                    expected = RuntimeError
                    message = "planted provider registration failure"

                def refuse(*_args):
                    msg = "planted provider registration failure"
                    raise RuntimeError(msg)

                try:
                    with monkeypatch.context() as patch:
                        if stage == "registration":
                            # Registration failure after journal attachment has no
                            # public trigger; inject it at the acquisition boundary.
                            patch.setattr(foreign, "register_provider", refuse)
                        with pytest.raises(expected, match=message):
                            await am.space(**options)
                    assert set(await am.space_names()) == before
                    if stage == "validation":
                        assert not journal.exists()
                    if stage == "registration":
                        # An owned provider that failed to attach must release its
                        # exclusive journal claim before the next constructor.
                        recovered = await am.space(journal=journal, schema={"edge": 2})
                        await recovered.drop()
                finally:
                    for name in set(await am.space_names()) - before:
                        await am.call(lambda _space, name=name: Space(name).drop())

    asyncio.run(go())


def test_an_anonymous_async_space_resolves_equations_through_its_home():
    """Home equations are visible while home atoms remain separate."""
    async def go():
        with MeTTa() as context:
            context.self.run("(= (async-context-equation) 41)")
            context.self.add(S.home_fact(S.private))
            async with _aio_surface.AsyncMeTTa(metta=context.self) as am:
                sibling = await am.space()
                try:
                    assert await sibling.eval(S.async_context_equation()) == [41]
                    assert await sibling.match(S.home_fact(V.value)) == []
                finally:
                    await sibling.drop()

    asyncio.run(go())


def test_async_space_provider_backing_attaches_and_remains_borrowed():
    """Provider writes and matches cross the worker; drop does not close a borrow."""
    class Provider(SpaceProvider):
        def __init__(self):
            self.stored = []
            self.closed = False

        def add(self, atom):
            self.stored.append(atom)

        def match(self, _pattern):
            return iter(self.stored)

        def atoms(self):
            return iter(self.stored)

        def close(self):
            self.closed = True

    async def go():
        with MeTTa() as context:
            async with _aio_surface.AsyncMeTTa(metta=context.self) as am:
                provider = Provider()
                attached = await am.space(backing=provider)
                try:
                    await attached.add(S.edge(S.a, S.b))
                    rows = await attached.match(S.edge(V.left, V.right))
                    assert [(row.left, row.right) for row in rows] == [(S.a, S.b)]
                    assert provider.stored == [S.edge(S.a, S.b)]
                finally:
                    await attached.drop()
                assert not provider.closed

    asyncio.run(go())


def test_a_borrowed_context_leaves_its_minted_handle_with_the_caller():
    """A borrowed context does not own the handle returned by its creation door."""
    context = MeTTa()
    home = context.self
    borrowed = home.metta
    assert borrowed is not context
    assert borrowed.self is home
    child = home.metta.space()
    name = str(child.name)
    try:
        borrowed.close()
        assert not child.dropped
        assert name in home.space_names()
        context.close()
        assert context.closed
        assert not child.dropped
        with MeTTa("&self") as observer:
            assert name not in observer.self.space_names()
    finally:
        child.drop()
        context.close()


@pytest.mark.parametrize("name", [None, "&async-grants-affinity"])
def test_async_space_consumes_grants_on_the_callers_loop(name):
    """Capture caller iterables before the worker validates and declares a model."""
    async def go():
        with MeTTa() as context:
            async with _aio_surface.AsyncMeTTa(metta=context.self) as am:
                loop = asyncio.get_running_loop()

                def grants():
                    assert asyncio.get_running_loop() is loop
                    yield from ()

                child = await am.space(name, grants=grants())
                try:
                    assert await child.count() == 0
                finally:
                    await child.drop()

    asyncio.run(go())
