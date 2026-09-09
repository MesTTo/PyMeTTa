"""Purpose: check source-size reporting against authored and generated fixtures.

Owns resources: pytest's tmp_path owns the fixture package and removes it under
the suite's temporary-directory policy.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "extensions/python/tools"))

import artifacts  # noqa: E402 -- inspect the checkout's output declarations
import filesizes  # noqa: E402 -- exercise the REPORT's actual reader


def test_file_sizes_use_declared_ownership(tmp_path):
    """Count generated regions once and retain authored siblings and native code."""
    package = tmp_path / "extensions/python/metta"
    package.mkdir(parents=True)
    sources = {"whole.py": "# generated\nvalue = 1\n", "empty.pyi": "",
               "native.pl": "value(1).\n", "half.py": "authored\n# begin\ngenerated\n# end\nauthored",
               "plain.py": "a\nb\nc\n"}
    for name, text in sources.items():
        (package / name).write_text(text, encoding="utf-8")
    command = ("fixture",)
    outputs = (artifacts.Output("extensions/python/metta/*.py", contains="# generated"),
               artifacts.Output("extensions/python/metta/half.py", ("# begin", "# end")))
    record = artifacts.Artifact("fixture", ("source",), command, outputs, command, (command,))
    files = filesizes.census(tmp_path, (record,))
    counts = {item.path: (item.physical, item.generated, item.handwritten) for item in files}
    assert counts == {"whole.py": (2, 2, 0), "empty.pyi": (0, 0, 0), "native.pl": (1, 0, 1),
                      "half.py": (5, 3, 2), "plain.py": (3, 0, 3)}
    report = filesizes.report(files)
    assert report["packages"] == {".": {"files": 5, "physical": 11, "generated": 5, "handwritten": 6}}
    assert [row["path"] for row in report["largest"]] == ["half.py", "plain.py", "whole.py", "native.pl", "empty.pyi"]
    (package / "half.py").write_text(sources["half.py"] + "\n# end", encoding="utf-8")
    with pytest.raises(ValueError, match="repeated output region"):
        filesizes.census(tmp_path, (record,))


def test_file_size_distributions_and_review_boundary():
    """The report covers empty input, a singleton and the exact review boundary."""
    assert set(filesizes.distribution([]).values()) == {None}
    assert set(filesizes.distribution([7]).values()) == {7}
    assert filesizes.distribution([0, 4, 8, 12, 16]) == {
        "min": 0, "q1": 4, "median": 8, "q3": 12, "max": 16, "mean": 8,
    }
    report = filesizes.report((filesizes.FileSize("a/short.py", 3000, 1000),
                              filesizes.FileSize("b/long.pl", 2001, 0)))
    assert [row["path"] for row in report["above_review_boundary"]] == ["b/long.pl"]
    assert report["packages"]["a"]["handwritten"] == 2000
    assert filesizes.report(())["largest"] == []
