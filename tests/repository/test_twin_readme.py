"""Purpose: the twin corpus's README describes the corpus that is there.

Its coverage table states a count per chapter and a total, which are the
numbers a reader uses to decide where to look. They are also the part that
rots: the MeTTa corpus README said "143 of the 365" against a directory of
386 for long enough that two of its three numbers were wrong and their halves
no longer summed, because the only tool that recomputed them could not find
its upstream checkout from a worktree and skipped in every gate
[measured 2026-09-22].

Derived rather than remembered. Nothing here spells a number: the table is
read out of the README and compared against the tree, so adding a twin fails
this until the table says so.

Assumes: the corpus is at extensions/python/examples/language-feature-examples
    and its chapters are the `chNN-` directories there.
Guarantees:
  - every chapter in the tree has a row, and every row a chapter, so a new
    chapter cannot be silently undocumented
    [tested: test_every_chapter_has_a_row_and_every_row_a_chapter; commit=dce8c4a68a653c350c4fbde798b9f09d1b113550]
  - each row's count is the number of twins in that chapter
    [tested: test_each_row_counts_its_chapter; commit=dce8c4a68a653c350c4fbde798b9f09d1b113550]
  - the stated total is the sum of the rows and the size of the corpus
    [tested: test_the_total_is_the_corpus; commit=dce8c4a68a653c350c4fbde798b9f09d1b113550]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import re

from metta._roots import workspace

CORPUS = workspace() / "extensions/python/examples/language-feature-examples"
README = CORPUS / "README.md"

#: A row of the coverage table: a backticked chapter directory, then its count.
_ROW = re.compile(r"^\| `(ch[\w-]+)` \| (\d+) \|", re.MULTILINE)


def _twins(chapter: str) -> int:
    """How many twins that chapter holds, ignoring compiled caches."""
    return len([p for p in (CORPUS / chapter).rglob("*.py") if "__pycache__" not in p.parts])


def _rows() -> dict[str, int]:
    return {name: int(count) for name, count in _ROW.findall(README.read_text(encoding="utf-8"))}


def test_every_chapter_has_a_row_and_every_row_a_chapter():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    rows = _rows()
    assert rows, "the coverage table is gone from the twin corpus README"
    present = {p.name for p in CORPUS.iterdir() if p.is_dir() and p.name.startswith("ch")}
    assert set(rows) == present, (
        f"undocumented chapters: {sorted(present - set(rows))}; "
        f"rows for chapters that are not there: {sorted(set(rows) - present)}"
    )


def test_each_row_counts_its_chapter():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    wrong = {name: (stated, _twins(name)) for name, stated in _rows().items()
             if stated != _twins(name)}
    assert not wrong, (
        "the twin corpus README counts a chapter wrongly; stated against actual: "
        + ", ".join(f"{n} says {s} and holds {a}" for n, (s, a) in sorted(wrong.items()))
    )


def test_the_total_is_the_corpus():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    rows = _rows()
    actual = sum(_twins(name) for name in rows)
    assert sum(rows.values()) == actual, "the rows do not sum to the corpus"
    stated = re.search(r"(\d+) twins across", README.read_text(encoding="utf-8"))
    assert stated is not None, "the README no longer states a total"
    assert int(stated.group(1)) == actual, (
        f"the README says {stated.group(1)} twins and the corpus holds {actual}"
    )
