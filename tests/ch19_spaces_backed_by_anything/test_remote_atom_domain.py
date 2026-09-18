"""Purpose: compare gateway removal with local removal over every atom shape."""

import pytest

from metta import Expression, Grounded, S
from metta.remote import Gateway, OutcomeUnknown, RemoteSpace, connect, serve


@pytest.mark.parametrize("atom", [S.audit_leaf, Grounded(7), Expression(()), S.audit_fact(7)])
@pytest.mark.parametrize("transport", ["gateway", "http"])
def test_remote_removal_preserves_the_local_atom_domain(metta, atom, transport):
    """Duplicates, absence and malformed wires have the local mutation law."""
    with metta._new_space() as local, metta._new_space() as served:
        local.add(atom, atom)
        served.add(atom, atom)
        with serve(served) if transport == "http" else Gateway(served) as owner:
            send = connect(owner.url) if transport == "http" else owner
            remote = RemoteSpace(send, served.name)
            for _ in range(3):
                assert remote.remove(atom) is local.remove(atom)
                assert list(remote.atoms()) == local.atoms()
            expected = OutcomeUnknown if transport == "http" else ValueError
            with pytest.raises(expected) as refused:
                send("remove", {"space": served.name, "atom": ["invalid", 7]})
            cause = refused.value
            while cause.__cause__ is not None:
                cause = cause.__cause__
            assert "wire" in str(cause)
            assert list(remote.atoms()) == []
