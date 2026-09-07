"""Purpose: pin mutation replay and explicit uncertainty after lost replies.

Guarantees:
  - a lost reply can be retried without executing the mutation twice
    [tested: test_lost_mutation_reply_has_a_safe_retry,
    test_expired_reentrant_mutation_cannot_resurrect_its_reservation; commit=ec64336e16ebb0299f9794d277daaee3cf234493]
"""

from concurrent.futures import ThreadPoolExecutor

import pytest

from metta import S, _json, remote
from metta import _network as network
from metta.errors import MettaError


@pytest.fixture()
def metta(metta):
    """Keep every mutation scenario in its own store."""
    with metta._new_space() as space:
        yield space


@pytest.mark.parametrize("operation", ["add", "add_many", "remove"])
def test_lost_mutation_reply_has_a_safe_retry(metta, monkeypatch, operation):
    """Discard a real HTTP response after the server has applied the write."""
    atom = S.replay_once(1)
    if operation == "remove":
        metta.add(atom)
    original = network.HTTPEndpoint.request
    lost = []

    def lose_reply(endpoint, method, path, **options):
        reply = original(endpoint, method, path, **options)
        if method == "POST" and path == operation and not lost:
            lost.append(reply)
            msg = "injected response loss after commit"
            raise OSError(msg)
        return reply

    with remote.serve(metta) as server:
        transport = remote.connect(server.url)
        space = remote.RemoteSpace(transport, metta.name)
        monkeypatch.setattr(network.HTTPEndpoint, "request", lose_reply)
        with pytest.raises(MettaError) as failure:
            getattr(space, operation)([atom] if operation == "add_many" else atom)
        assert getattr(failure.value, "outcome", None) == "unknown", (
            "a lost mutation reply must expose outcome='unknown'"
        )
        expected = {"removed": True} if operation == "remove" else {
            "added": 1 if operation == "add_many" else True
        }
        assert failure.value.retry() == expected, "retry must replay the original answer"
        assert failure.value.retry() == expected, "repeated recovery must remain idempotent"
        assert list(space.atoms()) == ([] if operation == "remove" else [atom]), (
            "retry must not apply the mutation twice"
        )


def test_replay_refuses_parameter_changes_expiry_and_restart(metta, monkeypatch):
    """An old key never turns into a new mutation after pruning or restart."""
    gateway = remote.Gateway(metta)
    clock = remote.time.monotonic()
    monkeypatch.setattr(remote.time, "monotonic", lambda: clock)
    token = {**gateway.health()["idempotency"], "key": "one-operation"}
    payload = {"space": metta.name, "atom": S.replay_guard(1).to_wire(), "idempotency": token}
    assert gateway("add", payload) == {"added": True}
    changed = {**payload, "atom": S.replay_guard(2).to_wire()}
    with pytest.raises(MettaError, match="different parameters"):
        gateway("add", changed)
    restarted = remote.Gateway(metta)
    with pytest.raises(MettaError, match="gateway instance changed"):
        restarted("add", payload)
    clock += 301
    with pytest.raises(MettaError, match="expired"):
        gateway("add", payload)
    assert metta.atoms() == [S.replay_guard(1)]


def test_a_failed_provider_mutation_is_not_executed_again(metta):
    """A provider that raises after a side effect remains outcome-unknown."""
    calls = []

    class FailingSpace:
        name = metta.name

        def add(self, _atom):
            calls.append(1)
            msg = "injected provider failure after side effect"
            raise RuntimeError(msg)

    gateway = remote.Gateway(FailingSpace())
    token = {"scope": gateway._mutation_scope, "expires": remote.time.monotonic() + 10,
             "key": "partial"}
    payload = {"atom": S.partial(1).to_wire(), "idempotency": token}
    assert gateway("add", payload)["outcome"] == "unknown"
    assert gateway("add", payload)["outcome"] == "unknown"
    assert calls == [1], "a partial provider failure must not be executed twice"


def test_replay_capacity_refuses_before_mutation_and_recovers_after_expiry(metta, monkeypatch):
    """The finite ledger cannot evict a live key to admit a new mutation."""
    gateway = remote.Gateway(metta, mutation_limit=1, mutation_ttl=10)
    clock = remote.time.monotonic()
    monkeypatch.setattr(remote.time, "monotonic", lambda: clock)

    def request(key):
        return {"atom": S.capacity(key).to_wire(), "idempotency": {
            **gateway.health()["idempotency"], "key": key,
        }}

    first = request("first")
    assert gateway("add", first) == {"added": True}
    with pytest.raises(MettaError, match="capacity reached"):
        gateway("add", request("second"))
    assert gateway("add", first) == {"added": True}
    clock += 11
    assert gateway("add", request("second")) == {"added": True}
    assert len(metta) == 2


def test_an_unkeyed_transport_exposes_uncertainty_without_retrying():
    """A custom transport must advertise replay before recovery can send."""
    calls = []

    def transport(operation, _payload):
        calls.append(operation)
        msg = "injected unkeyed response loss"
        raise OSError(msg)

    with pytest.raises(remote.OutcomeUnknown) as failure:
        remote.RemoteSpace(transport).add(S.unkeyed(1))
    with pytest.raises(MettaError, match="no negotiated idempotency key"):
        failure.value.retry()
    assert calls == ["add"]


def test_explicit_client_key_is_preserved_over_http(metta):
    """A caller-managed key is reused verbatim instead of replaced per call."""
    with remote.serve(metta) as server:
        transport = remote.connect(server.url)
        token = {**transport.health()["idempotency"], "key": "caller-managed-key"}
        request = {"space": metta.name, "atom": S.explicit_key(1).to_wire(),
                   "idempotency": token}
        assert transport("add", request) == {"added": True}
        assert transport("add", request) == {"added": True}
        assert metta.atoms() == [S.explicit_key(1)], "the supplied key must identify one write"


