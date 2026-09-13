"""Purpose: compress complete bytes and publish validated archive contents.

Guarantees: the same 54 claims as 41-compression_lib.metta.
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/41-compression_lib.metta; commit=7b42d5ee5cecb82709617b7ed08dfa2c1441f268].
Owns resources: finally removes the temporary directory; native operations
close their streams and remove unpublished staging on each exit.
"""

from metta import G, S, lib
from metta._errors.errors import MettaError


def twin(m):
    """Use one envelope parameter for bytes, files and archive validation."""
    m += lib.file
    m += lib.compression
    fn = m.fn

    def refused(call):
        """Observe an operation refusal through the public evaluation door."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    assert list(fn.compression_formats().one()) == [S.gzip, S.zlib]
    assert fn.path_join(G("one"), G("two")) == [G("one/two")]
    data = (0, 128, 255, 10)
    gzip_bytes = fn.compress_bytes(S.gzip, 6, data).one()
    zlib_bytes = fn.compress_bytes(S.zlib, 6, data).one()
    assert gzip_bytes[0] == 31
    assert gzip_bytes[1] == 139
    assert list(fn.decompress_bytes(S.gzip, gzip_bytes).one()) == list(data)
    assert list(fn.decompress_bytes(S.zlib, zlib_bytes).one()) == list(data)
    assert list(fn.decompress_bytes(S.gzip, fn.compress_bytes(S.gzip, 0, ()).one()).one()) == []
    assert list(fn.decompress_bytes(S.zlib, fn.compress_bytes(S.zlib, 9, ()).one()).one()) == []
    assert list(fn.decompress_bytes(S.gzip, fn.compress_bytes(S.gzip, 9, (1, 1, 1, 1, 1)).one()).one()) == [1, 1, 1, 1, 1]
    assert list(fn.decompress_bytes(S.zlib, fn.compress_bytes(S.zlib, 0, (1, 2, 3)).one()).one()) == [1, 2, 3]
    assert refused(S.compress_bytes(S.invented, 6, data))
    assert refused(S.compress_bytes(S.gzip, -1, data))
    assert refused(S.compress_bytes(S.gzip, 10, data))
    assert refused(S.compress_bytes(S.gzip, 6, (256,)))
    assert refused(S.compress_bytes(S.gzip, 6, (-1,)))
    assert refused(S.decompress_bytes(S.gzip, ()))
    assert refused(S.decompress_bytes(S.gzip, (31, 139)))
    assert refused(S.decompress_bytes(S.zlib, gzip_bytes))
    assert refused(S.decompress_bytes(S.gzip, zlib_bytes))

    work = fn["temp-dir!"](G("compression-lib")).one()
    try:
        source = fn.path_join(work, G("source")).one()
        packed = fn.path_join(work, G("packed.gz")).one()
        restored = fn.path_join(work, G("restored")).one()
        assert fn["write-bytes!"](source, data) == [True]
        assert fn["compress-file!"](S.gzip, 6, source, packed) == [True]
        assert list(fn.decompress_bytes(S.gzip, fn["read-bytes!"](packed).one()).one()) == list(data)
        assert fn["decompress-file!"](S.gzip, packed, restored) == [True]
        assert list(fn["read-bytes!"](restored).one()) == list(data)
        assert fn["compress-file!"](S.zlib, 0, source, source) == [True]
        assert fn["decompress-file!"](S.zlib, source, source) == [True]
        assert list(fn["read-bytes!"](source).one()) == list(data)
        assert fn["write-bytes!"](packed, (31, 139)) == [True]
        assert refused(S["decompress-file!"](S.gzip, packed, restored))
        assert list(fn["read-bytes!"](restored).one()) == list(data)

        fixtures = G("examples/ch08-data/08-03-the-shipped-libraries/_fixtures")
        fixture = fn.path_join(fixtures, G("compression-data.zip")).one()
        entries = fn["archive-entries!"](fixture).one()
        assert len(entries) == 4
        assert (entries[0][1], entries[0][2]) == (0, G("./"))
        assert list(fn["archive-read!"](fixture, 2).one()) == list(data)
        assert list(fn["archive-read!"](fixture, 3).one()) == []
        assert refused(S["archive-read!"](fixture, 0))
        assert refused(S["archive-read!"](fixture, 4))
        extracted = fn.path_join(work, G("extracted")).one()
        assert fn["archive-extract!"](fixture, extracted) == [True]
        assert list(fn["read-bytes!"](fn.path_join(extracted, G("sub/bytes.bin")).one()).one()) == list(data)
        assert list(fn["read-bytes!"](fn.path_join(extracted, G("empty")).one()).one()) == []
        assert refused(S["archive-extract!"](fixture, extracted))
        assert list(fn["read-bytes!"](fn.path_join(extracted, G("sub/bytes.bin")).one()).one()) == list(data)
        assert fn["compress-file!"](S.gzip, 6, fixture, packed) == [True]
        assert fn["archive-entries!"](packed) == [entries]
        assert list(fn["archive-read!"](packed, 2).one()) == list(data)
        second = fn.path_join(work, G("second")).one()
        assert fn["archive-extract!"](packed, second) == [True]
        assert list(fn["read-bytes!"](fn.path_join(second, G("sub/bytes.bin")).one()).one()) == list(data)

        assert fn["archive-entries!"](fn.path_join(fixtures, G("compression-unicode.zip")).one()).one()[0][2] == G("café/π🙂")
        assert fn["archive-entries!"](fn.path_join(fixtures, G("compression-legacy.zip")).one()).one()[0][2] == G("café")
        assert fn["archive-entries!"](fn.path_join(fixtures, G("compression-unicode-extra.zip")).one()).one()[0][2] == G("café/π🙂")

        unsafe = fn.path_join(fixtures, G("compression-unsafe.zip")).one()
        refused_path = fn.path_join(work, G("refused")).one()
        assert list(fn["archive-read!"](unsafe, 0).one()) == [42]
        assert refused(S["archive-extract!"](unsafe, refused_path))
        assert fn.dir_exists(refused_path) == [False]
        assert fn.file_exists(fn.path_join(work, G("escape")).one()) == [False]
    finally:
        assert fn["delete-tree!"](work) == [True]


#: MEASURED: all 54 claims cover envelopes, publication, extraction and ZIP names.
#: The example pays 229506; both notations import File before Compression.
#: [measured 2026-09-13: 204351 inferences, minimum of three fresh serial processes;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/41-compression_lib.metta;
#: fixture=lib_compression with engine/lib QLF artifacts purged; commit=7b42d5ee5cecb82709617b7ed08dfa2c1441f268].
#: RE-PINNED 2026-09-14, 204351 to 226243 (+21892), String now derives nine
#: text recipes through MeTTa equations, with one function parameter for
#: padding and complete validation before empty construction; all import
#: consumers are measured after the provider change [measured 2026-09-14: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 226243
