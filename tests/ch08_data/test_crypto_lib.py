"""Purpose: lib_crypto from Python: hashes agree with Python's hashlib,
determinism holds, unknown algorithms refuse loudly, and random hex is
well formed and fresh per call.
Guarantees:
  - the five hashes shared with library(sha) are all pinned on the full
    library(crypto) seat [tested:
    test_hashes_are_deterministic_and_agree_with_hashlib;
    commit=59792b524568755a2fbfe1c5f7cdb571bd78a3bf]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import hashlib
import re

import pytest

from metta.errors import EngineError


@pytest.fixture(scope="module")
def cr(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta.run("!(import! &self (library lib_crypto))")
    return metta


def test_hashes_are_deterministic_and_agree_with_hashlib(cr):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    for algorithm in ("sha1", "sha224", "sha256", "sha384", "sha512"):
        (digest,) = cr.eval(f'(crypto-hash {algorithm} "hello")')
        assert digest == getattr(hashlib, algorithm)(b"hello").hexdigest()
        assert cr.eval(f'(crypto-hash {algorithm} "hello")') == [digest]
        assert len(digest.value) == getattr(hashlib, algorithm)().digest_size * 2


def test_unknown_algorithm_is_loud(cr):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(EngineError):
        cr.eval('(crypto-hash not-a-hash "x")')


def test_random_hex_is_well_formed_and_fresh(cr):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (a,) = cr.eval("(crypto-random-hex 16)")
    (b,) = cr.eval("(crypto-random-hex 16)")
    assert re.fullmatch(r"[0-9a-f]{32}", a.value)
    assert re.fullmatch(r"[0-9a-f]{32}", b.value)
    assert a != b
