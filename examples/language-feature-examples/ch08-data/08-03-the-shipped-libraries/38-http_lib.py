"""Purpose: route local HTTP requests through equations and owned byte streams.

Guarantees: the same 41 claims as 38-http_lib.metta.
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/38-http_lib.metta; commit=0f22b69cfca5c108e4126bdd56ab9bb2e493744d].
Owns resources: finally stops the named loopback server; scoped resources close
through their library owners.
"""

from metta import TRUE, G, S, V, arrow, lib, typed
from metta._errors.errors import MettaError


def twin(m):
    """Use one request shape for methods, byte bodies, headers and streaming."""
    m += lib.http
    m += lib.encoding
    m.add(typed(S.library_http, arrow(S.Expression, S.Expression)),
          typed(S.read_http, arrow(S.Expression, S.Expression)),
          typed(S.ping_http, arrow(S.Expression, S.Expression)))
    routes = (
        (G("/"), S.http_response(200, ((G("X-Reply"), G("one")),
                                    (G("X-Reply"), G("two"))), (0, 128, 255))),
        (G("/echo"), S.http_response(201,
            ((G("Content-Type"), G("text/plain; charset=UTF-8")),
             (G("X-Method"), S.repr(V.method)), (G("X-Target"), V.target)), V.body)),
        (G("/absent"), S.http_response(404, (), ())),
        (G("/redirect"), S.http_response(307, ((G("Location"), G("/")),), ())),
        (G("/empty"), S.empty()),
        (G("/broken"), S.broken_response(7)),
    )
    m.add(*(S["="](S.library_http(S.http_request(V.method, path, V.target,
                                                  V.fields, V.body)), response)
            for path, response in routes))
    m.add(S["="](S.read_http(S.http_response(V.status, V.fields, V.handle)),
                  S["file-read-bytes!"](V.handle)),
          S["="](S.ping_http(V.server),
                  S["http-request!"](S.get, S.http_server_url(V.server), ())))

    def refused(call):
        """Read a native refusal through the evaluation boundary."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    request = m.fn["http-request!"]
    stop = m.fn["http-server-stop!"]
    close = m.fn["file-close!"]
    field = m.fn.http_header

    assert list(m.fn.http_methods().one()) == [S.delete, S.get, S.head, S.post,
                                              S.put, S.patch, S.options]
    server = m.fn["http-server-start!"](G("127.0.0.1"), 0, S.library_http,
                                          (S.workers(2),)).one()
    try:
        url = m.fn.http_server_url(server).one()
        echo = m.fn.string_join(G(""), (url, G("echo?q=one%20two"))).one()
        response = request(S.get, url, (S.timeout(5),)).one()
        assert response[1] == 200
        assert list(response[3]) == [0, 128, 255]
        assert field(response[2], G("Content-Type")) == [G("application/octet-stream")]
        assert field(response[2], G("CONTENT-LENGTH")) == [3]
        assert list(field(response[2], G("x-reply"))) == [G("one"), G("two")]
        assert list(field(response[2], G("missing"))) == []

        head = request(S.head, url, ()).one()
        assert head[1] == 200
        assert list(head[3]) == []
        assert field(head[2], G("content-length")) == [3]
        posted = request(S.post, echo,
            (S.body(G("text/plain; charset=UTF-8"), S.utf8_encode(G("aπ🙂"))),
             S.header(G("X-Input"), G("one")), S.header(G("X-Input"), G("two")))).one()
        assert posted[1] == 201
        assert m.fn.utf8_decode(posted[3]) == [G("aπ🙂")]
        assert field(posted[2], G("x-method")) == [G("post")]
        assert field(posted[2], G("x-target")) == [G("/echo?q=one%20two")]
        assert field(request(S.put, echo, ()).one()[2], G("x-method")) == [G("put")]
        assert field(request(S.patch, echo, ()).one()[2], G("x-method")) == [G("patch")]
        assert field(request(S.delete, echo, ()).one()[2], G("x-method")) == [G("delete")]
        assert field(request(S.options, echo, ()).one()[2], G("x-method")) == [G("options")]

        def at(path):
            """Append an example path through the same String operation."""
            return m.fn.string_join(G(""), (url, path)).one()

        assert request(S.get, at(G("absent")), ()).one()[1] == 404
        assert request(S.get, at(G("empty")), ()).one()[1] == 404
        assert request(S.get, at(G("broken")), ()).one()[1] == 500
        assert request(S.get, at(G("redirect")), ()).one()[1] == 307
        assert list(request(S.get, at(G("redirect")), (S.redirect(TRUE),)).one()[3]) == [0, 128, 255]

        stream = m.fn["http-open!"](S.get, url, ()).one()
        handle = stream[3]
        try:
            assert list(m.fn["file-read-bytes!"](handle, 2).one()) == [0, 128]
            assert list(m.fn["file-read-bytes!"](handle).one()) == [255]
        finally:
            assert close(handle) == [True]
        assert close(handle) == [True]
        assert list(m.fn["with-http"](S.get, url, (), S.read_http).one()) == [0, 128, 255]
        assert m.fn["with-http-server"](G("127.0.0.1"), 0, S.library_http,
                                       (S.workers(1),), S.ping_http).one()[1] == 200

        assert refused(S["http-request!"](S.invented, url, ()))
        assert refused(S["http-request!"](S.get, G("file:///etc/passwd"), ()))
        assert refused(S["http-request!"](S.get, url, (S.header(G("bad:name"), G("x")),)))
        assert refused(S["http-request!"](S.get, url, (S.header(G("X-Input"), G("a\nb")),)))
        assert refused(S["http-request!"](S.post, url,
                                          (S.body(G("application/octet-stream"), (256,)),)))
        assert refused(S["http-request!"](S.get, url, (S.timeout(1), S.timeout(2))))
        assert refused(S["http-request!"](S.get, url, (S.header(G("Content-Length"), G("3")),)))
        assert refused(S["http-server-start!"](G("127.0.0.1"), 0, S.library_http, (S.workers(0),)))
        assert refused(S.transaction(S["http-server-start!"](G("127.0.0.1"), 0, S.library_http, ())))
        assert refused(S.transaction(S["http-server-stop!"](server)))
    finally:
        assert stop(server) == [True]
    assert stop(server) == [True]


#: MEASURED: all 41 claims use loopback requests and native byte streams.
#: The example pays 328540; each shutdown owns its native acknowledgement mailbox.
#: [measured 2026-09-13: 323580 inferences, minimum of three fresh serial processes;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/38-http_lib.metta;
#: fixture=lib_http with engine/lib QLF artifacts purged; commit=0f22b69cfca5c108e4126bdd56ab9bb2e493744d].
#: RE-PINNED 2026-09-13, 323580 to 323706 (+126), File exports its shared
#: stream borrowing and rollback operations; failed Socket and HTTP publication
#: now withdraws the registered stream before closing it [measured 2026-09-13:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=781ee98e188c23ea7ef9298636d6e5e6c7fdc727].
#: RE-PINNED 2026-09-13, 323706 to 323720 (+14), File privately exports its
#: existing staged publisher with callback qualification; Compression shares
#: that ownership and publication protocol [measured 2026-09-13: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7b42d5ee5cecb82709617b7ed08dfa2c1441f268].
#: RE-PINNED 2026-09-13, 323720 to 324253 (+533), File exports its staged
#: publisher to Compression; the shared native builder accepts the private
#: archive provider recipe. All consumers are remeasured after those dependency
#: changes [measured 2026-09-13: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7b42d5ee5cecb82709617b7ed08dfa2c1441f268].
#: RE-PINNED 2026-09-14, 324253 to 346140 (+21887), String now derives nine
#: text recipes through MeTTa equations, with one function parameter for
#: padding and complete validation before empty construction; all import
#: consumers are measured after the provider change [measured 2026-09-14: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=118b805aedbee6de22be4f6131d97c3d6b9156de].
#: RE-PINNED 2026-09-14, 346140 to 369064 (+22924), Encoding hex and UUID
#: byte/name formulas are MeTTa recipes over shared strict boundaries;
#: malformed codec classification preserves all unrelated exceptions [measured
#: 2026-09-14: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=8fe20f1bdcde1af8b3e1753c545924f978246dba].
BUDGET = 369064
