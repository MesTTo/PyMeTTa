"""Purpose: pin catalog-driven deprecation warnings and explanations.

Guarantees:
  - ``(deprecated name since remedy)`` stays queryable, warns at direct and
    bound callable doors, appears in ``explain``, and stops warning after the
    declaration is removed [tested:
    test_deprecation_catalog_rows_drive_warnings_and_explanations;
    commit=d74e2e828cd9272882dcf907cfaf095d2d147ce0]
  - an empty catalog answers every name through one process-wide apply-seam
    probe, with no per-name goal-string read [tested:
    test_an_empty_deprecation_catalog_costs_one_cheap_probe;
    commit=670917170da5800ba74346382ed4f47756bcfc29]
"""

from __future__ import annotations

import warnings

import pytest

import metta as metta_package
from metta import S, V


def test_deprecation_catalog_rows_drive_warnings_and_explanations(metta):
    """One catalog row is the source of truth at every callable surface."""
    declaration = S.deprecated(
        S["deprecated-function"],
        S["0.2.0"],
        S.use(S["modern-function"]),
    )
    catalog = metta_package.catalog

    with metta._new_space() as space:

        @space.define(name="deprecated-function")
        def legacy(value):
            return S.modern(value)

        catalog.add(declaration)
        try:
            rows = catalog.match(
                S.deprecated(S["deprecated-function"], V.since, V.remedy)
            )
            assert [(str(row.since), str(row.remedy)) for row in rows] == [
                ("0.2.0", "(use modern-function)")
            ]

            warning = r"deprecated-function is deprecated since 0\.2\.0; \(use modern-function\)"
            with pytest.warns(DeprecationWarning, match=warning):
                assert list(legacy(S.value)) == [S.modern(S.value)]
            with pytest.warns(DeprecationWarning, match=warning):
                assert list(space.fn.deprecated_function(S.other)) == [
                    S.modern(S.other)
                ]

            explanation = metta.run("!(explain (deprecated-function value))")[0][0]
            items = {str(item.children[0]): item for item in explanation.children}
            assert str(items["deprecated"]) == (
                "(deprecated 0.2.0 (use modern-function))"
            )
        finally:
            catalog.remove(declaration)

        with warnings.catch_warnings(record=True) as seen:
            warnings.simplefilter("always")
            assert list(legacy(S.current)) == [S.modern(S.current)]
        assert seen == []


def test_an_empty_deprecation_catalog_costs_one_cheap_probe(
    metta, monkeypatch
):
    """The common case performs no per-name goal-string read at all.

    Until 2026-08-26 every distinct name's first call through a callable
    door compiled a fresh ``once/1`` goal string to learn the catalog was
    empty: 1,311 inferences measured on the first ``fn.parse`` call where
    the steady state is 5. With the process-wide apply-seam flag, an empty
    catalog answers every name without a single ``petta_deprecation``
    goal-string read.
    """
    from metta import _space as space_module

    reads = []
    real_once = space_module.Runtime.once

    def counting_once(self, goal, *args, **kwargs):
        if "petta_deprecation(" in goal:
            reads.append(goal)
        return real_once(self, goal, *args, **kwargs)

    monkeypatch.setattr(space_module.Runtime, "once", counting_once)
    with metta._new_space() as space:
        for name in ("parse", "repr", "car-atom"):
            answers = space.fn[name] if name == "car-atom" else getattr(
                space.fn, name
            )
        [answer] = space.fn.parse('"probe"')
        [answer] = space.fn.repr(answer)
    assert reads == []
