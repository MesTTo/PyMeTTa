"""Purpose: UUID generations, namespaces, complete names and byte round trips.

Guarantees: the same 45 claims as 33-uuid_lib.metta.
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/33-uuid_lib.metta; commit=d5de00cc183b4b395b552f3aae7fca87752ef38c].
"""

from metta import G, S, lib
from metta._errors.errors import MettaError


def twin(m):
    """Generate identifiers, preserve names and bytes, and check malformed input."""
    m += lib.crypto
    m += lib.uuid
    m += lib.encoding
    m += lib.string

    def refused(call):
        """Read a native refusal through the evaluation boundary."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    version, variant, valid = m.fn.uuid_version, m.fn.uuid_variant, m.fn.uuid_is
    name, timestamp = m.fn.uuid_name, m.fn.uuid_timestamp
    to_bytes, of_bytes = m.fn.uuid_bytes, m.fn.uuid_of_bytes

    assert len(m.fn.crypto_random_bytes(16).one()) == 16
    assert version(S["uuid-random!"]()) == [4]
    assert variant(S["uuid-random!"]()) == [S.rfc]
    assert valid(S["uuid-random!"]()) == [True]
    assert m.fn["uuid-random!"]().one() != m.fn["uuid-random!"]().one()
    assert version(S["uuid-time!"]()) == [1]
    assert variant(S["uuid-time!"]()) == [S.rfc]
    assert timestamp(S["uuid-time!"]()).one() > 0

    assert list(m.fn.uuid_namespaces().one()) == [S.dns, S.url, S.oid, S.x500]
    assert name(3, S.dns, G("example.com")) == [G("9073926b-929f-31c2-abc9-fad77ae3e8eb")]
    assert name(5, S.dns, G("example.com")) == [G("cfbff0d1-9375-5685-968c-48ce8b15ae17")]
    assert name(5, G("6ba7b810-9dad-11d1-80b4-00c04fd430c8"), G("example.com")).one() == name(
        5, S.dns, G("example.com"),
    ).one()
    assert name(3, S.url, G("http://example.com")) == [G("d632b50c-7913-3137-ae9a-2d93f56e70d5")]
    assert name(5, S.oid, G("1.3.6.1.4.1")) == [G("106dd502-8b3e-50db-80ed-1134f5c18eae")]
    assert name(5, S.x500, G("cn=Test")) == [G("1a09ab7e-5f76-53b6-b866-3b565a53dc51")]
    assert name(5, S.dns, G("")) == [G("4ebd0208-8328-5d69-8c44-ec50939c0967")]
    assert name(5, S.dns, G("é")) == [G("ebfe0af8-3997-5ade-b634-ba92cf69f557")]
    assert name(3, S.dns, G("漢")) == [G("1f9d873c-79c5-37f3-a181-6bab16c1f1c9")]
    assert name(5, S.dns, S.string_from_codes((97, 0, 98))) == [
        G("0a63f66b-e02f-5d2d-9fd4-aad819cf5352"),
    ]

    assert m.fn.uuid_nil() == [G("00000000-0000-0000-0000-000000000000")]
    assert valid(S.uuid_nil()) == [True]
    assert version(S.uuid_nil()) == [0]
    assert variant(S.uuid_nil()) == [S.ncs]
    assert variant(G("00000000-0000-0000-c000-000000000000")) == [S.microsoft]
    assert variant(G("ffffffff-ffff-ffff-ffff-ffffffffffff")) == [S.future]
    assert timestamp(G("13814000-1dd2-11b2-8000-000000000000")) == [0.0]
    assert list(timestamp(S["uuid-random!"]())) == []
    assert list(timestamp(S.uuid_nil())) == []

    assert valid(G("CFBFF0D1-9375-5685-968C-48CE8B15AE17")) == [True]
    assert m.fn.hex_encode(S.uuid_bytes(G("cfbff0d1-9375-5685-968c-48ce8b15ae17"))) == [
        G("cfbff0d193755685968c48ce8b15ae17"),
    ]
    assert of_bytes(S.uuid_bytes(G("CFBFF0D1-9375-5685-968C-48CE8B15AE17"))) == [
        G("cfbff0d1-9375-5685-968c-48ce8b15ae17"),
    ]
    assert list(to_bytes(S.uuid_nil()).one()) == [0] * 16
    assert of_bytes(S.hex_decode(G("ffffffffffffffffffffffffffffffff"))) == [
        G("ffffffff-ffff-ffff-ffff-ffffffffffff"),
    ]

    assert valid(G("------------------------------------")) == [False]
    assert valid(S.string_replace(S.uuid_nil(), G("-"), S.string_from_codes((0,)))) == [False]
    assert valid(G("cfbff0d193755685968c48ce8b15ae17")) == [False]
    assert valid(G("zfbff0d1-9375-5685-968c-48ce8b15ae17")) == [False]
    assert valid(3) == [False]
    assert refused(S.uuid_version(G("broken")))
    assert refused(S.uuid_timestamp(G("broken")))
    assert refused(S.uuid_of_bytes((1, 2)))
    assert refused(S.uuid_of_bytes((0,) * 15 + (256,)))
    assert refused(S.uuid_name(2, S.dns, G("name")))
    assert refused(S.uuid_name(5, S.missing, G("name")))
    assert refused(S.uuid_name(5, G("broken"), G("name")))


#: MEASURED: all 45 claims, including full names, literal UUID separators and
#: the explicit crypto import that demonstrates secure bytes beside identifiers.
#: Field inspection validates digits natively instead of decoding random bytes.
#: [measured 2026-09-12: 188846 inferences against the example's 190880, minimum
#: of three fresh serial processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/33-uuid_lib.metta;
#: fixture=lib_uuid at its functional commit with engine/lib QLF artifacts purged;
#: commit=d5de00cc183b4b395b552f3aae7fca87752ef38c].
BUDGET = 188846
