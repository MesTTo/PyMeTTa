"""Purpose: give an executable absence remedy for Rows.one()."""

import pytest

from metta._errors.errors import EngineError
from metta._spaces.results import Rows


@pytest.mark.parametrize("count", [0, 2])
def test_audit_a8_rows_one_names_the_absence_argument(count):
    """The recommended expression works for each refused cardinality."""
    rows = Rows(("x",), [(value,) for value in range(count)])
    with pytest.raises(EngineError, match=r"first\(default=None\)"):
        rows.one()
    assert rows.first(default=None) == (None if count == 0 else rows[0])
