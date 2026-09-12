"""Purpose: verify native compression and extraction with Python format oracles.

Guarantees: generated octets interoperate with gzip and zlib; independent TAR
and ZIP writers test names, kinds, nested filters and publication refusals.
[tested: test_compression_interoperability, test_nested_archive_filters,
test_archive_refused_entries; commit=WORKTREE].
Owns resources: pytest owns each temporary directory; context managers close
archive writers, and each native library call owns its streams and staging.
"""

import bz2
import gzip
import io
import locale
import lzma
import struct
import tarfile
import zipfile
import zlib

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from metta import G, S, lib
from metta._errors.errors import EngineError


@pytest.fixture(scope="module")
def compression(metta):
    """Import the same generated native face used by the executable chapter."""
    metta += lib.compression
    return metta


@pytest.mark.skipif(not hasattr(locale, "CODESET"), reason="POSIX CODESET observes the thread locale")
def test_archive_locale_restoration(compression):
    """Observe thread and process locales during nesting and after every exit."""
    before = locale.nl_langinfo(locale.CODESET)
    process = locale.setlocale(locale.LC_CTYPE)
    rt = compression.runtime
    inside = rt.must(
        "lib_compression_native:with_utf8(("
        "py_call(locale:nl_langinfo(Code),Encoding),"
        "py_call(locale:setlocale(Category),Process),"
        "lib_compression_native:with_utf8(py_call(locale:nl_langinfo(Code),Nested))))",
        Code=locale.CODESET, Category=locale.LC_CTYPE,
    )
    assert inside["Encoding"].replace("-", "").upper() == "UTF8"
    assert inside["Nested"] == inside["Encoding"]
    assert inside["Process"] == process
    assert locale.nl_langinfo(locale.CODESET) == before
    assert rt.once("lib_compression_native:with_utf8(fail)") == {}
    with pytest.raises(EngineError, match="archive_locale_probe"):
        rt.must("lib_compression_native:with_utf8(throw(archive_locale_probe))")
    assert locale.nl_langinfo(locale.CODESET) == before
    assert locale.setlocale(locale.LC_CTYPE) == process


@settings(max_examples=100)
@example(b"", 0)
@example(bytes(range(256)), 9)
@example(b"\x00" * 32768, 6)
@given(st.binary(max_size=2048), st.integers(0, 9))
def test_compression_interoperability(compression, data, level):
    """Both directions use independent implementations for every envelope."""
    for envelope, encode, decode in [(S.gzip, gzip.compress, gzip.decompress),
                                    (S.zlib, zlib.compress, zlib.decompress)]:
        native = bytes(compression.fn.compress_bytes(envelope, level, tuple(data)).one())
        assert decode(native) == data
        reference = encode(data, level)
        assert bytes(compression.fn.decompress_bytes(envelope, tuple(reference)).one()) == data


def tar_bytes(rows):
    """Write native TAR headers from name, kind and data or link target rows."""
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        for name, kind, value in rows:
            entry = tarfile.TarInfo(name)
            entry.type = kind
            if kind == tarfile.REGTYPE:
                entry.size = len(value)
                archive.addfile(entry, io.BytesIO(value))
            else:
                if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                    entry.linkname = value
                archive.addfile(entry)
    return output.getvalue()


@pytest.mark.parametrize("writer", ["tar", "zip"])
def test_archive_unicode_and_byte_identity(compression, tmp_path, writer):
    """Independent archive writers preserve Unicode names and every octet."""
    path = tmp_path / "archive"
    data = bytes(range(256))
    names = ["café/π🙂", ".env", "COM10", "space inside", "empty"]
    if writer == "tar":
        path.write_bytes(tar_bytes([(name, tarfile.REGTYPE, data if index < 4 else b"")
                                    for index, name in enumerate(names)]))
    else:
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for index, name in enumerate(names):
                archive.writestr(name, data if index < 4 else b"")
    fn = compression.fn
    entries = fn["archive-entries!"](G(str(path))).one()
    assert [entry[2] for entry in entries] == [G(name) for name in names]
    destination = tmp_path / "out"
    assert fn["archive-extract!"](G(str(path)), G(str(destination))).one() is True
    for index, name in enumerate(names):
        expected = data if index < 4 else b""
        assert bytes(fn["archive-read!"](G(str(path)), index).one()) == expected
        assert (destination / name).read_bytes() == expected


