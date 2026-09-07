"""Purpose: one kind set for the reserved control envelope, held to the tree.

`error(metta_control_signal(Kind, Detail), context(metta, _))` is how this
engine hands a refusal or a spent bound to a host seat. Three places name the
kinds and none of them derives from the others: the thrower, wherever it lives;
`metta_control_signal_info/3` in `extensions/python/metta/shim.pl`, which
decides whether the envelope is classified at all; and `_EXCEPTION_TYPES` in
`extensions/python/metta/_engine.py`, which decides what Python raises.

Drift between them is silent both ways and has happened both ways. A kind the
shim admits and Python does not becomes a bare `EngineError` (the `restraint`
signal did, until the cache-policies branch added it). A kind Python names and
the shim does not is never classified, so the entry is dead. And a kind that is
thrown and named in neither reaches the caller as the raw term.

`thrown_kinds` below derives the set from the tree rather than writing it
down, so this is a lane and not a list to keep updated. The Node seat's own
classifier maps the same set by hand until the refusal catalog lands (design
journal section 22); until then it is derived from here, with
`python -c "from tests.repository.test_error_kinds import thrown_kinds"` run
from `extensions/python`, so the two seats cannot be told apart by reading
different lists.

Guarantees:
  - the kinds thrown across the tree, the kinds the live shim classifies and
    the kinds Python raises for are one set, with both differences named
    [tested: test_every_thrown_kind_reaches_python_as_its_own_exception,
    test_the_shim_classifies_every_kind_python_names; commit=490cd97c382e5cafd0cf7b7ba2fc1aeecbf10b44]
  - SWI's own unenveloped resource balls stay classified beside them
    [tested: test_swis_own_resource_balls_are_classified_too; commit=490cd97c382e5cafd0cf7b7ba2fc1aeecbf10b44]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import re
import subprocess

import pytest

from metta import _engine

#: The two spellings that NAME a kind in this tree: the envelope term itself,
#: and shim.pl's metta_py_raise/2, which builds the envelope around a kind its
#: caller passes. Both are matched with a literal atom in the kind position; an
#: occurrence with a variable there is a reader or a re-thrower, not a source.
_NAMES_A_KIND = re.compile(
    r"metta_control_signal\(\s*([a-z][a-z_0-9]*)\s*,"
    r"|metta_py_raise\(\s*([a-z][a-z_0-9]*)\s*,"
)

#: Where a kind may be thrown from. Tests are excluded because a test naming a
#: kind is exercising the seam, not publishing one.
_SOURCE_ROOTS = ("engine", "lib", "extensions")
_SOURCE_SUFFIXES = (".pl", ".py", ".c")


def thrown_kinds(repo_root):
    """Every control-signal kind this tree names, read from the tree.

    TRACKED files, asked of git rather than walked, which is the rule
    ``check_component_python`` in ``check.sh`` already states for the same
    reason: a walk finds build output nothing here owns. The Node seat's
    ``npm run build:browser`` copies the whole engine into
    ``extensions/node/_runtime/``, so a walk reads every engine source twice,
    once live and once as whatever the last build left behind, and a stale copy
    would report a kind this tree no longer throws. A walk also has to know
    where the checkout SITS: an agent worktree of this repository lives under a
    directory literally named ``ai-tmp``, and pruning that by absolute path
    prunes the whole tree.
    """
    listing = subprocess.run(
        ["git", "ls-files", "--", *_SOURCE_ROOTS],
        cwd=repo_root, capture_output=True, text=True, timeout=60, check=True,
    )
    found = set()
    for name in listing.stdout.splitlines():
        path = repo_root / name
        if path.suffix not in _SOURCE_SUFFIXES or "tests" in path.parts:
            continue
        for envelope, raised in _NAMES_A_KIND.findall(
            path.read_text(encoding="utf-8", errors="replace")
        ):
            found.add(envelope or raised)
    return found


@pytest.fixture(name="tree_kinds")
def _tree_kinds(repo_root):
    """The tree's kinds, or a skip where git will not enumerate the checkout.

    The same reading its neighbour takes in test_workspace_paths.py: a CI
    checkout git declines to read, over ownership or otherwise, is a fact about
    that machine, and reporting it as a repository defect blames the wrong
    thing. thrown_kinds itself raises, because the Node seat calls it to
    GENERATE its map and a silent empty answer there would be worse.
    """
    try:
        return thrown_kinds(repo_root)
    except (OSError, subprocess.SubprocessError) as unavailable:
        pytest.skip(f"git ls-files is unavailable here: {unavailable}")


def test_every_thrown_kind_reaches_python_as_its_own_exception(tree_kinds):
    """The tree's kinds and Python's exception map are one set.

    An extra on the left is a signal that reaches a caller as a bare
    EngineError; an extra on the right is an entry nothing can ever produce.
    """
    named = set(_engine._EXCEPTION_TYPES)
    assert tree_kinds, "the scrape found nothing, so it is measuring itself"
    assert tree_kinds - named == set(), "thrown but unclassified in Python"
    assert named - tree_kinds == set(), "classified in Python but never thrown"


def test_the_shim_classifies_every_kind_python_names():
    """The live shim admits each kind, so no Python entry is unreachable.

    Asked of the running engine rather than read out of shim.pl, because what
    matters is what metta_control_signal_info/3 DOES with a term of that kind,
    which is also what _engine._raise asks it at the moment of the failure.
    """
    runtime = _engine.runtime()
    for kind in sorted(_engine._EXCEPTION_TYPES):
        row = runtime.once(
            "atom_string(Kind, KindText), "
            "metta_control_signal_info("
            "  error(metta_control_signal(Kind, detail), context(metta, Kind)), "
            "  Kind, _Detail)",
            KindText=kind,
        )
        assert row, f"the shim does not classify metta_control_signal({kind}, _)"


def test_swis_own_resource_balls_are_classified_too():
    """A bound spent in a NESTED query arrives unenveloped, and still lands.

    apply_once opens its query with PL_Q_CATCH_EXCEPTION, so it takes SWI's
    ball before the enclosing call_with_inference_limit/3 can wrap it. Both
    balls are classified by name, with no detail to report.
    """
    runtime = _engine.runtime()
    for ball, kind in (
        ("inference_limit_exceeded", "inference_limit"),
        ("time_limit_exceeded", "time_limit"),
    ):
        row = runtime.once(
            "atom_string(Ball, BallText), "
            "metta_control_signal_info(Ball, Kind, _Detail)",
            BallText=ball,
        )
        assert row.get("Kind") == kind
