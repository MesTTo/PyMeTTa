"""Purpose: compare crypto values and password records with Python and SWI.

Guarantees: generated Unicode, octets, intervals and password records preserve
their contracts across the Python face
[tested: test_hashes_and_hmac_agree_for_generated_values,
test_password_records_interoperate_with_swi_and_hashlib,
test_generated_password_records_and_mismatches; commit=28c6146d805b5adba3047ffc72b2508c11816636].
Owns resources: pytest owns fixture files; subprocesses are joined.
"""

import base64
import hashlib
import hmac
import json
import re
import subprocess

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from metta import G, S, lib
from metta._errors.errors import EngineError, SourceNotFound

TEXT = st.text(st.characters(blacklist_categories=("Cs",)), max_size=40)
ALGORITHMS = ("sha1", "sha224", "sha256", "sha384", "sha512", "sha3_256")


@pytest.fixture(scope="module")
def cr(metta):
    """Import the shipped native face once for the generated cases."""
    metta += lib.crypto
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


@settings(max_examples=100, deadline=None)
@given(TEXT, st.binary(max_size=150), st.sampled_from(ALGORITHMS))
def test_hashes_and_hmac_agree_for_generated_values(cr, text, data, algorithm):
    """Text and bytes take different explicit encodings and match hashlib/hmac."""
    encoded = text.encode("utf-8")
    assert cr.fn.crypto_hash(S[algorithm], G(text)).one() == hashlib.new(algorithm, encoded).hexdigest()
    assert cr.fn.crypto_hash_bytes(S[algorithm], tuple(data)).one() == hashlib.new(algorithm, data).hexdigest()
    assert cr.fn.crypto_hmac(S[algorithm], G(text), G(text)).one() == hmac.digest(encoded, encoded, algorithm).hex()
    assert cr.fn.crypto_hmac_bytes(S[algorithm], tuple(encoded), tuple(data)).one() == hmac.digest(encoded, data, algorithm).hex()


def test_file_hashes_exact_bytes_and_keeps_the_file(cr, tmp_path):
    """A non-ASCII file spanning several native buffers is neither transcoded nor edited."""
    path = tmp_path / "bytes.dat"
    for data in (b"", bytes(range(256)) * 1025 + b"\x00\xff"):
        path.write_bytes(data)
        for algorithm in ALGORITHMS:
            assert cr.fn["crypto-hash-file!"](S[algorithm], G(str(path))).one() == hashlib.new(algorithm, data).hexdigest()
        assert path.read_bytes() == data
    path.unlink()
    with pytest.raises(SourceNotFound, match="does not exist"):
        cr.fn["crypto-hash-file!"](S.sha256, G(str(path))).one()


@settings(max_examples=60, deadline=None)
@given(st.integers(-(2**1024), 2**1024), st.integers(1, 2**1024))
def test_secure_integer_intervals_keep_arbitrary_size_bounds(cr, lower, width):
    """The native interval sampler never narrows bounds to machine integers."""
    value = cr.fn.crypto_random_integer(lower, lower + width).one()
    assert lower <= value < lower + width
    assert cr.fn.crypto_random_integer(lower, lower + 1) == [lower]


def test_random_zero_and_invalid_counts(cr):
    """Empty requests are values; malformed counts and intervals raise."""
    assert cr.fn.crypto_random_hex(0) == [G("")]
    assert tuple(cr.fn.crypto_random_bytes(0).one()) == ()
    values = tuple(cr.fn.crypto_random_bytes(257).one())
    assert len(values) == 257 and all(0 <= value <= 255 for value in values)
    for count in (-1, 1.5, 2**256):
        with pytest.raises(EngineError):
            cr.fn.crypto_random_bytes(count).one()
    for lower, upper in ((0, 0), (2, 1), (1.5, 2)):
        with pytest.raises(EngineError):
            cr.fn.crypto_random_integer(lower, upper).one()


def password_record(password, salt, iterations):
    """Construct the documented SWI envelope from Python's independent PBKDF2."""
    digest = hashlib.pbkdf2_hmac("sha512", password.encode(), salt, iterations)
    salt64, digest64 = (base64.b64encode(value).decode().rstrip("=") for value in (salt, digest))
    return f"$pbkdf2-sha512$t={iterations}${salt64}${digest64}"


def test_password_records_interoperate_with_swi_and_hashlib(cr):
    """Default and explicit costs produce native-compatible self-describing records."""
    password = "fixture é\x00🦊"
    for cost in (None, 0, 4):
        arguments = (G(password),) if cost is None else (G(password), cost)
        record = cr.fn.crypto_password_hash(*arguments).one()
        empty, algorithm, parameters, salt64, digest64 = record.split("$")
        assert empty == "" and algorithm == "pbkdf2-sha512"
        iterations = int(parameters.removeprefix("t="))
        assert iterations == 2 ** (18 if cost is None else cost)
        salt = base64.b64decode(salt64 + "==")
        assert len(salt) == 16 and len(base64.b64decode(digest64 + "==")) == 64
        assert record == password_record(password, salt, iterations)
        assert cr.fn.crypto_password_verify(G(password), G(record)).one() is True
        assert cr.fn.crypto_password_verify(G("different"), G(record)).one() is False
        verification = subprocess.run(
            ["swipl", "--on-error=status", "-q", "-f", "none", "-g",
             "use_module(library(crypto)),use_module(library(http/json)),"
             "json_read_dict(current_input,D),get_dict(password,D,P),get_dict(record,D,R),"
             "atom_string(A,R),crypto_password_hash(P,A),halt"],
            input=json.dumps({"password": password, "record": record}, ensure_ascii=False),
            capture_output=True, text=True, check=False,
        )
        assert verification.returncode == 0, verification.stdout + verification.stderr


@settings(max_examples=70, deadline=None)
@given(TEXT, st.binary(max_size=48), st.integers(1, 50))
def test_generated_password_records_and_mismatches(cr, password, salt, iterations):
    """Valid legacy salts and non-power-of-two iteration counts remain verifiable."""
    record = password_record(password, salt, iterations)
    assert cr.fn.crypto_password_verify(G(password), G(record)).one() is True
    assert cr.fn.crypto_password_verify(G(password + "different"), G(record)).one() is False


@settings(max_examples=40, deadline=None)
@given(st.text(alphabet=" \t\n!?=-()", min_size=1, max_size=20),
       st.sampled_from((1, 2, 3, 4)))
def test_corrupt_password_record_fields_raise(cr, corruption, field):
    """Invalid fields never become a Boolean mismatch or a partially parsed record."""
    fields = password_record("fixture", b"salt", 1).split("$")
    fields[field] += corruption
    with pytest.raises(EngineError):
        cr.fn.crypto_password_verify(G("fixture"), G("$".join(fields))).one()


@pytest.mark.parametrize("cost", [-1, 1.5, 31, 2**1024])
def test_password_cost_refuses_before_expensive_work(cr, cost):
    """Out-of-range costs cannot allocate an enormous exponent or reach PBKDF2."""
    with pytest.raises(EngineError):
        cr.fn.crypto_password_hash(G("fixture"), cost).one()
