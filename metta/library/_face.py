"""Purpose: write a module's own signatures out as a MeTTa face.

A library that wraps a Python module is generated from that module rather than
kept by hand: one arrow per reachable call form, the `(@doc ...)` atom the
docstring already carries, the equation that applies the name through
`py-call`, and an effect class derived from what the signature says it answers.

`integrate.module_ops` is this same act at RUN time. A face is its written
half: the same names, the same reachable arities, the same map from a Python
annotation to a MeTTa type, in a file a MeTTa program imports with no Python
running first.

The face's own header is its INPUT. It carries the Python import statements
that say what was selected, the signatures the module could not answer for
itself, and the effect reviews a signature cannot show; everything below the
header is derived from those and from the live module. So checking a face is
one comparison: read the header, render, and require the result to equal the
file. A hand edit anywhere, including a mistyped field the reader drops, comes
back as drift rather than as silence.

Assumes:
  - `inspect.signature` reports an unsupported callable with TypeError and an
    unavailable signature with ValueError, which is every C function without
    an Argument Clinic text signature
    [source: https://docs.python.org/3/library/inspect.html#inspect.signature]
  - a docstring whose first lines read `name(...)` states the signature the
    runtime could not: CPython's own reader builds a Signature from that text
    by parsing `"def foo" + signature + ": pass"`
    [source: /usr/lib/python3.14/inspect.py:2152, _signature_fromstr; commit=7229962705d199fb08796b3090ec5a8a3a0ae393]
Guarantees:
  - a head is the import's module prefix and the tree's one Python-to-MeTTa
    name map, so `requires_grad_` reaches `torch-requires-grad` exactly as
    `S.not_` reaches `not`
    [source: extensions/python/metta/_atoms/names.py:101; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e]
    [tested: test_a_head_is_the_prefix_and_the_one_name_map; commit=7229962705d199fb08796b3090ec5a8a3a0ae393]
  - the served arities are `integrate.module_ops`'s own rule, shared rather
    than restated, so the written face and the run-time registration answer at
    the same call forms
    [tested: test_a_face_serves_the_call_forms_a_registration_answers;
    commit=7229962705d199fb08796b3090ec5a8a3a0ae393]
  - a type is the projection table's Python column read backwards, which names
    the scalar rows and answers `%Undefined%` for everything else, the classes
    a module names for itself INCLUDED: a declared type is checked against the
    crossed VALUE, so one head declaring `list` answers a list of symbols and
    refuses a list of numbers, and nothing in a signature says which of its
    module's values survive the crossing under the name it wrote
    [tested: test_a_declared_python_type_admits_one_value_and_refuses_another;
    commit=7229962705d199fb08796b3090ec5a8a3a0ae393]
  - rendering is deterministic: the selection keeps the import's own order, a
    whole module is taken in sorted order, and nothing reads the clock or the
    filesystem [tested: test_two_renders_of_one_face_are_the_same_text;
    commit=7229962705d199fb08796b3090ec5a8a3a0ae393]
  - a name the module cannot describe and the header does not declare is
    REFUSED by name, with the header line that answers it, rather than being
    dropped from the face [tested: test_a_name_with_no_signature_anywhere_is_refused;
    commit=7229962705d199fb08796b3090ec5a8a3a0ae393]
Fails when:
  - a docstring signature uses the `[, optional]` bracket notation rather than
    Python defaults. It is not Python and this reader does not guess what the
    brackets mean; the face declares a `Signature:` line for that name.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import ast
import builtins
import collections.abc as _collections_abc
import dataclasses
import importlib
import inspect
import re
import textwrap
from dataclasses import dataclass
from typing import Any, Final

from metta._atoms.factories import Expression, Symbol, Variable
from metta._atoms.names import attribute_name
from metta._catalog.annotations import metta_type_for, resolved_annotations
from metta._catalog.documentation import documentation_atom, first_paragraph
from metta._errors.errors import MettaError
from metta.vocabularies import EffectClass

__all__ = [
    "Face",
    "Manifest",
    "positional_arities",
    "read",
    "render",
]

#: The generator every face names, and the command that rewrites one.
GENERATOR: Final = "extensions/python/tools/facegen.py"

#: A `;Field: value` line of a face's header block, the same shape a library's
#: own header uses so `metta.library` reads a generated face's summary exactly
#: as it reads a hand-written one
#: [source: extensions/python/metta/library/__init__.py:87; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
_FIELD: Final = re.compile(r"^;+\s*([A-Z][A-Za-z ]*):\s*(.*)$")

#: The determinism every face head declares. One py-call answers once, which
#: is what `det` claims; the class beside it is the derived effect.
_DETERMINISM: Final = "det"

#: The Python types whose values cross as MeTTa data rather than as a handle,
#: which is what makes a call answering one a lookup rather than a write.
#: Subclasses count: `torch.Size` is a tuple and crosses as one.
_CONTAINERS: Final = (list, tuple, dict, set, frozenset)

#: The MeTTa types a scalar answer takes, from the projection table's own rows.
_SCALARS: Final = frozenset({"Number", "String", "Bool"})


@dataclass(frozen=True)
class Import:
    """One Python import statement of a face's selection.

    `names` is None for `import x`, which takes the module whole, and the
    (attribute path, local name) pairs of `from x import a, b as c` otherwise.
    An attribute path may reach INSIDE the module (`from x.C import method`),
    resolved the way `py-atom` resolves a dotted path: the longest importable
    prefix, then getattr for the rest.
    """

    module: str
    prefix: str
    names: tuple[tuple[str, str], ...] | None

    @classmethod
    def of(
        cls,
        module: str,
        names: tuple[tuple[str, str], ...] | None,
        prefix: str | None = None,
    ) -> Import:
        """One import, taking the module's own innermost module as the prefix."""
        return cls(module, prefix or _module_prefix(module), names)

    @property
    def statement(self) -> str:
        """The Python statement this import was read from."""
        if self.names is None:
            tail = "" if self.prefix == self.module else f" as {self.prefix}"
            return f"import {self.module}{tail}"
        spelled = ", ".join(
            name if name == local else f"{name} as {local}" for name, local in self.names
        )
        return f"from {self.module} import {spelled}"


