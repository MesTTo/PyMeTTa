"""Purpose: every python fence in the examples index is real lines from the
example it names, so the page cannot drift from code that runs.

The seat's examples all run under the gate, and `test_examples.py` executes
them. What nothing checked until now is the INDEX: it quotes 37 of them, and a
quoted line that has been reworded, renamed or invented reads exactly like one
that has not. `test_readme.py` covers only the repository root README, so these
fences were an ungated documentation corpus.

The fences are excerpts rather than whole files, so they cannot be executed the
way the root README's blocks are. They are held to the weaker claim that is
still worth holding: every non-blank line is a line of the file the fence is
attributed to. That catches a renamed door, a reworded call and an invented
keyword argument, which is what a reader would copy and be wrong about. It does
not claim the excerpt runs on its own, and it is not meant to.

Each fence is preceded by a line holding the example's repository-relative path
in backticks, which is what pairs the two.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import re

import pytest

from metta._roots import workspace

_INDEX = workspace() / "extensions/python/examples/README.md"
_TEXT = _INDEX.read_text(encoding="utf-8")

#: A backticked repository-relative path, then the fence it introduces.
_ATTRIBUTED = re.compile(
    r"`(extensions/python/examples/[^`]+\.py)`\s*\n+```python\n(.*?)```",
    re.DOTALL,
)
_PAIRS = _ATTRIBUTED.findall(_TEXT)


def test_the_index_attributes_every_python_fence():
    """A fence with no path above it would be skipped by the check below."""
    fences = len(re.findall(r"```python\n", _TEXT))
    assert fences >= 30, f"only {fences} python fences; the index lost its examples"
    assert len(_PAIRS) == fences, (
        f"{fences} python fences but {len(_PAIRS)} carry a backticked source path; "
        f"put the example's repository-relative path in backticks immediately above "
        f"each fence, which is what pairs a snippet with the file it quotes"
    )


@pytest.mark.parametrize(("path", "snippet"), _PAIRS, ids=[p for p, _ in _PAIRS])
def test_every_snippet_line_is_a_line_of_the_example(path, snippet):
    """Each non-blank line of the fence appears in the file it names."""
    source = workspace() / path
    assert source.is_file(), f"the index quotes {path}, which is not in the tree"
    known = {line.rstrip() for line in source.read_text(encoding="utf-8").splitlines()}
    unmatched = [
        line.rstrip()
        for line in snippet.splitlines()
        # `...` on its own marks an elision, and is the one line that is ours.
        if line.strip() and line.strip() != "..." and line.rstrip() not in known
    ]
    assert not unmatched, (
        f"{path}: {len(unmatched)} line(s) in the index are not in the file, so the "
        f"page shows code that is not there. First: {unmatched[0]!r}"
    )
