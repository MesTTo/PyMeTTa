"""Purpose: preserve registration identity across listener notifications."""

import pytest

from metta import seam


@pytest.mark.parametrize("name", ["plain", "O'Reilly", 'say "yes"', "'edge'", 'a "quoted" registration O\'Reilly'])
def test_registration_identity_is_not_parsed_from_prose(monkeypatch, name):
    """Listeners receive the exact point and name on insertion and removal."""
    seen = []
    monkeypatch.setattr(seam, "_LISTENERS", [lambda point, who, undo: seen.append((point, who))])
    point = seam.point("audit registration point", "declaration", fields=("value",), doc="identity")
    try:
        point.register(name, value=1)
        point.unregister(name)
        assert seen == [(point.name, name), (point.name, name)]
    finally:
        seam.withdraw(point.name)
