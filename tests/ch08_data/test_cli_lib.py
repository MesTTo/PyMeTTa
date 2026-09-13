"""Purpose: check argv parsing against occurrence and literal-token models.

Guarantees: generated repeats preserve the requested order and defaults;
arbitrary String values retain every character through both argument forms.
[tested: test_cli_occurrence_model, test_cli_literal_tokens,
test_cli_process_arguments; commit=WORKTREE].
Owns resources: the argv fixture joins its subprocess and captures its streams.
"""

import subprocess
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from metta import G, S, lib


@pytest.fixture(scope="module")
def cli(metta):
    """Load declarations through the public generated library face."""
    metta += lib.cli
    return metta


@settings(max_examples=100, deadline=None)
@given(st.lists(st.tuples(st.sampled_from(["a", "b", "c"]),
                         st.integers(-10**30, 10**30), st.booleans()), max_size=12),
       st.sampled_from(["keepfirst", "keeplast", "keepall"]))
def test_cli_occurrence_model(cli, occurrences, policy):
    """Occurrence indices determine retention independently of parser structure."""
    names = ("a", "b", "c")
    spec = tuple((S.opt(S[name]), S.type(S.integer), S.shortflags((S[name],)),
                  S.longflags((S[name],)), S.default(99)) for name in names)
    args = tuple(G(f"--{key}={value}" if long else f"-{key}{value}")
                 for key, value, long in occurrences)
    indices = range(len(occurrences))
    if policy == "keepfirst":
        indices = sorted({key: next(i for i, row in enumerate(occurrences) if row[0] == key)
                          for key, _, _ in occurrences}.values())
    elif policy == "keeplast":
        indices = sorted({key: i for i, (key, _, _) in enumerate(occurrences)}.values())
    supplied = {key for key, _, _ in occurrences}
    expected = tuple(S[name](99) for name in names if name not in supplied)
    expected += tuple(S[occurrences[i][0]](occurrences[i][1]) for i in indices)
    assert cli.fn.cli_parse(spec, args, S[policy]) == [(expected, ())]


@settings(max_examples=100, deadline=None)
@given(st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=30),
       st.lists(st.text(alphabet="aπ🙂\0- =", max_size=5), max_size=5))
def test_cli_literal_tokens(cli, text, operands):
    """Attached values and operands after the terminator keep exact text."""
    spec = ((S.opt(S.text), S.longflags((S.text,)), S.shortflags((S.t,))),)
    suffix = (G("--"), *map(G, operands))
    expected = [((S.text(G(text)),), tuple(map(G, operands)))]
    assert cli.fn.cli_parse(spec, (G(f"--text={text}"), *suffix), S.keepall) == expected
    if text and not text.startswith("="):
        assert cli.fn.cli_parse(spec, (G(f"-t{text}"), *suffix), S.keepall) == expected
    if not text.startswith("-") or text == "-":
        assert cli.fn.cli_parse(spec, (G("--text"), G(text), *suffix), S.keepall) == expected


def test_cli_process_arguments():
    """A real process exposes numeric spelling, Unicode and empty argv tokens."""
    root = Path(__file__).resolve().parents[4]
    goal = ("load_files('engine/metta.pl',[silent(true)]),"
            "use_module('lib/lib_cli/lib_cli'),"
            "'cli-arguments!'([\"007\",\"\",\"π\"]),writeln(argv_preserved)")
    result = subprocess.run(["swipl", "-q", "-f", "none", "-g", goal, "-t", "halt",
                             "--", "007", "", "π"], cwd=root, check=True,
                            capture_output=True, text=True)
    assert result.stdout == "argv_preserved\n"
