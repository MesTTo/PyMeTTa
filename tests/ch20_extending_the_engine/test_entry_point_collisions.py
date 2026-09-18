"""Purpose: refuse competing providers independently of discovery order."""

import importlib.metadata
import itertools
from types import SimpleNamespace

import pytest

from metta import seam


def _advertising(entries):
    """An `entry_points` stand-in answering the same entries for any group."""
    return lambda **_: entries


def test_entry_point_collision_reports_both_owners(monkeypatch):
    """Two distributions cannot silently share one entry-point identity."""
    entries = [
        importlib.metadata.EntryPoint(name="same", value=f"{name}:install", group=seam.GROUP)._for(
            SimpleNamespace(name=name, version="1", metadata={"Name": name})
        )
        for name in ("owner-one", "owner-two")
    ]
    messages = []
    for permutation in itertools.permutations(entries):
        monkeypatch.setattr(importlib.metadata, "entry_points", _advertising(permutation))
        with pytest.raises(ValueError) as failure:
            seam.advertised()
        messages.append(str(failure.value))
        assert all(name in messages[-1] for name in ("same", "owner-one", "owner-two"))
    assert messages[0] == messages[1]


@pytest.mark.parametrize("change", ["target", "version", "owner"])
def test_discovery_refuses_collisions_before_loading_any_entry(monkeypatch, change):
    """A partial load cannot make an ambiguous provider list look complete."""
    entries = [
        importlib.metadata.EntryPoint(
            name="same", value=f"module{number if change == 'target' else 0}:install",
            group="audit.collision",
        )._for(SimpleNamespace(
            name=f"owner{number if change == 'owner' else 0}",
            version=str(number if change == "version" else 0),
        ))
        for number in range(2)
    ]
    loaded = []
    monkeypatch.setattr(importlib.metadata, "entry_points", _advertising(entries))
    monkeypatch.setattr(importlib.metadata.EntryPoint, "load", lambda self: loaded.append(self))
    with pytest.raises(ValueError, match="competing entry point"):
        seam.discover("audit.collision")
    assert loaded == []


def test_duplicate_metadata_for_one_distribution_is_one_advertisement(monkeypatch):
    """Distribution objects and normalized name spellings do not create owners."""
    entries = [
        importlib.metadata.EntryPoint(name="same", value="module:install", group=seam.GROUP)._for(
            SimpleNamespace(name=name, version="1")
        )
        for name in ("Owner_One", "owner.one")
    ]
    monkeypatch.setattr(importlib.metadata, "entry_points", _advertising(entries))
    assert seam.advertised() == {"same": entries[0]}