@dataclass(frozen=True)
class Manifest:
    """What a face's header declares, which is everything its body derives from.

    `effects` and `signatures` are keyed by the LOCAL Python name, the one the
    import binds, because that is the name the header's reader has in hand
    before anything is resolved.
    """

    purpose: str
    imports: tuple[Import, ...]
    signatures: tuple[tuple[str, str], ...] = ()
    effects: tuple[tuple[str, str, str], ...] = ()
    #: The version each module reported when the face was written. It is an
    #: INPUT like every other header field, so a box whose installation moved
    #: on renders the same bytes and is told the difference rather than being
    #: shown drift. Empty asks for the live version, which is what a fresh
    #: face and a rewrite both want.
    versions: tuple[tuple[str, str], ...] = ()

    @classmethod
    def of(
        cls,
        module: Any,
        names: _collections_abc.Iterable[str] | None = None,
        *,
        purpose: str,
        prefix: str | None = None,
        rename: _collections_abc.Mapping[str, str] | None = None,
        effects: _collections_abc.Iterable[tuple[str, str, str]] = (),
        signatures: _collections_abc.Iterable[str] = (),
    ) -> Manifest:
        """The manifest one selection declares, as `integrate.face` states it."""
        named = module if isinstance(module, str) else module.__name__
        renamed = rename or {}
        selected = (
            None
            if names is None
            else tuple((name, renamed.get(name, name)) for name in names)
        )
        return cls(
            purpose=purpose,
            imports=(Import.of(named, selected, prefix),),
            signatures=tuple((_signature_name(line), line) for line in signatures),
            effects=tuple(effects),
        )

    def declared_signatures(self, local: str) -> tuple[str, ...]:
        """Every signature line the header declares for one local name."""
        return tuple(text for name, text in self.signatures if name == local)

    def declared_effect(self, local: str) -> tuple[str, str] | None:
        """The effect class and the review the header declares, if it does."""
        for name, effect, reason in self.effects:
            if name == local:
                return effect, reason
        return None


@dataclass(frozen=True)
class Name:
    """One selected name: where it lives, what it is, and how MeTTa calls it."""

    path: str
    local: str
    head: str
    target: Any
    owner: Any
    is_module_level: bool


@dataclass(frozen=True)
class CallForm:
    """One reachable call form: the parameters MeTTa passes and the result."""

    parameters: tuple[inspect.Parameter, ...]
    result: Any


