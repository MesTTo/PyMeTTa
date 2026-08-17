# A PeTTa space served from TypeScript

Two servers, one protocol. `space_server.ts` holds atoms in memory with
its own two-sided unifier and zero dependencies beyond Node's modules,
so it doubles as the protocol's reference implementation.
`mettascript_space_server.ts` holds them in a
[MeTTaScript](https://www.npmjs.com/package/@mettascript/core) space
instead, that engine's own atoms and unifier answering underneath: two
MeTTa implementations joined through one seam.

Attach either from PeTTa and the space is ordinary:

```python
import petta
from petta import remote

m = petta.MeTTa()
remote.attach(m, "&ts", "http://127.0.0.1:8700")
m.run("!(add-atom &ts (edge a b))")
m.run("!(match &ts (edge $x $y) ($x $y))")
```

## The protocol

What `petta.remote.serve()` speaks, so any language can stand on either
end. Four POST operations, JSON bodies both ways, plus `GET /health`:

| request | body | answer |
|---|---|---|
| `POST /match` | `{"space": "&self", "pattern": <wire>}` | `{"atoms": [<wire>...]}` |
| `POST /atoms` | `{"space": "&self"}` | `{"atoms": [...]}` |
| `POST /add` | `{"space": "&self", "atom": <wire>}` | `{"added": true}` |
| `POST /remove` | `{"space": "&self", "atom": <wire>}` | `{"removed": bool}` |
| `POST /add_many` | `{"space": "&self", "atoms": [<wire>...]}` | `{"added": n}` |

A wire atom is a tagged array: `["s", name]` symbol, `["v", name]`
variable, `["n", number]`, `["g", value]` grounded (strings cross this
way), `["e", [children...]]` expression. Errors are
`{"error": "..."}` with a 4xx status. Refusals mirror `serve()` exactly:
401 before the body is read when a Bearer token is configured and
missing or wrong (constant-time compare), 411 without content-length,
413 over the 16 MiB limit, 400 for ambiguous lengths, invalid JSON,
non-object payloads, unknown operations and malformed wire atoms.
Integers past IEEE-754 exact range are refused with a 400 rather than
silently rounded, because `JSON.parse` hands back doubles and a store
that rounds an atom would answer a different atom.

Removal takes every stored occurrence that UNIFIES with the sent atom,
the multiset reading `remove-atom` has everywhere; both servers carry a
real unifier for it (pattern and stored variables renamed apart, so
`(f $x 1)` removes a stored `(f 2 $x)`).

Measured on localhost [2026-08-17]: a match round trip costs about
243 microseconds and an add about 216, PeTTa client to Node server and
back. The engine re-unifies every candidate a storage provider yields,
so a defect in a remote store can cost time, never local soundness; a
semantic matcher (a grounded value's own `match_`) is a different tier
whose claims are authoritative and belong to the value.

## Building and running

The committed `.js` bundles run directly:

```sh
node space_server.js --port 8700
node mettascript_space_server.js --port 8700 \
     --mettascript /path/to/@mettascript/core/dist/index.js
```

Flags: `--host` (default 127.0.0.1), `--port` (0 picks a free one, the
readiness line on stdout names it), `--token` or `PETTA_SPACE_TOKEN`
for Bearer auth, `--spaces a,b` to allowlist served names, `--max-body`
bytes. SIGINT and SIGTERM close the listener and exit 0. Logs are one
line per request on stderr.

Rebuild from the TypeScript after editing (type-check, then bundle):

```sh
tsc --noEmit -p tsconfig.json
esbuild main_store.ts --bundle --platform=node --format=esm \
        --outfile=space_server.js
esbuild main_mettascript.ts --bundle --platform=node --format=esm \
        --outfile=mettascript_space_server.js
esbuild space_server.test.ts --bundle --platform=node --format=esm \
        --outfile=space_server.test.js && node --test space_server.test.js
```

`python/tests/test_typescript_space.py` drives the whole story from
PeTTa: MeTTa-driven queries, the conformance kit over the attached
provider, a thread pool, the async surface, one-request batches, and
the MeTTaScript backend when `PETTA_METTASCRIPT_CORE` names its core
module. Both servers are also certified by
`petta.testing.GatewayComplianceSuite`, the protocol's own conformance
suite, which any implementation in any language can subclass against a
URL.
