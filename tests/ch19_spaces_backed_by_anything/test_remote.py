"""Purpose: verify the remote transport's boundary, authorization, and lifecycle.
Guarantees:
  - metta installs a NullHandler and reports transport lifecycle events only
    through configured logging [tested test_library_logging_is_opt_in,
    test_remote_transport_logs_operation_without_payload]
  - server startup and shutdown expose attached-engine lifecycle failures
    [tested test_remote_serve_reports_worker_startup_failure,
    test_remote_close_waits_for_worker_detach]
  - malformed HTTP request framing and JSON receive explicit client errors
    [tested test_remote_server_rejects_malformed_request_bodies]
  - the ask/next/stop lifecycle computes what a client asks for and no
    more, and its server-side state is bounded and owned [tested
    test_two_answers_cross_the_wire_without_the_third_being_computed,
    test_a_served_provider_is_pulled_per_answer_not_drained,
    test_an_idle_cursor_is_released,
    test_a_gateway_refuses_more_cursors_than_it_holds,
    test_closing_the_server_releases_open_cursors]
  - lazy enumeration measurements vary only the atom count in one space and
    use the minimum of three samples [tested:
    test_two_answers_cross_the_wire_without_the_third_being_computed;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import logging
import threading
import time
from http.client import HTTPConnection, HTTPException

import janus_swi
import pytest

import metta
import metta._network as network
from metta import S, remote
from metta import testing as remote_testing
from metta.errors import MettaError
from metta.foreign import SpaceProvider


def test_library_logging_is_opt_in():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert any(
        isinstance(handler, logging.NullHandler)
        for handler in logging.getLogger("metta").handlers
    )


def test_remote_transport_logs_operation_without_payload(monkeypatch, caplog):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    transport = remote.connect("http://example.test/api")

    def request(*args, **kwargs):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        return 200, "OK", b'{"atoms": []}'

    monkeypatch.setattr(network.HTTPEndpoint, "request", request)
    sensitive_value = "payload-must-not-be-logged"
    with caplog.at_level(logging.DEBUG, logger="metta.remote"):
        assert transport("match", {"value": sensitive_value}) == {"atoms": []}

    text = caplog.text
    assert "sending remote engine operation match" in text
    assert "answered with HTTP 200" in text
    assert sensitive_value not in text


def test_bearer_token_uses_constant_time_comparison(monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    calls = []
    policies = []

    def compare(supplied, expected):
        calls.append((supplied, expected))
        return supplied == expected

    def authorize(request):
        policies.append(request)
        return True

    def asking(headers):
        return remote.Request("atoms", "&self", headers)

    monkeypatch.setattr(remote.hmac, "compare_digest", compare)

    matching = {"authorization": "Bearer secret"}
    assert remote._is_authorized(asking(matching), "secret", authorize)
    assert not remote._is_authorized(
        asking({"authorization": "Bearer wrong"}), "secret", authorize
    )
    assert not remote._is_authorized(asking({}), "secret", authorize)

    assert calls == [
        ("Bearer secret", "Bearer secret"),
        ("Bearer wrong", "Bearer secret"),
        ("", "Bearer secret"),
    ]
    # The policy hook runs only behind a good credential, and it is told
    # what is being asked for, not only who is asking.
    assert policies == [remote.Request("atoms", "&self", matching)]


@pytest.mark.parametrize(
    ("url", "scheme"),
    [
        ("file:///etc/passwd", "file"),
        ("ftp://example.test/data", "ftp"),
        ("data:text/plain,secret", "data"),
        ("example.test/api", "<missing>"),
    ],
)
def test_remote_connect_refuses_non_http_urls(url, scheme):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(MettaError, match=scheme):
        remote.connect(url)


@pytest.mark.parametrize(
    "headers",
    [None, {"Authorization": "Basic c2VjcmV0"}],
)
def test_remote_connect_refuses_credentials_over_http(headers):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    options = {"token": "secret"} if headers is None else {"headers": headers}
    with pytest.raises(MettaError, match="credentials require an https URL"):
        remote.connect("http://example.test", **options)


def test_remote_connect_accepts_http_and_https_urls():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert callable(remote.connect("http://example.test/api/"))
    assert callable(remote.connect("https://example.test/api/", token="secret"))


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan"), "invalid"])
def test_network_clients_refuse_invalid_timeouts(timeout):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match="timeout"):
        remote.connect("http://example.test", timeout=timeout)


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("http:///api", "no host"),
        ("https://example.test:invalid", "invalid"),
        ("https://example.test/api?token=value", "query or fragment"),
        ("https://example.test/api#section", "query or fragment"),
    ],
)
def test_remote_connect_refuses_malformed_base_urls(url, message):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(MettaError, match=message):
        remote.connect(url)


def test_remote_connect_refuses_embedded_credentials_without_echoing_them():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(MettaError, match="embedded credentials") as failure:
        remote.connect("https://operator:top-secret@example.test")
    assert "top-secret" not in str(failure.value)


def test_remote_serve_reports_worker_startup_failure(metta, monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def fail_attach():
        msg = "injected remote attach failure"
        raise RuntimeError(msg)

    monkeypatch.setattr(janus_swi, "attach_engine", fail_attach)

    with pytest.raises(MettaError, match="injected remote attach failure"):
        remote.serve(metta)


def test_remote_close_waits_for_worker_detach(metta, monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    original = janus_swi.detach_engine
    detach_started = threading.Event()
    release_detach = threading.Event()
    detached = threading.Event()

    def delayed_detach():
        detach_started.set()
        release_detach.wait(2.0)
        original()
        detached.set()

    monkeypatch.setattr(janus_swi, "detach_engine", delayed_detach)
    server = remote.serve(metta)
    failures = []

    def close():
        try:
            server.close(timeout=2.0)
        except BaseException as exc:
            failures.append(exc)

    closer = threading.Thread(target=close)
    closer.start()
    try:
        assert detach_started.wait(2.0)
        assert closer.is_alive()
    finally:
        release_detach.set()
        closer.join(2.0)

    assert not failures
    assert detached.is_set()
    assert not closer.is_alive()
    assert not server._worker.thread.is_alive()
    server.close()


@pytest.mark.parametrize(
    ("headers", "body", "status", "detail"),
    [
        ({}, b"", 411, "content-length is required"),
        ({"Content-Length": "nope"}, b"", 400, "decimal digits"),
        ({"Content-Length": "-1"}, b"", 400, "decimal digits"),
        (
            {"Content-Length": str(remote._MAX_REQUEST_BYTES + 1)},
            b"",
            413,
            "exceeds",
        ),
        ({"Content-Length": "1"}, b"[", 400, "not valid JSON"),
        ({"Content-Length": "2"}, b"[]", 400, "JSON object"),
        (
            {"Transfer-Encoding": "chunked", "Content-Length": "2"},
            b"{}",
            400,
            "transfer-encoding",
        ),
    ],
)
def test_remote_server_rejects_malformed_request_bodies(  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta,
    headers,
    body,
    status,
    detail,
):
    server = remote.serve(metta)
    connection = HTTPConnection(server.host, server.port, timeout=2.0)
    try:
        connection.putrequest("POST", "/atoms")
        for name, value in headers.items():
            connection.putheader(name, value)
        connection.endheaders(body)
        response = connection.getresponse()
        assert response.status == status
        assert detail.encode() in response.read()
    finally:
        connection.close()
        server.close()


def test_authorize_can_serve_a_space_read_only(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The hook saw the headers alone, so it could not tell a read from a
    # write and read-only was inexpressible.
    served = metta._new_space()
    served.add(S.stock(S.apple))
    name = served.name
    seen = []

    def read_only(request):
        seen.append((request.operation, request.space))
        return request.operation in ("atoms", "match")

    server = remote.serve(metta, spaces=[name], authorize=read_only)
    try:
        transport = remote.connect(server.url)
        space = remote.RemoteSpace(transport, name)
        assert list(space.atoms()) == [S.stock(S.apple)]
        with pytest.raises(MettaError, match="not authorized"):
            space.add(S.stock(S.pear))
        assert list(space.atoms()) == [S.stock(S.apple)]
    finally:
        server.close()
        served.drop()

    assert seen == [("atoms", name), ("add", name), ("atoms", name)]


@pytest.mark.parametrize(
    ("read_fails", "oversized"),
    [(False, False), (True, False), (False, True)],
)
def test_http_endpoint_closes_transport_resources(monkeypatch, read_fails, oversized):  # noqa: D103  -- test_http_endpoint_closes_transport_resources keeps the transport failure matrix together so its branches share one state; pytest discovers or injects this callable; its descriptive name states the contract
    class Response:
        status = 200
        reason = "OK"
        closed = False

        def __init__(self):
            self._body = b"12345" if oversized else b"{}"
            self._offset = 0

        def getheader(self, _name):
            return None

        def read(self, amount):
            if read_fails:
                msg = "injected read failure"
                raise OSError(msg)
            chunk = self._body[self._offset : self._offset + amount]
            self._offset += len(chunk)
            return chunk

        def close(self):
            self.closed = True

    class Connection:
        closed = False

        def __init__(self):
            self.response = Response()

        def request(self, method, target, *, body, headers):
            assert (method, target, body, headers) == (
                "GET",
                "/api/probe",
                None,
                {},
            )

        def getresponse(self):
            return self.response

        def close(self):
            self.closed = True

    connection = Connection()
    monkeypatch.setattr(network, "HTTPConnection", lambda *_args, **_kwargs: connection)
    if oversized:
        monkeypatch.setattr(network, "MAX_HTTP_RESPONSE_BYTES", 4)
    endpoint = network.HTTPEndpoint(
        "http://example.test/api",
        subject="test",
        error_type=MettaError,
    )

    if read_fails:
        with pytest.raises(OSError, match="injected read failure"):
            endpoint.request("GET", "/probe", timeout=1.0)
    elif oversized:
        with pytest.raises(HTTPException, match="response body exceeds"):
            endpoint.request("GET", "/probe", timeout=1.0)
    else:
        assert endpoint.request("GET", "/probe", timeout=1.0) == (
            200,
            "OK",
            b"{}",
        )

    assert connection.response.closed
    assert connection.closed


# ------------------------------------------------- the wire projection (J4)


def test_health_advertises_the_projection(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    server = remote.serve(metta)
    try:
        transport = remote.connect(server.url)
        body = transport.health()
        assert body["ok"] is True and body["protocol"] == 3
        assert {"match", "enumerate", "add", "remove", "stream"} <= set(
            body["capabilities"]
        )
        assert body["bound"] is True
        space = remote.RemoteSpace(transport)
        advertised = space.server_capabilities()
        assert advertised["bound"] is True and advertised["protocol"] == 3
    finally:
        server.close()


def test_server_capabilities_refuses_a_health_less_transport():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space = remote.RemoteSpace(lambda _operation, _payload: {"atoms": []})
    with pytest.raises(MettaError, match="health"):
        space.server_capabilities()


def test_bound_crosses_and_is_honored_exactly(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    scratch = metta._new_space()
    scratch.add(S.re_edge(S.a, S.b), S.re_edge(S.a, S.c), S.re_edge(S.a, S.d))
    server = remote.serve(metta)
    try:
        transport = remote.connect(server.url)
        space = remote.RemoteSpace(transport, scratch.name)
        pattern = metta.parse("(re-edge a $x)")
        assert len(list(space.match(pattern, limit=2))) == 2
        assert len(list(space.match(pattern))) == 3
        assert list(space.match(pattern, limit=0)) == []
        with pytest.raises(MettaError, match="bound"):
            list(space.match(pattern, limit=-1))
    finally:
        server.close()


def test_the_seam_pushes_the_callers_bound_onto_the_wire():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # No server at all: a capturing transport proves the engine-side
    # bounded query reaches RemoteSpace.match with the limit, and the
    # limit leaves as the wire's bound field.
    sent = []

    def capturing(operation, payload):
        sent.append((operation, payload))
        return {"atoms": []}

    space = remote.RemoteSpace(capturing)
    list(space.match(metta.parse("(re_probe $x)"), limit=5))
    assert sent[-1][1]["bound"] == 5
    list(space.match(metta.parse("(re_probe $x)")))
    assert "bound" not in sent[-1][1]


def test_add_many_lands_through_our_own_server(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The client always sent add_many; the server refused it as unknown
    # until the projection work, so bulk adds against serve() failed.
    scratch = metta._new_space()
    server = remote.serve(metta)
    try:
        space = remote.RemoteSpace(remote.connect(server.url), scratch.name)
        space.add_many([metta.parse(f"(re_bulk {n})") for n in range(4)])
        assert len(list(space.match(metta.parse("(re_bulk $n)")))) == 4
    finally:
        server.close()


# -------------------------------------------- lazy answers on the wire (P4.25)


def _live_engines(m) -> int:
    """How many Prolog engines exist right now.

    An open wire cursor holds exactly one, so the delta across a call is
    the direct oracle for whether a gateway released what it owns, rather
    than an inference about it.
    """
    return m.runtime.once("aggregate_all(count, current_engine(_), N)")["N"]


class _CountingProvider(SpaceProvider):
    """A served space that says how many candidates it was asked for."""

    def __init__(self, size: int) -> None:
        self.stored = [metta.parse(f"(re_counted {n})") for n in range(size)]
        self.yielded = 0

    def match(self, pattern):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
        for atom in self.stored:
            self.yielded += 1
            yield atom

    def atoms(self):
        return iter(self.stored)


def test_two_answers_cross_the_wire_without_the_third_being_computed(metta):
    """The lifecycle's whole claim, on the engine's own counters.

    Two answers are taken over real HTTP from a ten-atom enumeration and
    from a ten-thousand-atom one, and the SERVING engine spends the same
    inferences on both: what the client did not ask for is not computed,
    so the cost cannot grow with the size of what was left. The eager
    door is measured beside it and grows with the space, which is the gap
    the lifecycle exists to close.

    The same space grows from ten atoms to ten thousand, so space identity
    and module setup cannot masquerade as size-dependent work. Each point is
    the minimum of three samples. `statistics(inferences)` is process-wide in
    SWI, so the server's own worker thread is what these numbers count.

    The two comparisons AGAINST the eager door are counted in atoms rather
    than inferences, and the difference is not cosmetic. Until 2026-08-28 they
    read `lazy[10_000] < eager[10]` and `eager[10_000] > 100 * lazy[10_000]`,
    and what made those true was the client decoding the reply with
    `library(json)`: an eager reply carrying ten thousand atoms cost 1,490,407
    inferences to READ where two atoms cost 1,250. The C codec in
    engine/json_codec.c moved that reading out of the inference counter --
    the same run now reads 77 for both eager sizes -- so the counter stopped
    seeing reply volume at all and both comparisons went vacuous, then red.
    Reply volume is what they were always about, so it is counted directly and
    no codec can blind it again. The claim measured in inferences is the one
    the counter can still see: two answers cost the same whatever is behind
    them.
    """
    server = remote.serve(metta)
    scratch = metta._new_space()
    lazy, eager, crossings, sent, drained = {}, {}, {}, {}, {}
    try:
        calls: list[str] = []
        atoms_seen: list[int] = []
        inner = remote.connect(server.url)

        def counting(operation, payload, _inner=inner, _calls=calls,
                     _seen=atoms_seen):
            _calls.append(operation)
            answer = _inner(operation, payload)
            _seen.append(len(answer.get("atoms", ())))
            return answer

        space = remote.RemoteSpace(counting, scratch.name)
        pattern = metta.parse("(re_lazy $n)")
        populated = 0
        for size in (10, 10_000):
            scratch.add(
                *[
                    metta.parse(f"(re_lazy {number})")
                    for number in range(populated, size)
                ]
            )
            populated = size
            # Warm the path so first-call compilation and index realisation
            # sit outside every sample.
            with space.stream(pattern, batch=1) as warm:
                next(warm)
            lazy_samples = []
            crossing_samples = []
            eager_samples = []
            sent_samples = []
            drained_samples = []
            for _ in range(3):
                calls.clear()
                atoms_seen.clear()
                with metta.stats() as counted, space.stream(
                    pattern, batch=1
                ) as answers:
                    taken = [next(answers), next(answers)]
                assert [str(atom) for atom in taken] == [
                    "(re_lazy 0)",
                    "(re_lazy 1)",
                ]
                lazy_samples.append(counted.inferences)
                crossing_samples.append(list(calls))
                sent_samples.append(sum(atoms_seen))
                atoms_seen.clear()
                with metta.stats() as counted_all:
                    assert len(list(space.match(pattern))) == size
                eager_samples.append(counted_all.inferences)
                drained_samples.append(sum(atoms_seen))
            lazy[size] = min(lazy_samples)
            eager[size] = min(eager_samples)
            crossings[size] = crossing_samples
            sent[size] = min(sent_samples)
            drained[size] = min(drained_samples)
    finally:
        server.close()
        scratch.drop()

    # One ask, one next, one stop: the client took two answers and told the
    # server it was done, and nothing else crossed.
    expected_crossings = [["ask", "next", "stop"]] * 3
    assert crossings[10] == crossings[10_000] == expected_crossings
    # The cost of two answers does not grow with the enumeration behind
    # them, which is only possible if the rest was never computed.
    assert lazy[10_000] <= lazy[10], (
        f"two answers cost {lazy[10_000]} inferences over 10,000 atoms and "
        f"{lazy[10]} over 10; the lifecycle computed something the client "
        f"never asked for"
    )
    # Taking two of ten thousand carries less than taking all ten of ten.
    assert sent[10_000] < drained[10], (
        f"two answers of 10,000 carried {sent[10_000]} atoms and all ten of "
        f"ten carried {drained[10]}"
    )
    # And the eager door's volume grows with the space where the lazy door's
    # does not, which is the gap the lifecycle exists to close.
    assert drained[10_000] > 100 * sent[10_000], (
        f"the eager door carried {drained[10_000]} atoms over 10,000 against "
        f"the lazy door's {sent[10_000]}"
    )
    assert sent[10] == sent[10_000] == 2


def test_a_served_provider_is_pulled_per_answer_not_drained(metta):
    """The same claim observed at the far end instead of inferred.

    The served space counts the candidates it is asked for, so taking two
    answers over the wire says in one number how much of a ten-thousand
    answer enumeration the serving side computed. Measured 2026-08-20:
    three, the extra one being janus's `py_iter` reading a candidate
    ahead, which the in-process cursor pays identically; the eager door
    over the same space pulls every one.
    """
    provider = _CountingProvider(10_000)
    metta._register_space(provider, "&re-counted")
    server = remote.serve(metta)
    try:
        space = remote.RemoteSpace(remote.connect(server.url), "&re-counted")
        pattern = metta.parse("(re_counted $n)")
        with space.stream(pattern, batch=1) as warm:
            next(warm)
        provider.yielded = 0
        with space.stream(pattern, batch=1) as answers:
            assert len([next(answers), next(answers)]) == 2
        pulled = provider.yielded
        provider.yielded = 0
        assert len(list(space.match(pattern))) == 10_000
        drained = provider.yielded
    finally:
        server.close()
        metta._unregister_space("&re-counted")
    assert pulled < 10, f"two answers pulled {pulled} candidates of 10,000"
    assert drained >= 10_000


def test_the_lifecycle_answers_exactly_what_the_eager_door_answers(metta):
    """Chunking is a CHUNK and not a cut: every answer still crosses,
    whatever batch carries it.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    scratch = metta._new_space()
    scratch.add(*[metta.parse(f"(re_chunk {n})") for n in range(7)])
    server = remote.serve(metta)
    try:
        space = remote.RemoteSpace(remote.connect(server.url), scratch.name)
        pattern = metta.parse("(re_chunk $n)")
        whole = sorted(str(a) for a in space.match(pattern))
        assert len(whole) == 7
        for batch in (1, 2, 7, 100):
            with space.stream(pattern, batch=batch) as answers:
                assert sorted(str(a) for a in answers) == whole
        # A bound is the cut, and it is honored exactly.
        with space.stream(pattern, batch=3, limit=4) as answers:
            assert len(list(answers)) == 4
        with space.stream(pattern, batch=3, limit=0) as answers:
            assert list(answers) == []
        # The chunk may change between pulls, pengines' next(Count): the
        # batch a request names is the batch that request gets.
        transport = remote.connect(server.url)
        opened = transport(
            "ask",
            {"space": scratch.name, "pattern": pattern.to_wire(), "batch": 1},
        )
        widened = transport("next", {"cursor": opened["cursor"], "batch": 4})
        rest = transport("next", {"cursor": widened["cursor"], "batch": 100})
        assert [len(opened["atoms"]), len(widened["atoms"]), len(rest["atoms"])] == [1, 4, 2]
        assert rest["cursor"] is None
    finally:
        server.close()
        scratch.drop()


