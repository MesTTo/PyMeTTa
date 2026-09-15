"""Purpose: expose remote clients, serving lifetimes and transports lazily."""

from collections.abc import Callable
from typing import TYPE_CHECKING

from metta._lazy import package as _package

if TYPE_CHECKING:
    from ._client import RemoteCursor as RemoteCursor
    from ._client import RemoteSpace as RemoteSpace
    from ._gateway import Gateway as Gateway
    from ._gateway import Request as Request
    from ._gateway import Server as Server
    from ._gateway import serve as serve
    from ._transport import OutcomeUnknown as OutcomeUnknown
    from ._transport import ProtocolError as ProtocolError
    from ._transport import Transport as Transport
    from ._transport import connect as connect

__all__ = ['Gateway', 'OutcomeUnknown', 'ProtocolError', 'RemoteCursor', 'RemoteSpace', 'Request', 'Server', 'connect', 'serve']

__getattr__: Callable[[str], object]
__dir__: Callable[[], list[str]]
__getattr__, __dir__ = _package(__name__)
