"""Purpose: exchange TCP bytes and IPv6 datagrams through owned File handles.

Guarantees: the same 53 claims as 40-socket_lib.metta.
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/40-socket_lib.metta; commit=781ee98e188c23ea7ef9298636d6e5e6c7fdc727].
Owns resources: finally closes remaining loopback handles if an assertion fails;
with-socket owns each scoped acquisition through its answer stream.
"""

from metta import G, S, V, arrow, lib, typed
from metta._errors.errors import MettaError


def twin(m):
    """Share File ownership, query actual endpoints and preserve UDP packets."""
    m += lib.file
    m += lib.socket
    m.add(typed(S.socket_answers, arrow(S.Number, S.Number)),
          S["="](S.socket_answers(V.handle), S.superpose((1, 2))))
    fn = m.fn
    close = fn["file-close!"]
    owned = []

    def refused(call):
        """Read an operation refusal at the public evaluation boundary."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    assert fn.path_join(G("one"), G("two")) == [G("one/two")]
    assert list(fn["socket-wait!"]((), S.infinite).one()) == []
    listener = fn["tcp-listen!"](S.endpoint(S.ipv4, G("127.0.0.1"), 0), 8).one()
    owned.append(listener)
    try:
        address = fn.socket_endpoint(listener, S.local).one()
        assert fn.socket_kind(listener) == [S.listener]
        assert address[1] == S.ipv4
        assert address[2] == G("127.0.0.1")
        assert address[3] > 0
        assert list(fn["socket-wait!"]((listener,), 0).one()) == []
        client = fn["tcp-connect!"](address).one()
        owned.append(client)
        assert list(fn["socket-wait!"]((listener,), S.infinite).one()) == [listener]
        accepted = fn["tcp-accept!"](listener).one()
        owned.append(accepted)
        assert fn.socket_kind(client) == [S.tcp]
        assert fn.socket_kind(accepted) == [S.tcp]
        assert fn.socket_endpoint(accepted, S.local) == [address]
        assert fn.socket_endpoint(client, S.peer) == [address]
        assert fn.socket_endpoint(accepted, S.peer) == fn.socket_endpoint(client, S.local)

        assert fn["file-write-bytes!"](client, (0, 128, 255, 10)) == [True]
        assert list(fn["socket-wait!"]((accepted, accepted), S.infinite).one()) == [accepted, accepted]
        assert list(fn["file-read-bytes!"](accepted, 2).one()) == [0, 128]
        assert list(fn["file-read-bytes!"](accepted, 2).one()) == [255, 10]
        assert fn["socket-shutdown!"](client, S.write) == [True]
        assert list(fn["file-read-bytes!"](accepted).one()) == []
        assert fn["file-write-bytes!"](accepted, (42,)) == [True]
        assert list(fn["file-read-bytes!"](client, 1).one()) == [42]
        assert fn["socket-shutdown!"](accepted, S.both) == [True]
        assert close(listener) == [True]
        owned.remove(listener)
        assert close(client) == [True]
        owned.remove(client)
        assert close(accepted) == [True]
        owned.remove(accepted)
        assert close(accepted) == [True]

        udp = fn["udp-bind!"](S.endpoint(S.ipv6, G("::1"), 0)).one()
        owned.append(udp)
        udp_address = fn.socket_endpoint(udp, S.local).one()
        assert fn.socket_kind(udp) == [S.udp]
        assert udp_address[1] == S.ipv6
        assert udp_address[2] == G("::1")
        assert list(fn["socket-wait!"]((udp,), 0).one()) == []
        assert fn["udp-send!"](udp, udp_address, (0, 255, 1)) == [True]
        assert fn["udp-send!"](udp, udp_address, ()) == [True]
        assert list(fn["socket-wait!"]((udp,), S.infinite).one()) == [udp]
        assert fn["udp-receive!"](udp) == [S.datagram(udp_address, (0, 255, 1))]
        assert fn["udp-receive!"](udp) == [S.datagram(udp_address, ())]
        assert refused(S["udp-send!"](udp, udp_address, (256,)))
        assert list(fn["socket-wait!"]((udp,), 0).one()) == []
        assert refused(S["udp-send!"](udp, S.endpoint(S.ipv4, G("127.0.0.1"), 1), ()))
        assert refused(S.socket_endpoint(udp, S.peer))
        assert refused(S["tcp-accept!"](udp))
        assert refused(S["socket-shutdown!"](udp, S.write))
        assert close(udp) == [True]
        owned.remove(udp)
        assert refused(S.socket_kind(udp))
        assert refused(S["udp-bind!"](S.endpoint(S.unknown, G("127.0.0.1"), 0)))
        assert refused(S["udp-bind!"](S.endpoint(S.ipv4, G(""), 0)))
        assert refused(S["udp-bind!"](S.endpoint(S.ipv4, G("127.0.0.1"), 65536)))
        assert refused(S["tcp-connect!"](S.endpoint(S.ipv4, G("127.0.0.1"), 0)))
        assert refused(S["tcp-listen!"](S.endpoint(S.ipv4, G("127.0.0.1"), 0), -1))
        assert refused(S["socket-wait!"]((), -1))
        assert refused(S.transaction(S["udp-bind!"](S.endpoint(S.ipv4, G("127.0.0.1"), 0))))

        acquire = S["udp-bind!"](S.endpoint(S.ipv4, G("127.0.0.1"), 0))
        assert list(fn["with-socket"](acquire, S.socket_answers)) == [1, 2]
        assert fn["with-socket"](acquire, S.socket_kind) == [S.udp]
        closed = fn["with-socket"](acquire, S["lambda"](V.handle, V.handle)).one()
        assert refused(S.socket_kind(closed))
    finally:
        for handle in owned:
            close(handle).one()


#: MEASURED: all 53 claims cross TCP, IPv6 UDP and owned socket scopes.
#: The example pays 189530; both notations import File before Socket.
#: [measured 2026-09-13: 178533 inferences, minimum of three fresh serial processes;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/40-socket_lib.metta;
#: fixture=lib_socket with engine/lib QLF artifacts purged; commit=781ee98e188c23ea7ef9298636d6e5e6c7fdc727].
#: RE-PINNED 2026-09-13, 178533 to 178547 (+14), File privately exports its
#: existing staged publisher with callback qualification; Compression shares
#: that ownership and publication protocol [measured 2026-09-13: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7b42d5ee5cecb82709617b7ed08dfa2c1441f268].
#: RE-PINNED 2026-09-13, 178547 to 179079 (+532), File exports its staged
#: publisher to Compression; the shared native builder accepts the private
#: archive provider recipe. All consumers are remeasured after those dependency
#: changes [measured 2026-09-13: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7b42d5ee5cecb82709617b7ed08dfa2c1441f268].
#: RE-PINNED 2026-09-14, 179079 to 200969 (+21890), String now derives nine
#: text recipes through MeTTa equations, with one function parameter for
#: padding and complete validation before empty construction; all import
#: consumers are measured after the provider change [measured 2026-09-14: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=118b805aedbee6de22be4f6131d97c3d6b9156de].
BUDGET = 200969
