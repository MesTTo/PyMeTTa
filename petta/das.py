"""Purpose: first-class client for the Distributed Atomspace (DAS): the
command-router protocol, HTTP and WebSocket with JSON both ways. query()
streams STI-ordered answers back as petta atoms, DAS's MeTTa text read
straight into terms and petta's $-variables rendered as DAS's %-sigil;
count() runs the same query in the router's count mode and answers the
server's own total; cancel() stops an execution mid-stream; execute()
passes any router command through (evolution, link_creation, context),
parameters validated server-side. DASSpace registers a connection as a
read-only space provider, so match and joins over DAS answers run the
engine's own unification. Loading knowledge is das-cli's job, and every
write path says so instead of pretending.

Two router dialects exist in the wild and both are spoken. Current
sources take an enveloped {"command", "params"} request, MeTTa-text
queries, and enveloped events; the deployed 1.2.0-rc images take a flat
{"command_type", "command_text"} request, token-vector queries
(LINK_TEMPLATE Expression ...), flat events whose answer chunks ride
under "data", and answer handles without MeTTa text, verified against a
live das-cli deployment. The dialect negotiates once per connection off
the server's own 400 naming the missing legacy fields; anything else
stays loud.
Guarantees:
  - DAS refuses non-HTTP endpoint URLs during construction [tested
    test_das_refuses_non_http_urls]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from http.client import HTTPException
from typing import Any

from . import _json
from ._network import HTTPEndpoint
from .atoms import Atom, Expr, Gnd, Sym, Var, map_atoms, parse
from .errors import PettaError
from .foreign import SpaceProvider

logger = logging.getLogger(__name__)

__all__ = ["DAS", "DASAnswer", "DASError", "DASSpace"]

_TERMINAL = ("completed", "error", "aborted")


class DASError(PettaError):
    """A DAS request failed, or an answer could not be read."""


def _render(value: Any) -> str:
    """A petta pattern as DAS MeTTa query text: variables carry the
    %-sigil, strings quote JSON-style, expressions parenthesize."""
    if isinstance(value, str):
        return value
    if isinstance(value, Var):
        return "%" + value.name
    if isinstance(value, Sym):
        return value.name
    if isinstance(value, Gnd):
        plain = value.value
        if isinstance(plain, str):
            return json.dumps(plain)
        if isinstance(plain, (int, float)) and not isinstance(plain, bool):
            return str(plain)
        raise DASError(
            f"{value!r} has no DAS query spelling; use symbols, strings, "
            f"numbers, variables, and expressions"
        )
    if isinstance(value, Expr):
        return "(" + " ".join(_render(item) for item in value) + ")"
    raise DASError(
        f"{value!r} is not a DAS query pattern; pass atoms or MeTTa text"
    )


def _has_var(value: Any) -> bool:
    if isinstance(value, Var):
        return True
    if isinstance(value, Expr):
        return any(_has_var(item) for item in value)
    return False


def _render_tokens(value: Any) -> str:
    """The same pattern in DAS token-vector spelling, the legacy query
    syntax the query agent walks as a prefix stack machine: a link with
    any variable inside is a LINK_TEMPLATE, a fully ground link is a
    LINK, a leaf symbol is NODE Symbol, a variable is VARIABLE. MeTTa
    text patterns parse first so both input spellings serve both
    dialects."""
    if isinstance(value, str):
        value = parse(value)
    if isinstance(value, Var):
        return f"VARIABLE {value.name}"
    if isinstance(value, Sym):
        return f"NODE Symbol {value.name}"
    if isinstance(value, Gnd):
        plain = value.value
        if isinstance(plain, str):
            return f'NODE Symbol "{plain}"'
        if isinstance(plain, (int, float)) and not isinstance(plain, bool):
            return f"NODE Symbol {plain}"
        raise DASError(
            f"{value!r} has no DAS token spelling; use symbols, strings, "
            f"numbers, variables, and expressions"
        )
    if isinstance(value, Expr):
        head = "LINK_TEMPLATE" if _has_var(value) else "LINK"
        parts = [_render_tokens(item) for item in value]
        return f"{head} Expression {len(parts)} " + " ".join(parts)
    raise DASError(
        f"{value!r} is not a DAS query pattern; pass atoms or MeTTa text"
    )


class DASAnswer:
    """One STI-ordered answer: variable bindings as petta atoms, the
    matched expressions themselves, the raw atom handles, and the
    attention numbers. A router that maps answers back to MeTTa text
    binds real terms; the deployed legacy routers answer handles only,
    which arrive as string values under the same names."""

    __slots__ = ("bindings", "expressions", "handles", "importance", "strength")

    def __init__(self, item: dict) -> None:
        self.handles = dict(item.get("assignment") or {})
        metta_assignment = item.get("assignment_metta") or {}
        self.bindings = {
            name: parse(text) for name, text in metta_assignment.items()
        }
        for name, handle in self.handles.items():
            if name not in self.bindings:
                self.bindings[name] = Gnd(handle)
        self.expressions = [
            parse(text)
            for group in item.get("metta_expressions") or []
            for text in group
        ]
        self.importance = float(item.get("importance", 0.0))
        self.strength = float(item.get("strength", 0.0))

    def __getitem__(self, name: str) -> Atom:
        return self.bindings[name]

    def __repr__(self) -> str:
        return f"DASAnswer({self.bindings!r})"


class DAS:
    """A connection to a DAS command router.

        das = petta.das.DAS("http://localhost:40009")
        das.ping()
        for answer in das.query(S.Similarity(S['"human"'], V.x)):
            print(answer["x"], answer.importance)
    """

    def __init__(self, url: str = "http://localhost:40009", timeout: float = 10.0):
        self._endpoint = HTTPEndpoint(
            url, subject="DAS command router", error_type=DASError
        )
        self._base = self._endpoint.url
        self._timeout = float(timeout)
        self._dialect: str | None = None

    # ------------------------------------------------------------- transport

    def _request(self, method: str, path: str, body: dict | None = None) -> Any:
        data = None if body is None else _json.dumps(body)
        logger.debug("sending DAS %s %s", method, path)
        try:
            status, _reason, raw = self._endpoint.request(
                method,
                path,
                body=data,
                headers={"Content-Type": "application/json"} if data else None,
                timeout=self._timeout,
            )
        except (HTTPException, OSError) as exc:
            logger.warning(
                "DAS %s %s failed during transport", method, path, exc_info=True
            )
            raise DASError(
                f"no DAS command router at {self._base}: {exc}"
            ) from exc
        logger.debug("DAS %s %s answered with HTTP %d", method, path, status)
        if status >= 400:
            text = raw.decode("utf8", "replace")
            raise DASError(
                f"DAS {method} {path} answered {status}: {text}"
            )
        if not raw:
            return None
        try:
            return _json.loads(raw)
        except ValueError:
            return raw.decode("utf8")

    def _events(self, execution_id: str) -> Iterator[dict]:
        try:
            from websocket import create_connection
        except ImportError as exc:
            raise DASError(
                "streaming DAS answers needs the websocket-client package; "
                "pip install websocket-client"
            ) from exc
        ws_base = self._base.replace("http://", "ws://", 1).replace(
            "https://", "wss://", 1
        )
        connection = create_connection(
            f"{ws_base}/command-router/ws/{execution_id}",
            timeout=self._timeout,
        )
        logger.debug("connected DAS event stream for execution %s", execution_id)
        from websocket import WebSocketConnectionClosedException

        try:
            while True:
                message = connection.recv()
                if not message:
                    continue
                yield _json.loads(message)
        except WebSocketConnectionClosedException:
            # The server closed the stream; the caller's terminal-event
            # handling decides whether the answer set was complete.
            return
        except Exception as exc:
            logger.warning(
                "DAS event stream for execution %s failed",
                execution_id,
                exc_info=True,
            )
            raise DASError(
                f"the DAS event stream broke mid-query: {exc}"
            ) from exc
        finally:
            connection.close()
            logger.debug("closed DAS event stream for execution %s", execution_id)

    # --------------------------------------------------------------- surface

    def ping(self) -> bool:
        """Whether a command router answers at this url."""
        try:
            return self._request("GET", "/ping") == "PONG!"
        except DASError:
            logger.debug("DAS ping failed", exc_info=True)
            return False

    def execute(self, command: str, params: dict) -> str:
        """Start any router command and answer its execution id, in the
        current sources' enveloped shape. The server validates
        parameters; unknown ones refuse loudly there. Legacy routers
        serve query() and count(), which negotiate the dialect."""
        body = self._request(
            "POST", "/command-router/executions",
            {"command": command, "params": params},
        )
        return body["execution_id"]

    def _start_query(self, patterns: tuple, count: bool, unique: bool,
        max_answers: int | None, extra: dict) -> str:
        if self._dialect != "legacy":
            body: dict[str, Any] = {
                "command": "query",
                "params": self._query_params(
                    patterns, count, unique, max_answers, extra
                ),
            }
            try:
                answer = self._request(
                    "POST", "/command-router/executions", body
                )
                self._dialect = "modern"
                return answer["execution_id"]
            except DASError as error:
                if self._dialect is None and "command_type" in str(error):
                    self._dialect = "legacy"
                    logger.info("DAS command router uses the legacy query dialect")
                else:
                    raise
        if unique:
            raise DASError(
                "unique= needs a current router; the connected one speaks "
                "the legacy dialect without unique_assignment_flag"
            )
        tokens = [_render_tokens(pattern) for pattern in patterns]
        text = tokens[0] if len(tokens) == 1 else (
            f"AND {len(tokens)} " + " ".join(tokens)
        )
        body = {"command_type": "query", "command_text": text}
        if count:
            body["count_flag"] = True
        if max_answers is not None:
            body["max_answers"] = int(max_answers)
        body.update(extra)
        answer = self._request("POST", "/command-router/executions", body)
        return answer["execution_id"]

    def _answer_stream(self, execution_id: str) -> Iterator[tuple[str, Any]]:
        """Both dialects' events as ('answers', items) and
        ('status', payload) pairs."""
        for event in self._events(execution_id):
            if "command" in event:
                body = event.get("params") or {}
                if event["command"] == "query_answers":
                    yield "answers", body.get("answers") or []
                elif event["command"] == "execution_status":
                    yield "status", body
            elif "data" in event:
                yield "answers", event.get("data") or []
            elif "status" in event:
                yield "status", event

    def status(self, execution_id: str) -> dict:
        return self._request(
            "GET", f"/command-router/executions/{execution_id}"
        )

    def cancel(self, execution_id: str) -> None:
        self._request(
            "POST", f"/command-router/executions/{execution_id}/cancel"
        )

    def _query_params(self, patterns: tuple, count: bool, unique: bool,
                      max_answers: int | None, extra: dict) -> dict:
        if not patterns:
            raise DASError("a DAS query needs at least one pattern")
        tokens = [_render(pattern) for pattern in patterns]
        token = tokens[0] if len(tokens) == 1 else "(and " + " ".join(tokens) + ")"
        params: dict = {
            "query": {"syntax": "metta", "tokens": [token]},
            "use_metta_as_query_tokens": True,
            "populate_metta_mapping": True,
        }
        if count:
            params["count_flag"] = True
        if unique:
            params["unique_assignment_flag"] = True
        if max_answers is not None:
            params["max_answers"] = int(max_answers)
        params.update(extra)
        return params

    def query(self, *patterns: Any, max_answers: int | None = None,
              unique: bool = False, **extra: Any) -> list[DASAnswer]:
        """Run a pattern query and collect its STI-ordered answers.
        Several patterns compose as one server-side conjunction, DAS's
        own query tree. Extra keyword arguments pass through to the
        router's query parameters verbatim."""
        execution_id = self._start_query(
            patterns, False, unique, max_answers, extra
        )
        answers: list[DASAnswer] = []
        for kind, body in self._answer_stream(execution_id):
            if kind == "answers":
                answers.extend(DASAnswer(item) for item in body)
                continue
            status = body.get("status")
            if status == "error":
                raise DASError(
                    f"DAS query failed: {body.get('message', 'no detail')}"
                )
            if status in _TERMINAL:
                break
        return answers

    def count(self, *patterns: Any, **extra: Any) -> int:
        """The router's count mode: the server's own total, no answers
        shipped."""
        execution_id = self._start_query(patterns, True, False, None, extra)
        counted = 0
        for kind, body in self._answer_stream(execution_id):
            if kind == "answers":
                counted += len(body)
                continue
            status = body.get("status")
            if status == "error":
                raise DASError(
                    f"DAS count failed: {body.get('message', 'no detail')}"
                )
            if status in _TERMINAL:
                return int(body.get("total_items", counted))
        raise DASError("the DAS answer stream closed before completing")


class DASSpace(SpaceProvider):
    """A DAS connection as a read-only petta space: match answers the
    expressions DAS matched, and the engine unifies them, so joins mix
    DAS candidates with native facts. Knowledge loads through das-cli;
    the write paths say so."""

    def __init__(self, das: DAS) -> None:
        self._das = das

    def can_run(self, capability: str, /, **request: Any) -> bool:
        if capability in {"add", "clear", "enumerate", "remove", "subscribe"}:
            return False
        return super().can_run(capability, **request)

    def match(self, pattern: Atom):
        for answer in self._das.query(pattern):
            if answer.expressions:
                yield from answer.expressions
            elif answer.bindings:
                yield _substitute(pattern, answer.bindings)

    def add(self, atom: Atom) -> None:
        raise DASError(
            "DAS spaces are read-only through the command router; load "
            "knowledge with das-cli metta load"
        )

    def remove(self, atom: Atom) -> bool:
        raise DASError(
            "DAS spaces are read-only through the command router; manage "
            "knowledge with das-cli"
        )


def _substitute(pattern: Atom, bindings: dict[str, Atom]) -> Atom:
    return map_atoms(
        pattern,
        lambda atom: bindings.get(atom.name, atom)
        if isinstance(atom, Var)
        else atom,
    )
