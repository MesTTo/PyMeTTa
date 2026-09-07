"""Purpose: the python -m metta subcommands, each driven as a real
subprocess: run prints answer groups, the repl reads multi-line forms
and exits cleanly, including after reporting a malformed or incomplete form;
run refuses the same incomplete file with a nonzero exit, reads its program
from standard input for `-` and for no operand at all, and frames its answers
as JSON Lines under --json; lint gates on
findings, doc answers or refuses or proposes declarations under --infer, stubs
writes a program's declarations as a
.pyi while its printing stays on stderr, and serve and boot expose spaces until
interrupted. Convert imports a real Python file and emits source that reloads
as the same program, and llms prints the repository root's cheat sheet, the
same bytes the package door prints [tested:
test_convert_imports_a_python_program_and_round_trips_its_source,
test_convert_restores_the_in_process_declaration_receiver,
test_repl_reports_an_incomplete_final_form_at_eof,
test_run_refuses_an_incomplete_file,
test_repl_reports_an_error_and_keeps_going,
test_llms_prints_the_root_cheat_sheet_and_answers_none,
test_the_llms_verb_prints_the_same_cheat_sheet_the_package_door_prints;
commit=d4f129e1d977239c2e25b5042e3b1df30d9d32d3].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import ast
import json
import os
import random
import select
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

import metta as metta_package
from metta import MeTTa, S, ground
from metta.__main__ import _completer, _history_path, _scan_line
from metta.__main__ import main as module_main
from metta.atoms import _atom_from_wire

_PACKAGE_ROOT = str(Path(__file__).resolve().parents[2])
_CONVERT_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "convert_program.py"
_ROOT_SHEET = Path(__file__).resolve().parents[4] / "llms.txt"


def _environment():
    environment = dict(os.environ)
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        f"{_PACKAGE_ROOT}{os.pathsep}{existing}" if existing else _PACKAGE_ROOT
    )
    return environment


def _metta(*arguments, stdin=None):
    return subprocess.run(
        [sys.executable, "-m", "metta", *arguments],
        capture_output=True,
        text=True,
        timeout=240,
        env=_environment(),
        input=stdin,
    )


def test_run_prints_answer_groups(tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (tmp_path / "prog.metta").write_text("(= (m-double $x) (* $x 2))\n!(m-double 21)\n")
    finished = _metta("run", str(tmp_path / "prog.metta"))
    assert finished.returncode == 0, finished.stderr
    assert finished.stdout.strip() == "42"


def test_convert_imports_a_python_program_and_round_trips_its_source(tmp_path):
    """Convert a real module to the exact source that reloads its program."""
    printed = _metta("convert", str(_CONVERT_FIXTURE))
    assert printed.returncode == 0, printed.stderr
    assert "convert fixture imported" in printed.stderr
    assert "convert fixture imported" not in printed.stdout
    assert len(printed.stdout.splitlines()) == 9
    assert "(: converted-double (-> Number Number))" in printed.stdout
    assert "(= (converted-double " in printed.stdout
    assert "(= (converted-identity " in printed.stdout
    assert "(: ConvertedPair (-> Number Number ConvertedPair))" in printed.stdout
    assert "(@doc converted-double " in printed.stdout
    assert "(@doc ConvertedPair " in printed.stdout
    assert "(converted-fact ready)" in printed.stdout
    assert "(op " not in printed.stdout

    output = tmp_path / "converted.metta"
    written = _metta("convert", str(_CONVERT_FIXTURE), "-o", str(output))
    assert written.returncode == 0, written.stderr
    assert written.stdout == ""
    assert "convert fixture imported" in written.stderr
    assert output.read_text() == printed.stdout

    with MeTTa() as restored:
        assert restored.self.load(output) == []
        assert restored.self.run("!(converted-double 21)") == [[42]]
        assert restored.self.run("!(converted-identity ready)") == [[S.ready]]
        assert restored.self.run("!(ConvertedPair-right (ConvertedPair 3 4))") == [[4]]


def test_convert_validates_paths_before_importing_or_overwriting(tmp_path):
    """Reject invalid and self-overwriting conversion paths before import."""
    missing = _metta("convert", str(tmp_path / "missing.py"))
    assert missing.returncode == 2
    assert "convert input does not exist" in missing.stderr

    wrong_suffix = tmp_path / "program.txt"
    wrong_suffix.write_text("print('not imported')\n")
    wrong = _metta("convert", str(wrong_suffix))
    assert wrong.returncode == 2
    assert "convert input must be a .py file" in wrong.stderr

    same = tmp_path / "same.py"
    same.write_text("raise AssertionError('must not be imported')\n")
    original = same.read_text()
    refused = _metta("convert", str(same), "-o", str(same))
    assert refused.returncode == 2
    assert "convert output must differ" in refused.stderr
    assert same.read_text() == original


def test_convert_publishes_nothing_when_the_python_import_fails(tmp_path):
    """Keep both output channels transactional when module import fails."""
    broken = tmp_path / "broken.py"
    broken.write_text(
        "import metta\n"
        "@metta.define\n"
        "def partial(value: int) -> int:\n"
        "    return value + 1\n"
        "raise RuntimeError('conversion exploded')\n"
    )
    output = tmp_path / "existing.metta"
    output.write_text("old source stays\n")

    finished = _metta("convert", str(broken), "-o", str(output))

    assert finished.returncode != 0
    assert finished.stdout == ""
    assert "conversion exploded" in finished.stderr
    assert output.read_text() == "old source stays\n"


def test_convert_restores_the_in_process_declaration_receiver(capsys):
    """Restore package functions and context methods after direct dispatch."""
    package_engine = metta_package.engine
    package_space = metta_package.space
    context_init = MeTTa.__init__
    context_space = MeTTa.space
    context_close = MeTTa.close

    assert module_main(["convert", str(_CONVERT_FIXTURE)]) == 0
    captured = capsys.readouterr()
    assert "(: converted-double (-> Number Number))" in captured.out
    assert "convert fixture imported" in captured.err
    assert metta_package.engine is package_engine
    assert metta_package.space is package_space
    assert MeTTa.__init__ is context_init
    assert MeTTa.space is context_space
    assert MeTTa.close is context_close

    with MeTTa() as first, MeTTa() as second:
        assert first.self != second.self


def test_repl_reads_multi_line_forms_and_exits():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    finished = _metta("repl", stdin="(= (m-inc $x)\n   (+ $x 1))\n!(m-inc 41)\nexit\n")
    assert finished.returncode == 0, finished.stderr
    assert "42" in finished.stdout


def test_repl_reports_an_error_and_keeps_going():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # A stray closer is a complete-but-broken form: the error prints to
    # stderr and the loop keeps answering.
    finished = _metta("repl", stdin=")\n!(+ 1 2)\nexit\n")
    assert finished.returncode == 0, finished.stderr
    assert "error:" in finished.stderr
    assert "3" in finished.stdout


def test_repl_reports_an_incomplete_final_form_at_eof():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    finished = _metta("repl", stdin="!(+ 1 2")
    assert finished.returncode == 0
    assert finished.stdout == ""
    assert "error:" in finished.stderr
    assert "missing ')'" in finished.stderr


def test_run_refuses_an_incomplete_file(tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    path = tmp_path / "incomplete.metta"
    path.write_text("!(+ 1 2")
    finished = _metta("run", str(path))
    assert finished.returncode != 0
    assert finished.stdout == ""
    assert "missing ')'" in finished.stderr


def test_complete_form_reads_strings_and_comments():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert _complete_form('(f "a)b" ; c)\n)')
    assert not _complete_form('(f "a)b"')
    assert not _complete_form('(f ")')
    assert not _complete_form("(f ; )\n")
    assert _complete_form("plain-symbol")


def _complete_form(text: str) -> bool:
    """Fold the reader's line scan over a whole text.

    The CLI never asks this of a whole buffer, which is the point: it carries
    the pair from line to line so a form is read in time linear in its length.
    Folding it here is how a test states the same question in one call.
    """
    depth = 0
    in_string = False
    for line in text.split("\n"):
        depth, in_string = _scan_line(line, depth, in_string=in_string)
        if depth < 0:
            return True
    return not in_string and depth <= 0


def _engine_stops_reading(runtime, text: str) -> bool:
    """Whether the ENGINE considers this text bracket-finished.

    command_wants_more/1 is the question both readers ask: could further input
    still close what this opens. sread_command/2 asks a second one on top of it,
    whether the text has any CONTENT at all, because a blank or comment-only
    line should re-prompt rather than be submitted; the CLI asks that one in
    _forms instead, so the comparison here is on the bracket question alone.

    Nothing compound crosses the boundary: the goal answers an atom.
    """
    answer = runtime.once(
        "atom_codes(T, Codes),"
        " ( command_wants_more(Codes) -> Verdict = keep ; Verdict = stop )",
        T=text,
    )
    return answer["Verdict"] == "stop"


_READER_CORPUS = [
    "(f a)", "(f", "(f))", '(f "a)b" ; c)\n)', '(f "a)b"', '(f ")',
    "(f ; )\n", "; only a comment", '"', '"\\""', '(f "a\nb")',
    '; ")"\n(f)', '(f ; "a)', '"a" ; ")"', "((()))", "(()",
    # The case the regex got wrong: a backslash escaping a LINE BREAK inside a
    # string. `\\.` in that pattern does not match a newline, so it read the
    # string as unterminated and the CLI kept prompting for a close that had
    # already happened, where the engine's escaped state takes any character
    # including the break.
    '"\\\n"', '(f "a\\\nb")',
]


def test_the_cli_reader_agrees_with_the_engine_on_when_to_stop(metta_module):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    runtime = metta_module.MeTTa().runtime
    for text in _READER_CORPUS:
        assert _complete_form(text) is _engine_stops_reading(runtime, text), repr(text)


def test_the_cli_reader_agrees_with_the_engine_over_a_random_corpus(metta_module):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # Seeded rather than generated afresh, so a disagreement reproduces from the
    # failure message alone.
    generator = random.Random(20260823)
    alphabet = ["(", ")", '"', ";", "\\", "a", " ", "\n"]
    runtime = metta_module.MeTTa().runtime
    for _ in range(200):
        text = "".join(generator.choice(alphabet) for _ in range(generator.randrange(12)))
        assert _complete_form(text) is _engine_stops_reading(runtime, text), repr(text)


def test_lint_gates_on_findings(tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (tmp_path / "bad.metta").write_text("(: m-ghost (-> Number Number))\n")
    failing = _metta("lint", str(tmp_path / "bad.metta"))
    assert failing.returncode == 1
    assert "declared-but-undefined" in failing.stdout
    # findings anchor to their source line, path:line fashion
    assert f"{tmp_path / 'bad.metta'}:1:" in failing.stdout
    (tmp_path / "good.metta").write_text("(= (m-fine $x) $x)\n")
    passing = _metta("lint", str(tmp_path / "good.metta"))
    assert passing.returncode == 0, passing.stderr
    assert "no findings" in passing.stdout


def test_doc_answers_and_refuses(tmp_path):  # noqa: ARG001, D103  -- pytest injects this fixture to establish engine state for the scenario; pytest discovers or injects this callable; its descriptive name states the contract
    found = _metta("doc", "car-atom")
    assert found.returncode == 0, found.stderr
    assert "car-atom" in found.stdout
    missing = _metta("doc", "m-no-such-name")
    assert missing.returncode == 1
    assert "no documentation" in missing.stderr


def test_llms_prints_the_root_cheat_sheet_and_answers_none(capsys):
    """Print llms.txt verbatim, the way help() prints rather than returns."""
    assert metta_package.llms() is None
    assert capsys.readouterr().out == _ROOT_SHEET.read_text(encoding="utf-8")


def test_the_llms_verb_prints_the_same_cheat_sheet_the_package_door_prints():
    """One document behind two faces, checked as bytes rather than by shape."""
    finished = _metta("llms")
    assert finished.returncode == 0, finished.stderr
    assert finished.stdout == _ROOT_SHEET.read_text(encoding="utf-8")


def test_stubs_writes_a_pyi_and_keeps_the_programs_output_off_stdout(tmp_path):
    """The artefact is stdout, so the program it loads prints on stderr.

    The engine prints from Prolog, which is why the subcommand swaps the
    descriptor rather than redirecting Python's stream: with
    `contextlib.redirect_stdout` the program's line landed in the middle of
    the stub [measured 2026-09-07].
    """
    program = tmp_path / "shapes.metta"
    program.write_text(
        '(: Sq Type)\n'
        '(: Sq (-> Number Sq))\n'
        '(: sq-area (-> Sq Number))\n'
        '(@doc sq-area (@desc "The area of a square."))\n'
        '(= (sq-area (Sq $s)) (* $s $s))\n'
        '!(println! "loading shapes")\n',
        encoding="utf-8",
    )
    printed = _metta("stubs", str(program))
    assert printed.returncode == 0, printed.stderr
    assert printed.stdout.startswith('"""MeTTa declarations from ')
    assert "def sq_area(x1: Sq, /) -> int | float:" in printed.stdout
    assert "The area of a square." in printed.stdout
    assert "loading shapes" not in printed.stdout
    assert "loading shapes" in printed.stderr

    written = tmp_path / "shapes.pyi"
    to_file = _metta("stubs", str(program), "-o", str(written))
    assert to_file.returncode == 0, to_file.stderr
    assert to_file.stdout == ""
    assert written.read_text(encoding="utf-8") == printed.stdout
    ast.parse(written.read_text(encoding="utf-8"))


