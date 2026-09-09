"""Purpose: verify occurrence identity through native and portable image loads.

Guarantees: colliding copies retain bag multiplicity and receive distinct tokens;
    empty targets retain every token [tested: test_image_collision_rule;
    commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
"""

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import sys

import pytest

import metta.aio as _aio_surface
from metta import MeTTa, S, V
from metta._errors.errors import EngineError


@pytest.mark.parametrize("suffix", ["fast", "fast.gz"])
def test_image_collision_rule(tmp_path, suffix):
    """File replacement and a second filename preserve the cut's four counts."""
    first = tmp_path / f"first.{suffix}"
    second = tmp_path / f"second.{suffix}"
    atom = S.row(1)
    with MeTTa() as m, m.space() as source, m.space() as empty:
        source.add(atom)
        original = source.blame(atom)
        assert len(original) == 1
        assert source.save(first, format="fast") == 1
        shutil.copyfile(first, second)
        assert first.read_bytes() == second.read_bytes()
        empty.load(first)
        assert list(empty.atoms()) == [atom]
        assert empty.blame(atom) == original
        counts = [len(source)]
        for path in (first, first, second):
            source.load(path)
            tokens = source.blame(atom)
            counts.append(len(source))
            assert len(tokens) == len(set(tokens)) == len(source)
            assert original[0] in tokens
        assert counts == [1, 2, 2, 3]
        for expected in (2, 1, 0):
            before = source.blame(atom)
            assert source.remove(atom)
            assert source.blame(atom) == before[1:]
            assert len(source) == expected


def test_image_tokens_survive_an_actor_change(tmp_path):
    """A receiving process retains the sender's identity and advances its clock."""
    path = tmp_path / "remote.fast"
    script = """
import json, sys
from metta import MeTTa, S
with MeTTa() as m, m.space() as s:
    s.add(S.row(1), S.row(1))
    s.save(sys.argv[1], format='fast')
    print(json.dumps([str(t) for t in s.blame(S.row(1))]))
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(path)],
        env=dict(os.environ, METTA_ACTOR="image-sender", METTA_GENERATION="1000000"),
        capture_output=True, text=True, check=True,
    )
    expected = json.loads(result.stdout)
    with MeTTa() as m, m.space() as target:
        target.load(path)
        assert list(map(str, target.blame(S.row(1)))) == expected
        target.add(S.row(2))
        token = target.blame(S.row(2))[0]
        assert str(token[1]) == m.info()["actor"]
        assert token[2].value > max(t[2].value for t in target.blame(S.row(1)))


def write_payload(m, path, image, *, hash_payload=True):
    """Build a checksummed malformed image with the engine's own binary writer."""
    header, _ = path.read_bytes().split(b"\n", 1)
    payload_path = path.with_suffix(".payload")
    m.runtime.must(
        "term_string(_Image, Text), "
        "setup_call_cleanup(open(Path, write, _Out, [type(binary)]), "
        "fast_write(_Out, _Image), close(_Out))",
        Text=image, Path=str(payload_path),
    )
    payload = payload_path.read_bytes()
    if hash_payload:
        header = header.rsplit(b"\t", 1)[0] + b"\t" + hashlib.sha256(payload).hexdigest().encode()
    path.write_bytes(header + b"\n" + payload)


@pytest.mark.parametrize(
    ("identity", "tokens"),
    [
        ("identity(image, 3)", "[1]"),
        ("identity(image, 3)", "[1, 1]"),
        ("identity(image, 3)", "[1, t(image, 1)]"),
        ("identity(image, 3)", "[1, t(other, -1)]"),
        ("identity(image, 3)", "[1, t(other, 3)]"),
        ("identity(image, 3)", "[1, t(other, 2.0)]"),
        ("identity(image, 3)", "[1, t('', 2)]"),
        ("identity(image, 3)", "[1, t(_, 2)]"),
        ("identity(image, 3)", "[1, _]"),
        ("identity(image, 3)", "[1|_]"),
        ("identity('', 3)", "[1, 2]"),
        ("identity(image, -1)", "[1, 2]"),
        ("identity(image, 9223372036854775808)", "[1, 2]"),
    ],
)
def test_invalid_occurrences_do_not_replace_a_loaded_image(tmp_path, identity, tokens):
    """Correct hashes cannot authorize missing, duplicate or malformed identity."""
    path = tmp_path / "invalid.fast"
    with MeTTa() as m, m.space() as target, m.space() as donor:
        donor.add(S.row(1), S.row(2))
        donor.save(path, format="fast")
        target.load(path)
        before = target.blame(S.row(V.x))
        write_payload(m, path, f"metta_fast_image({identity}, "
                      f"[space(0, root, [[row, 1], [row, 2]], [], {tokens})], [], [], [])")
        with pytest.raises(EngineError, match="corrupt or incomplete"):
            target.load(path)
        assert list(target.atoms()) == [S.row(1), S.row(2)]
        assert target.blame(S.row(V.x)) == before


def test_image_integrity_covers_occurrence_metadata(tmp_path):
    """A token-only edit with the former checksum is refused before decoding."""
    path = tmp_path / "integrity.fast"
    with MeTTa() as m, m.space() as source:
        source.add(S.row(1))
        source.save(path, format="fast")
        write_payload(m, path, "metta_fast_image(identity(changed, 2), "
                      "[space(0, root, [[row, 1]], [], [1])], [], [], [])",
                      hash_payload=False)
        with pytest.raises(EngineError, match="integrity"):
            source.load(path)
        assert len(source) == 1


def test_async_blame_keeps_the_synchronous_identity():
    """The generated async door reads the same held occurrences on its worker."""
    async def check():
        with MeTTa() as context, context.space() as space:
            space.add(S.row(1), S.row(1))
            before = space.blame(S.row(1))
            async with _aio_surface.AsyncMeTTa(metta=space) as mirrored:
                assert await mirrored.blame(S.row(1)) == before
                await mirrored.remove(S.row(1))
                assert await mirrored.blame(S.row(1)) == before[1:]

    asyncio.run(check())