class Face:
    """A module's selected names, rendered as MeTTa source.

    The longhand is the three steps this composes: resolve each selected name,
    derive its call forms from `inspect.signature` or from the signature its
    docstring states, and write the arrow, the `(@doc ...)` atom and the
    `py-call` equation for each. `metta.integrate.face` is the door.
    """

    __slots__ = ("_manifest",)

    def __init__(self, manifest: Manifest) -> None:
        """Hold the manifest whose body this renders."""
        self._manifest = manifest

    def text(self) -> str:
        """The whole face: its header, then one block per selected name."""
        blocks = [self._block(name) for name in self._names()]
        versions = self._manifest.versions or self._live_versions()
        return _header(self._manifest, versions) + "\n" + "\n\n".join(blocks) + "\n"

    def drifted_versions(self) -> tuple[tuple[str, str, str], ...]:
        """Each module whose live version is not the one the face pinned."""
        live = dict(self._live_versions())
        return tuple(
            (module, pinned, live[module])
            for module, pinned in self._manifest.versions
            if module in live and live[module] != pinned
        )

    def _live_versions(self) -> tuple[tuple[str, str], ...]:
        """The version each imported MODULE reports right now, once each.

        By the module rather than by the import, because two imports reaching
        into one module -- its functions and one of its classes -- were read
        from one installation and have one version between them.
        """
        seen: dict[str, str] = {}
        for statement in self._manifest.imports:
            module = _module_of(statement.module)
            seen.setdefault(module.__name__, _version_of(module))
        return tuple(seen.items())

    def _names(self) -> list[Name]:
        """Every selected name, in the selection's own order, refusing a clash."""
        selected: list[Name] = []
        heads: dict[str, str] = {}
        for statement in self._manifest.imports:
            for name in _selected(statement):
                previous = heads.get(name.head)
                if previous is not None:
                    msg = (
                        f"{name.path} and {previous} both reach the MeTTa head "
                        f"{name.head}; one of them needs an `as` in the face's "
                        f"import, which is where a rename belongs"
                    )
                    raise MettaError(msg)
                heads[name.head] = name.path
                selected.append(name)
        return selected

    def _block(self, name: Name) -> str:
        """One name's arrows, documentation and equations, in that order."""
        forms = self._call_forms(name)
        effect = self._effect(name, forms)
        lines = [
            _arrow(name.head, form, effect) for _arity, form in sorted(forms.items())
        ]
        documentation = _documentation(name, forms)
        if documentation is not None:
            lines.append(documentation)
        lines.extend(
            _equation(name, form) for _arity, form in sorted(forms.items())
        )
        return "\n".join(lines)

    def _call_forms(self, name: Name) -> dict[int, CallForm]:
        """Every reachable call form of one name, by the arity MeTTa calls it at.

        An overload family contributes each of its forms; the first signature
        that reaches an arity owns that arity's parameters and result, the
        same choice `_projection.arrows_of` makes for a head declared twice.
        """
        if not callable(name.target):
            #An attribute READ takes the receiver and nothing else. Its result
            #is whatever its docstring declares, which is a `shape() -> Size`
            #line for a descriptor that has one and nothing for a field.
            declared = self._signatures(name)
            result = declared[0].return_annotation if declared else inspect.Signature.empty
            receiver = inspect.Parameter("self", inspect.Parameter.POSITIONAL_ONLY)
            return {1: CallForm((receiver,), result)}
        forms: dict[int, CallForm] = {}
        for signature in self._signatures(name):
            for arity in positional_arities(name.head, signature):
                forms.setdefault(arity, _call_form(signature, arity))
        return forms

    def _signatures(self, name: Name) -> tuple[inspect.Signature, ...]:
        """One name's signatures, down the ladder, refusing when none answers.

        The rungs, in order: the runtime's own answer, which covers every
        Python function and every C function carrying an Argument Clinic text
        signature; the signature the docstring states in prose, which is what
        a C extension writes instead; and the `Signature:` lines the face's
        header declares for a name neither answers.
        """
        declared = self._manifest.declared_signatures(name.local)
        if declared:
            signatures = tuple(
                _signature_from_text(text, name.path, name.owner) for text in declared
            )
            if _signature_of(name.target) is not None or _docstring_signatures(name):
                msg = (
                    f"the face declares a signature for {name.path}, and the "
                    f"module answers for it: delete the `;Signature: "
                    f"{declared[0]}` line and let it derive"
                )
                raise MettaError(msg)
            return _with_receiver(signatures, name)
        runtime = _signature_of(name.target)
        if runtime is not None:
            return _with_receiver((runtime,), name)
        from_docstring = _docstring_signatures(name)
        if from_docstring:
            return _with_receiver(from_docstring, name)
        if not callable(name.target):
            return ()
        msg = (
            f"{name.path} has no signature: the runtime refuses one and its "
            f"docstring states none, so its call forms cannot be derived. "
            f"Declare it in the face's header, `;Signature: "
            f"{name.local}(<parameters>)`, one line per call form"
        )
        raise MettaError(msg)

    def _effect(self, name: Name, forms: _collections_abc.Mapping[int, CallForm]) -> str:
        """The effect class one head declares, derived unless the face reviews it.

        The rule is `arrays.py`'s, read off the signature: a result that
        crosses as MeTTa data is a lookup, a result that is a live foreign
        object is a write, a call made for what it does is a write, and a name
        whose result nothing declares is `oracleIO`, the top, exactly what the
        bridge declares for `py-call` itself
        [source: ext/metta-arrays/metta_arrays.py:install;
        extensions/python/metta/_binding/surface.pl:743, seam:extension_builtin('py-call', oracleIO); commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
        """
        derived = _derived_effect(forms)
        review = self._manifest.declared_effect(name.local)
        if review is None:
            return derived
        effect, reason = review
        if effect == derived:
            msg = (
                f"the face declares {name.local} {effect}, which is what the "
                f"rule derives: delete the `;Effect:` line"
            )
            raise MettaError(msg)
        if not reason:
            msg = (
                f"the face declares {name.local} {effect} over the derived "
                f"{derived} and gives no reason; an effect review says why"
            )
            raise MettaError(msg)
        return effect