def test_an_answer_set_too_large_for_one_body_still_crosses_in_chunks(metta, monkeypatch):
    """The eager door is bounded by the HTTP body cap at both ends, so an
    answer set past it cannot cross that way at all, and chunks are how it
    crosses. The cap is lowered here rather than the answer set raised,
    which measures the same thing without moving 16 MiB.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    scratch = metta._new_space()
    scratch.add(*[metta.parse(f"(re_big {n})") for n in range(200)])
    server = remote.serve(metta)
    try:
        space = remote.RemoteSpace(remote.connect(server.url), scratch.name)
        pattern = metta.parse("(re_big $n)")
        monkeypatch.setattr(network, "MAX_HTTP_RESPONSE_BYTES", 1024)
        with pytest.raises(MettaError, match="response body exceeds"):
            list(space.match(pattern))
        with space.stream(pattern, batch=10) as answers:
            assert len(list(answers)) == 200
    finally:
        server.close()
        scratch.drop()


def test_a_gateway_is_a_drop_in_transport(metta):
    """The two halves of the wire carry one signature, so a Gateway goes
    wherever a connected transport goes, health reflection included.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    scratch = metta._new_space()
    scratch.add(metta.parse("(re_drop a)"))
    gateway = remote.Gateway(metta)
    try:
        space = remote.RemoteSpace(gateway, scratch.name)
        advertised = space.server_capabilities()
        assert advertised["protocol"] == 3
        assert "stream" in advertised["capabilities"]
        assert [str(a) for a in space.match(metta.parse("(re_drop $x)"))] == ["(re_drop a)"]
        # Both doors name the field a request left out, rather than
        # answering a KeyError whose whole message is 'pattern'.
        with pytest.raises(MettaError, match="needs the `pattern` field"):
            gateway("ask", {"space": scratch.name})
        with pytest.raises(MettaError, match="needs the `pattern` field"):
            gateway("match", {"space": scratch.name})
    finally:
        gateway.close()
        scratch.drop()


