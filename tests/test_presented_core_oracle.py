"""Purpose: the presented core is an operational oracle. Every program here
runs twice, through this engine's minimal-MeTTa library and through the
LeaTTa interpreter's `--min` door, which evaluates the same instruction set
that LeaTTa's tests/mettail/metta.mettail transcribes, and the answers must
agree. The corpus stays on the state-free fragment: `function`/`return`,
`cons-atom`, `decons-atom`, `chain`, `superpose-bind`, and `unify`. The
five instructions that need a configuration, a collection, or a host
(`eval`, `evalc`, `context-space`, `metta`, `call-native`) are excluded on
the presentation's own authority: its module header names their semantics
as follow-up presentations.
Assumes:
  - the oracle lives at a fixed local path outside this repository, the
    same assumption tests/conformance/leatta.py documents; CI never has
    it, so the agreement tests skip rather than fail where it is absent
  - the oracle's --min prints one bracketed answer line per bang form,
    after any printed output, per the LeaTTa Main module header
Guarantees:
  - answers compare as multisets within a group, never as ordered lines,
    so an answer-order difference between the evaluators is not a
    divergence [tested: test_the_oracle_lane_catches_a_planted_divergence]
  - the comparator is exercised even where the oracle is absent, by the
    planted-divergence test, which needs no binary
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: widen the corpus with the oracle's own
    --fuzz-generate differential programs once the shared fragment grows
    its stateful legs.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import os
import string
import subprocess
from pathlib import Path

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

_ORACLE_ROOT = Path(os.environ.get("LEATTA_PATH", "/home/user/Dev/LeaTTa"))
_ORACLE_BIN = _ORACLE_ROOT / ".lake" / "build" / "bin" / "LeaTTa"

needs_oracle = pytest.mark.skipif(
    not _ORACLE_BIN.exists(),
    reason="the LeaTTa oracle is a fixed local checkout outside this "
    "repository; agreement is enforced only where it exists, as with "
    "tests/conformance/leatta.py",
)

# The state-free shared fragment. Every program is one bang form with no
# printed output, so each side answers exactly one line.
CORPUS = [
    "!(function (return 42))",
    "!(function (return (a b)))",
    "!(cons-atom a (b c))",
    "!(cons-atom (f 1) (g 2))",
    "!(decons-atom (a b c))",
    "!(decons-atom (a))",
    "!(chain (cons-atom a (b)) $x $x)",
    "!(chain (decons-atom (a b)) $x (c $x))",
    "!(function (chain (cons-atom a (b)) $x (return $x)))",
    "!(chain (function (return 7)) $y (cons-atom $y (8)))",
    "!(superpose-bind ((42 ()) (43 ())))",
    "!(superpose-bind ((a ())))",
    "!(unify (a $x) (a b) $x nope)",
    "!(unify 1 2 yes nope)",
    # THE EVALUATION MASK, on the same fragment. Every row here carries a
    # REDUCIBLE operand in a position the callee's declaration holds back, so a
    # row that agreed only because both sides reduced everything cannot pass by
    # accident. `cons-atom` and `decons-atom` declare `Atom` and `Expression`
    # parameters and an `Atom` result, so the operand arrives as written and
    # the answer is final; `cdr-atom`'s `Expression` result and `chain`'s
    # `%Undefined%` one re-enter evaluation, which is where the sum finally
    # reduces.
    "!(cons-atom (+ 1 2) (b))",
    "!(cons-atom a ((+ 1 2) c))",
    "!(decons-atom ((+ 1 2) b))",
    "!(cdr-atom (cdr-atom (a b c)))",
    "!(chain (cons-atom (+ 1 2) (b)) $x $x)",
    "!(chain (decons-atom ((+ 1 2) b)) $x $x)",
    "!(chain (cons-atom a (b)) $x (cons-atom $x (c)))",
    "!(unify (a $x) (a (+ 1 2)) $x nope)",
    "!(function (return (+ 1 2)))",
]


def _split_answers(line: str) -> list[str]:
    """One bracketed answer line into its sorted individual answers.

    The split is on top-level commas only: an answer such as (a (b c))
    contains no top-level comma, so parenthesised structure survives.
    """
    stripped = line.strip()
    if not (stripped.startswith("[") and stripped.endswith("]")):
        msg = f"not an answer line: {line!r}"
        raise ValueError(msg)
    inner = stripped[1:-1]
    parts: list[str] = []
    depth = 0
    start = 0
    for position, ch in enumerate(inner):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(inner[start:position].strip())
            start = position + 1
    tail = inner[start:].strip()
    if tail:
        parts.append(tail)
    return sorted(parts)


def _oracle_answers(program: str) -> list[str]:
    finished = subprocess.run(
        [str(_ORACLE_BIN), "--min", program],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
        cwd=_ORACLE_ROOT,
    )
    lines = [line for line in finished.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        msg = f"expected one answer line, got {finished.stdout!r}"
        raise ValueError(msg)
    return _split_answers(lines[0])


@pytest.fixture(scope="module")
def minimal(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run("!(import! &self (library minimal_metta_lib))")
    return metta


def _engine_answers(minimal, program: str) -> list[str]:
    groups = minimal.run(program)
    if len(groups) != 1:
        msg = f"expected one answer group, got {groups!r}"
        raise ValueError(msg)
    return sorted(str(atom) for atom in groups[0])


@needs_oracle
@pytest.mark.parametrize("program", CORPUS)
def test_the_presented_core_agrees_with_the_engine_on_the_shared_fragment(  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    minimal, program
):
    assert _engine_answers(minimal, program) == _oracle_answers(program)


_symbols = st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=3).map(
    lambda s: "s" + s
)
_trees = st.recursive(
    _symbols,
    lambda inner: st.lists(inner, min_size=1, max_size=3).map(
        lambda xs: "(" + " ".join(xs) + ")"
    ),
    max_leaves=6,
)


def _has_ambient_meaning(head: str, _memo: dict[str, bool] = {}) -> bool:  # noqa: B006 -- module-lifetime memo, one engine ask per distinct head
    """Whether the SHARED engine already gives this head a meaning.

    The suite's engine is process-global: a registration another test made
    (test_adoptions registers `swap`) outlives its handle, so a drawn head
    that collides answers `(partial swap ())` where the oracle's clean
    world keeps `(swap)` inert. That is legitimate engine behavior, not a
    divergence, so collided draws are assumed away. The catalogue member
    door is the same fun/1-or-special-form union the lint lane asks
    [measured 2026-08-24: the battery order with test_adoptions ahead of
    this file failed the swap draw deterministically in ten of ten runs].
    """
    if head not in _memo:
        from metta import _engine

        runtime = _engine.active_runtime()
        _memo[head] = runtime is not None and bool(
            runtime.once(f"catch(petta_py_catalogue_member('{head}'), _, fail)")
        )
    return _memo[head]


@needs_oracle
@settings(max_examples=25, deadline=None)
@given(head=_symbols, tail=st.lists(_trees, max_size=3))
def test_random_structural_programs_agree_with_the_presented_core(  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    minimal, head, tail
):
    assume(not _has_ambient_meaning(head))
    program = "!(chain (cons-atom {} ({})) $x $x)".format(head, " ".join(tail))
    assert _engine_answers(minimal, program) == _oracle_answers(program)


def test_the_oracle_lane_catches_a_planted_divergence():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert _split_answers("[42, 43]") == _split_answers("[43, 42]")
    assert _split_answers("[42]") != _split_answers("[43]")
    assert _split_answers("[(a (b c)), x]") == ["(a (b c))", "x"]
    with pytest.raises(ValueError):
        _split_answers("no brackets")