def positional_arities(name: str, signature: inspect.Signature) -> list[int]:
    """Every arity a positional MeTTa call site can reach on one signature.

    A defaulted positional parameter makes every arity between the required
    count and the whole list reachable; a `*args` serves the conventional zero
    to four; a `**kwargs` and a defaulted keyword-only parameter are invisible
    from a positional call site, and a REQUIRED keyword-only parameter refuses,
    because no call MeTTa can write would supply it.

    This is the rule `integrate.module_ops` registers by, in one place so the
    written face and the run-time registration cannot answer at different call
    forms.
    """
    positional = []
    variadic = False
    for parameter in signature.parameters.values():
        if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
            variadic = True
        elif parameter.kind is inspect.Parameter.KEYWORD_ONLY and (
            parameter.default is inspect.Parameter.empty
        ):
            msg = (
                f"{name}: required keyword-only parameter "
                f"{parameter.name!r} is unreachable from a positional "
                f"MeTTa call site"
            )
            raise MettaError(msg)
        elif parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            positional.append(parameter)
    required = sum(
        1 for parameter in positional if parameter.default is inspect.Parameter.empty
    )
    if variadic:
        return list(range(required, max(required + 1, 5)))
    return list(range(required, len(positional) + 1))


def read(text: str) -> Manifest | None:
    """The manifest one face's header declares, or None when it carries none.

    A file with no `Import:` line is not a face, which is how the sync lane
    tells a generated library from a hand-written one without a list of names
    it would have to keep.
    """
    purpose: list[str] = []
    imports: list[Import] = []
    prefix: str | None = None
    signatures: list[tuple[str, str]] = []
    effects: list[tuple[str, str, str]] = []
    versions: list[tuple[str, str]] = []
    describing = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(";"):
            break
        field = _FIELD.match(stripped)
        if field is None:
            #The purpose is prose and prose wraps, so a line under it and above
            #the next field continues it, which is how a library's own header
            #reads its summary too
            #[source: extensions/python/metta/library/__init__.py:490; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
            if describing:
                purpose.append(stripped.lstrip(";").strip())
            continue
        label, value = field.group(1).strip(), field.group(2).strip()
        describing = label == "Purpose"
        if label == "Purpose":
            purpose.append(value)
        elif label == "Import":
            imports.extend(imports_from(value))
        elif label == "Prefix":
            prefix = value
        elif label == "Signature":
            signatures.append((_signature_name(value), value))
        elif label == "Effect":
            effects.append(_effect_row(value))
        elif label == "Read from":
            versions.append(_version_row(value))
    if not imports:
        return None
    if prefix is not None:
        imports = [
            dataclasses.replace(statement, prefix=prefix) for statement in imports
        ]
    return Manifest(
        purpose=" ".join(purpose),
        imports=tuple(imports),
        signatures=tuple(signatures),
        effects=tuple(effects),
        versions=tuple(versions),
    )


def render(manifest: Manifest) -> str:
    """One face's whole text, header included, from its manifest."""
    return Face(manifest).text()


def imports_from(statement: str) -> tuple[Import, ...]:
    """Read one Python import statement into the selection it names.

    Python's own grammar says what a selection is, so the face's header writes
    the statement and this parses it: `import torch`, `import torch as t`,
    `from torch import matmul, relu`, `from torch import matmul as mm`. The
    module path may reach a class inside the module, `from torch.Tensor import
    tolist`, which Python's grammar accepts and its import machinery does not;
    the resolver below reads it the way `py-atom` reads any dotted path.
    """
    try:
        tree = ast.parse(statement)
    except SyntaxError as exc:
        msg = f"{statement!r} is not a Python import statement: {exc.msg}"
        raise MettaError(msg) from exc
    if len(tree.body) != 1 or not isinstance(tree.body[0], (ast.Import, ast.ImportFrom)):
        msg = f"{statement!r} is not a Python import statement"
        raise MettaError(msg)
    node = tree.body[0]
    if isinstance(node, ast.Import):
        return tuple(
            Import(alias.name, alias.asname or alias.name, None) for alias in node.names
        )
    if node.level or node.module is None:
        msg = f"{statement!r} imports relatively, and a face names a module outright"
        raise MettaError(msg)
    names = tuple((alias.name, alias.asname or alias.name) for alias in node.names)
    return (Import.of(node.module, names),)


def _module_prefix(path: str) -> str:
    """The prefix every head of one import takes, before the name map.

    The innermost MODULE of the path, so `torch.Tensor` prefixes with `torch`
    and `os.path` with `os.path`: a class in the path is a namespace the head
    does not repeat, because MeTTa reaches a method through its receiver
    rather than through the class.
    """
    parts = path.split(".")
    while parts:
        try:
            importlib.import_module(".".join(parts))
        except ImportError:
            parts.pop()
        else:
            return ".".join(parts)
    return path.split(".", maxsplit=1)[0]


def _module_of(path: str) -> Any:
    """The module an import's path names, importing the longest prefix.

    The same resolution `py-atom` performs for a dotted name of any depth
    [source: extensions/python/metta/_binding/host.py:728, resolve; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
    """
    return importlib.import_module(_module_prefix(path))


