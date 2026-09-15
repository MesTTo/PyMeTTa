# Locked Python protocol sources

`protocol_source.py` reads these inputs to derive source members, C slot roles,
module callable contracts, exact aliases and Python syntax projections. Its
output contains no native implementation status. The protocol generator joins
these facts with the seat's meaning policies.

CPython is pinned to release `v3.14.4`, commit
`23116f998f6789d8c2fbe5ed5b8146854c8c2a4f`. The release tag object is
`97af9512532f73e0af69b79098f6a9c147145c09`. Files under `cpython/` retain exact
upstream bytes and are covered by the retained [CPython license](cpython/LICENSE).
Whole Python syntax files are retained. C and reference inputs pack the exact
regions their parsers consume. Each manifest segment records its packed byte
offset and length, original inclusive line interval and SHA-256. Every source
also records its full-file SHA-256, byte count, line count and immutable URL.
Packed excerpts are not standalone compilable C files.

The journal excerpt is a separate requirement source pinned to repository commit
`47cd8770eadfbfd183b602906537b99fd60b1f98`. Its API namespaces are explicit in the
manifest. Inline API references and call heads are resolved in those namespaces;
MeTTa expressions and operator words do not create additional module APIs.
`typing.runtime_checkable` is the explicit class-requirement addendum. These
requirements select source facts; they do not replace the facts with a maintained
method list.

## Source interface

`inventory(source_root=None)` returns a JSON-compatible dictionary. The default
root is this directory. `validate_inventory(data, source_root=None)` independently
reads the locked inputs and rejects any field, identity, order or required-set
difference. A count match does not pass the check.

| Field | Meaning |
|---|---|
| `sources` | Manifest source records, including exact revision and byte provenance. |
| `members` | `(owner, name)` identities with all source spans and all corresponding slot rows. Public classes and sentinels also have members. |
| `callables` | Verifiable module functions and active aliases, with parameter syntax, positional bounds, required keyword-only names and keyword eligibility. This is not an inventory of every object that can be called. |
| `forms` | Operator source bodies, direct AST forms when present, operand projections in syntax evaluation order and value/target/none result projections. |
| `required.reference` | The special-method section named by `manifest.reference`, including its continuation directives. Other reference chapters contribute members only. |
| `required.journal_members` | Exact owner/name pairs for the journal's named hooks, including class metadata and generated dataclass hooks. |
| `required.journal_apis` | Exact module/name pairs for its API references and explicit class addenda. |
| `required.journal_parameters` | Module/name/parameter triples from the verifiable required API contracts. |

A source span is `{source, start_line, end_line}` using the original file's line
numbers. `source` identifies one manifest record. A slot contains `family`,
`c_member`, `macro`, `generic`, `wrapper`, C-expression `flags`, its documented
signature and a left/reflected/inplace/null role. The generic `object` owner for
slot-table rows is the reference's protocol-owner convention; it does not claim
that `vars(object)` implements every method. Reference owners such as `type` and
`module` remain distinct.

A callable's `source_function` names its active module function. `alias_of` is an
actual assignment to another active export. Parameter kinds use the names from
`inspect.Parameter`. Defaults are source expressions; a missing default is JSON
null, while the Python default `None` is the string `"None"`. A maximum positional
arity of null means unbounded. `math.log` has known positional bounds but no
published machine-readable signature, so its signature and parameter list are
null. Clinic's `<unrepresentable>` marker is retained literally as default
metadata rather than replaced with an invented value.

Forms keep the Python callable contract separate from syntax operands and the
seat's Atom arity. `contains(a, b)` projects syntax operands as `b, a`;
`a[b] = c` evaluates them as `c, a, b`. Operand strings are AST expressions and
can include a literal such as `None`. Augmented assignment returns the assigned
target. A guarded or variable call body is `kind="Function", direct=false` with
its complete body, null operand/result projections and its exact callable form.
Consumers must not infer a primitive lowering from its final statement. Source
bodies can depend on source imports, such as `_abs` in `operator.py`; an exact
module call avoids inventing a standalone environment for them.

## Derivation boundaries

The slot reader expands the retained
[CPython slot macros and table](https://github.com/python/cpython/blob/23116f998f6789d8c2fbe5ed5b8146854c8c2a4f/Objects/typeobject.c#L10914-L11149).
It retains all rows, including shared sequence/mapping slots and NULL generic
dispatchers. Role interpretation belongs to the numeric wrapper shapes and C
in-place fields, not a table of dunder spellings. The table does not encode all
dispatch precedence, fallback sentinels, result checks or lifetime rules; native
equation schemas must retain those semantic policies.

AST classes alone do not map operators to dunder names. The reader obtains each
form from the pinned `operator.py` function body and checks its operator node
against `Python.asdl`. Active signatures come from the C module's published
Clinic definitions or its exact positional guard. For example, `math.log` uses
`_PyArg_CheckPositional("log", nargs, 1, 2)` and `METH_FASTCALL`. Its optional base
is not converted into a fabricated default expression.

Import replacement precedes trailing aliases. In this release, `_operator`
replaces the Python fallback's `invert = inv` with two distinct C functions;
`__inv__` and `__invert__` then alias those separate objects. The syntax for both
still comes from the fallback body. The `__invert__` alias supplies a protocol
member link; `__inv__` is not a slot-table spelling. Similarly, sequence guards
in `concat` and `iconcat` remain part of their source bodies.

Public library exports are read from source declarations and `__all__`, including
lazy exports through module `__getattr__`. Arbitrary decorated callables and
callable classes receive no invented call signature. Dataclass field options and
decorator defaults come from actual function parameter structures. Generated
class hooks are linked to the source's method-builder and attribute operations.

## Offline commands and explicit refresh

Use the repository's selected Python interpreter. Normal generation and checking
perform no imports of PeTTa, network request, package installation or C build.

The reader and source-only controls support the package's Python 3.12 floor.
Active stdlib signature and alias comparisons run only on the locked CPython
3.14.4; other interpreters skip that one version-specific oracle. Parsing the
locked sources and checking their complete inventory remain enabled.

```sh
"$PY" extensions/python/tools/protocol_source.py inventory > inventory.json
"$PY" extensions/python/tools/protocol_source.py check inventory.json
"$PY" extensions/python/tests/repository/test_protocol_source.py
```

An explicit refresh reads full files from a checkout or unpacked source tree:

```sh
"$PY" extensions/python/tools/protocol_source.py refresh \
  --checkout /path/to/cpython-source \
  --revision 23116f998f6789d8c2fbe5ed5b8146854c8c2a4f \
  --destination /path/to/new-protocol-sources
```

The revision must equal the lock. All full-file and excerpt hashes must match
before publication. The destination must be absent and its parent must exist.
The operation constructs and validates the entire new input tree, reports its
exact empty membership/signature/shape diff, and then publishes the directory.
The caller owns that destination exclusively. Local requirement excerpts keep
their separately pinned identity. A release upgrade requires an explicit lock
change and source review; refresh never repins from network state.

Source-only controls cover continuation and nested directives, same-count member
substitution, reflected roles, aliases, arity, missing required APIs, source byte
drift, cyclic macros/aliases, guarded forms, checked refresh and active stdlib
contracts. The live oracle requires CPython 3.14.4. These checks establish source
extraction; native class execution remains the responsibility of its differential
programs and graph-rewrite checks.