def test_stubs_refuses_to_write_over_its_input(tmp_path):
    """A generator that can destroy its own source is a generator that will."""
    program = tmp_path / "keep.metta"
    program.write_text("(: keep-head (-> Number Number))\n", encoding="utf-8")
    refused = _metta("stubs", str(program), "-o", str(program))
    assert refused.returncode == 2
    assert "must differ from every input file" in refused.stderr
    assert program.read_text(encoding="utf-8") == "(: keep-head (-> Number Number))\n"


def test_the_parser_requires_a_subcommand_and_answers_version():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    bare = _metta()
    assert bare.returncode == 2
    version = _metta("--version")
    assert version.returncode == 0
    assert version.stdout.startswith("metta ")


@pytest.mark.parametrize(
    "arguments",
    [("serve", "{file}", "--port", "0"), ("boot", "{manifest}")],
    ids=["serve", "boot"],
)
def test_serve_and_boot_expose_spaces_until_interrupted(tmp_path, arguments):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (tmp_path / "facts.metta").write_text("(m-served fact)\n")
    (tmp_path / "app.metta").write_text(
        '(boot (load "facts.metta"))\n(boot (serve (&self) 0))\n'
    )
    filled = [
        a.format(file=tmp_path / "facts.metta", manifest=tmp_path / "app.metta")
        for a in arguments
    ]
    process = subprocess.Popen(
        [sys.executable, "-m", "metta", *filled],
        stdout=subprocess.PIPE,
        text=True,
        env=_environment(),
    )
    try:
        url = None
        for _ in range(300):
            line = process.stdout.readline()
            if line.startswith("serving "):
                url = line.split()[1]
                break
        assert url, "the subcommand never printed its serving line"
        health = json.loads(urllib.request.urlopen(url + "/health", timeout=5).read())
        assert health["protocol"] == 3
    finally:
        process.send_signal(signal.SIGINT)
        assert process.wait(timeout=30) == 0
        process.stdout.close()