def _resolve(module: Any, path: str) -> Any:
    """Walk a dotted attribute path from a module, refusing what is not there."""
    found = module
    for part in path.split("."):
        try:
            found = getattr(found, part)
        except AttributeError as exc:
            msg = f"{module.__name__} has no attribute {path!r}"
            raise MettaError(msg) from exc
    return found


def _owner(module: Any, path: str) -> Any:
    """What a dotted path's last component hangs off: the module, or a class."""
    parts = path.split(".")
    return module if len(parts) == 1 else _resolve(module, ".".join(parts[:-1]))


def _module_names(module: Any) -> list[str]:
    """Every name `import x` publishes, by the rule a face's header states.

    The module's own `__all__` when it declares one, and otherwise its public
    callables that are not classes, which is `integrate.module_ops`'s rule for
    a module handed no name list
    [source: extensions/python/metta/integrate.py:458; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
    Sorted, so the face is the same text whatever order the module's namespace
    happens to be in.
    """
    published = (
        [str(name) for name in module.__all__]
        if getattr(module, "__all__", None) is not None
        else [name for name in vars(module) if not name.startswith("_")]
    )
    return sorted(
        name
        for name in published
        if callable(getattr(module, name, None))
        and not inspect.isclass(getattr(module, name))
    )


def _selected(statement: Import) -> _collections_abc.Iterator[Name]:
    """Every name one import statement selects, resolved against the module."""
    module = _module_of(statement.module)
    inside = statement.module[len(_module_prefix(statement.module)) :].lstrip(".")
    pairs = statement.names
    if pairs is None:
        pairs = tuple((name, name) for name in _module_names(module))
    for attribute, local in pairs:
        path = f"{inside}.{attribute}" if inside else attribute
        target = _resolve(module, path)
        yield Name(
            path=f"{statement.module}.{attribute}",
            local=local,
            head=f"{attribute_name(statement.prefix.replace('.', '_'))}-{attribute_name(local)}",
            target=target,
            owner=_owner(module, path),
            is_module_level=inspect.ismodule(_owner(module, path)),
        )


def _signature_of(target: Any) -> inspect.Signature | None:
    """The runtime's own signature for a callable, or None when it refuses one.

    Its annotations are RESOLVED first: a module written under `from __future__
    import annotations` carries the string `"float"` where it means the type,
    and a face reading the string would declare `%Undefined%` for a parameter
    the module typed. The resolver is the one `@m.define` uses, so an
    annotation neither can name stands in as `Unresolved` rather than costing
    the annotations beside it
    [source: extensions/python/metta/_catalog/annotations.py:560; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
    """
    if not callable(target):
        return None
    try:
        signature = inspect.signature(target)
    except (TypeError, ValueError):
        return None
    resolved = resolved_annotations(target)
    return signature.replace(
        parameters=[
            parameter.replace(annotation=resolved.get(parameter.name, parameter.annotation))
            for parameter in signature.parameters.values()
        ],
        return_annotation=resolved.get("return", signature.return_annotation),
    )


def _docstring_signatures(name: Name) -> tuple[inspect.Signature, ...]:
    """The signatures a docstring states in its leading lines.

    A C extension that carries no Argument Clinic text signature writes it in
    the docstring instead, one line per overload, which is how `range` states
    its two forms and how every torch factory states its one. Each line is
    read the way CPython reads a text signature: as the header of a function
    definition [source: /usr/lib/python3.14/inspect.py:2152].
    """
    documentation = inspect.getdoc(name.target) or ""
    signatures = []
    for line in _leading_signature_lines(documentation, name.local):
        try:
            signatures.append(_signature_from_text(line, name.path, name.owner))
        except MettaError:
            #A leading line that reads as a signature and does not PARSE as one
            #is the module's own defect, and guessing what it meant would put
            #an invented call form in a shipped file. The face declares that
            #name instead, and the refusal above says so.
            return ()
    return tuple(signatures)


def _leading_signature_lines(documentation: str, local: str) -> list[str]:
    """The docstring's opening lines that read as `name(...)`, in order."""
    lines = []
    for line in documentation.splitlines():
        text = line.strip()
        if not text.startswith(f"{local}("):
            break
        lines.append(text)
    return lines