@pytest.mark.parametrize("writer", ["tar", "zip"])
def test_empty_archive_publication(compression, tmp_path, writer):
    """Zero entries remain an empty archive and publish an empty directory."""
    path = tmp_path / "archive"
    if writer == "tar":
        path.write_bytes(tar_bytes([]))
    else:
        with zipfile.ZipFile(path, "w"):
            pass
    fn = compression.fn
    assert list(fn["archive-entries!"](G(str(path))).one()) == []
    with pytest.raises(EngineError, match="archive_entry"):
        fn["archive-read!"](G(str(path)), 0).one()
    destination = tmp_path / "out"
    assert fn["archive-extract!"](G(str(path)), G(str(destination))).one() is True
    assert list(destination.iterdir()) == []


@pytest.mark.parametrize("raw_name", [b"caf\x82", b"caf\xc3\xa9"])
@pytest.mark.parametrize("unicode_extra", ["none", "valid", "stale"])
def test_archive_legacy_zip_names(compression, tmp_path, raw_name, unicode_extra):
    """CP437 supplies the default while a valid Unicode extra field prevails."""
    path = tmp_path / "archive"
    expected = "café/π🙂" if unicode_extra == "valid" else raw_name.decode("cp437")
    placeholder = b"caf" + b"_" * (len(raw_name) - 3)
    info = zipfile.ZipInfo(placeholder.decode())
    if unicode_extra != "none":
        crc = zlib.crc32(raw_name) ^ (unicode_extra == "stale")
        payload = b"\x01" + struct.pack("<I", crc) + "café/π🙂".encode()
        info.extra = struct.pack("<HH", 0x7075, len(payload)) + payload
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(info, b"bytes")
    packed = path.read_bytes()
    # Equal-length filename replacement in both headers keeps the ZIP offsets
    # intact. The original ASCII name has no UTF8 flag; Python reads CP437.
    assert packed.count(placeholder) == 2
    path.write_bytes(packed.replace(placeholder, raw_name))
    with zipfile.ZipFile(path) as reference:
        assert reference.namelist() == [expected]
    fn = compression.fn
    entries = fn["archive-entries!"](G(str(path))).one()
    assert [entry[2] for entry in entries] == [G(expected)]
    assert bytes(fn["archive-read!"](G(str(path)), 0).one()) == b"bytes"
    destination = tmp_path / "out"
    assert fn["archive-extract!"](G(str(path)), G(str(destination))).one() is True
    assert (destination / expected).read_bytes() == b"bytes"


def test_archive_unconvertible_pathname_is_refused(compression, tmp_path):
    """An unlabelled invalid TAR name raises before the host wide-string call."""
    packed = bytearray(tar_bytes([("caf_", tarfile.REGTYPE, b"bytes")]))
    packed[3] = 255
    packed[148:156] = b" " * 8
    packed[148:156] = f"{sum(packed[:512]):06o}\0 ".encode()
    path = tmp_path / "archive"
    path.write_bytes(packed)
    destination = tmp_path / "out"
    for head, args in [("archive-entries!", ()), ("archive-read!", (0,)),
                       ("archive-extract!", (G(str(destination)),))]:
        with pytest.raises(EngineError, match="archive_pathname"):
            compression.fn[head](G(str(path)), *args).one()
        assert set(tmp_path.iterdir()) == {path}


@pytest.mark.parametrize("name", ["../outside", "/outside", "a/../../outside", "a\\b",
                                  "C:/outside", "a:b", "a*", "a?", "a<", "a>", "a|",
                                  'a"', "a\x01b", "trailing.", "trailing ", " leading",
                                  "NUL.txt", "com1", "LPT9.dat", "COM¹", "LPT².txt"])