@pytest.mark.parametrize(("status", "body"), [
    (500, b'{"error":"worker failed"}'),
    (200, b'not JSON'),
    (200, b'{}'),
])
def test_legacy_http_mutation_cannot_claim_failure_after_an_uncertain_reply(monkeypatch, status, body):
    """Revision 3 peers without replay metadata still expose an unknown outcome."""
    calls = []

    def request(_endpoint, method, _path, **_options):
        calls.append(method)
        if method == "GET":
            return network.Response(
                200, "OK", _json.dumps({"ok": True, "atoms": 0, "protocol": 3}), {}
            )
        return network.Response(status, "injected reply", body, {})

    monkeypatch.setattr(network.HTTPEndpoint, "request", request)
    with pytest.raises(remote.OutcomeUnknown) as failure:
        remote.RemoteSpace(remote.connect("http://example.test")).add(S.legacy)
    with pytest.raises(MettaError, match="no negotiated idempotency key"):
        failure.value.retry()
    assert calls == ["GET", "POST"], "unkeyed recovery must not send a second mutation"


def test_repeated_reply_loss_retains_the_original_recovery_key(metta):
    """Each uncertainty exception can recover the same first mutation."""
    gateway = remote.Gateway(metta)
    deliveries = []

    class LosingTransport:
        health = gateway.health

        def __call__(self, operation, payload):
            answer = gateway(operation, payload)
            deliveries.append(payload)
            if len(deliveries) <= 2:
                msg = "injected repeated response loss"
                raise OSError(msg)
            return answer

    with pytest.raises(remote.OutcomeUnknown) as first:
        remote.RemoteSpace(LosingTransport(), metta.name).add(S.repeated_loss)
    with pytest.raises(remote.OutcomeUnknown) as second:
        first.value.retry()
    assert second.value.retry() == {"added": True}
    assert deliveries[0] == deliveries[1] == deliveries[2], "every recovery must reuse the request"
    assert metta.atoms() == [S.repeated_loss]


def test_mutation_outcome_survives_engine_provider_boundary(metta):
    """The exception's recovery callable survives an attached provider's write."""
    failure = remote.OutcomeUnknown("add", lambda: {"added": True})

    def transport(_operation, _payload):
        raise failure

    with metta._new_space() as attached:
        metta._register_space(remote.RemoteSpace(transport), attached.name)
        with pytest.raises(remote.OutcomeUnknown) as caught:
            metta.run(f"!(add-atom {attached.name} (edge a b))")
        assert caught.value is failure, "the engine must preserve the original unknown outcome"
        assert caught.value.retry() == {"added": True}


@pytest.mark.parametrize("deadline", [False, True])
def test_worker_failure_cannot_claim_a_mutation_was_not_applied(metta, monkeypatch, deadline):
    """A worker can fail while reporting an already applied request."""
    original = remote._RemoteWorker.call

    def fail(worker, operation, payload, *, timeout):
        result = original(worker, operation, payload, timeout=timeout)
        if operation == "add":
            if deadline:
                msg = "injected worker deadline after mutation"
                raise TimeoutError(msg)
            return "error", "injected worker failure after mutation"
        return result

    with remote.serve(metta) as server:
        monkeypatch.setattr(remote._RemoteWorker, "call", fail)
        space = remote.RemoteSpace(remote.connect(server.url), metta.name)
        with pytest.raises(remote.OutcomeUnknown) as failure:
            space.add(S.worker_outcome)
        monkeypatch.setattr(remote._RemoteWorker, "call", original)
        assert failure.value.retry() == {"added": True}
        assert metta.atoms() == [S.worker_outcome], "worker failure recovery must not duplicate effects"


def test_concurrent_http_replays_share_one_mutation(metta):
    """Independent connections with the same key cannot race past admission."""
    with remote.serve(metta) as server:
        token = {**remote.connect(server.url).health()["idempotency"], "key": "concurrent"}
        request = {"space": metta.name, "atom": S.concurrent_replay.to_wire(),
                   "idempotency": token}

        def add(_index):
            return remote.connect(server.url)("add", request)

        with ThreadPoolExecutor(max_workers=4) as clients:
            assert list(clients.map(add, range(8))) == [{"added": True}] * 8
        assert metta.atoms() == [S.concurrent_replay], "concurrent replays must execute once"


def test_expired_reentrant_mutation_cannot_resurrect_its_reservation(monkeypatch):
    """Late completion must not restore an expired slot over newer admission."""
    clock = [100.0]
    calls = []

    class Store:
        name = "&reentrant-replay"

        def __len__(self):
            return len(calls)

        def add(self, atom):
            calls.append(atom)
            if len(calls) == 1:
                clock[0] += 11
                gateway("add", payload("nested"))

    gateway = remote.Gateway(Store(), mutation_limit=1, mutation_ttl=10)
    monkeypatch.setattr(remote.time, "monotonic", lambda: clock[0])

    def payload(key):
        return {"atom": S[key].to_wire(), "idempotency": {
            **gateway.health()["idempotency"], "key": key,
        }}

    assert gateway("add", payload("outer")) == {"added": True}
    clock[0] += 11
    try:
        result = gateway("add", payload("later"))
    except MettaError as failure:
        result = str(failure)
    assert result == {"added": True}, (
        "expiry during a reentrant write must not resurrect a pruned reservation"
    )
    assert calls == [S.outer, S.nested, S.later]