def test_the_shutdown_guard_ignores_the_signal_that_started_it():
    """SIGINT is held off for the close, and the old handler comes back.

    Tested at the MECHANISM rather than through the race it exists for. The
    race is real and reproduces 10 times out of 10 from a standalone script:
    `serve` waits for an interrupt and closes in a `finally`, a second signal
    arriving inside that close lands in `socketserver.shutdown`'s wait,
    `RemoteServer._stop_http` collects it as a close FAILURE, and `close()`
    re-raises it, so the shutdown the first signal asked for is aborted and
    the process exits nonzero half torn down.

    It does NOT reproduce under pytest, and several attempts to make it did
    not either: serving a request first to widen the window, exactly two
    signals rather than a burst, and looping the attempt. This repository's
    own concurrency tests use a barrier for exactly this reason, and a
    barrier cannot be threaded into a subprocess's shutdown without changing
    what is being tested. So the guard's contract is asserted directly, which
    is deterministic, and the integration case below is a smoke test rather
    than the proof.
    """
    from metta.__main__ import _shutdown_uninterrupted

    before = signal.getsignal(signal.SIGINT)
    with _shutdown_uninterrupted():
        assert signal.getsignal(signal.SIGINT) is signal.SIG_IGN, (
            "a repeat of the signal that asked for the shutdown must not reach it"
        )
    assert signal.getsignal(signal.SIGINT) is before, "and the handler is given back"


