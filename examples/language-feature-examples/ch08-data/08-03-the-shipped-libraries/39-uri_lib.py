"""Purpose: compose URI components, resolve references and encode query relations.

Guarantees: the same 55 claims as 39-uri_lib.metta.
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/39-uri_lib.metta; commit=24b96f8ec8468bc97cec35e1d71ce689ede7fdcf].
"""

from metta import G, S, lib
from metta._errors.errors import MettaError


def twin(m):
    """Preserve URI structure and move Unicode through percent-encoded pairs."""
    m += lib.uri
    m += lib.pairs
    m += lib.encoding

    def refused(call):
        """Read a native refusal through the evaluation boundary."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    parts, build = m.fn.uri_parts, m.fn.uri_build
    normalize, resolve = m.fn.uri_normalize, m.fn.uri_resolve
    encode, decode = m.fn.uri_encode, m.fn.uri_decode
    parse_query, build_query = m.fn.uri_query_parse, m.fn.uri_query_build

    assert parts(G("")) == [((G("path"), G("")),)]
    assert parts(G("?#")) == [((G("path"), G("")), (G("query"), G("")), (G("fragment"), G("")))]
    assert parts(G("https://User:Pass@[::1]:0012/a%2Fb?q=1#F")) == [(
        (G("scheme"), G("https")), (G("authority"), G("User:Pass@[::1]:0012")),
        (G("path"), G("/a%2Fb")), (G("query"), G("q=1")), (G("fragment"), G("F")),
    )]
    assert parts(G("urn:Example:ABC")) == [((G("scheme"), G("urn")), (G("path"), G("Example:ABC")))]
    assert build(()) == [G("")]
    assert build(((G("query"), G("")), (G("fragment"), G("")))) == [G("?#")]
    assert build(((G("path"), G("/x")), (G("authority"), G("host:")), (G("scheme"), G("http")))) == [G("http://host:/x")]
    assert build(S.uri_parts(G("a:b?x#"))) == [G("a:b?x#")]

    assert normalize(G("HTTP://User:Pass@HOST/a/%2e%2e/b?x=%7e#F")) == [G("http://User:Pass@host/b?x=~#F")]
    assert normalize(G("urn:Example:ABC")) == [G("urn:Example:ABC")]
    assert normalize(G("http://HOST/%ff/%c0%af/%2f?#")) == [G("http://host/%FF/%C0%AF/%2F?#")]
    assert normalize(G("../a/./b")) == [G("../a/./b")]
    assert normalize(G("foo:/a/..//b")) == [G("foo:/.//b")]

    assert resolve(G("g"), G("http://a")) == [G("http://a/g")]
    assert resolve(G("../g"), G("http://a/b/c/d;p?q")) == [G("http://a/b/g")]
    assert resolve(G("?"), G("http://a/b?old#f")) == [G("http://a/b?")]
    assert resolve(G("#"), G("http://a/b?old#f")) == [G("http://a/b?old#")]
    assert resolve(G(""), G("http://a/b?old#f")) == [G("http://a/b?old")]
    assert resolve(G("//other/x"), G("http://a/b")) == [G("http://other/x")]
    assert resolve(G("http:g"), G("http://a/b")) == [G("http:g")]
    assert resolve(G("urn:Example:ABC"), G("http://a/b")) == [G("urn:Example:ABC")]
    assert resolve(G("g?y/../x"), G("http://a/b/c/d;p?q")) == [G("http://a/b/c/g?y/../x")]
    assert resolve(G("%2e%2e/g"), G("http://a/b/")) == [G("http://a/b/%2e%2e/g")]

    assert tuple(m.fn.uri_contexts().one()) == (S.path, S.segment, S.query_value, S.fragment)
    assert encode(S.path, G("a b/c?d")) == [G("a%20b/c%3Fd")]
    assert encode(S.segment, G("a b/c?d")) == [G("a%20b%2Fc%3Fd")]
    assert encode(S.query_value, G("a+b&c=d")) == [G("a%2Bb%26c%3Dd")]
    assert encode(S.fragment, G("a+b&c=d/x?y")) == [G("a+b&c=d/x?y")]
    assert encode(S.segment, G("π🙂")) == [G("%CF%80%F0%9F%99%82")]
    assert encode(S.segment, S.utf8_decode((97, 0, 98))) == [G("a%00b")]
    assert decode(G("%CF%80%F0%9F%99%82")) == [G("π🙂")]
    assert decode(G("%252F+a")) == [G("%2F+a")]
    assert tuple(m.fn.utf8_encode(S.uri_decode(G("%00x"))).one()) == (0, 120)

    assert parse_query(S.uri, G("a+b=c+d&&a=2&bare&empty=&")) == [(
        (G("a+b"), G("c+d")), (G("a"), G("2")), (G("bare"), G("")), (G("empty"), G("")),
    )]
    assert parse_query(S.form, G("a+b=c+d&&a=2&bare&empty=&")) == [(
        (G("a b"), G("c d")), (G("a"), G("2")), (G("bare"), G("")), (G("empty"), G("")),
    )]
    assert parse_query(S.uri, G("a=1;b=2&=x")) == [((G("a"), G("1;b=2")), (G(""), G("x")))]
    assert tuple(parse_query(S.form, G("")).one()) == ()
    pairs = ((G("a b"), G("c+d")), (G("a b"), G("")), (G(""), G("π🙂")))
    assert build_query(S.uri, pairs) == [G("a%20b=c%2Bd&a%20b=&=%CF%80%F0%9F%99%82")]
    assert build_query(S.form, pairs) == [G("a+b=c%2Bd&a+b=&=%CF%80%F0%9F%99%82")]
    assert build_query(S.form, ()) == [G("")]
    assert m.fn.pairs_lookup(S.uri_query_parse(S.uri, G("a=1&a=2&b=3")), G("a")) == [G("1"), G("2")]
    assert build_query(S.form, S.uri_query_parse(S.form, G("%2B=%00&x=a/b?c"))) == [G("%2B=%00&x=a/b?c")]

    assert refused(S.uri_parts(G("a b")))
    assert refused(S.uri_parts(S.utf8_decode((97, 0, 98))))
    assert refused(S.uri_parts(G("x%ZZ")))
    assert refused(S.uri_build(((G("path"), G("a")), (G("authority"), G("host")))))
    assert refused(S.uri_build(((G("path"), G("a")), (G("path"), G("b")))))
    assert refused(S.uri_build(((G("missing"), G("x")),)))
    assert refused(S.uri_resolve(G("x"), G("relative")))
    assert refused(S.uri_encode(S.missing, G("x")))
    assert refused(S.uri_decode(G("%")))
    assert refused(S.uri_decode(G("%FF")))
    assert refused(S.uri_decode(G("%C0%AF")))
    assert refused(S.uri_query_parse(S.form, G("x=%ED%A0%80")))
    assert refused(S.uri_query_build(S.missing, ()))


#: MEASURED: all 55 claims, including encoded components, RFC resolution,
#: strict decoding, query relations and refusals. The example pays 125852.
#: [measured 2026-09-13: 118602 inferences, minimum of three fresh serial processes;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/39-uri_lib.metta;
#: fixture=lib_uri with engine/lib QLF artifacts purged;
#: commit=24b96f8ec8468bc97cec35e1d71ce689ede7fdcf].
#: RE-PINNED 2026-09-13, 118602 to 180593 (+61991), Combinatorics, Functional,
#: Pairs and Sets now derive collection operations through MeTTa equations,
#: segments and folds. This example imports the changed provider directly or
#: through its library dependencies [measured 2026-09-13: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=6471fbad35eced5ed6440ebf2c25a053b20221f3].
#: RE-PINNED 2026-09-13, 180593 to 181936 (+1343), The validated range
#: continuation now lives in the private support file rather than appearing as
#: a public library head. The import adds its measured loading cost without
#: changing the continuation body [measured 2026-09-13: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=6471fbad35eced5ed6440ebf2c25a053b20221f3].
#: RE-PINNED 2026-09-13, 181936 to 185656 (+3720), Math and Statistics derive
#: their recipes from MeTTa equations; Statistics consolidates finite laws and
#: adds reflective claims. Their collection dependencies share the proper
#: finite expression boundary in lib/_support/collections_data.pl [measured
#: 2026-09-13: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6fa571d1b7059b610f73e9feed657711414251e5].
#: RE-PINNED 2026-09-13, 185656 to 185678 (+22), Vector, Math and the shared
#: collection boundary declare their native effects. The engine reads late
#: provider declarations and retains definition analysis for computed function
#: heads [measured 2026-09-13: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=1d0b78a359f58de49f2f98bed50a6480d56cd5f6].
#: RE-PINNED 2026-09-14, 185678 to 181677 (-4001), Functional applies finished
#: callback arguments through reduce; Statistics derives exact coefficient rows
#: and Combinatorics retires its native probability provider [measured
#: 2026-09-14: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 181677
