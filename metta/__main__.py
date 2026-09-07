"""Purpose: `python -m metta` subcommands, the stdlib "Command-line
usage" chapter for the installed wheel: run a program, talk to a repl,
serve spaces, boot a manifest, lint a file, read documentation, print
`llms.txt` and write a program's `.pyi`, all without a checkout, or convert
a Python-authored program to MeTTa source. The bare `metta` console script keeps upstream's
swipl-launcher contract exactly; the subcommands live here, on the
library engine.
Guarantees:
  - run, lint, doc, serve and boot expose failures through a nonzero process
    exit; the interactive repl instead reports each malformed form on stderr,
    continues after it, and exits zero when its input ends [tested:
    test_run_refuses_an_incomplete_file,
    test_repl_reports_an_error_and_keeps_going;
    commit=c6d72f55aa94e2d33adb376e294a3c5ead429e5b]
  - a noninteractive repl submits a buffered final form at EOF, so an
    incomplete form is reported rather than discarded silently [tested:
    test_repl_reports_an_incomplete_final_form_at_eof;
    commit=c6d72f55aa94e2d33adb376e294a3c5ead429e5b]
  - doc reports an unknown function as a normal missing-documentation result
    after bound function access became fail-fast [tested:
    test_doc_answers_and_refuses; commit=2d4d4583c2d82e90bb21a7e8671842f126edd4f4]
  - convert imports a real Python module against a fresh default space and
    emits exactly that space's round-trippable MeTTa source, keeping module
    stdout off the source channel, then restores the ordinary package and
    context factories [tested:
    test_convert_imports_a_python_program_and_round_trips_its_source,
    test_convert_restores_the_in_process_declaration_receiver; commit=42502e9d4a7fedd419856d5e6a1c291fc18ba644]
  - an interactive repl completes a head or a space name against the live
    engine, hyphens included, and keeps its history between sessions without
    the terminator [tested: test_the_completer_offers_heads_and_space_names,
    test_the_history_file_follows_its_variable,
    test_the_repl_completes_a_head_on_a_terminal,
    test_the_repl_keeps_its_history_between_sessions; commit=76ddfc8495fa9c4db6d17263080e1427ec447755]
  - llms calls the package's own ``metta.llms()``, so the shell face and the
    Python face cannot print different documents [tested:
    test_the_llms_verb_prints_the_same_cheat_sheet_the_package_door_prints;
    commit=d4f129e1d977239c2e25b5042e3b1df30d9d32d3]
  - stubs calls the package's own ``metta.stubs()`` and keeps the loaded
    program's printing on stderr, so the artefact on stdout is the stub alone
    [tested: test_stubs_writes_a_pyi_and_keeps_the_programs_output_off_stdout;
    commit=dd4f82100a052e2c5254a2ef9e91f6eb9d2e0c49]
  - run reads its program from standard input for the operand ``-`` and for no
    operand at all, and refuses when that would read a terminal [tested:
    test_run_reads_a_program_from_standard_input,
    test_run_refuses_a_dash_on_a_terminal; commit=WORKTREE]
  - ``run --json`` writes one JSON object per ! group on stdout and one per
    error on stderr, one value a line, with the program's own printing moved
    to stderr so the stream stays parseable; the exit status is the one the
    same run without the flag would give [tested:
    test_json_lines_carry_the_query_and_its_answers,
    test_json_wire_answers_read_back_as_atoms,
    test_a_json_error_line_names_its_input_line; commit=WORKTREE]
  - doc keeps the loaded program's printing on stderr for the same reason
    stubs does, and ``doc --infer`` prints the declarations a program's own
    atoms justify rather than one head's documentation [tested:
    test_doc_infer_prints_the_proposals; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import argparse
import contextlib
import os
import signal
import sys
import threading
from pathlib import Path
from typing import Any


def _print_groups(groups) -> None:
    for group in groups:
        print(" ".join(str(atom) for atom in group))


#: The operand that means standard input, which is guideline 13 of the POSIX
#: Utility Syntax Guidelines: a utility that names files reads standard input
#: for `-` [source:
#: https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap12.html].
STDIN_OPERAND = "-"

#: The two renderings `--json` chooses between. `text` prints each answer the
#: way the plain run prints it, so the flag changes only the framing; `wire`
#: prints the tagged form `metta.atoms._atom_from_wire` reads back, which
#: keeps a number a number where text has only a spelling.
JSON_TEXT = "text"
JSON_WIRE = "wire"
JSON_FORMS = (JSON_TEXT, JSON_WIRE)


def _sources(files) -> list[str]:
    """The operands to run, with no operand meaning standard input.

    A utility that reads standard input when it is given no file is the shape
    `cat`, `wc` and `grep` all have; `-` says the same thing explicitly, and
    both reach the same reader here.
    """
    return list(files) if files else [STDIN_OPERAND]


def _reads_a_terminal(files) -> bool:
    """Whether running these operands would read a program off a terminal."""
    return _sources(files) == [STDIN_OPERAND] and sys.stdin.isatty()


def _stdin_program() -> str:
    """The program on standard input, decoded the way the engine decodes a file.

    Bytes rather than `sys.stdin.read()`, because a text stdin decodes with
    the locale's encoding and the engine reads every source as UTF-8
    (`read_file_to_string/3` with `encoding(utf8)`), so under `LC_ALL=C` the
    two doors would disagree about the same program.
    """
    return sys.stdin.buffer.read().decode("utf-8")


def _program_text(source: str) -> str:
    """One operand's source text, for the position walk `--json` aligns to."""
    from ._source_forms import _source_text  # noqa: PLC0415 -- version and help must not boot

    return _stdin_program() if source == STDIN_OPERAND else _source_text(source)


