"""Purpose: deployment as knowledge. `metta.boot(path)` assembles an app
from a MeTTa manifest of `(boot ...)` forms, each a thin declaration over
one existing imperative call, and records every performed form in the
booted space, so the deployment is queryable knowledge rather than dead
config.
Assumes:
  - shim.pl metta_py_read_forms answers every form in a source without
    compiling, storing, or running any [tested
    test_a_manifest_neither_runs_nor_defines]
Guarantees:
  - the vocabulary is closed (load, attach, bridge, serve) and every form
    is validated before ANY form performs; a bad manifest changes nothing
    [tested test_every_problem_is_reported_before_anything_performs]
  - forms perform in source order; a bridge name materializes at its
    first bridge form carrying every declaration the manifest holds for
    that name, so a later serve can name it [tested
    test_bridge_declarations_gather_and_source_order_holds]
  - each performed form lands as its own (boot ...) atom in the booted
    space [tested test_load_and_serve_assemble_and_record]
  - manifest space operands accept decoded Space handles as well as the
    legacy symbol spelling [tested: test_load_and_serve_assemble_and_record;
    commit=4e2398075da67bb2cbcc123a9fc1e078ecac6fbf]
Owns: the servers its serve forms started. Boot.close() stops them, on
  the failure path too; the engine and the registered providers stay,
  because passive state belongs to the space story, not to the assembler.
Decides: a manifest that fails mid-way keeps the writes its performed
  prefix made, the same law the engine's own guards follow; the error
  names the failing form and how many stood.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Self, cast

from . import remote as _remote
from . import tables as _tables
from ._engine import runtime
from ._space import Space
from .atoms import Atom, Expression, Grounded, Symbol, _expr, parse
from .errors import MettaError

_VOCABULARY = ("load", "attach", "bridge", "serve")


def _read_forms(source: str) -> list[Atom]:
    """Every form in the source, read without evaluating anything. The
    engine door answers each form's own text, so variable names in bridge
    shapes survive into the recorded topology.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    row = runtime().must("metta_py_read_forms(Source, Forms)", Source=source)
    forms = []
    for kind, text in row["Forms"]:
        if kind == "runnable":
            msg = f"a manifest declares, it does not run: {text} (drop the !)"
            raise MettaError(msg)
        if kind != "expression":
            msg = (
                f"a manifest declares, it does not define: {text} "
                f"(definitions belong in a loaded file)"
            )
            raise MettaError(
                msg
            )
        forms.append(parse(text))
    return forms


def _is_text(atom: Any) -> bool:
    return isinstance(atom, Grounded) and isinstance(atom.value, str)


def _space_name(atom: Any) -> str | None:
    """The space a manifest names: an executable handle."""
    if isinstance(atom, Space):
        return str(atom.name)
    if isinstance(atom, Symbol) and atom.name.startswith("&"):
        return atom.name
    return None


def _load_complaints(arguments: list) -> list[str]:
    if len(arguments) != 1 or not _is_text(arguments[0]):
        return ['load takes one string path: (load "rules.metta")']
    return []


def _attach_complaints(arguments: list) -> list[str]:
    if (
        len(arguments) not in (2, 3)
        or _space_name(arguments[0]) is None
        or not _is_text(arguments[1])
        or (len(arguments) == 3 and _space_name(arguments[2]) is None)
    ):
        return [
            "attach takes a space symbol, a URL string, and optionally "
            'the remote-side space symbol: (attach &crm "http://crm:8700")'
        ]
    return []


def _bridge_complaints(arguments: list) -> list[str]:
    if (
        len(arguments) != 3
        or _space_name(arguments[0]) is None
        or not isinstance(arguments[1], Expression)
        or not isinstance(arguments[2], Expression)
    ):
        return [
            "bridge takes a space symbol, an atom shape, and a row shape: "
            "(bridge &db (edge $a $b) (row edges (a $a) (b $b)))"
        ]
    return []


