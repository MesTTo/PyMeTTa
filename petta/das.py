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
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import json
from typing import Any, Iterator
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .atoms import Atom, Expr, Gnd, Sym, Var, parse
from .errors import PettaError
from .foreign import SpaceProvider

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


class DASAnswer:
    """One STI-ordered answer: variable bindings as petta atoms, the
    matched expressions themselves, and the attention numbers."""

    __slots__ = ("bindings", "expressions", "importance", "strength")

    def __init__(self, item: dict) -> None:
        assignment = item.get("assignment_metta") or {}
        self.bindings = {
            name: parse(text) for name, text in assignment.items()
        }
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
        self._base = url.rstrip("/")
        self._timeout = float(timeout)

    # ------------------------------------------------------------- transport

    def _request(self, method: str, path: str, body: dict | None = None) -> Any:
        data = None if body is None else json.dumps(body).encode("utf8")
        request = Request(
            self._base + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if data else {},
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:
                text = response.read().decode("utf8")
        except HTTPError as exc:
            detail = exc.read().decode("utf8", "replace")
            raise DASError(
                f"DAS {method} {path} answered {exc.code}: {detail}"
            ) from exc
        except URLError as exc:
            raise DASError(
                f"no DAS command router at {self._base}: {exc.reason}"
            ) from exc
        if not text:
            return None
        try:
            return json.loads(text)
        except ValueError:
            return text

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
        try:
            while True:
                message = connection.recv()
                if not message:
                    continue
                yield json.loads(message)
        except Exception:
            return
        finally:
            connection.close()

    # --------------------------------------------------------------- surface

    def ping(self) -> bool:
        """Whether a command router answers at this url."""
        try:
            return self._request("GET", "/ping") == "PONG!"
        except DASError:
            return False

    def execute(self, command: str, params: dict) -> str:
        """Start any router command and answer its execution id. The
        server validates parameters; unknown ones refuse loudly there."""
        body = self._request(
            "POST", "/command-router/executions",
            {"command": command, "params": params},
        )
        return body["execution_id"]

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
        Several patterns compose as (and ...), DAS's own query tree, so
        the conjunction runs server-side. Extra keyword arguments pass
        through to the router's query parameters verbatim."""
        params = self._query_params(patterns, False, unique, max_answers, extra)
        execution_id = self.execute("query", params)
        answers: list[DASAnswer] = []
        for event in self._events(execution_id):
            command = event.get("command")
            body = event.get("params") or {}
            if command == "query_answers":
                for item in body.get("answers") or []:
                    answers.append(DASAnswer(item))
            elif command == "execution_status":
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
        params = self._query_params(patterns, True, False, None, extra)
        execution_id = self.execute("query", params)
        for event in self._events(execution_id):
            body = event.get("params") or {}
            if event.get("command") == "execution_status":
                status = body.get("status")
                if status == "error":
                    raise DASError(
                        f"DAS count failed: {body.get('message', 'no detail')}"
                    )
                if status in _TERMINAL:
                    return int(body.get("total_items", 0))
        raise DASError("the DAS answer stream closed before completing")


class DASSpace(SpaceProvider):
    """A DAS connection as a read-only petta space: match answers the
    expressions DAS matched, and the engine unifies them, so joins mix
    DAS candidates with native facts. Knowledge loads through das-cli;
    the write paths say so."""

    def __init__(self, das: DAS) -> None:
        self._das = das

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
    if isinstance(pattern, Var):
        return bindings.get(pattern.name, pattern)
    if isinstance(pattern, Expr):
        return Expr([_substitute(item, bindings) for item in pattern])
    return pattern