def _run_source(m, source: str, text: str | None = None):
    """One operand, run the way that operand is run.

    A file goes through `load`, which is a consult: it sets the working
    directory to the file's own, so a relative `import!` inside it resolves
    against the file rather than the shell's directory, and it replaces what
    an earlier load of the same file put in the space. Standard input has no
    file to be relative to and goes through `run`.
    """
    if source != STDIN_OPERAND:
        return m.load(source)
    return m.run(_stdin_program() if text is None else text)


def _run(arguments) -> int:
    from ._space import Space  # noqa: PLC0415 -- version and help must not boot

    m = Space()
    sources = _sources(arguments.files)
    if arguments.json is None:
        for source in sources:
            _print_groups(_run_source(m, source))
        return 0
    return _run_as_json(m, sources, arguments.json)


def _write_json(payload: dict[str, Any], stream) -> None:
    """One JSON value on one line, flushed, which is what JSON Lines is.

    The codec is the engine's own, `metta._json`, and it writes at width 0, so
    every value is one line by construction rather than by a post-pass
    [source: engine/json_codec.pl, json_codec_write/3 answers what
    json_write_dict/3 answers under width(0)]. The bytes go to the descriptor
    rather than through the text stream because JSON Lines is UTF-8 and a text
    stdout carries the locale's encoding [source: https://jsonlines.org].
    """
    from ._json import dumps  # noqa: PLC0415 -- version and help must not boot

    stream.write(dumps(payload) + b"\n")
    stream.flush()


def _run_as_json(m, sources: list[str], form: str) -> int:
    """Run each operand and write its ! groups as JSON Lines.

    The framing changes and the execution does not: each operand runs exactly
    once, through the same door the plain run uses. What the flag adds is the
    position walk, which reads the source a second time WITHOUT evaluating it
    and pairs each `!` form's own text with the group it produced; a source
    the walk cannot read is reported and never run, the way a load that
    cannot parse leaves the space untouched.

    The program's own printing moves to stderr for the duration, at the
    descriptor, because the engine prints from Prolog and the JSON stream
    shares stdout with it otherwise.
    """
    from ._source_forms import positioned_forms  # noqa: PLC0415 -- version and help must not boot
    from .errors import (  # noqa: PLC0415 -- version and help must not boot
        MettaError,
        MettaSyntaxError,
    )

    failed = False
    for source in sources:
        try:
            text = _program_text(source)
            runnables = [f for f in positioned_forms(text) if f.kind == "runnable"]
            with _output_on_stderr():
                groups = _run_source(m, source, text)
            for runnable, group in _paired(runnables, groups):
                _write_json(
                    {"query": runnable.text, "answers": _answers(group, form)},
                    sys.stdout.buffer,
                )
        except (MettaError, OSError, ValueError, TypeError) as error:
            failed = True
            line = error.line if isinstance(error, MettaSyntaxError) else None
            _write_json({"error": str(error), "line": line}, sys.stderr.buffer)
    return 1 if failed else 0


