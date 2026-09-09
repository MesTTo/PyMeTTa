"""Purpose: declare remote resource defaults independently of transport loading.

Decides: _CURSOR_IDLE and _CURSOR_LIMIT bound cursor retention; _MUTATION_TTL
and _MUTATION_LIMIT bound mutation replay retention
[source: extensions/python/metta/remote/_defaults.py:9, _CURSOR_LIMIT,
_MUTATION_TTL, _MUTATION_LIMIT; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
"""

_CURSOR_IDLE = 300.0
_CURSOR_LIMIT = 256
_MUTATION_TTL = 300.0
_MUTATION_LIMIT = 4096

_SERVER_TIMEOUT = 10.0

_MAX_REQUEST_BYTES = 16 * 1024 * 1024

_DEFAULT_BATCH = 1
