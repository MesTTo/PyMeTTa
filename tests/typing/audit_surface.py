"""Purpose: check concrete types at the owned registry, result and remote doors."""

from typing import Any, assert_type

from metta import V, remote, seam
from metta._spaces.results import Answers
from metta.algebra import DeclaredAlgebra, bag
from metta.remote import Gateway, Server
from metta.tables import TableBridge


def consumers(server: Server, gateway: Gateway, bridge: TableBridge, answers: Answers[int]) -> None:
    """Each accepted projection retains its declared value kind."""
    assert_type(seam.frame, seam.Point)
    assert_type(seam.frame.fields, tuple[str, ...])
    assert_type(seam.frame.optional, tuple[str, ...])
    assert_type(bag, DeclaredAlgebra)
    assert_type(server.host, str)
    assert_type(server.port, int)
    assert_type(server.url, str)
    assert_type(gateway("health", {}), dict[str, object])
    assert_type(bridge.__arrow_c_schema__(), object)
    assert_type(bridge.__arrow_c_stream__(), object)
    assert_type(answers[0], int)
    assert_type(answers[V.value], Answers[Any])
    assert_type(answers["value"], Answers[Any])

    _bad_port: str = server.port  # type: ignore[assignment]
    _bad_field: int = seam.frame.fields[0]  # type: ignore[assignment]
    _bad_value: str = gateway("health", {})["ok"]  # type: ignore[assignment]
    remote.not_a_remote_export()  # type: ignore[operator]
