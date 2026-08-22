"""Purpose: lib_crypto from Python: hashes agree with Python's hashlib,
determinism holds, unknown algorithms refuse loudly, and random hex is
well formed and fresh per call.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import hashlib
import re

import pytest

from petta.errors import EngineError


@pytest.fixture(scope="module")
def cr(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run("!(import! &self (library lib_crypto))")
    return metta


def test_hashes_are_deterministic_and_agree_with_hashlib(cr):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (digest,) = cr.eval('(crypto-hash sha256 "hello")')
    assert digest == hashlib.sha256(b"hello").hexdigest()
    assert cr.eval('(crypto-hash sha256 "hello")') == [digest]
    (wide,) = cr.eval('(crypto-hash sha512 "hello")')
    assert wide == hashlib.sha512(b"hello").hexdigest()
    assert len(wide.value) == 128


def test_unknown_algorithm_is_loud(cr):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(EngineError):
        cr.eval('(crypto-hash not-a-hash "x")')


def test_random_hex_is_well_formed_and_fresh(cr):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (a,) = cr.eval("(crypto-random-hex 16)")
    (b,) = cr.eval("(crypto-random-hex 16)")
    assert re.fullmatch(r"[0-9a-f]{32}", a.value)
    assert re.fullmatch(r"[0-9a-f]{32}", b.value)
    assert a != b