def test_a_finished_stream_needs_no_stop(metta):
    """Exhaustion releases the server's cursor, so the reply that ends a
    stream carries a null continuation and a later stop finds nothing.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    scratch = metta._new_space()
    scratch.add(metta.parse("(re_short a)"))
    gateway = remote.Gateway(metta)
    try:
        opened = gateway(
            "ask",
            {
                "space": scratch.name,
                "pattern": metta.parse("(re_short $x)").to_wire(),
                "batch": 4,
            },
        )
        assert len(opened["atoms"]) == 1 and opened["cursor"] is None
        assert gateway("stop", {"cursor": "no-such-token"}) == {"stopped": False}
    finally:
        gateway.close()
        scratch.drop()


def test_pulling_a_cursor_that_is_gone_is_refused_rather_than_answered_empty(metta):
    """Answering nothing would say the enumeration ended, and
    under-answering is the one thing this protocol forbids.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    scratch = metta._new_space()
    scratch.add(*[metta.parse(f"(re_gone {n})") for n in range(4)])
    gateway = remote.Gateway(metta)
    try:
        opened = gateway(
            "ask",
            {
                "space": scratch.name,
                "pattern": metta.parse("(re_gone $n)").to_wire(),
                "batch": 1,
            },
        )
        token = opened["cursor"]
        assert gateway("stop", {"cursor": token}) == {"stopped": True}
        with pytest.raises(MettaError, match="no such cursor"):
            gateway("next", {"cursor": token})
        with pytest.raises(MettaError, match="cursor must be a string"):
            gateway("next", {"cursor": 7})
    finally:
        gateway.close()
        scratch.drop()


