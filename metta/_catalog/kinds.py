"""Purpose: this seat's own DECLARATION KINDS, typed. Loaded into &metta at
boot, before any user declaration, so a declaration's kind and every typed head
are ordinary atoms a program can match, get-type, and widen over.

The ENGINE's words are not here. Every closed value set this file used to
restate -- the effect ranks, the fidelities and their Exact :< Partial :< Sound
chain, the image modes, the registry images, the error modes, the atomicities,
the answer policies, the source kinds, the determinisms, the operation kinds,
the semirings and the argument deliveries -- is a `(vocabulary ...)` row the
engine types itself, under the name the row gives it. The seat had chosen its
own CamelCase for eleven of them, one of which (`Semiring`) listed six members
while the engine derived ten, and one of which (`ArgumentDelivery`) is now an
engine vocabulary of that exact name. What is left here is what this seat
DECLARES and no other seat has.
Assumes:
  - the &metta reflection space exists by the time install runs, which
    engine boot guarantees by installing the prelude operations first
    [tested test_the_ontology_is_loaded_at_boot]
Guarantees:
  - host door contracts and their typed constructors are present at boot;
    publication refuses invalid rows atomically [tested:
    test_boot_publishes_complete_typed_door_rows,
    test_door_catalog_publication_is_atomic_and_idempotent; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543]
  - a door row registered or withdrawn after boot is in the catalog at once,
    with no refresh asked for: the catalog is a function of the door registry
    [tested: test_door_catalog_publication_is_atomic_and_idempotent;
    commit=58bf75947fc58ec32b2372ef0d2c14a00aa2390a]
  - install is idempotent per engine process: the ontology enters once
    [tested test_the_ontology_loads_once]
  - registered synchronous and coroutine operation kinds inhabit OpKind and
    `(op ...)` terms inhabit OpDecl [tested:
    test_every_register_op_writes_its_declaration_and_get_doc_answers,
    test_an_async_operation_answers_a_future_space; commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - compiled-definition source, capture, and effect facts are typed ordinary
    declarations [tested: test_each_ast_derived_fact_replaces_the_flag_it_supersedes;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the vocabulary types these arrows name are the ENGINE's own, written
    beside each `(vocabulary ...)` row rather than here
    [tested: test_every_vocabulary_is_typed_by_the_engine; commit=7f9c810e5f4a2023ad98de34e848667dd72bc4a7]
  - lint evidence and named suppression intent are typed declarations rather
    than comments lost after parsing [tested:
    test_lint_evidence_and_intent_are_typed_reflection_facts; commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - callable argument delivery is a typed `(arguments name atoms|values)`
    policy in &metta [tested:
    test_no_decorator_flag_changes_the_return_shape_and_declarations_are_atoms;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - context image declarations state whether one Python type crosses as a
    handle or a structural expression [tested:
    test_an_opaque_blob_column_is_reached_by_a_lazy_path_without_crossing;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from typing import TYPE_CHECKING

from metta._atoms.factories import Expression, Symbol
from metta._atoms.registry import subscribe_registrations
from metta._lazy import lazy
from metta.seam import on_registration

if TYPE_CHECKING:
    import metta._binding.runtime
    import metta.doors  # noqa: F401 -- child of the deferred package namespace
if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
if TYPE_CHECKING:
    from metta import _binding
else:
    _binding = lazy('metta._binding')

__all__ = ["ONTOLOGY", "install"]

_COLON = ":"
_SUB = ":<"

# (head, subject, object) triples; the whole ontology is (: X Y) and
# (:< X Y) forms, so triples are the entire grammar it needs.
# A NAME position is declared `Atom` rather than `Symbol`. A name's metatype
# says whether the engine holds a FUNCTION for it, which is upstream PeTTa's
# rule and this engine's since 2026-09-05 [source: PeTTa@43705f5d
# src/metta.pl:202], so an operation name is `Grounded` the moment
# `metta.op` registers it and a defined name is `Grounded` the moment its
# clauses exist. These positions hold exactly those names, so `Symbol`
# refused the facts this ontology exists to type and
# `!(get-type (op p5-async-1 1 async))` answered no type at all. `Atom` is
# the metatype wildcard and the true claim; a field naming a CLOSED set keeps
# the type the ENGINE gives that vocabulary (`OpKind`, `EffectClass`,
# `ArgumentDelivery`, `ImageMode`, `RegistryImage`), which is the mechanical
# CamelCase of the row's name or its declared `(vocabulary-type ...)`
# exception.
_OP_DECL_TYPE = Expression([Symbol("->"), Symbol("Atom"), Symbol("Number"), Symbol("OpKind"), Symbol("OpDecl")])
_DEFINED_TYPE = Expression([Symbol("->"), Symbol("SpaceType"), Symbol("Atom"), Symbol("DefinitionFact")])
_SOURCE_SPAN_TYPE = Expression(
    [
        Symbol("->"),
        Symbol("SpaceType"),
        Symbol("Atom"),
        Symbol("String"),
        Symbol("Number"),
        Symbol("Number"),
        Symbol("Number"),
        Symbol("Number"),
        Symbol("DefinitionFact"),
    ]
)
_FREE_VARIABLE_TYPE = Expression(
    [
        Symbol("->"),
        Symbol("SpaceType"),
        Symbol("Atom"),
        Symbol("Atom"),
        Symbol("DefinitionFact"),
    ]
)
_EFFECT_TYPE = Expression([Symbol("->"), Symbol("Atom"), Symbol("EffectClass"), Symbol("EffectDecl")])
_ARGUMENTS_TYPE = Expression(
    [Symbol("->"), Symbol("Atom"), Symbol("ArgumentDelivery"), Symbol("ArgumentsDecl")]
)
_CONTEXT_IMAGE_TYPE = Expression(
    [Symbol("->"), Symbol("SpaceType"), Symbol("Atom"), Symbol("ImageMode"), Symbol("ImageDecl")]
)
_REGISTRY_IMAGE_TYPE = Expression(
    [Symbol("->"), Symbol("Atom"), Symbol("RegistryImage"), Symbol("ImageDecl")]
)
_LINT_EVIDENCE_TYPE = Expression(
    [
        Symbol("->"),
        Symbol("SpaceType"),
        Symbol("Atom"),
        Symbol("String"),
        Symbol("String"),
        Symbol("Number"),
        Symbol("Number"),
        Symbol("String"),
        Symbol("LintEvidence"),
    ]
)
_LINT_INTENT_TYPE = Expression(
    [
        Symbol("->"),
        Symbol("SpaceType"),
        Symbol("Atom"),
        Symbol("String"),
        Symbol("Number"),
        Symbol("Number"),
        Symbol("Number"),
        Symbol("Number"),
        Symbol("String"),
        Symbol("LintIntent"),
    ]
)

# closed-set: decides; policy=this seat's own DECLARATION KINDS and their types, which no other seat has; reads=none, it is the source, and every engine vocabulary it used to restate is now typed by the engine itself
ONTOLOGY: tuple[tuple[str, str, str | Expression], ...] = (
    (_COLON, "Declaration", "Type"),
    (_COLON, "OpDecl", "Type"),
    (_SUB, "OpDecl", "Declaration"),
    (_COLON, "op", _OP_DECL_TYPE),
    (_COLON, "DefinitionFact", "Type"),
    (_SUB, "DefinitionFact", "Declaration"),
    (_COLON, "defined", _DEFINED_TYPE),
    (_COLON, "source-span", _SOURCE_SPAN_TYPE),
    (_COLON, "free-variable", _FREE_VARIABLE_TYPE),
    (_COLON, "EffectDecl", "Type"),
    (_SUB, "EffectDecl", "Declaration"),
    (_COLON, "ArgumentsDecl", "Type"),
    (_SUB, "ArgumentsDecl", "Declaration"),
    (_COLON, "arguments", _ARGUMENTS_TYPE),
    (_COLON, "ImageDecl", "Type"),
    (_SUB, "ImageDecl", "Declaration"),
    (_COLON, "image", _CONTEXT_IMAGE_TYPE),
    (_COLON, "type-image", _REGISTRY_IMAGE_TYPE),
    (_COLON, "LintEvidence", "Type"),
    (_SUB, "LintEvidence", "Declaration"),
    (_COLON, "lint-evidence", _LINT_EVIDENCE_TYPE),
    (_COLON, "LintIntent", "Type"),
    (_SUB, "LintIntent", "Declaration"),
    (_COLON, "lint-intent", _LINT_INTENT_TYPE),
    (_COLON, "HandlesDecl", "Type"),
    (_SUB, "HandlesDecl", "Declaration"),
    (_COLON, "LoweringDecl", "Type"),
    (_SUB, "LoweringDecl", "Declaration"),
    (_COLON, "ContextDecl", "Type"),
    (_SUB, "ContextDecl", "Declaration"),
    (_COLON, "SourceDecl", "Type"),
    (_SUB, "SourceDecl", "Declaration"),
    (_COLON, "ErrorDecl", "Type"),
    (_SUB, "ErrorDecl", "Declaration"),
    (_COLON, "WritesDecl", "Type"),
    (_SUB, "WritesDecl", "Declaration"),
    (_COLON, "MergeDecl", "Type"),
    (_SUB, "MergeDecl", "Declaration"),
    (_COLON, "BridgeDecl", "Type"),
    (_SUB, "BridgeDecl", "Declaration"),
    (_COLON, "effect", _EFFECT_TYPE),
)

_SPACE = "&metta"
# The atom whose presence says the ontology is in; its own first triple.
_SENTINEL = Expression([Symbol(_COLON), Symbol("Declaration"), Symbol("Type")])


def _image_atom(registration) -> Expression:
    return Expression([Symbol("type-image"), Symbol(registration.type_name), Symbol(registration.image)])


def _reflect_image(runtime, old, new) -> None:
    if old is not None:
        runtime.once("metta_py_remove(Space, W, _)", Space=_SPACE, W=_image_atom(old).to_wire())
    if new is not None:
        runtime.must("metta_py_add(Space, W)", Space=_SPACE, W=_image_atom(new).to_wire())


def install(runtime) -> None:
    """Assert the ontology into &metta, once per engine, and keep the
    registry's explicit type images reflected there: one
    (type-image TypeName registry-image) atom per register_type, retired on
    unregister. The registry stays engine-free; this listener is the whole
    coupling, and it hears the past (the snapshot) before the future.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if runtime.do("metta_py_contains", _SPACE, _SENTINEL.to_wire()):
        _root.doors.publish(runtime)
        return
    for head, subject, obj in ONTOLOGY:
        atom = Expression([Symbol(head), Symbol(subject), obj if isinstance(obj, Expression) else Symbol(obj)])
        runtime.must("metta_py_add(Space, W)", Space=_SPACE, W=atom.to_wire())
    # The seat's own bounds, as rows a program can read and replace. Here
    # because this is the one place a boot already writes the seat's
    # declarations into &metta [source: extensions/python/metta/_catalog/bounds.py:573,
    # publish; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
    from metta._catalog.bounds import (  # noqa: PLC0415 -- the bounds table
        publish as _publish_limits,
    )

    _publish_limits(runtime)

    def listener(_cls, old, new, _runtime=runtime):
        _reflect_image(_runtime, old, new)

    for _cls, registration in subscribe_registrations(listener):
        _reflect_image(runtime, None, registration)

    _root.doors.publish(runtime)


def _doors_changed(point: str, _name: str, _undo: object) -> None:
    """Keep the door catalog a function of the door registry.

    A door row registered or withdrawn after boot is published to the live
    engine at once, through the same transactional, idempotent publication
    boot uses, so a package discovered late or withdrawn early is never in the
    table and absent from the catalog. Before boot there is no engine to
    publish to and boot's own publication reads the registry as it stands.
    """
    if point != "door":
        return

    if _binding.runtime.booted():

        _root.doors.publish(_binding.runtime.runtime())


on_registration(_doors_changed)