def _paired(runnables, groups):
    """Each ! form beside the group it produced, or a refusal naming both counts.

    The reader and the run walk the same source, so the two lists are the same
    length; a disagreement is a defect in one of them and never a stream that
    quietly shifts by one, which is what an unchecked zip would give.
    """
    from .errors import MettaError  # noqa: PLC0415 -- version and help must not boot

    if len(runnables) != len(groups):
        msg = (
            f"the reader found {len(runnables)} ! forms and the run answered "
            f"{len(groups)} groups; they cannot be paired"
        )
        raise MettaError(msg)
    return zip(runnables, groups, strict=True)


def _answers(group, form: str) -> list:
    """One ! group's answers, in the rendering `--json` was asked for."""
    if form == JSON_WIRE:
        return [atom.to_wire() for atom in group]
    return [str(atom) for atom in group]


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
            if has_content:
                yield "\n".join(lines)
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


#: Where a session's history is kept between runs, and the variable that moves
#: it. The name follows CPython's own PYTHON_HISTORY, which site.py reads for
#: exactly this [source:
#: https://docs.python.org/3.14/using/cmdline.html#envvar-PYTHON_HISTORY].
HISTORY_VARIABLE = "METTA_HISTORY"
HISTORY_FILE = ".metta_history"

#: Lines kept in that file. readline writes the WHOLE history on exit,
#: startup's included, so without a bound the file grows for the life of the
#: installation; CPython leaves it unbounded and bash's own default is 500.
HISTORY_LENGTH = 1000


def _completer(m):
    """Complete the token under the cursor from the live engine.

    The pool is every name the language knows, plus the spaces this engine
    registers when the token opens with &.
    readline's protocol is one call per candidate: state 0 computes the
    matches and each later state indexes them, which is how rlcompleter is
    written and why the matches are cached rather than recomputed per key
    [source: https://github.com/python/cpython/blob/3.14/Lib/rlcompleter.py].
    """
    matches: list[str] = []

    def complete(text: str, state: int) -> str | None:
        if state == 0:
            pool = m.space_names() if text.startswith("&") else m.builtins()
            matches[:] = sorted(name for name in pool if name.startswith(text))
        return matches[state] if state < len(matches) else None

    return complete


def _history_path():
    named = os.environ.get(HISTORY_VARIABLE)
    return Path(named) if named else Path.home() / HISTORY_FILE


def _install_readline(m) -> object | None:
    """Install MeTTa completion and a persistent history, where readline is.

    Answers the readline module, or None on a platform without one.
    The shape is CPython's own site.register_readline: bind the completion
    key for whichever backend is present, read the user's init file if there
    is one, then load the history file
    [source: https://github.com/python/cpython/blob/3.14/Lib/site.py].

    What is ours is the delimiters. readline's default set breaks a token on
    `-`, `!`, `?`, `*` and `&`, every one of which is ordinary inside a MeTTa
    head, so with them `car-a` completes against `a` and answers nothing
    useful. Whitespace, parentheses and the string quote are the only
    characters that actually end a head here.
    """
    try:
        import readline  # noqa: PLC0415  deferred: --version and help must not boot
    except ImportError:
        return None
    backend = getattr(readline, "backend", None)
    if backend is None:
        # readline.backend arrived in 3.13; before it, libedit says so in the
        # module docstring, which is the test CPython's site.py used. FURB143 is
        # suppressed because it reads mypy's synthesized `module.__doc__: str`
        # as a fact: a module object's docstring is `str | None`, and
        # `"libedit" in None` raises.
        doc = readline.__doc__ or ""  # noqa: FURB143
        backend = "editline" if "libedit" in doc else "readline"
    readline.parse_and_bind(
        "bind ^I rl_complete" if backend == "editline" else "tab: complete"
    )
    with contextlib.suppress(OSError):
        # No .inputrc, or no .editrc on macOS, is the ordinary case.
        readline.read_init_file()
    readline.set_completer_delims(' \t\n()"')
    readline.set_completer(_completer(m))
    readline.set_history_length(HISTORY_LENGTH)
    with contextlib.suppress(OSError):
        # A first run has no history file yet.
        readline.read_history_file(_history_path())
    return readline


