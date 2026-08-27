"""Purpose: prove executable translation, output, and bilingual docs can fail.

Guarantees:
  - source spans accept the ruled adjacent form and refuse missing or drifting
    translation and output claims [tested:
    test_source_spans_bind_translation_and_output_comments_to_one_call,
    test_unmappable_checked_comment_is_rejected,
    test_translation_drift_is_rejected,
    test_shown_output_drift_is_rejected; commit=8bfe05c3850776543ece25a85038242f10b1d841]
  - emitted doctests execute in both languages with order-insensitive,
    multiplicity-preserving comparison [tested:
    test_emitted_doctests_run_in_both_languages_as_alpha_multisets,
    test_bilingual_doctests_reject_a_python_side_multiplicity_drift;
    commit=8bfe05c3850776543ece25a85038242f10b1d841]
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from metta import MeTTa, S

TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))

from executable_docs import (  # noqa: E402  -- tools are scripts, not package modules
    DocumentationDriftError,
    source_expectations,
    verify_claim,
    verify_defined_examples,
)


@dataclass
class _DefinedView:
    name: str
    py: object
    space: object


def _source(tmp_path: Path, translation: str, *outputs: str) -> Path:
    path = tmp_path / "checked.py"
    comments = "\n".join(f"# => {output}" for output in outputs)
    path.write_text(
        f"claim('edge', S.edge(S.a, S.b), lambda term: [term])\n# -> {translation}\n{comments}\n",
        encoding="utf-8",
    )
    return path


def test_source_spans_bind_translation_and_output_comments_to_one_call(tmp_path):
    """Token spans attach both adjacent comments to the executable call."""
    path = _source(tmp_path, "(edge a b)", "(edge a b)")
    expectations = source_expectations(path)
    assert len(expectations) == 1
    assert str(expectations[0].emitted) == "(edge a b)"
    assert [str(answer) for answer in expectations[0].answers] == ["(edge a b)"]
    assert verify_claim(
        S.edge(S.a, S.b),
        lambda term: [term],
        path=path,
        line=1,
    ) == (S.edge(S.a, S.b),)


def test_translation_drift_is_rejected(tmp_path):
    """Planted drift in ``# ->`` names both comment and actual emission."""
    path = _source(tmp_path, "(edge a stale)", "(edge a b)")
    with pytest.raises(DocumentationDriftError, match="emitted MeTTa drift") as caught:
        verify_claim(
            S.edge(S.a, S.b),
            lambda term: [term],
            path=path,
            line=1,
        )
    assert "comment=[(edge a stale)]" in str(caught.value)
    assert "actual=[(edge a b)]" in str(caught.value)


def test_shown_output_drift_is_rejected(tmp_path):
    """Planted drift in ``# =>`` names the checked and executed outputs."""
    path = _source(tmp_path, "(edge a b)", "stale")
    with pytest.raises(DocumentationDriftError, match="shown output drift") as caught:
        verify_claim(
            S.edge(S.a, S.b),
            lambda term: [term],
            path=path,
            line=1,
        )
    assert "comment=[stale]" in str(caught.value)
    assert "actual=[(edge a b)]" in str(caught.value)


def test_comment_markers_inside_strings_cannot_satisfy_a_source_span(tmp_path):
    """Tokenize distinguishes documentation comments from string contents."""
    path = tmp_path / "string.py"
    path.write_text(
        "claim('edge', S.edge(S.a, S.b), lambda term: [term])\n"
        'markers = "# -> (edge a b) # => (edge a b)"\n',
        encoding="utf-8",
    )
    with pytest.raises(DocumentationDriftError, match="adjacent # ->"):
        source_expectations(path)


def test_unmappable_checked_comment_is_rejected(tmp_path):
    """A marker outside a known claim is warned about, never skipped."""
    path = tmp_path / "orphan.py"
    path.write_text("value = 1\n# -> stale\n# => 1\n", encoding="utf-8")
    with pytest.raises(DocumentationDriftError, match="not attached to a claim source span"):
        source_expectations(path)


def test_emitted_doctests_run_in_both_languages_as_alpha_multisets():
    """Order and duplicate counts use the shared alpha-multiset relation."""
    space = MeTTa().space("&executable-docs")

    @space.define
    def doc_choices(n: int):
        """Repeat the selected value around its predecessor.

        >>> !(doc-choices 2)
        [2, 1, 2]
        """
        yield n
        yield n - 1
        yield n

    def reordered_python(n: int):
        """Repeat the selected value around its predecessor.

        >>> !(doc-choices 2)
        [2, 1, 2]
        """
        yield n
        yield n
        yield n - 1

    reordered = _DefinedView(doc_choices.name, reordered_python, space)
    assert verify_defined_examples(reordered) == 1


def test_bilingual_doctests_reject_a_python_side_multiplicity_drift():
    """Dropping one duplicate on only the Python side is observable drift."""
    space = MeTTa().space("&executable-docs-drift")

    @space.define
    def doc_duplicates(n: int):
        """Repeat one value twice.

        >>> !(doc-duplicates 3)
        [3, 3]
        """
        yield n
        yield n

    def missing_copy(n: int):
        """Repeat one value twice.

        >>> !(doc-duplicates 3)
        [3, 3]
        """
        yield n

    mismatched = _DefinedView(doc_duplicates.name, missing_copy, space)
    with pytest.raises(DocumentationDriftError, match="Python output drift") as caught:
        verify_defined_examples(mismatched)
    assert "comment=[3, 3] actual=[3]" in str(caught.value)
    assert "missing=[3] extra=[]" in str(caught.value)