def _serve_complaints(arguments: list) -> list[str]:
    if len(arguments) != 2:
        return ["serve takes a space list and a port: (serve (&self &crm) 8700)"]
    found = []
    spaces, port = arguments
    if (
        not isinstance(spaces, Expression)
        or not spaces.children
        or any(_space_name(s) is None for s in spaces.children)
    ):
        found.append("serve's first argument is a nonempty list of space symbols")
    if (
        not isinstance(port, Grounded)
        or isinstance(port.value, bool)
        or not isinstance(port.value, int)
        or not 0 <= port.value <= 65535
    ):
        found.append("serve's second argument is a port number, 0 picks a free one")
    return found


_VALIDATORS = {
    "load": _load_complaints,
    "attach": _attach_complaints,
    "bridge": _bridge_complaints,
    "serve": _serve_complaints,
}


def _complaints(directive: Expression) -> list[str]:
    """Everything wrong with one directive's shape, empty when sound."""
    head, *arguments = directive.children
    validator = _VALIDATORS.get(str(head)) if isinstance(head, Symbol) else None
    if validator is None:
        return [f"unknown boot form {head}; the vocabulary is {', '.join(_VOCABULARY)}"]
    return validator(arguments)


def _is_bridge(directive: Expression) -> bool:
    return directive.children[0] == Symbol("bridge")


class Boot:
    """The assembled app: the engine, and the servers the manifest started.

    A context manager, closing what boot itself started: every server.
    Registered providers and loaded knowledge stay, they are space state.
    """

    def __init__(self, m: Space, servers: tuple, performed: tuple) -> None:  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self.m = m
        self.servers = servers
        self.performed = performed

    def close(self) -> None:
        """Stop every server the manifest started."""
        for server in self.servers:
            server.close()

    def __enter__(self) -> Self:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return self

    def __exit__(self, *_exc_info: object) -> None:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        self.close()

    def __repr__(self) -> str:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return f"Boot({len(self.performed)} forms performed, {len(self.servers)} servers)"


def boot(
    manifest: str | os.PathLike[str],
    *,
    m: Space | None = None,
    connections: Mapping[str, Any] | None = None,
    host: str = "127.0.0.1",
    token: str | None = None,
    authorize: Callable[[_remote.Request], bool] | None = None,
    ssl_context: Any = None,
) -> Boot:
    """Assemble an app from a manifest of (boot ...) forms.

    Each form is sugar for exactly one existing call, performed in source
    order against `m` (a fresh engine when none is given):

        (boot (load "rules.metta"))                 m.load, manifest-relative
        (boot (attach &crm "http://crm:8700"))      metta.remote.attach
        (boot (bridge &db (edge $a $b) (row ...)))  metta.tables declare + bridge
        (boot (serve (&self &crm) 8700))            metta.remote.serve

    The vocabulary is closed and validated whole before anything runs.
    Bridges name live database connections, which MeTTa source cannot
    carry, so every bridged name must appear in `connections`, and every
    connection must be claimed by a bridge. The remaining keywords are
    the serve policy metta.remote.serve documents: host, token,
    authorize, ssl_context apply to every server the manifest starts.

    Each performed form is stored as its own `(boot ...)` atom, so the
    running app answers `(match &self (boot $what) $what)` with its own
    topology. A manifest that fails mid-way keeps its performed prefix's
    writes and closes any servers it started; the error names the form.
    """
    path = Path(os.fspath(manifest))
    directives = _validated(path, dict(connections or {}))
    assembler = _Assembler(
        m if m is not None else Space(),
        path,
        dict(connections or {}),
        {
            "host": host,
            "token": token,
            "authorize": authorize,
            "ssl_context": ssl_context,
        },
        _declarations(directives),
    )
    try:
        for form, directive in directives:
            assembler.perform(form, directive)
    except BaseException as exc:
        assembler.abandon()
        if not isinstance(exc, Exception):
            raise
        msg = (
            f"boot form {len(assembler.performed) + 1} failed: {form}. The "
            f"{len(assembler.performed)} forms before it performed and their "
            f"writes stand; every started server is closed."
        )
        raise MettaError(
            msg
        ) from exc
    return Boot(assembler.m, tuple(assembler.servers), tuple(assembler.performed))