@pytest.mark.parametrize("batch", [0, -1, 1.5, True, "two"])
def test_a_malformed_batch_is_refused(metta, batch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    scratch = metta._new_space()
    gateway = remote.Gateway(metta)
    try:
        with pytest.raises(MettaError, match="batch must be a positive integer"):
            gateway(
                "ask",
                {
                    "space": scratch.name,
                    "pattern": metta.parse("(re_bad $n)").to_wire(),
                    "batch": batch,
                },
            )
    finally:
        gateway.close()
        scratch.drop()


def test_an_idle_cursor_is_released(metta):
    """A client that walks away mid-stream leaves an engine behind, so a
    cursor nobody pulls from is released after its idle deadline; the
    engine count is the oracle.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    scratch = metta._new_space()
    scratch.add(*[metta.parse(f"(re_idle {n})") for n in range(4)])
    gateway = remote.Gateway(metta, cursor_idle=0.05)
    try:
        before = _live_engines(metta)
        token = gateway(
            "ask",
            {
                "space": scratch.name,
                "pattern": metta.parse("(re_idle $n)").to_wire(),
                "batch": 1,
            },
        )["cursor"]
        assert _live_engines(metta) == before + 1
        time.sleep(0.2)
        with pytest.raises(MettaError, match=r"untouched for 0\.05 seconds"):
            gateway("next", {"cursor": token})
        assert _live_engines(metta) == before
    finally:
        gateway.close()
        scratch.drop()


def test_a_gateway_refuses_more_cursors_than_it_holds(metta):
    """The ceiling is refused rather than grown: an open cursor owns an
    engine, so an unbounded table of them is an unbounded resource on an
    open port.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    scratch = metta._new_space()
    scratch.add(*[metta.parse(f"(re_many {n})") for n in range(4)])
    gateway = remote.Gateway(metta, cursor_limit=2)
    ask = {
        "space": scratch.name,
        "pattern": metta.parse("(re_many $n)").to_wire(),
        "batch": 1,
    }
    try:
        held = [gateway("ask", ask)["cursor"] for _ in range(2)]
        assert all(held)
        with pytest.raises(MettaError, match="already holds 2 answer cursors"):
            gateway("ask", ask)
        assert gateway("stop", {"cursor": held[0]}) == {"stopped": True}
        assert gateway("ask", ask)["cursor"]
    finally:
        gateway.close()
        scratch.drop()


def test_closing_the_server_releases_open_cursors(metta):
    """A gateway OWNS its cursors, so closing one releases every engine
    behind them rather than waiting on an idle deadline that no longer
    has a server to fire on.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    scratch = metta._new_space()
    scratch.add(*[metta.parse(f"(re_owned {n})") for n in range(4)])
    before = _live_engines(metta)
    server = remote.serve(metta)
    try:
        space = remote.RemoteSpace(remote.connect(server.url), scratch.name)
        answers = space.stream(metta.parse("(re_owned $n)"), batch=1)
        assert str(next(answers)) == "(re_owned 0)"
        assert _live_engines(metta) == before + 1
    finally:
        server.close()
        scratch.drop()
    assert _live_engines(metta) == before


def test_authorize_sees_the_cursors_own_space(metta):
    """/next and /stop carry a cursor and no space, so a per-space policy
    is handed the space the ANSWERS come from; reading the absent field's
    default would have judged the wrong one.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    served = metta._new_space()
    served.add(*[metta.parse(f"(re_auth {n})") for n in range(4)])
    name = served.name
    seen = []

    def watch(request):
        seen.append((request.operation, request.space))
        return True

    server = remote.serve(metta, spaces=[name], authorize=watch)
    try:
        space = remote.RemoteSpace(remote.connect(server.url), name)
        with space.stream(metta.parse("(re_auth $n)"), batch=1) as answers:
            next(answers)
    finally:
        server.close()
        served.drop()
    assert seen == [("ask", name), ("stop", name)]


def test_a_lazily_attached_space_stops_the_serving_engine_when_metta_stops(metta):
    """The knob a MeTTa program feels: an attached space built with a
    batch matches through the lifecycle, so `once` over it stops the
    server's join instead of paying for the whole answer set.

    The transport here is a Gateway rather than a URL, which is the one
    way serving and attaching join inside one process: an HTTP server
    answers on a thread of its own and would wait on the very evaluation
    waiting on it, while a Gateway runs on the calling thread.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    provider = _CountingProvider(2_000)
    metta._register_space(provider, "&re-lazy-attached")
    gateway = remote.Gateway(metta)
    client = metta._new_space()
    try:
        remote.attach(client, "&hq", gateway, "&re-lazy-attached", batch=1)
        provider.yielded = 0
        (group,) = client.run("!(once (match &hq (re_counted $n) $n))")
        assert [str(a) for a in group] == ["0"]
        stopped_early = provider.yielded
        provider.yielded = 0
        (whole,) = client.run("!(collapse (match &hq (re_counted $n) $n))")
        assert len(whole[0]) == 2_000
        drained = provider.yielded
    finally:
        client._unregister_space("&hq")
        client.drop()
        gateway.close()
        metta._unregister_space("&re-lazy-attached")
    assert stopped_early < 10, (
        f"once over a lazily attached space pulled {stopped_early} of 2,000 "
        f"candidates; the wire did not stop when the engine did"
    )
    assert drained >= 2_000, "and a query that wants them all still gets them all"


def test_a_remote_cursor_refuses_a_server_that_would_loop_it(metta):  # pytest injects this fixture to establish engine state for the scenario
    """A chunk carrying nothing ends the stream, so a live cursor beside
    an empty chunk is a server that would spin a client forever.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    def looping(operation, payload):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        return {"atoms": [], "cursor": "forever"}

    with pytest.raises(MettaError, match="live cursor with no atoms"):
        remote.RemoteCursor(looping, "&self", metta.parse("(re_loop $x)"))

    def shapeless(operation, payload):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        return {"cursor": None}

    with pytest.raises(MettaError, match="chunk without an atom list"):
        remote.RemoteCursor(shapeless, "&self", metta.parse("(re_loop $x)"))


def test_a_closed_remote_cursor_refuses_further_pulls(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    scratch = metta._new_space()
    scratch.add(*[metta.parse(f"(re_closed {n})") for n in range(4)])
    server = remote.serve(metta)
    try:
        space = remote.RemoteSpace(remote.connect(server.url), scratch.name)
        answers = space.stream(metta.parse("(re_closed $n)"), batch=1)
        next(answers)
        assert "open" in repr(answers)
        answers.close()
        answers.close()  # idempotent
        assert "closed" in repr(answers)
        with pytest.raises(MettaError, match="this cursor is closed"):
            next(answers)
        # An exhausted cursor is the other state, and it stays an
        # ordinary iterator: StopIteration, again and again.
        with space.stream(metta.parse("(re_closed $n)"), batch=100) as drained:
            assert len(list(drained)) == 4
            assert list(drained) == []
            assert "exhausted" in repr(drained)
    finally:
        server.close()
        scratch.drop()


@pytest.mark.parametrize("batch", [0, -1, 1.5, True])
def test_a_remote_cursor_refuses_a_malformed_batch(metta, batch):  # noqa: D103  -- pytest injects this fixture to establish engine state for the scenario; pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match="batch must be a positive integer"):
        remote.RemoteCursor(
            lambda _operation, _payload: {"atoms": [], "cursor": None},
            "&self",
            metta.parse("(re_bad $x)"),
            batch=batch,
        )
    with pytest.raises(ValueError, match="batch must be a positive integer or None"):
        remote.RemoteSpace(lambda _operation, _payload: {}, batch=batch)


class TestServeSpeaksItsOwnProtocol(remote_testing.GatewayComplianceSuite):
    """Our own serve() certified by the same suite that certifies the
    TypeScript references: the page made executable, pointed inward.
    This is what caught add_many missing, /health missing, and 501
    where the contract says 405.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

    @pytest.fixture()
    def gateway_url(self, metta):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        server = remote.serve(metta)
        try:
            yield server.url
        finally:
            server.close()


def test_a_server_is_a_context_manager(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with remote.serve(metta) as server:
        assert server.url.startswith("http://")
        opened = server
    # Closing is idempotent, so the with-block's exit is the whole teardown.
    opened.close()


def test_attaching_a_space_this_process_serves_is_refused_with_the_remedy(metta):
    """The one configuration that cannot work, refused where it is written.

    Janus holds the GIL across a Prolog call, so the serving thread cannot run
    while the evaluation waiting on it holds the interpreter. Before this the
    attach succeeded and the first match hung for the transport's whole
    timeout, then failed on a broken pipe with nothing naming the cause.
    """
    with remote.serve(metta, spaces=[metta.name]) as server:
        client = metta._new_space()
        with pytest.raises(MettaError) as refusal:
            remote.attach(client, "&hq", server.url, metta.name)
    message = str(refusal.value)
    assert "same process" in message
    assert "Gateway" in message, "the refusal has to name the transport that works"

    # And the remedy the message gives does work, in this same process.
    client = metta._new_space()
    remote.attach(client, "&hq", remote.Gateway(metta, [metta.name]), metta.name)
    assert client.run("!(match &hq (re_ctx_probe $x) $x)") == [[]]


def test_a_url_no_server_in_this_process_owns_is_not_refused(metta):
    """The guard is on the address, so an ordinary remote URL still attaches."""
    # Nothing is listening; attaching is still allowed, and only a call fails.
    client = metta._new_space()
    remote.attach(client, "&elsewhere", "http://127.0.0.1:9/", "&self")
