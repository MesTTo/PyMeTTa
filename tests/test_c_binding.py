"""Purpose: hold the C binding and the Python host to the same answers, so the
seam has a third consumer and the newest one is checked against a live engine
rather than against a written-down expectation.

The C seat has no wire codec, so `tests/codec/corpus.json` cannot be pointed at
it the way it is pointed at Node: being in the engine's own process, it reads
`term_t` directly and never builds a tagged array (C6 in
ai-cetta-c-constraints.md). What replaces that check is this one, and it is the
stronger half of what the Node lane does anyway: two LIVE hosts, the same
programs, the same moment.

Three things are compared, and between them they pin what a codec would have:
GROUPING and MULTIPLICITY (which `!` form produced an answer, and how many
times), the engine's own TEXT for each answer, and the METATYPE. Order within a
group is unspecified by the language and is compared as a multiset.

Assumes:
  - a C compiler and SWI's development headers are present; without either the
    suite skips, the same optional-toolchain shape test_node_binding.py has
Guarantees:
  - both seats answer every corpus program with the same groups, the same
    number of answers and the same text
    [tested test_the_c_binding_and_the_python_host_answer_the_same_programs]
  - the two seats' metatypes agree except where _KNOWN_METATYPE_DIVERGENCES
    names the disagreement and says why
    [tested test_the_c_binding_and_the_python_host_answer_the_same_programs]
  - the C seat's own suite passes against the same tree, and its process
    stdout carries only its own writes while the engine's assertion report
    goes to stderr
    [tested test_the_c_binding_suite_passes]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import collections
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

import metta

_BINDING = Path(__file__).resolve().parents[3] / "bindings" / "cetta"
_CORPUS = json.loads((_BINDING / "kit" / "corpus.json").read_text(encoding="utf-8"))

# The C seat splits what the Python seat keeps whole, because C has the types
# to split it with. Both are reported as one metatype to MeTTa; the mapping
# says which C kind belongs to which.
_KIND_TO_METATYPE = {
    "Symbol": "Symbol",
    "Expression": "Expression",
    "Variable": "Variable",
    "Number": "Grounded",
    "BigInt": "Grounded",
    "Rational": "Grounded",
    "Bool": "Grounded",
    "String": "Grounded",
    "Grounded": "Grounded",
    "Space": "Grounded",
}

# Where the two seats classify the SAME atom differently. A pinned inventory
# rather than a filter: a divergence that is not listed fails the comparison,
# and a listed one carries why.
#
# One entry, and it is deliberate. An executable space reaches the C seat as
# CETTA_SPACE, whose metatype is Grounded, because that seat asks
# metta_space_names/1 whether the name really is a space. The Python shim
# hardcodes `&self` and `&petta` and tags nothing else, so a space the engine
# just made crosses to it as an ordinary Symbol. Measured 2026-08-27:
# `!(new-space)` answers metatype Symbol in Python and Space in C, and
# `metta_space_names/1` lists the name in both. C5 in
# ai-cetta-c-constraints.md has the probe and the finding.
_KNOWN_METATYPE_DIVERGENCES = {
    ("Space", "Symbol"),
}


def _toolchain_ready() -> bool:
    """Whether this machine can build the C binding at all."""
    if not (shutil.which("cc") or shutil.which("gcc")):
        return False
    if not shutil.which("swipl"):
        return False
    dump = subprocess.run(
        ["swipl", "--dump-runtime-variables"],
        capture_output=True, text=True, check=False,
    ).stdout
    for line in dump.splitlines():
        if line.startswith("PLBASE="):
            base = line.split('"', 2)[1]
            return (Path(base) / "include" / "SWI-Prolog.h").exists()
    return False


pytestmark = pytest.mark.skipif(
    not _toolchain_ready(),
    reason="the C binding needs a C compiler and SWI-Prolog's development headers",
)


@pytest.fixture(scope="module")
def built() -> Path:
    """Build the binding once, and fail loudly rather than skipping on error."""
    done = subprocess.run(
        ["make", "--quiet", "kit", "tests/test_cetta"],
        cwd=_BINDING, capture_output=True, text=True, check=False,
    )
    if done.returncode != 0:
        pytest.fail(f"the C binding did not build:\n{done.stdout}\n{done.stderr}")
    return _BINDING


@pytest.fixture(scope="module")
def c_report(built: Path) -> dict[str, Any]:
    """Every corpus program, as the C seat answered it."""
    done = subprocess.run(
        [str(built / "kit" / "driver"), str(built / "kit" / "corpus.json")],
        capture_output=True, text=True, check=False,
    )
    if done.returncode != 0:
        pytest.fail(f"the C driver failed:\n{done.stdout}\n{done.stderr}")
    return json.loads(done.stdout)


def test_the_c_binding_suite_passes(built: Path) -> None:
    """The seat's own C suite, run against this tree rather than a built one.

    Its streams are read as well as its status. That suite runs a failing
    assertEqual, and the engine used to print "Assertion failed: ..." to
    current_output before raising, which for a host that embeds SWI in its own
    process is the HOST's stdout with no way to suppress it (C12 in
    ai-cetta-c-constraints.md, filed from here). The process has exited by the
    time these strings are read, so every stream is flushed: what is absent
    from stdout was never written to it, and the summary line below is the
    proof that stdout is being read at all.
    """
    done = subprocess.run(
        [str(built / "tests" / "test_cetta")],
        capture_output=True, text=True, check=False,
    )
    assert done.returncode == 0, f"{done.stdout}\n{done.stderr}"
    assert "0 failures" in done.stdout
    assert "Assertion failed" not in done.stdout, (
        f"the engine wrote its assertion report to the C host's stdout: "
        f"{done.stdout!r}"
    )
    assert "MeTTa assertion failed" in done.stderr, (
        f"the assertion failure was not reported at all; moving it off stdout "
        f"must not mean losing it: {done.stderr!r}"
    )


def test_the_c_binding_and_the_python_host_answer_the_same_programs(
    c_report: dict[str, Any],
) -> None:
    """Two live seats, the same programs, compared in the same moment."""
    engine = metta.MeTTa().self

    assert len(c_report["programs"]) == len(_CORPUS["programs"])
    divergences: set[tuple[str, str]] = set()

    for case, ran in zip(_CORPUS["programs"], c_report["programs"], strict=True):
        source = case["source"]
        assert ran["source"] == source
        assert "error" not in ran, f"{source}: {ran.get('error')}"

        expected = engine.run(source)
        answered = ran["answers"]

        # Grouping and multiplicity: which ! form produced what, and how many.
        here = [len(group) for group in expected]
        there_counts: collections.Counter[int] = collections.Counter(
            answer["group"] for answer in answered
        )
        there = [there_counts.get(index, 0) for index in range(len(here))]
        assert here == there, f"{source}: groups {here} here, {there} there"

        for index, group in enumerate(expected):
            texts = [answer["text"] for answer in answered if answer["group"] == index]
            kinds = [answer["kind"] for answer in answered if answer["group"] == index]

            allocated = case.get("allocated")
            if allocated:
                # The answer names something the engine just made, from a
                # per-process counter, so the two seats hold different numbers
                # and comparing the text would only measure how many spaces
                # each process had made first. The SHAPE is compared instead.
                pattern = re.compile(allocated)
                assert all(pattern.fullmatch(text) for text in texts), (source, texts)
                assert all(
                    pattern.fullmatch(str(atom)) for atom in group
                ), (source, [str(atom) for atom in group])
            else:
                # Order within a group is unspecified; multiplicity is not.
                mine = collections.Counter(str(atom) for atom in group)
                assert mine == collections.Counter(texts), f"{source}, group {index}"

            if allocated:
                pairs = list(zip(sorted(kinds), sorted(group, key=str), strict=True))
            else:
                by_text: dict[str, list[str]] = {}
                for text, kind in zip(texts, kinds, strict=True):
                    by_text.setdefault(text, []).append(kind)
                pairs = [(by_text[str(atom)].pop(), atom) for atom in group]
            for kind, atom in pairs:
                if _KIND_TO_METATYPE[kind] != atom.metatype:
                    divergences.add((kind, atom.metatype))

    assert divergences == _KNOWN_METATYPE_DIVERGENCES


def test_every_c_kind_the_corpus_reaches_is_mapped(c_report: dict[str, Any]) -> None:
    """Reject a C kind this file has no mapping for.

    An unmapped kind is a hole in the comparison rather than a passing run.
    """
    seen = {
        answer["kind"]
        for program in c_report["programs"]
        for answer in program.get("answers", [])
    }
    assert seen <= set(_KIND_TO_METATYPE), f"unmapped C kinds: {seen - set(_KIND_TO_METATYPE)}"
    # The corpus is meant to exercise the split C makes; if it stops doing so,
    # the mapping above stops being tested.
    assert {"Symbol", "Expression", "Number", "BigInt", "Bool"} <= seen