def _signature_from_text(text: str, path: str, owner: Any) -> inspect.Signature:
    """One signature line read as Python, with its annotations resolved.

    `def <line>: ...` is the program CPython's own `__text_signature__` reader
    parses, so a line this refuses is a line Python's grammar refuses. The one
    repair is a bare `*` marker sitting after a `*args`, which torch's factory
    docstrings write and Python rejects as a second `*`: everything after
    `*args` is keyword-only already, so dropping it changes no meaning
    [measured 2026-09-07: torch 2.13.0+cpu writes `zeros(*size, *, out=None,
    ...)`, which ast refuses with "* argument may appear only once";
    fixture=torch 2.13.0+cpu; command=python -c
    'import ast, inspect, torch; ast.parse("def " + inspect.getdoc(torch.zeros).splitlines()[0] + ": ...")';
    commit=7229962705d199fb08796b3090ec5a8a3a0ae393].
    """
    try:
        tree = ast.parse(f"def {_without_redundant_star(text)}: ...")
    except SyntaxError as exc:
        msg = (
            f"{path}: {text!r} is not a Python signature ({exc.msg}), so its "
            f"call forms cannot be read; declare it in the face's header"
        )
        raise MettaError(msg) from exc
    definition = tree.body[0]
    if not isinstance(definition, ast.FunctionDef):
        msg = f"{path}: {text!r} is not a Python signature"
        raise MettaError(msg)
    parameters = _positional(definition.args, owner)
    if definition.args.vararg is not None:
        parameters.append(
            inspect.Parameter(
                definition.args.vararg.arg, inspect.Parameter.VAR_POSITIONAL
            )
        )
    parameters.extend(
        inspect.Parameter(
            argument.arg,
            inspect.Parameter.KEYWORD_ONLY,
            default=None if default is None else _annotation(default, owner),
            annotation=_annotation(argument.annotation, owner),
        )
        for argument, default in zip(
            definition.args.kwonlyargs, definition.args.kw_defaults, strict=True
        )
    )
    if definition.args.kwarg is not None:
        parameters.append(
            inspect.Parameter(definition.args.kwarg.arg, inspect.Parameter.VAR_KEYWORD)
        )
    return inspect.Signature(
        parameters, return_annotation=_annotation(definition.returns, owner)
    )