def test_archive_unsafe_paths(compression, tmp_path, name):
    """Inspection retains unsafe names; extraction refuses the whole tree."""
    path = tmp_path / "archive"
    path.write_bytes(tar_bytes([("valid", tarfile.REGTYPE, b"ok"),
                                (name, tarfile.REGTYPE, b"bad")]))
    destination = tmp_path / "out"
    fn = compression.fn
    assert bytes(fn["archive-read!"](G(str(path)), 1).one()) == b"bad"
    with pytest.raises(EngineError, match=r"archive_(path|component)"):
        fn["archive-extract!"](G(str(path)), G(str(destination))).one()
    assert set(tmp_path.iterdir()) == {path}


@pytest.mark.parametrize("kind", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE,
                                  tarfile.CHRTYPE, tarfile.BLKTYPE])
def test_archive_refused_entries(compression, tmp_path, kind):
    """Links and special entries never turn into approximated regular files."""
    path = tmp_path / "archive"
    path.write_bytes(tar_bytes([("target", tarfile.REGTYPE, b"target"),
                                ("entry", kind, "target")]))
    fn = compression.fn
    assert len(fn["archive-entries!"](G(str(path))).one()) == 2
    with pytest.raises(EngineError, match="regular_archive_entry"):
        fn["archive-read!"](G(str(path)), 1).one()
    with pytest.raises(EngineError, match="extractable_archive_entry"):
        fn["archive-extract!"](G(str(path)), G(str(tmp_path / "out"))).one()
    assert set(tmp_path.iterdir()) == {path}


@pytest.mark.parametrize("outer", [bytes, bz2.compress, lzma.compress])
@pytest.mark.parametrize("wrap_again", [bytes, gzip.compress])
@pytest.mark.parametrize("damaged", [False, True])
def test_nested_archive_filters(compression, tmp_path, outer, wrap_again, damaged):
    """Gzip checks remain effective inside other filters and multiple layers."""
    data = bytes(range(256)) * 128
    packed = gzip.compress(tar_bytes([("data", tarfile.REGTYPE, data)]), mtime=0)
    if damaged:
        packed = packed[:-8] + bytes([packed[-8] ^ 1]) + packed[-7:]
    path = tmp_path / "archive"
    path.write_bytes(wrap_again(outer(packed)))
    destination = tmp_path / "out"
    fn = compression.fn
    if damaged:
        for head, args in [("archive-entries!", ()), ("archive-read!", (0,)),
                           ("archive-extract!", (G(str(destination)),))]:
            with pytest.raises(EngineError, match=r"(data check|CRC|checksum)"):
                fn[head](G(str(path)), *args).one()
        assert set(tmp_path.iterdir()) == {path}
    else:
        assert bytes(fn["archive-read!"](G(str(path)), 0).one()) == data
        assert fn["archive-extract!"](G(str(path)), G(str(destination))).one() is True
        assert (destination / "data").read_bytes() == data


@pytest.mark.parametrize("damage", ["body", "checksum"])
def test_archive_read_errors_preserve_existing_destination(compression, tmp_path, damage):
    """Truncated TAR bodies and ZIP CRC errors are observed before publication."""
    path = tmp_path / "archive"
    data = bytes(range(256)) * 128
    if damage == "body":
        path.write_bytes(tar_bytes([("data", tarfile.REGTYPE, data)])[:1000])
    else:
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr("data", data)
        packed = path.read_bytes()
        offset = packed.index(data)
        path.write_bytes(packed[:offset] + bytes([packed[offset] ^ 1]) + packed[offset + 1:])
    destination = tmp_path / "out"
    destination.mkdir()
    for head, args in [("archive-entries!", ()), ("archive-read!", (0,)),
                       ("archive-extract!", (G(str(destination)),))]:
        with pytest.raises(EngineError, match="I/O error in read"):
            compression.fn[head](G(str(path)), *args).one()
        assert destination.is_dir()
        assert list(destination.iterdir()) == []
        assert set(tmp_path.iterdir()) == {path, destination}
