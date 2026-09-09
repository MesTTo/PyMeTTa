"""Purpose: prove settings and layer projections reject drift and reach boot.

Guarantees: a defect in each generated region is refused, and the reflected
layer rows equal the declared graph [tested: this file; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from metta import MeTTa, Rows, S, V
from metta._layers import ORDERS

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "extensions/python/tools"))

import boundsgen  # noqa: E402 -- test the checkout's generation commands
import layergen  # noqa: E402 -- test the checkout's generation commands


@pytest.mark.parametrize(("generator", "relative", "marker"), [
    (boundsgen, "extensions/python/metta/_catalog/bounds.py", boundsgen.END),
    (boundsgen, "DEVELOPING.md", boundsgen.DOC_END),
    (layergen, "pyproject.toml", layergen.END),
    (layergen, "DEVELOPING.md", layergen.DOC_END),
], ids=["boundsgen-config", "boundsgen-guide", "layergen-imports", "layergen-guide"])
def test_each_declaration_projection_refuses_an_independent_edit(
    monkeypatch, generator, relative, marker,
):
    """Run the actual check with one changed region, then with pristine input."""
    path = ROOT / relative
    original = path.read_text()
    planted = original.replace(marker, "# planted region drift\n" + marker, 1)
    assert planted != original
    read = Path.read_text
    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", lambda file, *a, **kw: planted if file == path else read(file, *a, **kw))
        assert generator.main([]) == 1
    assert generator.main([]) == 0


def test_boot_publishes_the_declared_package_orders():
    """Every package order is queryable through the ordinary catalog match."""
    with MeTTa() as context:
        rows = context.space("&metta").match(S.layer(V.package, V.order), into=Rows)
        assert {str(row.package): row.order.value for row in rows} == dict(ORDERS)


@pytest.mark.parametrize("suffix", [".py", ".pl", ".pyi"])
def test_nested_package_evidence_rejects_a_missing_test(tmp_path, monkeypatch, suffix):
    """Moving a claimed source deeper must not hide an invalid citation."""
    monkeypatch.syspath_prepend(str(ROOT / "tests/checks"))
    import check_evidence_tags as evidence

    path = tmp_path / "extensions/python/metta/_package/nested" / f"unit{suffix}"
    path.parent.mkdir(parents=True)
    comment = "%" if suffix == ".pl" else "#"
    tag, missing = "tested", "test_layout_planted_absent"
    path.write_text(f"{comment} [{tag}: {missing}]\n")
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    sites = evidence.claim_sites()
    assert len(sites) == 1
    found, _line, kind, body = sites[0]
    assert found == path and kind == "tested"
    known = evidence.Evidence({}, {}, frozenset(), {})
    assert evidence.tested_problems(body, known, path) == [
        "names test_layout_planted_absent, which is not a test in the tree",
    ]
