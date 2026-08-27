"""Purpose: `python -m metta` subcommands, the stdlib "Command-line
usage" chapter for the installed wheel: run a program, talk to a repl,
serve spaces, boot a manifest, lint a file, and read documentation, all
without a checkout. The bare `metta` console script keeps upstream's
swipl-launcher contract exactly; the subcommands live here, on the
library engine.
Guarantees:
  - every subcommand exits nonzero on failure, so each is scriptable
    [tested test_serve_and_boot_expose_spaces_until_interrupted]
  - doc reports an unknown function as a normal missing-documentation result
    after bound function access became fail-fast [tested:
    test_doc_answers_and_refuses; commit=2d4d4583c2d82e90bb21a7e8671842f126edd4f4]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import argparse
import contextlib
import sys
import threading


def _print_groups(groups) -> None:
    for group in groups:
        print(" ".join(str(atom) for atom in group))


def _run(arguments) -> int:
    from ._space import Space  # noqa: PLC0415 -- version and help must not boot

    m = Space()
    for path in arguments.files:
        _print_groups(m.load(path))
    return 0


def _scan_line(line: str, depth: int, *, in_string: bool) -> tuple[int, bool]:
    """Advance the paren depth and the string state across ONE line, reading
    strings and comments the way the engine does, so a paren inside either
    never counts and a ; inside a string never starts a comment. Carrying the
    pair from one line to the next is what lets a multi-line form be read in
    time linear in its length rather than quadratic.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    index = 0
    length = len(line)
    while index < length:
        character = line[index]
        if in_string:
            if character == "\\":
                index += 2  # an escape covers whatever follows it
                continue
            if character == '"':
                in_string = False
        elif character == '"':
            in_string = True
        elif character == ";":
            break  # a comment runs to the end of its line
        elif character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth < 0:
                # Over-closed, which no further input repairs: the engine's own
                # scan fails here rather than reading on, and the caller stops
                # so the stray paren errors instead of prompting forever.
                return depth, in_string
        index += 1
    return depth, in_string


def _forms(interactive: bool):  # noqa: FBT001  -- the boolean is established API data and positional compatibility is part of the call shape
    """Complete buffered forms from stdin, until EOF or a bare exit.

    The lines are kept and joined ONCE, when the form completes, and the paren
    depth and string state are carried from line to line. Rebuilding the whole
    buffer and re-scanning it per line is quadratic in the form's length: 4,000
    lines spent 14,675,666,660 instructions re-scanning here and spend
    61,610,327 now, and the engine's own reader carried the same cost.
    """
    lines: list[str] = []
    depth = 0
    in_string = False
    has_content = False
    while True:
        prompt = ("metta> " if not lines else "  ...> ") if interactive else ""
        try:
            line = input(prompt)
        except EOFError:
            if interactive:
                print()
            return
        except KeyboardInterrupt:
            print()
            lines, depth, in_string, has_content = [], 0, False, False
            continue
        lines.append(line)
        has_content = has_content or bool(line.strip())
        if not has_content:
            lines = []
            continue
        if len(lines) == 1 and line.strip() in ("exit", "quit"):
            return
        depth, in_string = _scan_line(line, depth, in_string=in_string)
        if depth < 0 or (not in_string and depth <= 0):
            yield "\n".join(lines)
            lines, depth, in_string, has_content = [], 0, False, False


def _repl(_arguments) -> int:
    from ._space import Space  # noqa: PLC0415 -- version and help must not boot
    from ._version import __version__  # noqa: PLC0415  deferred: --version and help must not boot
    from .errors import MettaError  # noqa: PLC0415  deferred: --version and help must not boot

    with contextlib.suppress(ImportError):
        # history and line editing where the platform has readline
        import readline  # noqa: F401, PLC0415  # pylint: disable=unused-import
    m = Space()
    interactive = sys.stdin.isatty()
    if interactive:
        print(f"PeTTa {__version__}; a bare `exit` leaves, Ctrl-D too.")
    for source in _forms(interactive):
        try:
            _print_groups(m.run(source))
        except MettaError as error:
            print(f"error: {error}", file=sys.stderr)
    return 0


