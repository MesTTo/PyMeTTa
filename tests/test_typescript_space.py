"""Purpose: prove the TypeScript space server serves the remote-space
protocol PeTTa attaches to: MeTTa-driven queries, the conformance kit,
threaded and async clients, and the MeTTaScript-backed variant when a
core module is named.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import petta
from petta import S, V, aio, remote, testing
from petta.remote import RemoteSpace

_SERVER_DIR = Path(__file__).resolve().parents[1] / "examples" / "integration" / "typescript_space"
_NODE = shutil.which("node")


def _start(script: str, *extra: str):
    process = subprocess.Popen(
        [_NODE, str(_SERVER_DIR / script), "--port", "0", *extra],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    line = process.stdout.readline()
    try:
        ready = json.loads(line)
        port = ready["listening"]["port"]
    except (ValueError, KeyError, TypeError) as error:
        process.kill()
        msg = f"space server did not report readiness: {line!r}"
        raise RuntimeError(
            msg
        ) from error
    return process, f"http://127.0.0.1:{port}"


def _stop(process) -> None:
    process.send_signal(signal.SIGTERM)
    assert process.wait(timeout=10) == 0, "the server should exit 0 on SIGTERM"


@pytest.fixture
def ts_server():
    if _NODE is None:
        pytest.skip("node is not installed")
    process, url = _start("space_server.js")
    try:
        yield url
    finally:
        _stop(process)


@pytest.fixture
def mettascript_server():
    if _NODE is None:
        pytest.skip("node is not installed")
    core = os.environ.get("PETTA_METTASCRIPT_CORE")
    if not core:
        pytest.skip("PETTA_METTASCRIPT_CORE does not name a @mettascript/core module")
    process, url = _start("mettascript_space_server.js", "--mettascript", core)
    try:
        yield url
    finally:
        _stop(process)


def test_metta_reaches_atoms_held_by_typescript(ts_server):
    m = petta.MeTTa().new_space()
    try:
        remote.attach(m, "&ts-basics", ts_server)
        m.run("!(add-atom &ts-basics (edge a b))")
        m.run("!(add-atom &ts-basics (edge a c))")
        (group,) = m.run("!(collapse (match &ts-basics (edge a $x) $x))")
        assert sorted(str(atom) for atom in group[0]) == ["b", "c"]
        m.run("!(remove-atom &ts-basics (edge $any b))")
        (group,) = m.run("!(collapse (match &ts-basics (edge $x $y) ($x $y)))")
        assert [str(atom) for atom in group[0]] == ["(a c)"]
    finally:
        m.unregister_space("&ts-basics")
        m.drop()


def test_the_conformance_kit_certifies_the_typescript_provider(ts_server):
    provider = RemoteSpace(remote.connect(ts_server), "&self")
    report = testing.check_space_provider(
        provider,
        atoms_to_store=[S.edge(S.a, S.b), S.edge(S.a, S.c), S.fact(S.f(V.x), V.x)],
    )
    assert any("over-approximation holds over" in line for line in report)


def test_threaded_clients_interleave_whole_operations(ts_server):
    m = petta.MeTTa().new_space()
    try:
        remote.attach(m, "&ts-threads", ts_server)

        def add(index: int) -> None:
            m.run(f"!(add-atom &ts-threads (row {index}))")

        def read(_index: int) -> int:
            (group,) = m.run("!(collapse (match &ts-threads (row $n) $n))")
            return len(group[0])

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(add, range(32)))
            counts = list(pool.map(read, range(8)))
        assert all(count == 32 for count in counts)
    finally:
        m.unregister_space("&ts-threads")
        m.drop()


def test_async_clients_reach_the_typescript_space(ts_server):
    async def drive() -> list:
        m = petta.MeTTa().new_space()
        try:
            remote.attach(m, "&async-ts", ts_server)
            async with await aio.connect(metta=m) as engine:
                await engine.run("!(add-atom &async-ts (fact 1))")
                await engine.run("!(add-atom &async-ts (fact 2))")
                waits = [
                    engine.run("!(collapse (match &async-ts (fact $n) $n))")
                    for _ in range(4)
                ]
                return await asyncio.gather(*waits)
        finally:
            m.unregister_space("&async-ts")
            m.drop()

    answers = asyncio.run(drive())
    for (group,) in answers:
        assert sorted(str(atom) for atom in group[0]) == ["1", "2"]


def test_the_wire_round_trip_is_fast_enough_to_matter(ts_server):
    transport = remote.connect(ts_server)
    provider = RemoteSpace(transport, "&self")
    provider.add(S.probe(S.x))
    start = time.perf_counter()
    rounds = 200
    for _ in range(rounds):
        assert list(provider.match(S.probe(V.q)))
    elapsed = time.perf_counter() - start
    per_op = elapsed / rounds
    # localhost HTTP round trips run in the hundreds of microseconds; a
    # second per operation would mean the transport is broken, not slow.
    assert per_op < 0.25, f"a wire match took {per_op:.3f}s"


def test_mettascript_holds_the_atoms_when_named(mettascript_server):
    m = petta.MeTTa().new_space()
    try:
        remote.attach(m, "&ms", mettascript_server)
        m.run("!(add-atom &ms (edge a b))")
        m.run("!(add-atom &ms (edge a c))")
        (group,) = m.run("!(collapse (match &ms (edge a $x) $x))")
        assert sorted(str(atom) for atom in group[0]) == ["b", "c"]
        provider = RemoteSpace(remote.connect(mettascript_server), "&self")
        report = testing.check_space_provider(
            provider,
            atoms_to_store=[S.pin(S.p, S.q), S.pin(S.p, V.tail)],
        )
        assert any("over-approximation holds over" in line for line in report)
    finally:
        m.unregister_space("&ms")
        m.drop()


def test_a_batch_crosses_in_one_request(ts_server):
    operations: list[str] = []
    inner = remote.connect(ts_server)

    def counting(operation, payload):
        operations.append(operation)
        return inner(operation, payload)

    m = petta.MeTTa().new_space()
    try:
        remote.attach(m, "&ts-batch", counting)
        m.space("&ts-batch").add(S.row(1), S.row(2), S.row(3))
        assert operations.count("add_many") == 1
        assert operations.count("add") == 0
        (group,) = m.run("!(collapse (match &ts-batch (row $n) $n))")
        assert sorted(str(atom) for atom in group[0]) == ["1", "2", "3"]
    finally:
        m.unregister_space("&ts-batch")
        m.drop()


class TestTheReferenceServerSpeaksTheProtocol(testing.GatewayComplianceSuite):
    """The zero-dependency server, certified by the protocol's own suite."""

    @pytest.fixture()
    def gateway_url(self, ts_server):
        return ts_server


class TestTheMettascriptServerSpeaksTheProtocol(testing.GatewayComplianceSuite):
    """Two MeTTa engines, one wire contract, one suite certifying it."""

    @pytest.fixture()
    def gateway_url(self, mettascript_server):
        return mettascript_server