def _save_history(readline) -> None:
    """Keep this session's lines for the next one.

    A failure is reported rather than raised.
    A read-only home, a full disk or a path the variable points somewhere
    unwritable are all real, and losing history is not worth ending the
    session over; it IS worth one line on stderr, because history that
    silently stops persisting looks like a REPL that forgot how.
    """
    if readline is None:
        return
    # The line that ended the session is the one line never worth recalling,
    # and it is always the last, so leaving it in makes the first Up of the
    # next session answer `exit`. get_history_item counts from one and
    # remove_history_item from zero [source:
    # https://docs.python.org/3.14/library/readline.html#history-list].
    length = readline.get_current_history_length()
    if length and (readline.get_history_item(length) or "").strip() in ("exit", "quit"):
        readline.remove_history_item(length - 1)
    path = _history_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        readline.write_history_file(path)
    except OSError as error:
        print(f"history not saved to {path}: {error}", file=sys.stderr)


def _repl(_arguments) -> int:
    from ._space import Space  # noqa: PLC0415 -- version and help must not boot
    from ._version import __version__  # noqa: PLC0415  deferred: --version and help must not boot
    from .errors import MettaError  # noqa: PLC0415  deferred: --version and help must not boot

    m = Space()
    interactive = sys.stdin.isatty()
    # Completion needs a terminal to complete into, and a piped session
    # writing its lines to the history file would fill it with test input.
    readline = _install_readline(m) if interactive else None
    if interactive:
        print(f"MeTTa {__version__}; a bare `exit` leaves, Ctrl-D too.")
    try:
        for source in _forms(interactive):
            try:
                _print_groups(m.run(source))
            except MettaError as error:
                print(f"error: {error}", file=sys.stderr)
    finally:
        _save_history(readline)
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
        with _shutdown_uninterrupted():
            server.close()
    return 0


@contextlib.contextmanager
def _shutdown_uninterrupted():
    """Hold SIGINT off a shutdown that a SIGINT just started.

    `serve` and `boot` wait for an interrupt and then close in a `finally`.
    A SECOND interrupt arriving inside that close lands in
    `socketserver.shutdown`'s wait, and `RemoteServer._stop_http` collects it
    as a close FAILURE, which `close()` then re-raises: the graceful shutdown
    the first signal asked for is aborted by a repeat of the same signal, and
    the process exits nonzero having half torn down. Reproduced deterministically
    by sending two signals 20ms apart [measured 2026-09-05]; under load it
    reproduces on one signal, because the delivery can land after the main
    thread has already left the wait.

    The shape is asyncio.Runner's, which installs its own SIGINT handler for
    the duration of a run and restores it in `finally`: the first signal is
    the graceful request and a repeat must not be handled as a new one. Its
    guards are worth copying too, main thread only and tolerating a ValueError,
    because `signal.signal` raises where signals are not registered
    [source: /usr/lib/python3.14/asyncio/runners.py:111-138,159-166].

    The close is bounded by its own timeout, so holding the signal cannot hang
    a shutdown indefinitely.
    """
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    try:
        previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
    except ValueError:  # signals not registered in this interpreter
        yield
        return
    try:
        yield
    finally:
        with contextlib.suppress(ValueError):
            signal.signal(signal.SIGINT, previous)


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
        with _shutdown_uninterrupted():
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
    # The loaded program's printing goes to stderr for the reason stubs gives:
    # what lands on stdout is the answer this verb was asked for and nothing
    # a program printed on its way in, so `metta doc ... > file` is an answer.
    with _output_on_stderr():
        for path in _doc_files(arguments):
            m.load(path)
    if arguments.infer:
        proposals = m.infer_types()
        for proposal in proposals:
            print(proposal)
        if not proposals:
            print("no undeclared head here: every one this space mentions is declared")
        return 0
    try:
        text = m.fn[arguments.name].__doc__
    except AttributeError:
        text = None
    if not text:
        print(f"no documentation for {arguments.name}", file=sys.stderr)
        return 1
    print(text)
    return 0


def _doc_files(arguments) -> list[str]:
    """The sources `doc` loads first.

    Under `--infer` there is no name to ask about, so every operand is a file
    and the first one lands in `name` because argparse fills the optional
    positional before the repeated one.
    """
    if not arguments.infer:
        return list(arguments.files)
    named = [] if arguments.name is None else [arguments.name]
    return [*named, *arguments.files]