def _declarations(directives: list[tuple[Expression, Expression]]) -> dict[str, list[Expression]]:
    """Every bridged name's (bridge <shape> <row>) declarations, gathered
    across the whole manifest in source order.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    gathered: dict[str, list[Expression]] = {}
    for _form, directive in directives:
        if _is_bridge(directive):
            _bridge_head, name, shape, row = directive.children
            gathered.setdefault(str(name), []).append(_expr(Symbol("bridge"), shape, row))
    return gathered


def _validated(path: Path, connections: dict) -> list[tuple[Expression, Expression]]:
    """Every (form, directive) pair, or one refusal listing every problem."""
    forms = _read_forms(path.read_text(encoding="utf-8"))
    if not forms:
        msg = f"the manifest {str(path)!r} declares nothing"
        raise MettaError(msg)
    directives = []
    problems = []
    for position, form in enumerate(forms, start=1):
        if (
            not isinstance(form, Expression)
            or len(form.children) != 2
            or form.children[0] != Symbol("boot")
            or not isinstance(form.children[1], Expression)
            or not form.children[1].children
        ):
            problems.append(f"form {position}: {form} is not a (boot (...)) form")
            continue
        directive = form.children[1]
        problems.extend(f"form {position}: {complaint}" for complaint in _complaints(directive))
        directives.append((form, directive))
    bridged = {str(d.children[1]) for _f, d in directives if _is_bridge(d) and not _complaints(d)}
    problems.extend(
        f"bridge {name} names no connection; pass connections={{{name!r}: ...}}"
        for name in sorted(bridged - set(connections))
    )
    problems.extend(
        f"connection {name!r} is claimed by no bridge form"
        for name in sorted(set(connections) - bridged)
    )
    if problems:
        detail = "\n  ".join(problems)
        msg = f"the manifest {str(path)!r} does not boot:\n  {detail}"
        raise MettaError(msg)
    return directives


class _Assembler:
    """One boot run's state: the engine, the manifest's directory, the
    connections, the serve policy, and everything started so far.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(
        self,
        m: Space,
        path: Path,
        connections: dict,
        serve_policy: dict,
        declarations: dict[str, list[Expression]],
    ) -> None:
        self.m = m
        self.path = path
        self.connections = connections
        self.serve_policy = serve_policy
        self.declarations = declarations
        self.servers: list[Any] = []
        self.performed: list[Expression] = []
        self._materialized: set[str] = set()

    def perform(self, form: Expression, directive: Expression) -> None:
        """Perform one validated directive, then record its form."""
        head, *arguments = directive.children
        if head == Symbol("load"):
            self.m.load(self.path.parent / cast(Grounded, arguments[0]).value)
        elif head == Symbol("attach"):
            remote_space = str(arguments[2]) if len(arguments) == 3 else "&self"
            _remote.attach(self.m, str(arguments[0]), cast(Grounded, arguments[1]).value, remote_space)
        elif head == Symbol("bridge"):
            self._bridge(str(arguments[0]))
        else:  # serve, the only remaining vocabulary entry
            spaces, port = arguments
            self.servers.append(
                _remote.serve(
                    self.m,
                    port=cast(Grounded, port).value,
                    spaces=[str(s) for s in spaces.children],
                    **self.serve_policy,
                )
            )
        self.m.add(form)
        self.performed.append(form)

    def _bridge(self, name: str) -> None:
        """Materialize a bridged name once, at its first form, carrying
        every declaration the manifest holds for it.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if name in self._materialized:
            return
        self._materialized.add(name)
        for declaration in self.declarations[name]:
            _tables.declare(self.m, name, declaration)
        provider = _tables.TableBridge.from_context(self.m, name, self.connections[name])
        self.m._register_space(provider, name)

    def abandon(self) -> None:
        """The failure path: stop every server this run started."""
        for server in self.servers:
            server.close()
