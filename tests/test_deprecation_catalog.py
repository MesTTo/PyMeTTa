"""Purpose: pin catalog-driven deprecation warnings and explanations.

Guarantees:
  - ``(deprecated name since remedy)`` stays queryable, warns at direct and
    bound callable doors, appears in ``explain``, and stops warning after the
    declaration is removed [tested:
    test_deprecation_catalog_rows_drive_warnings_and_explanations;
    commit=d74e2e828cd9272882dcf907cfaf095d2d147ce0]
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