def test_the_shutdown_guard_restores_its_handler_when_the_close_raises():
    """A failing close must not leave the process deaf to Ctrl-C."""
    from metta.__main__ import _shutdown_uninterrupted

    before = signal.getsignal(signal.SIGINT)
    failure = RuntimeError("close failed")
    with pytest.raises(RuntimeError, match="close failed"), _shutdown_uninterrupted():
        raise failure
    assert signal.getsignal(signal.SIGINT) is before


def test_serve_exits_cleanly_when_the_interrupt_repeats(tmp_path):
    """The integration smoke test for the guard above."""
    (tmp_path / "facts.metta").write_text("(m-twice fact)\n")
    process = subprocess.Popen(
        [sys.executable, "-m", "metta", "serve", str(tmp_path / "facts.metta"), "--port", "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=_environment(),
    )
    try:
        url = None
        for _ in range(300):
            line = process.stdout.readline()
            if line.startswith("serving "):
                url = line.split()[1]
                break
        assert url, "serve never printed its serving line"
        urllib.request.urlopen(url + "/health", timeout=5).read()
        process.send_signal(signal.SIGINT)
        time.sleep(0.02)
        process.send_signal(signal.SIGINT)
        assert process.wait(timeout=30) == 0, process.stderr.read()[-1500:]
    finally:
        process.stdout.close()
        process.stderr.close()


def _every_match(complete, text):
    """Drain readline's one-call-per-candidate protocol into a list."""
    found = []
    while (match := complete(text, len(found))) is not None:
        found.append(match)
    return found


def test_the_completer_offers_heads_and_space_names(metta):
    """Completion draws on the language catalogue and the engine's spaces.

    Special forms are in the catalogue as well as functions, so a half-typed
    `collap` completes as readily as a half-typed `car-a`, and a token opening
    with & completes a space instead.
    """
    complete = _completer(metta)
    assert complete("car-a", 0) == "car-atom"
    assert complete("car-a", 1) is None
    # A translator special form, which fun/1 alone would not have offered.
    assert complete("collap", 0) == "collapse"
    # Every match rather than the first: the suite's workers share one engine,
    # so which space sorts first is another test's business.
    assert "&self" in _every_match(complete, "&s")
    assert complete("no-such-prefix-here", 0) is None

    # A function this session defines is offered at once, because the
    # catalogue is stamped with the engine's own function generation.
    metta.run("(= (completion-probe $x) $x)")
    assert _completer(metta)("completion-pro", 0) == "completion-probe"


def test_the_history_file_follows_its_variable(monkeypatch, tmp_path):
    """METTA_HISTORY moves the file; without it the file is ~/.metta_history."""
    monkeypatch.setenv("METTA_HISTORY", str(tmp_path / "elsewhere"))
    assert _history_path() == tmp_path / "elsewhere"
    monkeypatch.delenv("METTA_HISTORY")
    monkeypatch.setenv("HOME", str(tmp_path))
    assert _history_path() == tmp_path / ".metta_history"


def _repl_on_a_terminal(keys, home, timeout=60.0):
    """Run `python -m metta repl` against a real terminal and answer what it
    wrote. A pipe is not enough: readline installs itself only for a tty, so
    completion and history are exactly the behaviour a piped session skips.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    # Local, because pty does not exist on Windows and importing it at module
    # level would take the whole file's collection down with it there.
    import pty

    environment = _environment()
    environment["HOME"] = str(home)
    environment.setdefault("TERM", "xterm")
    primary, secondary = pty.openpty()
    child = subprocess.Popen(
        [sys.executable, "-m", "metta", "repl"],
        stdin=secondary,
        stdout=secondary,
        stderr=secondary,
        env=environment,
        close_fds=True,
    )
    os.close(secondary)

    def drain(seconds):
        out = b""
        deadline = time.time() + seconds
        while time.time() < deadline:
            ready, _, _ = select.select([primary], [], [], 0.3)
            if not ready:
                continue
            try:
                chunk = os.read(primary, 65536)
            except OSError:
                break
            if not chunk:
                break
            out += chunk
            deadline = time.time() + 0.8
        return out

    transcript = drain(timeout)
    try:
        for keystroke, wait in keys:
            os.write(primary, keystroke)
            transcript += drain(wait)
        # \x15 clears the edit line so a half-typed completion cannot swallow
        # the exit that ends the session.
        os.write(primary, b"\x15exit\r")
        transcript += drain(15.0)
        child.wait(timeout=60)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=30)
        os.close(primary)
    return transcript.decode(errors="replace")


@pytest.mark.skipif(sys.platform == "win32", reason="pty is POSIX only")
def test_the_repl_completes_a_head_on_a_terminal(tmp_path):
    """TAB completes the token under the cursor, hyphen included.

    The hyphen is the whole point: readline's default delimiters break a
    token on it, so before the delimiters were set for MeTTa this inserted a
    tab and completed nothing.
    """
    transcript = _repl_on_a_terminal([(b"(car-a", 3.0), (b"\t", 8.0)], tmp_path)
    assert "(car-atom" in transcript


@pytest.mark.skipif(sys.platform == "win32", reason="pty is POSIX only")
def test_the_repl_keeps_its_history_between_sessions(tmp_path):
    """A line typed in one session is recalled by Up in the next.

    The terminator is not kept, because it is always the last line and
    leaving it in makes the next session's first Up answer `exit`.
    """
    first = _repl_on_a_terminal([(b"!(+ 40 2)\r", 20.0)], tmp_path)
    assert "42" in first
    history = tmp_path / ".metta_history"
    assert history.read_text() == "!(+ 40 2)\n"

    second = _repl_on_a_terminal([(b"\x1b[A", 5.0), (b"\r", 20.0)], tmp_path)
    assert "!(+ 40 2)" in second
    assert "42" in second
    assert history.read_text() == "!(+ 40 2)\n"


def test_run_reads_a_program_from_standard_input():
    """`-` and no operand at all reach the same reader, which is what a
    utility that names files does with standard input.
    """  # noqa: D205  -- the contract is one sentence about two spellings
    named = _metta("run", "-", stdin="!(+ 1 2)\n")
    assert named.returncode == 0, named.stderr
    assert named.stdout.strip() == "3"
    # No operand at all is the same reader, which is what `cat` and `wc` do.
    implied = _metta("run", stdin="!(+ 40 2)\n")
    assert implied.returncode == 0, implied.stderr
    assert implied.stdout.strip() == "42"


class _Terminal:
    """Standard input as a terminal, which subprocess cannot give a child here."""

    def isatty(self) -> bool:
        return True


def test_run_refuses_a_dash_on_a_terminal(monkeypatch, capsys):
    """The refusal names `-`, because that is the operand that would block."""
    import metta.__main__ as module

    monkeypatch.setattr(module.sys, "stdin", _Terminal())
    with pytest.raises(SystemExit) as refused:
        module.main(["run", "-"])
    assert refused.value.code == 2
    assert "`-` reads the program from standard input" in capsys.readouterr().err
    # And with no operand at all, which is the same reader by another spelling.
    with pytest.raises(SystemExit) as implied:
        module.main(["run"])
    assert implied.value.code == 2


def test_json_lines_carry_the_query_and_its_answers(tmp_path):
    """One object per ! group, and the program's own printing off the stream."""
    program = '(= (m-json $x) (* $x 2))\n!(m-json 21)\n!(println! "aside")\n'
    (tmp_path / "prog.metta").write_text(program)
    finished = _metta("run", "--json", str(tmp_path / "prog.metta"))
    assert finished.returncode == 0, finished.stderr
    rows = [json.loads(line) for line in finished.stdout.splitlines()]
    assert rows == [
        {"query": "(m-json 21)", "answers": ["42"]},
        {"query": '(println! "aside")', "answers": ["True"]},
    ]
    # Every line of stdout parsed as JSON above, which is the property the
    # descriptor swap buys: the program's own printing is on stderr, where a
    # line of it would otherwise have sat between two objects and broken the
    # stream for `jq`.
    assert '"aside"' in finished.stderr
    # The same program without the flag answers the same atoms, so the flag
    # frames rather than reruns. The engine prints "aside" as it loads, which
    # is exactly the interleaving --json moves off stdout.
    plain = _metta("run", str(tmp_path / "prog.metta"))
    assert plain.returncode == 0, plain.stderr
    assert plain.stdout.splitlines() == ['"aside"', "42", "True"]


def test_json_wire_answers_read_back_as_atoms():
    """The wire form is the atom, so a consumer decodes rather than parses."""
    finished = _metta("run", "--json=wire", "-", stdin='!(+ 1 2)\n!(quote alpha)\n')
    assert finished.returncode == 0, finished.stderr
    rows = [json.loads(line) for line in finished.stdout.splitlines()]
    assert [row["query"] for row in rows] == ["(+ 1 2)", "(quote alpha)"]
    read_back = [
        [_atom_from_wire(wire) for wire in row["answers"]] for row in rows
    ]
    assert read_back == [[ground(3)], [S.alpha]]


def test_a_json_error_line_names_its_input_line(tmp_path):
    """A reader failure points at the line, on stderr, with a nonzero exit."""
    (tmp_path / "bad.metta").write_text("!(+ 1 2)\n!(oops\n")
    finished = _metta("run", "--json", str(tmp_path / "bad.metta"))
    assert finished.returncode == 1
    assert finished.stdout == ""
    (row,) = [json.loads(line) for line in finished.stderr.splitlines()]
    assert row["line"] == 2
    assert "missing ')'" in row["error"]


def test_a_json_run_refuses_a_live_host_object_with_the_codecs_sentence():
    """Text prints what the plain run prints; the wire has to carry the value."""
    text = _metta("run", "--json", "-", stdin='!(py-atom "open")\n')
    assert text.returncode == 0, text.stderr
    assert json.loads(text.stdout)["answers"] == ["<builtin_function_or_method>"]
    wire = _metta("run", "--json=wire", "-", stdin='!(py-atom "open")\n')
    assert wire.returncode == 1
    assert "JSON cannot carry" in json.loads(wire.stderr)["error"]


def test_the_json_flag_never_eats_the_file_after_it(tmp_path):
    """getopt_long's optional_argument: the value attaches with `=` or is absent."""
    (tmp_path / "prog.metta").write_text("!(+ 2 2)\n")
    finished = _metta("run", "--json", str(tmp_path / "prog.metta"))
    assert finished.returncode == 0, finished.stderr
    assert json.loads(finished.stdout)["answers"] == ["4"]


def test_doc_infer_prints_the_proposals(tmp_path):
    """The declarations a program's own atoms justify, one per line."""
    (tmp_path / "prog.metta").write_text(
        "(m-inferred-user 1 ada)\n(= (m-inferred-double $x) (* $x 2))\n"
    )
    finished = _metta("doc", "--infer", str(tmp_path / "prog.metta"))
    assert finished.returncode == 0, finished.stderr
    assert finished.stdout.splitlines() == [
        "(: m-inferred-user (-> Number Symbol %Undefined%))",
        "(: m-inferred-double (-> %Undefined% Number))",
    ]
    empty = _metta("doc", "--infer")
    assert empty.returncode == 0, empty.stderr
    assert "no undeclared head" in empty.stdout