@contextlib.contextmanager
def _output_on_stderr():
    """Send everything the loaded program prints to stderr, at the descriptor.

    Without -o the stub IS this process's standard output, and a program that
    prints while it loads would land in the middle of it. The swap is at the
    file descriptor rather than through `contextlib.redirect_stdout` because
    the engine prints from Prolog: a Python-level redirection catches nothing
    [measured 2026-09-07: `!(println! "x")` under redirect_stdout captured "",
    and the text reached the process's own stdout]. Both sides flush inside
    the swap so nothing buffered arrives after it, which is the shape
    extensions/python/tools/phrasebook.py:quiet already uses for the same
    two-writer problem.

    m.capture() is the in-process door for the same text and does not reach
    here: load_space calls the runtime directly rather than through the
    execution policy that installs a capture, so a load prints past it.
    """
    sys.stdout.flush()
    saved = os.dup(1)
    try:
        os.dup2(2, 1)
        yield
    finally:
        sys.stdout.flush()
        os.dup2(saved, 1)
        os.close(saved)


def _stubs(arguments) -> int:
    from . import stubs  # noqa: PLC0415  deferred: --version and help must not boot
    from ._space import Space  # noqa: PLC0415 -- version and help must not boot

    m = Space()
    with _output_on_stderr():
        for path in arguments.files:
            m.load(path)
    text = stubs(m, sources=arguments.files)
    if arguments.output is None:
        sys.stdout.write(text)
    else:
        arguments.output.write_text(text, encoding="utf-8")
    return 0


def _llms(_arguments) -> int:
    # The package door itself, so the shell and Python faces cannot print
    # different documents. It boots nothing: the sheet is a file.
    from . import llms  # noqa: PLC0415  deferred: --version and help must not boot

    llms()
    return 0


def _python_program(value: str) -> Path:
    """Resolve one existing Python source file for ``convert``."""
    path = Path(value).resolve()
    if path.suffix != ".py":
        msg = f"convert input must be a .py file: {value}"
        raise argparse.ArgumentTypeError(msg)
    if not path.is_file():
        msg = f"convert input does not exist: {value}"
        raise argparse.ArgumentTypeError(msg)
    return path


@contextlib.contextmanager
def _conversion_receiver(context):
    """Make module-level Python declarations target one fresh context.

    Root helpers already route through ``metta.engine()``. The two conventional
    ways to bind a program receiver, ``metta.space()`` and
    ``metta.MeTTa().space()``, also denote the conversion context's own space
    for the duration of this import. Explicitly named spaces keep their
    ordinary meaning.
    """
    package = sys.modules[__package__ or "metta"]
    namespace = vars(package)
    original_engine = namespace["engine"]
    original_space = namespace["space"]
    context_type = type(context)
    original_context_init = context_type.__init__
    original_context_space = context_type.space
    original_context_close = context_type.close

    def captured_space(*args, **kwargs):
        return context.self if not args and not kwargs else context.space(*args, **kwargs)

    def captured_context_init(
        receiver,
        space=None,
        *,
        verbose=None,
        metta_path=None,
        _runtime=None,
    ):
        target = context.self if space is _runtime is None else space
        original_context_init(
            receiver,
            target,
            verbose=verbose,
            metta_path=metta_path,
            _runtime=_runtime,
        )

    def captured_context_space(receiver, *args, **kwargs):
        if receiver.self is context.self and not args and not kwargs:
            return context.self
        return original_context_space(receiver, *args, **kwargs)

    def captured_context_close(receiver):
        if receiver is not context:
            original_context_close(receiver)

    try:
        namespace["engine"] = lambda: context
        namespace["space"] = captured_space
        context_type.__init__ = captured_context_init
        context_type.space = captured_context_space
        context_type.close = captured_context_close
        yield
    finally:
        context_type.close = original_context_close
        context_type.space = original_context_space
        context_type.__init__ = original_context_init
        namespace["engine"] = original_engine
        namespace["space"] = original_space


def _convert(arguments) -> int:
    """Import a Python-authored program and emit its lowered MeTTa source."""
    from . import MeTTa  # noqa: PLC0415 -- version and help must not boot
    from .vocabularies import SaveFormat  # noqa: PLC0415 -- version and help must not boot

    with MeTTa() as context:
        with _conversion_receiver(context), contextlib.redirect_stdout(sys.stderr):
            context.self.fn["import!"](context.self, str(arguments.program))
        if arguments.output is None:
            sys.stdout.write(context.self.source())
        else:
            context.self.save(arguments.output, format=SaveFormat.metta)
    return 0