def _positional(arguments: ast.arguments, owner: Any) -> list[inspect.Parameter]:
    """Every positional parameter of a parsed signature, in its own order.

    Python's own rule for the defaults: the list is right-aligned against the
    whole positional run, so the first `count - len(defaults)` have none.
    """
    written = [
        (argument, inspect.Parameter.POSITIONAL_ONLY)
        for argument in arguments.posonlyargs
    ] + [
        (argument, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        for argument in arguments.args
    ]
    first_default = len(written) - len(arguments.defaults)
    return [
        inspect.Parameter(
            argument.arg,
            kind,
            default=(
                inspect.Parameter.empty
                if index < first_default
                else _annotation(arguments.defaults[index - first_default], owner)
            ),
            annotation=_annotation(argument.annotation, owner),
        )
        for index, (argument, kind) in enumerate(written)
    ]


def _without_redundant_star(text: str) -> str:
    """Drop a bare `*` marker that follows a `*args` in the same signature."""
    if not re.search(r"\*[A-Za-z_]", text):
        return text
    return re.sub(r",\s*\*\s*,", ",", text, count=1)


def _annotation(node: ast.expr | None, owner: Any) -> Any:
    """One annotation node as the object it names, or as its own text.

    A dotted name is resolved against the module the name lives in and then
    against builtins, because the effect rule below has to tell a class from a
    docstring's prose. Nothing is evaluated: a subscript, an operator or a
    literal keeps its written text, which the type map reads as `%Undefined%`
    exactly as it reads an unresolvable name.
    """
    if node is None:
        return inspect.Signature.empty
    dotted = _dotted(node)
    if dotted:
        resolved = _resolved_name(dotted, owner)
        if resolved is not None:
            return resolved
    if isinstance(node, ast.Constant):
        return node.value
    return ast.unparse(node)


def _dotted(node: ast.expr) -> str:
    """The dotted spelling of a name or attribute chain, or "" for anything else."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return f"{base}.{node.attr}" if base else ""
    return ""


def _resolved_name(dotted: str, owner: Any) -> Any:
    """A dotted name looked up where the annotation was written, then builtins."""
    module = inspect.getmodule(owner) or owner
    for namespace in (module, builtins):
        found: Any = namespace
        for part in dotted.split("."):
            found = getattr(found, part, None)
            if found is None:
                break
        else:
            return found
    return None


def _with_receiver(
    signatures: tuple[inspect.Signature, ...], name: Name
) -> tuple[inspect.Signature, ...]:
    """Put the receiver in front of a class member's signature when it is absent.

    `py-call`'s `.method` form takes the object as its first argument, so a
    class member's MeTTa arity counts the receiver. A method descriptor's own
    signature already carries `self`; a docstring writes the BOUND form,
    `requires_grad_(requires_grad=True)`, and this puts the receiver back.
    """
    if name.is_module_level:
        return signatures
    return tuple(_receiving(signature) for signature in signatures)


def _receiving(signature: inspect.Signature) -> inspect.Signature:
    """One signature with a leading receiver, unless it already has one."""
    parameters = list(signature.parameters.values())
    if parameters and parameters[0].name == "self":
        return signature
    receiver = inspect.Parameter("self", inspect.Parameter.POSITIONAL_ONLY)
    return signature.replace(parameters=[receiver, *parameters])


def _call_form(signature: inspect.Signature, arity: int) -> CallForm:
    """The parameters one call of this arity passes, and the result it answers.

    A `*args` tail contributes as many parameters as the arity asks for, each
    named for the variadic and numbered, so the equation reads as the module's
    own parameter list rather than as anonymous slots.
    """
    positional = [
        parameter
        for parameter in signature.parameters.values()
        if parameter.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    variadic = next(
        (
            parameter
            for parameter in signature.parameters.values()
            if parameter.kind is inspect.Parameter.VAR_POSITIONAL
        ),
        None,
    )
    taken = list(positional[:arity])
    if variadic is not None:
        taken.extend(
            inspect.Parameter(
                f"{variadic.name}{index + 1}",
                inspect.Parameter.POSITIONAL_ONLY,
                annotation=variadic.annotation,
            )
            for index in range(arity - len(taken))
        )
    return CallForm(tuple(taken), signature.return_annotation)


def _derived_effect(forms: _collections_abc.Mapping[int, CallForm]) -> str:
    """The effect class a signature's declared result derives.

    Every call form of one head answers the same kind of thing, so the first
    is read and the rest follow it.
    """
    result = next(iter(sorted(forms.items())))[1].result if forms else inspect.Signature.empty
    if result is inspect.Signature.empty:
        return str(EffectClass.oracleIO)
    if metta_type_for(result) in _SCALARS:
        return str(EffectClass.readOnlyLookup)
    if result is None or result is type(None):
        return str(EffectClass.writesState)
    if isinstance(result, type):
        if issubclass(result, _CONTAINERS):
            return str(EffectClass.readOnlyLookup)
        return str(EffectClass.writesState)
    #A result the annotation names and nothing resolves: a docstring's prose,
    #`item() -> number`, declares no type at all. Nothing was reviewed, so the
    #class is the top, which is what the bridge declares for py-call itself.
    return str(EffectClass.oracleIO)


def _arrow(head: str, form: CallForm, effect: str) -> str:
    """One call form's declaration, its effect class inside the arrow.

    The annotated arrow is where MeTTa writes an effect class beside a type,
    so a face declares both in one atom rather than in two
    [source: engine/metta/types.pl, metta_arrow_type_shape].
    """
    types = [
        Symbol(metta_type_for(parameter.annotation)) for parameter in form.parameters
    ]
    types.append(Symbol(metta_type_for(form.result)))
    arrow = Expression([Symbol(f"-[{_DETERMINISM},{effect}]->"), *types])
    return str(Expression([Symbol(":"), Symbol(head), arrow]))


def _equation(name: Name, form: CallForm) -> str:
    """One call form's equation, applying the name through `py-call`.

    Which of `py-call`'s three spellings depends on what the name IS: a module
    function is `(mod.fun ...)`, a class member is `(.method receiver ...)`,
    and anything that is not callable is read with `getattr`
    [source: extensions/python/metta/_binding/surface.pl:839, 'py-call'/3; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
    """
    variables = [Variable(parameter.name) for parameter in form.parameters]
    head = Expression([Symbol(name.head), *variables])
    attribute = name.path.rsplit(".", 1)[-1]
    if not callable(name.target):
        body = Expression(
            [
                Symbol("py-call"),
                Expression([Symbol("getattr"), variables[0], Symbol(attribute)]),
            ]
        )
    elif not name.is_module_level:
        body = Expression(
            [
                Symbol("py-call"),
                Expression([Symbol(f".{attribute}"), *variables]),
            ]
        )
    elif "." in name.path.rsplit(".", 1)[0]:
        #py-call's `mod.fun` spelling splits on EVERY dot and unifies the parts
        #with a two-element list, so a module of any depth misses it: `(py-call
        #(os.path.join "a" "b"))` reports "No module named 'path'". The
        #language's own resolution door reaches a dotted path of any depth and
        #what it answers is applicable in head position, which is the same call
        #written where py-call cannot reach
        #[tested: test_py_call_reaches_one_dot_and_py_atom_reaches_any;
        #commit=7229962705d199fb08796b3090ec5a8a3a0ae393].
        body = Expression(
            [Expression([Symbol("py-atom"), Symbol(name.path)]), *variables]
        )
    else:
        module = name.path.rsplit(".", 2)
        call = Expression([Symbol(f"{module[-2]}.{module[-1]}"), *variables])
        body = Expression([Symbol("py-call"), call])
    if isinstance(form.result, type) and issubclass(form.result, tuple):
        #A Python tuple crossing py-call is neither MeTTa data nor a handle: it
        #arrives as a term that PRINTS as an expression, carries the Expression
        #metatype, and unifies with nothing, so `(== (py-call (divmod 7 2))
        #(3 1))` is False. Through builtins.list it is an ordinary expression
        #and the same comparison is True
        #[tested:
        #test_a_tuple_crossing_py_call_unifies_with_nothing_until_it_is_listed;
        #commit=7229962705d199fb08796b3090ec5a8a3a0ae393].
        body = Expression(
            [Symbol("py-call"), Expression([Symbol("list"), body])]
        )
    return str(Expression([Symbol("="), head, body]))


def _documentation(name: Name, forms: _collections_abc.Mapping[int, CallForm]) -> str | None:
    """One name's `(@doc ...)` atom, or None when the module documents nothing.

    The prose is the docstring with its leading signature lines removed, since
    those are the signature this file has already read and not a description
    of anything. The parameters are the widest call form's, so a head served at
    several arities documents every parameter it can take.
    """
    documentation = inspect.getdoc(name.target) or ""
    prose = _prose(documentation, name.local)
    if not prose:
        return None
    widest = max(forms.items())[1] if forms else CallForm((), inspect.Signature.empty)
    atom = documentation_atom(
        name.head,
        name.target,
        kind="function",
        documentation=prose,
        parameters=[parameter.name for parameter in widest.parameters],
        annotations={
            **{
                parameter.name: parameter.annotation
                for parameter in widest.parameters
            },
            "return": widest.result,
        },
    )
    return None if atom is None else str(atom)


def _prose(documentation: str, local: str) -> str:
    """A docstring with its leading signature lines removed, summary joined."""
    lines = documentation.splitlines()
    taken = len(_leading_signature_lines(documentation, local))
    return first_paragraph("\n".join(lines[taken:]).strip())


def _version_of(module: Any) -> str:
    """The version a module reports for itself, or `unversioned`.

    `__version__` is what a module states about itself, which is the number a
    face was READ from even when the distribution around it is named
    differently.
    """
    return str(getattr(module, "__version__", "unversioned"))


def _signature_name(text: str) -> str:
    """The name one declared signature line describes."""
    name, _, rest = text.partition("(")
    if not rest:
        msg = f"{text!r} is not a signature line: it names no call"
        raise MettaError(msg)
    return name.strip()


def _effect_row(text: str) -> tuple[str, str, str]:
    """One `Effect:` line: the name, the class it declares, and the review."""
    parts = text.split(None, 2)
    if len(parts) < 2:
        msg = (
            f"{text!r} is not an effect review: a line declares a name, an "
            f"effect class and the reason the derived class is wrong"
        )
        raise MettaError(msg)
    name, effect = parts[0], parts[1]
    if effect not in tuple(EffectClass):
        classes = ", ".join(EffectClass)
        msg = f"{effect!r} is not an effect class; the catalog's are {classes}"
        raise MettaError(msg)
    return name, effect, parts[2].strip() if len(parts) > 2 else ""


def _version_row(text: str) -> tuple[str, str]:
    """One `Read from:` line: the module named, and the version it reported."""
    module, _, version = text.partition(" ")
    return module.strip(), version.strip()


def _header(manifest: Manifest, versions: tuple[tuple[str, str], ...]) -> str:
    """A face's header: what it is, what it selected, and the rules it applied."""
    lines = textwrap.wrap(
        manifest.purpose,
        width=79,
        initial_indent=";Purpose: ",
        subsequent_indent=";  ",
    )
    lines.append(f";Generated by: {GENERATOR} --write; edit this header, never the body")
    lines.extend(f";Import: {statement.statement}" for statement in manifest.imports)
    chosen = {
        statement.prefix
        for statement in manifest.imports
        if statement.prefix != _module_prefix(statement.module)
    }
    if len(chosen) > 1:
        spelled = ", ".join(sorted(chosen))
        msg = (
            f"a face publishes under ONE prefix and this one names {spelled}; "
            f"write one face per prefix"
        )
        raise MettaError(msg)
    lines.extend(f";Prefix: {prefix}" for prefix in chosen)
    lines.extend(f";Signature: {text}" for _name, text in manifest.signatures)
    lines.extend(
        f";Effect: {name} {effect}  {reason}" for name, effect, reason in manifest.effects
    )
    lines.extend(f";Read from: {module} {version}" for module, version in versions)
    lines.extend(
        ";" + line if line else ";"
        for line in _RULES.splitlines()
    )
    return "\n".join(lines) + "\n"


#: What every generated face says about how its body was derived. One text, in
#: the generator, so a reader of any face reads the same rules.
_RULES: Final = """
A head is the import's module prefix and the name's own spelling with
underscores read as hyphens. Each declaration is one reachable POSITIONAL call
form: a defaulted parameter makes its arity optional, a `*args` serves zero to
four arguments, and `**kwargs` and keyword-only parameters are absent, because
a MeTTa call site passes positionally. A parameter the module does not annotate
is `%Undefined%`, and so is every foreign class: a py-call'd object's type IS
`%Undefined%`, and a face naming the class would refuse the call it wraps. The
effect class inside each arrow is derived from the result the signature
declares -- a scalar or a container answers a VALUE and is `readOnlyLookup`, a
live foreign object or a call made for what it does is `writesState`, and a
result nothing declares is `oracleIO`, the top, exactly as the engine
classifies `py-call` itself -- and an `Effect:` line above declares the review
a signature cannot show."""
