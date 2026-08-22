"""Purpose: the python -m petta subcommands, each driven as a real
subprocess: run prints answer groups, the repl reads multi-line forms
and exits cleanly, lint gates on findings, doc answers or refuses, and
serve and boot expose spaces until interrupted.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import json
import os
import random
import signal
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

from petta.__main__ import _scan_line

_PACKAGE_ROOT = str(Path(__file__).resolve().parents[1])


def _environment():
    environment = dict(os.environ)
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        f"{_PACKAGE_ROOT}{os.pathsep}{existing}" if existing else _PACKAGE_ROOT
    )
    return environment


def _petta(*arguments, stdin=None):
    return subprocess.run(
        [sys.executable, "-m", "petta", *arguments],
        capture_output=True,
        text=True,
        timeout=240,
        env=_environment(),
        input=stdin,
    )


def test_run_prints_answer_groups(tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (tmp_path / "prog.metta").write_text("(= (m-double $x) (* $x 2))\n!(m-double 21)\n")
    finished = _petta("run", str(tmp_path / "prog.metta"))
    assert finished.returncode == 0, finished.stderr
    assert finished.stdout.strip() == "42"


def test_repl_reads_multi_line_forms_and_exits():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    finished = _petta("repl", stdin="(= (m-inc $x)\n   (+ $x 1))\n!(m-inc 41)\nexit\n")
    assert finished.returncode == 0, finished.stderr
    assert "42" in finished.stdout


def test_repl_reports_an_error_and_keeps_going():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # A stray closer is a complete-but-broken form: the error prints to
    # stderr and the loop keeps answering.
    finished = _petta("repl", stdin=")\n!(+ 1 2)\nexit\n")
    assert finished.returncode == 0, finished.stderr
    assert "error:" in finished.stderr
    assert "3" in finished.stdout


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


def _engine_stops_reading(petta_module, text: str) -> bool:
    """Whether the ENGINE considers this text bracket-finished.

    command_wants_more/1 is the question both readers ask: could further input
    still close what this opens. sread_command/2 asks a second one on top of it,
    whether the text has any CONTENT at all, because a blank or comment-only
    line should re-prompt rather than be submitted; the CLI asks that one in
    _forms instead, so the comparison here is on the bracket question alone.

    Nothing compound crosses the boundary: the goal answers an atom.
    """
    answer = petta_module.janus.query_once(
        "atom_codes(T, Codes),"
        " ( command_wants_more(Codes) -> Verdict = keep ; Verdict = stop )",
        {"T": text},
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


def test_the_cli_reader_agrees_with_the_engine_on_when_to_stop(petta_instance, petta_module):  # noqa: ARG001, D103  -- pytest injects this fixture to boot the engine the goal runs in; pytest discovers or injects this callable; its descriptive name states the contract
    for text in _READER_CORPUS:
        assert _complete_form(text) is _engine_stops_reading(petta_module, text), repr(text)


def test_the_cli_reader_agrees_with_the_engine_over_a_random_corpus(petta_instance, petta_module):  # noqa: ARG001, D103  -- pytest injects this fixture to boot the engine the goal runs in; pytest discovers or injects this callable; its descriptive name states the contract
    # Seeded rather than generated afresh, so a disagreement reproduces from the
    # failure message alone.
    generator = random.Random(20260823)
    alphabet = ["(", ")", '"', ";", "\\", "a", " ", "\n"]
    for _ in range(200):
        text = "".join(generator.choice(alphabet) for _ in range(generator.randrange(12)))
        assert _complete_form(text) is _engine_stops_reading(petta_module, text), repr(text)


def test_lint_gates_on_findings(tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (tmp_path / "bad.metta").write_text("(: m-ghost (-> Number Number))\n")
    failing = _petta("lint", str(tmp_path / "bad.metta"))
    assert failing.returncode == 1
    assert "declared-but-undefined" in failing.stdout
    # findings anchor to their source line, path:line fashion
    assert f"{tmp_path / 'bad.metta'}:1:" in failing.stdout
    (tmp_path / "good.metta").write_text("(= (m-fine $x) $x)\n")
    passing = _petta("lint", str(tmp_path / "good.metta"))
    assert passing.returncode == 0, passing.stderr
    assert "no findings" in passing.stdout


def test_doc_answers_and_refuses(tmp_path):  # noqa: ARG001, D103  -- pytest injects this fixture to establish engine state for the scenario; pytest discovers or injects this callable; its descriptive name states the contract
    found = _petta("doc", "car-atom")
    assert found.returncode == 0, found.stderr
    assert "car-atom" in found.stdout
    missing = _petta("doc", "m-no-such-name")
    assert missing.returncode == 1
    assert "no documentation" in missing.stderr


def test_the_parser_requires_a_subcommand_and_answers_version():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    bare = _petta()
    assert bare.returncode == 2
    version = _petta("--version")
    assert version.returncode == 0
    assert version.stdout.startswith("petta ")


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
        [sys.executable, "-m", "petta", *filled],
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
