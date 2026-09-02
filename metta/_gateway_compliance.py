"""Purpose: the remote space protocol's conformance suite, pointed at a URL.

check-space-provider lifted over the wire: `GatewayComplianceSuite` is a
pytest class that certifies ANY implementation of the protocol
documented in website/live/remote-protocol.md, with no MeTTa checkout
knowledge on the serving side. The two TypeScript reference servers are
certified by it, and a third party's gateway is certified the same way,
by subclassing with a `gateway_url` fixture. "Speaks the space protocol"
becomes a checkable claim instead of a compatibility rumor, which is the
same reading SpaceComplianceSuite gives in-process providers.

Guarantees:
  - the four operations are exercised with the semantics the protocol
    promises: multiset adds, match by pattern, removal by unification of
    one occurrence [tested test_the_operations_keep_space_semantics,
    test_add_many_lands_the_batch]
  - the ask/next/stop lifecycle answers the eager method's answer set at
    every batch, ends on a null cursor, and refuses a cursor it no longer
    holds [tested test_the_lifecycle_streams_the_same_answers_the_eager_door_gives,
    test_the_lifecycle_refuses_what_it_cannot_answer,
    test_a_client_cursor_takes_two_answers_and_stops]
  - the refusal ladder answers JSON errors with the documented statuses,
    including the pre-body refusals only a raw socket can probe
    [tested test_refusals_carry_json_errors]
  - wide integers are stored exactly or refused, never rounded
    [tested test_wide_integers_are_exact_or_refused]
  - the conformance kit certifies the attached RemoteSpace, match
    contract and round-trip law included, so the wire, the store and the
    kit agree about one live gateway
    [tested test_the_kit_certifies_the_attached_space]
Decides:
  - the suite writes only into its own scratch space name and removes
    what it stored, so it can be pointed at a running deployment
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import json
import socket
from typing import Any
from urllib.parse import urlparse

from . import remote, testing
from ._network import HTTPEndpoint
from ._optional import require_module
from .atoms import parse
from .errors import MettaError
from .remote import RemoteSpace

pytest = require_module(
    "pytest",
    "metta.testing.GatewayComplianceSuite is a pytest suite; install pytest "
    "to run it against a gateway URL",
)

_SCRATCH = "&gateway-compliance-scratch"


def _post(url: str, operation: str, payload: Any) -> tuple[int, Any]:
    """One POST against the gateway, refusal statuses answered rather than
    raised, because reading them is half of what this suite is for.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    endpoint = HTTPEndpoint(url, subject="gateway under test", error_type=MettaError)
    status, _, raw = endpoint.request(
        "POST",
        operation,
        body=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
        timeout=30.0,
    )
    return status, json.loads(raw)


