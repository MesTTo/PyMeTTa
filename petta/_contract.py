"""Purpose: the contract ontology, the typed vocabulary every seam
declaration is stated in. Loaded into &petta at boot, before any user
declaration, so a declaration's kind, fidelity, effect, image, source,
error-mode, atomicity, merge-policy and semiring names are ordinary typed
atoms a program can match, get-type, and widen over. The fidelity chain
Exact :< Partial :< Sound rides the engine's own subtype widening, which is
what lets a stronger claim stand wherever a weaker one is required.
Assumes:
  - the &petta reflection space exists by the time install runs, which
    engine boot guarantees by installing the prelude operations first
    [tested test_the_ontology_is_loaded_at_boot]
Guarantees:
  - install is idempotent per engine process: the ontology enters once
    [tested test_the_ontology_loads_once]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from ._convert_registry import subscribe_registrations
from .atoms import Expr, Sym

__all__ = ["ONTOLOGY", "install"]

_COLON = ":"
_SUB = ":<"

# (head, subject, object) triples; the whole ontology is (: X Y) and
# (:< X Y) forms, so triples are the entire grammar it needs.
ONTOLOGY: tuple[tuple[str, str, str], ...] = (
    (_COLON, "Declaration", "Type"),
    (_COLON, "OpDecl", "Type"),
    (_SUB, "OpDecl", "Declaration"),
    (_COLON, "EffectDecl", "Type"),
    (_SUB, "EffectDecl", "Declaration"),
    (_COLON, "ImageDecl", "Type"),
    (_SUB, "ImageDecl", "Declaration"),
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
    (_COLON, "Fidelity", "Type"),
    (_COLON, "Exact", "Fidelity"),
    (_COLON, "Partial", "Fidelity"),
    (_COLON, "Sound", "Fidelity"),
    (_COLON, "Refuse", "Fidelity"),
    # Refuse is deliberately outside the chain: it is not a weaker claim,
    # it is the absence of a stream.
    (_SUB, "Exact", "Partial"),
    (_SUB, "Partial", "Sound"),
    (_COLON, "Effect", "Type"),
    (_COLON, "immutable", "Effect"),
    (_COLON, "stable", "Effect"),
    (_COLON, "volatile", "Effect"),
    (_COLON, "ImageSetting", "Type"),
    (_COLON, "opaque", "ImageSetting"),
    (_COLON, "transparent", "ImageSetting"),
    (_COLON, "auto", "ImageSetting"),
    (_COLON, "SourceKind", "Type"),
    (_COLON, "linear", "SourceKind"),
    (_COLON, "repeated", "SourceKind"),
    (_COLON, "peek", "SourceKind"),
    (_COLON, "ErrorMode", "Type"),
    (_COLON, "keep", "ErrorMode"),
    (_COLON, "empty", "ErrorMode"),
    (_COLON, "abort", "ErrorMode"),
    (_COLON, "Atomicity", "Type"),
    (_COLON, "transactional", "Atomicity"),
    (_COLON, "atomic-single", "Atomicity"),
    (_COLON, "best-effort", "Atomicity"),
    (_COLON, "MergePolicy", "Type"),
    (_COLON, "depth", "MergePolicy"),
    (_COLON, "fair", "MergePolicy"),
    (_COLON, "best-first", "MergePolicy"),
    (_COLON, "Semiring", "Type"),
    (_COLON, "bool", "Semiring"),
    (_COLON, "bag", "Semiring"),
    (_COLON, "set", "Semiring"),
    (_COLON, "ranked", "Semiring"),
    (_COLON, "prob", "Semiring"),
    (_COLON, "prov", "Semiring"),
    (_COLON, "TypeImage", "Type"),
    (_COLON, "symbol", "TypeImage"),
    (_COLON, "expression", "TypeImage"),
    (_COLON, "handle", "TypeImage"),
    (_COLON, "operations", "TypeImage"),
    (_COLON, "Determinism", "Type"),
    (_COLON, "det", "Determinism"),
    (_COLON, "semidet", "Determinism"),
    (_COLON, "nondet", "Determinism"),
)

_SPACE = "&petta"
# The atom whose presence says the ontology is in; its own first triple.
_SENTINEL = Expr([Sym(_COLON), Sym("Declaration"), Sym("Type")])


def _image_atom(registration) -> Expr:
    return Expr([Sym("image"), Sym(registration.type_name), Sym(registration.image)])


def _reflect_image(runtime, old, new) -> None:
    if old is not None:
        runtime.once("petta_py_remove(Space, W, _)", Space=_SPACE, W=_image_atom(old).to_wire())
    if new is not None:
        runtime.must("petta_py_add(Space, W)", Space=_SPACE, W=_image_atom(new).to_wire())


def install(runtime) -> None:
    """Assert the ontology into &petta, once per engine, and keep the
    registry's explicit type images reflected there: one
    (image TypeName registry-image) atom per register_type, retired on
    unregister. The registry stays engine-free; this listener is the whole
    coupling, and it hears the past (the snapshot) before the future.
    """
    if runtime.do("petta_py_contains", _SPACE, _SENTINEL.to_wire()):
        return
    for head, subject, obj in ONTOLOGY:
        atom = Expr([Sym(head), Sym(subject), Sym(obj)])
        runtime.must("petta_py_add(Space, W)", Space=_SPACE, W=atom.to_wire())
    def listener(_cls, old, new, _runtime=runtime):
        _reflect_image(_runtime, old, new)

    for _cls, registration in subscribe_registrations(listener):
        _reflect_image(runtime, None, registration)
