"""Purpose: `python -m petta` subcommands, the stdlib "Command-line
usage" chapter for the installed wheel: run a program, talk to a repl,
serve spaces, boot a manifest, lint a file, and read documentation, all
without a checkout. The bare `petta` console script keeps upstream's
swipl-launcher contract exactly; the subcommands live here, on the
library engine.
Guarantees:
  - every subcommand exits nonzero on failure, so each is scriptable
    [tested test_serve_and_boot_expose_spaces_until_interrupted]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import argparse
import contextlib
import re
import sys
import threading


def _print_groups(groups) -> None:
    for group in groups:
        print(" ".join(str(atom) for atom in group))


def _run(arguments) -> int:
    from .space import MeTTa  # noqa: PLC0415  deferred: --version and help must not boot

    m = MeTTa()
    for path in arguments.files:
        _print_groups(m.load(path))
    return 0


#: Complete strings (escapes included) and ;-comments, in reading order,
#: so a paren inside either never counts and a ; inside a string never
#: starts a comment.
_OPAQUE = re.compile(r'"(?:\\.|[^"\\])*"|;[^\n]*')


def _complete_form(text: str) -> bool:
    """Whether the buffered input closes every paren it opens, reading
    strings and comments the way the engine does. An over-closed buffer
    counts as complete so the stray paren errors instead of hanging.
    """
    remaining = _OPAQUE.sub("", text)
    if '"' in remaining:
        return False  # an unterminated string never completes
    return remaining.count("(") <= remaining.count(")")


def _forms(interactive: bool):
    """Complete buffered forms from stdin, until EOF or a bare exit."""
    buffer = ""
    while True:
        prompt = ("petta> " if not buffer else "  ...> ") if interactive else ""
        try:
            line = input(prompt)
        except EOFError:
            if interactive:
                print()
            return
        except KeyboardInterrupt:
            print()
            buffer = ""
            continue
        buffer = f"{buffer}\n{line}" if buffer else line
        if not buffer.strip() or buffer.strip() in ("exit", "quit"):
            if buffer.strip():
                return
            buffer = ""
            continue
        if _complete_form(buffer):
            yield buffer
            buffer = ""


def _repl(_arguments) -> int:
    from ._version import __version__  # noqa: PLC0415  deferred: --version and help must not boot
    from .errors import PettaError  # noqa: PLC0415  deferred: --version and help must not boot
    from .space import MeTTa  # noqa: PLC0415  deferred: --version and help must not boot

    with contextlib.suppress(ImportError):
        # history and line editing where the platform has readline
        import readline  # noqa: F401, PLC0415  # pylint: disable=unused-import
    m = MeTTa()
    interactive = sys.stdin.isatty()
    if interactive:
        print(f"PeTTa {__version__}; a bare `exit` leaves, Ctrl-D too.")
    for source in _forms(interactive):
        try:
            _print_groups(m.run(source))
        except PettaError as error:
            print(f"error: {error}", file=sys.stderr)
    return 0


def _serve(arguments) -> int:
    from . import remote  # noqa: PLC0415  deferred: --version and help must not boot
    from .space import MeTTa  # noqa: PLC0415  deferred: --version and help must not boot

    m = MeTTa()
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
    from .lint import lint_file  # noqa: PLC0415  deferred: --version and help must not boot
    from .space import MeTTa  # noqa: PLC0415  deferred: --version and help must not boot

    m = MeTTa()
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
    from .space import MeTTa  # noqa: PLC0415  deferred: --version and help must not boot

    m = MeTTa()
    for path in arguments.files:
        m.load(path)
    text = m.fn(arguments.name).__doc__
    if not text:
        print(f"no documentation for {arguments.name}", file=sys.stderr)
        return 1
    print(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    from ._version import __version__  # noqa: PLC0415  deferred: --version and help must not boot

    parser = argparse.ArgumentParser(
        prog="python -m petta",
        description="PeTTa's command-line surface on the library engine.",
    )
    parser.add_argument("--version", action="version", version=f"petta {__version__}")
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
