"""Purpose: apply authorization and finite cursor ownership to a remote space.

The example uses the bundled loopback HTTP server because authorization belongs
to the transport boundary. The server and every open cursor are closed before
the process exits.
"""

from _common import check, done

import metta.remote._client as _moved_metta_remote__client
import metta.remote._gateway as _moved_metta_remote__gateway
import metta.remote._transport as _moved_metta_remote__transport
from metta import MeTTa, S, V
from metta._errors.errors import MettaError, is_transport_failure

check("a backend outage is a transport failure", is_transport_failure(ConnectionError("down")))
check("an application refusal is not a transport failure", not is_transport_failure(ValueError("bad row")))

with MeTTa() as context:
    served = context.space("&remote-controls")
    served.add(*(S.item(number) for number in range(4)))
    served_name = str(served.name)
    seen_requests = []

    def read_only(request: _moved_metta_remote__gateway.Request) -> bool:
        """Admit health and reads of one named space; refuse every write."""
        seen_requests.append((request.operation, request.space))
        return request.operation == "health" or (
            request.space == served_name
            and request.operation in {"match", "atoms", "ask", "next", "stop"}
        )

    with _moved_metta_remote__gateway.serve(
        served,
        spaces=[served_name],
        authorize=read_only,
        cursor_idle=30,
        cursor_limit=1,
    ) as server:
        transport = _moved_metta_remote__transport.connect(server.url, timeout=5)
        client = _moved_metta_remote__client.RemoteSpace(transport, served_name)
        capabilities = client.server_capabilities()
        check("the client can inspect the server before writing", capabilities["bound"])

        check(
            "an authorized read crosses the wire",
            sorted(str(atom) for atom in client.match(S.item(V.number))),
            ["(item 0)", "(item 1)", "(item 2)", "(item 3)"],
        )

        try:
            client.add(S.item(4))
        except MettaError as refusal:
            check("the authorization hook refuses a write", "not authorized" in str(refusal))
        else:
            msg = "the read-only server admitted a write"
            raise AssertionError(msg)

        first = client.stream(S.item(V.number), batch=1)
        check("the first cursor opens", str(next(first)), "(item 0)")
        try:
            client.stream(S.item(V.number), batch=1)
        except MettaError as refusal:
            check("the cursor ceiling refuses excess state", "already holds 1" in str(refusal))
        else:
            msg = "the server exceeded its cursor limit"
            raise AssertionError(msg)
        finally:
            first.close()

    check("authorization receives operation and space", ("add", served_name) in seen_requests)

done("remote_controls")
