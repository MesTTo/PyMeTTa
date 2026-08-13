"""Purpose: shared spaces over Redis. One process's writes are another
process's facts under the same attach, joins mix shared and native
facts through the engine, clear() deletes the shared set through the
foreign-clear hook, and subscriptions fire across processes: a write in
one process lands in another's Python callback through the per-space
channel, remote events asynchronous, each write heard once per process.
Skips whole when docker cannot serve an ephemeral Redis.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import os
import subprocess
import sys
import time
import uuid

import pytest

from petta import S, V, expr

_CONTAINER = f"petta-redis-test-{uuid.uuid4().hex[:12]}"


def _docker_ready() -> bool:
    try:
        return (
            subprocess.run(
                ["docker", "info"], capture_output=True, timeout=20
            ).returncode
            == 0
        )
    except (OSError, subprocess.TimeoutExpired):
        return False


pytestmark = pytest.mark.skipif(
    not _docker_ready(), reason="docker is not available for ephemeral Redis"
)


@pytest.fixture(scope="module")
def redis_address(metta):
    run = subprocess.run(
        ["docker", "run", "-d", "--rm", "--name", _CONTAINER,
         "-p", "127.0.0.1::6379", "redis:7.2.3-alpine"],
        capture_output=True, text=True, timeout=120,
    )
    assert run.returncode == 0, run.stderr
    try:
        port = subprocess.run(
            [
                "docker",
                "inspect",
                "--format",
                '{{(index (index .NetworkSettings.Ports "6379/tcp") 0).HostPort}}',
                _CONTAINER,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert port.returncode == 0, port.stderr
        host_port = port.stdout.strip()
        assert host_port.isdigit(), port.stdout
        time.sleep(0.5)
        metta.run("!(import! &self (library lib_redis))")
        yield f"localhost:{host_port}"
    finally:
        subprocess.run(
            ["docker", "rm", "-f", _CONTAINER],
            capture_output=True,
            timeout=30,
            check=False,
        )


@pytest.fixture()
def shared(metta, redis_address):
    metta.run(f'!(redis-attach &shared-test "{redis_address}")')
    space = metta.space("&shared-test")
    space.clear()
    yield space
    space.clear()
    metta.run("!(redis-detach &shared-test)")


def _other_process(redis_address: str, program: str) -> str:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    source = (
        "from petta import MeTTa, S\n"
        "m = MeTTa()\n"
        "m.run('!(import! &self (library lib_redis))')\n"
        f"m.run('!(redis-attach &shared-test \"{redis_address}\")')\n"
        + program
    )
    done = subprocess.run(
        [sys.executable, "-c", source],
        capture_output=True, text=True, timeout=180, env=env,
    )
    assert done.returncode == 0, done.stderr
    return done.stdout


def test_shared_space_serves_one_process(shared):
    shared.add(S.stock(S.widget, 5), S.stock(S.gadget, 7))
    rows = shared.query(S.stock(V.item, V.n))
    assert sorted(str(row.item) for row in rows) == ["gadget", "widget"]
    assert shared.count() == 2
    assert shared.remove(S.stock(S.widget, 5)) is True
    assert [str(atom) for atom in shared.atoms()] == ["(stock gadget 7)"]


def test_writes_in_another_process_are_this_processs_facts(shared, redis_address):
    _other_process(
        redis_address,
        "m.space('&shared-test').add(S.remote(S.fact, 1), S.remote(S.fact, 2))\n",
    )
    rows = shared.query(S.remote(S.fact, V.n))
    assert sorted(int(row.n.value) for row in rows) == [1, 2]


def test_shared_facts_join_native_facts(shared, metta):
    shared.add(S.lives(S.ann, S.paris))
    metta.add(S.capital(S.paris, S.france))
    try:
        groups = metta.run(
            "!(match &shared-test (lives $who $city)"
            " (match &self (capital $city $land) ($who $land)))"
        )
        assert groups == [[expr(S.ann, S.france)]]
    finally:
        metta.remove(S.capital(S.paris, S.france))


def test_subscriptions_fire_across_processes(shared, redis_address):
    seen = []
    subscription = shared.subscribe(
        S.alert(V.level), lambda event: seen.append(event)
    )
    try:
        _other_process(
            redis_address,
            "m.space('&shared-test').add(S.alert(S.red), S.other(S.noise))\n",
        )
        deadline = time.monotonic() + 10.0
        while not seen and time.monotonic() < deadline:
            time.sleep(0.05)
        assert len(seen) == 1
        assert seen[0].bindings["level"] == S.red
    finally:
        subscription.cancel()


def test_local_writes_fire_subscriptions_exactly_once(shared):
    seen = []
    subscription = shared.subscribe(
        S.local(V.x), lambda event: seen.append(event)
    )
    try:
        shared.add(S.local(S.one))
        time.sleep(0.5)  # the echo must NOT double-fire through the channel
        assert len(seen) == 1
    finally:
        subscription.cancel()