def _attached_values(argv: list[str] | None, option: str, absent: str) -> list[str]:
    """Give a bare `--option` its default value, without touching the next word.

    This is getopt_long's `optional_argument`, which argparse has no spelling
    for: the value of a long option that may take one attaches with `=` or is
    absent, and the following argument is never consumed [source:
    https://www.gnu.org/software/libc/manual/html_node/Getopt-Long-Options.html].
    argparse's own `nargs="?"` DOES consume it, so `metta run --json p.metta`
    read p.metta as the format and refused it as an invalid choice; rewriting
    the bare spelling here keeps `--json` a flag and `--json=wire` a choice,
    and leaves p.metta an operand. Everything after `--` is an operand by
    definition and is left alone.
    """
    # sys.argv rather than handing None to parse_args, because the rewrite has
    # to reach the real command line too.
    words = sys.argv[1:] if argv is None else argv
    rewritten: list[str] = []
    for index, word in enumerate(words):
        if word == "--":
            rewritten.extend(words[index:])
            break
        rewritten.append(f"{option}={absent}" if word == option else word)
    return rewritten


def main(argv: list[str] | None = None) -> int:  # noqa: D103  -- the package reference and enclosing module document this exported entry point
    from ._version import __version__  # noqa: PLC0415  deferred: --version and help must not boot

    parser = argparse.ArgumentParser(
        prog="python -m metta",
        description="MeTTa's command-line surface on the library engine.",
    )
    parser.add_argument("--version", action="version", version=f"metta {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="run MeTTa files and print each ! answer group")
    run.add_argument(
        "files",
        nargs="*",
        metavar="file.metta",
        help=f"programs to run; `{STDIN_OPERAND}`, or no operand, reads standard input",
    )
    run.add_argument(
        "--json",
        nargs="?",
        const=JSON_TEXT,
        choices=JSON_FORMS,
        help="write one JSON object per ! group instead of printing answers; "
        "--json=wire carries the tagged atom forms",
    )
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
    doc.add_argument("name", nargs="?")
    doc.add_argument("files", nargs="*", metavar="file.metta", help="sources to load first")
    doc.add_argument(
        "--infer",
        action="store_true",
        help="print the (: head (-> ...)) declarations the program's own atoms "
        "justify, instead of one name's documentation; every operand is a file",
    )
    doc.set_defaults(entry=_doc)

    llms = commands.add_parser("llms", help="print llms.txt, the sheet that teaches this library")
    llms.set_defaults(entry=_llms)

    stubs = commands.add_parser(
        "stubs", help="write a .pyi for the heads a program declares"
    )
    stubs.add_argument("files", nargs="+", metavar="file.metta")
    stubs.add_argument(
        "-o", "--output", type=Path, metavar="out.pyi", help="write the stub to this file"
    )
    stubs.set_defaults(entry=_stubs)

    convert = commands.add_parser(
        "convert", help="lower a Python-authored program to MeTTa source"
    )
    convert.add_argument("program", type=_python_program, metavar="program.py")
    convert.add_argument(
        "-o", "--output", type=Path, metavar="out.metta", help="write the source to this file"
    )
    convert.set_defaults(entry=_convert)

    arguments = parser.parse_args(_attached_values(argv, "--json", JSON_TEXT))
    if arguments.command == "run" and _reads_a_terminal(arguments.files):
        parser.error(
            f"`{STDIN_OPERAND}` reads the program from standard input and "
            f"standard input here is a terminal: name a file, or pipe a "
            f"program in"
        )
    if arguments.command == "doc" and not arguments.infer and arguments.name is None:
        parser.error("doc needs a name, or --infer to propose declarations")
    if (
        arguments.command == "convert"
        and arguments.output is not None
        and arguments.output.resolve() == arguments.program
    ):
        parser.error("convert output must differ from the input Python file")
    if arguments.command == "stubs" and arguments.output is not None:
        written = arguments.output.resolve()
        if any(Path(source).resolve() == written for source in arguments.files):
            parser.error("stubs output must differ from every input file")
    return arguments.entry(arguments)


if __name__ == "__main__":
    sys.exit(main())
