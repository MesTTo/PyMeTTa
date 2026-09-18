"""Purpose: serve a context through its resolved home on both HTTP methods."""

import pytest

from metta import MeTTa, S
from metta.remote import connect, serve


@pytest.mark.parametrize("receiver_kind", ["context", "space"])
@pytest.mark.parametrize("operation", ["health", "atoms"])
def test_serving_a_context_authorizes_its_resolved_home(receiver_kind, operation):
    """GET and POST use the same space that Gateway resolved at construction."""
    requests = []

    def authorize(request):
        requests.append((request.operation, request.space))
        return True

    with MeTTa() as context:
        context.self.add(S.served_context)
        receiver = context if receiver_kind == "context" else context.self
        with serve(receiver, authorize=authorize) as server:
            transport = connect(server.url)
            if operation == "health":
                assert transport.health()["ok"] is True
            else:
                assert transport(operation, {})["atoms"] == [S.served_context.to_wire()]
        assert requests == [(operation, context.self.name)]
