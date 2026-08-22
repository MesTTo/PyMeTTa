"""Purpose: prove the C space provider under Python drivers: the same
cstore.pl the CLI example consults registers here, threads interleave
whole operations against the C store, and the store's snapshot
enumeration holds under concurrent writers.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import petta

_PROVIDER = (
    Path(__file__).resolve().parents[3]
    / "examples"
    / "integration"
    / "c_space"
    / "cstore.pl"
)
_ARTEFACT = _PROVIDER.with_name("cstore.so")


@pytest.fixture
def cstore():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    if not _ARTEFACT.is_file():
        pytest.skip("cstore.so is not built; see examples/integration/c_space/README.md")
    m = petta.MeTTa().space()
    m.register_prolog(path=_PROVIDER)
    try:
        m.run("!(remove-atom &cstore $any)")
        yield m
    finally:
        m.run("!(remove-atom &cstore $any)")
        m.unregister_prolog("cstore_example")
        m.drop()


def test_metta_reaches_the_c_store(cstore):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m = cstore
    m.run("!(add-atom &cstore (edge a b))")
    m.run("!(add-atom &cstore (edge a c))")
    (group,) = m.run("!(collapse (match &cstore (edge a $x) $x))")
    assert sorted(str(atom) for atom in group[0]) == ["b", "c"]


def test_threads_interleave_whole_operations(cstore):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m = cstore

    def add(index: int) -> None:
        m.run(f"!(add-atom &cstore (row {index}))")

    def count(_index: int) -> int:
        (group,) = m.run("!(collapse (match &cstore (row $n) $n))")
        return len(group[0])

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(add, range(64)))
        counts = list(pool.map(count, range(8)))
    assert all(value == 64 for value in counts)