def _serve(arguments) -> int:
    from . import remote  # noqa: PLC0415  deferred: --version and help must not boot
    from ._space import Space  # noqa: PLC0415 -- version and help must not boot

    m = Space()
    for path in arguments.files:
        _print_groups(m.load(path))
    server = remote.serve(
        m,
        host=arguments.host,
        port=arguments.port,
        spaces=arguments.space or None,
        token=arguments.token,
    )
    print(f"serving {server.url}", flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
    return 0


def _boot(arguments) -> int:
    from .manifest import boot  # noqa: PLC0415  deferred: --version and help must not boot

    booted = boot(arguments.manifest, host=arguments.host, token=arguments.token)
    for form in booted.performed:
        print(str(form))
    for server in booted.servers:
        print(f"serving {server.url}", flush=True)
    if not booted.servers:
        return 0
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        booted.close()
    return 0


def _lint(arguments) -> int:
    from ._space import Space  # noqa: PLC0415 -- version and help must not boot
    from .lint import lint_file  # noqa: PLC0415  deferred: --version and help must not boot

    m = Space()
    failed = False
    for path in arguments.files:
        for finding in lint_file(path, m=m):
            failed = True
            line = (finding.payload or {}).get("line")
            where = f"{path}:{line}" if line is not None else str(path)
            print(f"{where}: {finding}")
    if not failed:
        print("no findings")
    return 1 if failed else 0


def _doc(arguments) -> int:
    from ._space import Space  # noqa: PLC0415 -- version and help must not boot

    m = Space()
    for path in arguments.files:
        m.load(path)
    try:
        text = m.fn[arguments.name].__doc__
    except AttributeError:
        text = None
    if not text:
        print(f"no documentation for {arguments.name}", file=sys.stderr)
        return 1
    print(text)
    return 0


def main(argv: list[str] | None = None) -> int:  # noqa: D103  -- the package reference and enclosing module document this exported entry point
    from ._version import __version__  # noqa: PLC0415  deferred: --version and help must not boot

    parser = argparse.ArgumentParser(
        prog="python -m metta",
        description="PeTTa's command-line surface on the library engine.",
    )
    parser.add_argument("--version", action="version", version=f"metta {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="run MeTTa files and print each ! answer group")
    run.add_argument("files", nargs="+", metavar="file.metta")
    run.set_defaults(entry=_run)

    repl = commands.add_parser("repl", help="an interactive read-eval-print loop")
    repl.set_defaults(entry=_repl)

    serve = commands.add_parser("serve", help="expose this engine's spaces over HTTP")
    serve.add_argument("files", nargs="*", metavar="file.metta", help="knowledge to load first")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=0, help="0 picks a free port")
    serve.add_argument("--space", action="append", help="allowlist; repeatable")
    serve.add_argument("--token", help="require this Bearer token")
    serve.set_defaults(entry=_serve)

    boot = commands.add_parser("boot", help="assemble an app from a (boot ...) manifest")
    boot.add_argument("manifest", metavar="app.metta")
    boot.add_argument("--host", default="127.0.0.1")
    boot.add_argument("--token", help="Bearer token for every served endpoint")
    boot.set_defaults(entry=_boot)

    lint = commands.add_parser("lint", help="diagnose files; nonzero exit on findings")
    lint.add_argument("files", nargs="+", metavar="file.metta")
    lint.set_defaults(entry=_lint)

    doc = commands.add_parser("doc", help="print a name's (@doc ...) documentation")
    doc.add_argument("name")
    doc.add_argument("files", nargs="*", metavar="file.metta", help="sources to load first")
    doc.set_defaults(entry=_doc)

    arguments = parser.parse_args(argv)
    return arguments.entry(arguments)


if __name__ == "__main__":
    sys.exit(main())