def _raw(url: str, request_text: str) -> int:
    """One hand-written HTTP request, for the refusals a client library
    will not let us send; answers the status code.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    parts = urlparse(url)
    with socket.create_connection((parts.hostname, parts.port), timeout=10) as sock:
        sock.sendall(request_text.encode("utf-8"))
        head = sock.recv(4096).decode("utf-8", "replace")
    return int(head.split(" ", 2)[1])


class GatewayComplianceSuite:
    """Subclass with a `gateway_url` fixture answering the base URL of a
    running gateway; every test below then certifies it.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init_subclass__(cls, **kwargs) -> None:
        """The same class-definition-time refusal SpaceComplianceSuite
        makes: a collectible subclass must bring its gateway_url.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        super().__init_subclass__(**kwargs)
        if cls.__name__.startswith("Test") and not any(
            "gateway_url" in ancestor.__dict__
            for ancestor in cls.__mro__
            if ancestor not in (GatewayComplianceSuite, object)
        ):
            msg = (
                f"{cls.__name__} subclasses GatewayComplianceSuite without a "
                f"`gateway_url` fixture; define one answering the base URL "
                f"of a running gateway"
            )
            raise TypeError(
                msg
            )

    @pytest.fixture()
    def gateway_url(self) -> str:
        msg = (
            "subclass GatewayComplianceSuite with a gateway_url fixture "
            "answering the base URL of a running gateway"
        )
        raise NotImplementedError(
            msg
        )

    @pytest.fixture()
    def scratch(self, gateway_url):
        provider = RemoteSpace(remote.connect(gateway_url), _SCRATCH)
        yield provider
        provider.remove(parse("$everything"))

    def test_health_names_the_protocol(self, gateway_url):
        endpoint = HTTPEndpoint(
            gateway_url, subject="gateway under test", error_type=MettaError
        )
        status, _, raw = endpoint.request("GET", "health", timeout=30.0)
        assert status == 200
        health = json.loads(raw)
        assert health["ok"] is True
        assert health["protocol"] == 3
        assert isinstance(health["atoms"], int)
        # Revision 2's reflection: what the server admits, so a client
        # can ask before writing, and whether /match honors a bound.
        # Revision 3 adds `stream`, the ask/next/stop lifecycle, which
        # every gateway at this revision speaks.
        assert isinstance(health["capabilities"], list)
        assert {"match", "enumerate", "add", "remove", "stream"} <= set(
            health["capabilities"]
        )
        assert isinstance(health["bound"], bool)

    def test_a_bound_is_honored_or_ignored_soundly(self, gateway_url, scratch):
        """bound=1 answers at most one atom on an honoring server and
        every unifying atom on an ignoring one; anything between is the
        under-approximation the protocol forbids.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        endpoint = HTTPEndpoint(
            gateway_url, subject="gateway under test", error_type=MettaError
        )
        _, _, raw = endpoint.request("GET", "health", timeout=30.0)
        honors = json.loads(raw)["bound"]
        stored = [parse(f"(gc-bound {n})") for n in range(3)]
        scratch.add_many(stored)
        status, body = _post(
            gateway_url,
            "match",
            {
                "space": _SCRATCH,
                "pattern": parse("(gc-bound $n)").to_wire(),
                "bound": 1,
            },
        )
        assert status == 200
        answered = body["atoms"]
        assert len(answered) == (1 if honors else 3)
        wire_forms = [atom.to_wire() for atom in stored]
        assert all(atom in wire_forms for atom in answered)

    def test_the_operations_keep_space_semantics(self, scratch):
        atom = parse("(gc-edge a b)")
        scratch.add(atom)
        scratch.add(atom)
        held = [str(a) for a in scratch.atoms()]
        assert held.count("(gc-edge a b)") == 2, "a space is a multiset"
        matched = [str(a) for a in scratch.match(parse("(gc-edge a $x)"))]
        assert matched.count("(gc-edge a b)") == 2
        # Removal is by unification and takes ONE occurrence, variables
        # renamed apart: a space is a multiset, and subtracting from a
        # multiset walks the count down one at a time rather than emptying
        # it. Two stored copies therefore need two removals, and the third
        # finds nothing.
        assert scratch.remove(parse("(gc-edge $q b)")) is True
        assert scratch.remove(parse("(gc-edge $q b)")) is True
        assert scratch.remove(parse("(gc-edge $q b)")) is False

    def test_add_many_lands_the_batch(self, gateway_url, scratch):
        status, body = _post(
            gateway_url,
            "add_many",
            {
                "space": _SCRATCH,
                "atoms": [parse(f"(gc-row {n})").to_wire() for n in range(5)],
            },
        )
        assert (status, body) == (200, {"added": 5})
        assert len(list(scratch.match(parse("(gc-row $n)")))) == 5

    def test_refusals_carry_json_errors(self, gateway_url):
        status, body = _post(gateway_url, "no-such-operation", {})
        assert status == 400 and "error" in body
        status, body = _post(gateway_url, "add", [1, 2])
        assert status == 400 and "error" in body
        status, body = _post(gateway_url, "add", {"atom": ["not-a-tag", 1]})
        assert status == 400 and "error" in body

        parts = urlparse(gateway_url)
        host = f"{parts.hostname}:{parts.port}"
        assert (
            _raw(gateway_url, f"POST /atoms HTTP/1.1\r\nHost: {host}\r\n\r\n") == 411
        ), "content-length is required"
        assert (
            _raw(
                gateway_url,
                f"POST /atoms HTTP/1.1\r\nHost: {host}\r\n"
                "Transfer-Encoding: chunked\r\n\r\n0\r\n\r\n",
            )
            == 400
        ), "transfer-encoding is refused"
        assert (
            _raw(gateway_url, f"PUT /atoms HTTP/1.1\r\nHost: {host}\r\nContent-Length: 0\r\n\r\n")
            == 405
        ), "only POST operates"

    def test_wide_integers_are_exact_or_refused(self, gateway_url, scratch):
        """MeTTa's numbers are exact at any width, so the one forbidden
        outcome is rounding: a server either refuses the literal (a JSON
        parser that would round past 2^53 must) or stores it exactly and
        answers it back exactly.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        wide = 123456789012345678901
        parts = urlparse(gateway_url)
        host = f"{parts.hostname}:{parts.port}"
        body = '{"space": "' + _SCRATCH + '", "atom": ["n", ' + str(wide) + "]}"
        status = _raw(
            gateway_url,
            f"POST /add HTTP/1.1\r\nHost: {host}\r\n"
            f"Content-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n{body}",
        )
        if status == 400:
            return
        assert status == 200
        stored = [atom.to_wire() for atom in scratch.atoms()]
        assert ["n", wide] in stored

    def test_the_lifecycle_streams_the_same_answers_the_eager_door_gives(
        self, gateway_url, scratch
    ):
        """ask/next/stop is required at revision 3, and chunking is a
        CHUNK: whatever batch carries the answers, the set is the set.

        A short chunk ends the stream, so the reply that ends it names a
        null cursor and nothing looks ahead to decide that. Whether a
        server actually defers the work behind the chunks is its own
        affair; what this certifies is the shape that makes deferring
        possible, which is what a client needs to rely on.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        stored = [parse(f"(gc-stream {n})") for n in range(5)]
        scratch.add_many(stored)
        pattern = parse("(gc-stream $n)").to_wire()
        _, whole = _post(gateway_url, "match", {"space": _SCRATCH, "pattern": pattern})
        eager = sorted(json.dumps(atom) for atom in whole["atoms"])
        for batch in (1, 2, 5, 50):
            answered: list[Any] = []
            status, body = _post(
                gateway_url,
                "ask",
                {"space": _SCRATCH, "pattern": pattern, "batch": batch},
            )
            assert status == 200, body
            while True:
                assert len(body["atoms"]) <= batch, "a chunk may not exceed the batch"
                answered.extend(body["atoms"])
                token = body["cursor"]
                if token is None:
                    break
                assert body["atoms"], "an empty chunk ends the stream and answers null"
                status, body = _post(
                    gateway_url, "next", {"cursor": token, "batch": batch}
                )
                assert status == 200, body
            assert sorted(json.dumps(atom) for atom in answered) == eager

        # The bound is the cut, honored exactly or ignored, the same rule
        # /match's bound keeps.
        _, bounded = _post(
            gateway_url,
            "ask",
            {"space": _SCRATCH, "pattern": pattern, "batch": 5, "bound": 2},
        )
        assert len(bounded["atoms"]) in (2, 5)

    def test_the_lifecycle_refuses_what_it_cannot_answer(self, gateway_url, scratch):
        """A cursor the server no longer holds is an ERROR on /next,
        because answering nothing would say the enumeration ended, and
        under-answering is the one thing this protocol forbids. On /stop
        it is the honest no, since a client calls stop from a
        finally-block where the stream may have ended already.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        scratch.add_many([parse(f"(gc-refuse {n})") for n in range(3)])
        pattern = parse("(gc-refuse $n)").to_wire()
        _, opened = _post(
            gateway_url, "ask", {"space": _SCRATCH, "pattern": pattern, "batch": 1}
        )
        token = opened["cursor"]
        assert isinstance(token, str), "an unfinished stream names its continuation"
        assert _post(gateway_url, "stop", {"cursor": token}) == (200, {"stopped": True})
        status, body = _post(gateway_url, "next", {"cursor": token, "batch": 1})
        assert status == 400 and "error" in body
        assert _post(gateway_url, "stop", {"cursor": token})[1] == {"stopped": False}
        for bad in (0, -1, 1.5, "two"):
            status, body = _post(
                gateway_url,
                "ask",
                {"space": _SCRATCH, "pattern": pattern, "batch": bad},
            )
            assert status == 400 and "error" in body, f"batch {bad!r} was accepted"

    def test_a_client_cursor_takes_two_answers_and_stops(self, scratch):
        """The lifecycle through the shipped client, which is how a MeTTa
        program reaches it: two answers taken, the rest never asked for,
        and the server's cursor released on the way out.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        scratch.add_many([parse(f"(gc-take {n})") for n in range(6)])
        pattern = parse("(gc-take $n)")
        with scratch.stream(pattern, batch=1) as answers:
            taken = [next(answers), next(answers)]
        assert len(taken) == 2
        assert {str(atom) for atom in taken} <= {f"(gc-take {n})" for n in range(6)}
        with scratch.stream(pattern, batch=2) as answers:
            assert len(list(answers)) == 6

    def test_the_kit_certifies_the_attached_space(self, scratch):
        report = testing.check_space_provider(
            scratch,
            atoms_to_store=[
                parse("(gc-fact a b)"),
                parse("(gc-fact a c)"),
                parse("(gc-fact (f $x) $x)"),
            ],
        )
        assert any("over-approximation holds over" in line for line in report)
        assert "round-trip: 3 stored atoms recovered intact" in report
