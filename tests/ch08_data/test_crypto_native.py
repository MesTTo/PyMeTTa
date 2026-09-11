"""Purpose: inject failures into actual copies of the checked OpenSSL adapter.

Guarantees: native failures raise with their operation even when OpenSSL supplied
no error-queue entry; a comparison result comes from CRYPTO_memcmp
[tested: test_native_provider_failures_raise, test_password_comparison_uses_crypto_memcmp; commit=28c6146d805b5adba3047ffc72b2508c11816636].
Owns resources: pytest removes copied sources and objects; each child is joined.
"""

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "lib/lib_crypto/support/crypto_native.c"
HEADERS = """
#include <openssl/bn.h>
#include <openssl/crypto.h>
#include <openssl/evp.h>
#include <openssl/rand.h>
"""
DIGEST = "digest(sha256,utf8(fixture),none,_)"
MAC = "digest(sha256,utf8(fixture),[1,2,3],_)"
PASSWORD = "password_hash(fixture,[1,2,3],1,_)"
INTEGER = "random_below_hex('100000000000000000000000000000001',_)"


def compile_adapter(tmp_path, replacement):
    """Change only provider call results in a copied translation unit."""
    source = tmp_path / "crypto_failure.c"
    binary = tmp_path / "crypto_failure.so"
    source.write_text(HEADERS + replacement + "\n" + SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
    built = subprocess.run(
        ["swipl-ld", "-shared", "-O1", "-o", str(binary), str(source), "-lcrypto"],
        capture_output=True, text=True, check=False,
    )
    assert built.returncode == 0, built.stdout + built.stderr
    return binary


def run_adapter(binary, goal):
    """Load one private adapter in a fresh process, with no competing registration."""
    return subprocess.run(
        ["swipl", "--on-error=status", "-q", "-f", "none", "-g",
         f"use_module(library(shlib)),load_foreign_library({json.dumps(str(binary))},install_lib_crypto),"
         f"{goal},halt"],
        capture_output=True, text=True, check=False,
    )


@pytest.mark.parametrize(("operation", "failure", "goal"), [
    ("EVP_MD_fetch", "NULL", DIGEST),
    ("EVP_MD_get_size", "0", DIGEST),
    ("EVP_MD_CTX_new", "NULL", DIGEST),
    ("EVP_DigestInit_ex2", "0", DIGEST),
    ("EVP_DigestUpdate", "0", DIGEST),
    ("EVP_DigestFinal_ex", "0", DIGEST),
    ("EVP_MAC_fetch", "NULL", MAC),
    ("EVP_MAC_CTX_new", "NULL", MAC),
    ("EVP_MAC_init", "0", MAC),
    ("EVP_MAC_CTX_get_mac_size", "0", MAC),
    ("EVP_MAC_update", "0", MAC),
    ("EVP_MAC_final", "0", MAC),
    ("OPENSSL_malloc", "NULL", DIGEST),
    ("OPENSSL_malloc", "NULL", "random_bytes(16,_)"),
    ("RAND_priv_bytes_ex", "0", "random_bytes(16,_)"),
    ("RAND_priv_bytes_ex", "-1", "random_bytes(16,_)"),
    ("BN_hex2bn", "0", INTEGER),
    ("BN_new", "NULL", INTEGER),
    ("BN_priv_rand_range", "0", INTEGER),
    ("BN_bn2hex", "NULL", INTEGER),
    ("PKCS5_PBKDF2_HMAC", "0", PASSWORD),
])
def test_native_provider_failures_raise(tmp_path, operation, failure, goal):
    """Every checked provider boundary refuses an injected failure before publishing."""
    binary = compile_adapter(tmp_path, f"\n#undef {operation}\n#define {operation}(...) ({failure})\n")
    outcome = run_adapter(
        binary,
        f"catch((lib_crypto_native:{goal},R=answered),E,R=raised(E)),"
        f"R=raised(error(crypto_native_error('{operation}',0,Message),_)),"
        "sub_string(Message,_,_,_,'without an error-queue entry')",
    )
    assert outcome.returncode == 0, outcome.stdout + outcome.stderr


def test_password_comparison_uses_crypto_memcmp(tmp_path):
    """Replacing only CRYPTO_memcmp changes a deliberately mismatched comparison."""
    binary = compile_adapter(tmp_path, "\n#undef CRYPTO_memcmp\n#define CRYPTO_memcmp(...) (0)\n")
    outcome = run_adapter(
        binary,
        "lib_crypto_native:password_hash(fixture,[],1,Expected),"
        "lib_crypto_native:password_verify(different,[],1,Expected,true)",
    )
    assert outcome.returncode == 0, outcome.stdout + outcome.stderr


def test_zero_bytes_and_singleton_do_not_request_entropy(tmp_path):
    """The zero-byte case avoids the provider and OpenSSL handles a singleton."""
    binary = compile_adapter(tmp_path, "\n#undef RAND_priv_bytes_ex\n#define RAND_priv_bytes_ex(...) (0)\n")
    outcome = run_adapter(
        binary,
        "lib_crypto_native:random_bytes(0,[]),"
        "lib_crypto_native:random_below_hex('1',\"0\")",
    )
    assert outcome.returncode == 0, outcome.stdout + outcome.stderr
