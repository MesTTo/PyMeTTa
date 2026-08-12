"""Purpose: registration of Python callables as MeTTa functions. Reads the
signature for arities (defaults yield several), auto-detects nondeterminism
(a generator function is one), derives a MeTTa type declaration from the
annotations, and registers the whole thing with the engine through shim.pl.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: keyword-argument call forms once PeTTa itself grows a
    spelling for them; today MeTTa call sites are positional.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable

from .atoms import Atom, Expr, S, Sym, Var, expr
from ._ops import REGISTRY, Operation

__all__ = ["register", "unregister", "metta_type_for", "registered"]

# Python annotation -> MeTTa type name. Everything else is %Undefined%,
# matching what the engine says about an undeclared value.
_TYPE_NAMES: list[tuple[type, str]] = [
    (bool, "Bool"),  # before int: bool is an int in Python, not in MeTTa
    (int, "Number"),
    (float, "Number"),
    (str, "String"),
]


def metta_type_for(annotation: Any) -> str:
    """The MeTTa type a Python annotation names."""
    if annotation is inspect.Parameter.empty or annotation is Any:
        return "%Undefined%"
    if annotation in (Atom, Expr, Sym, Var):
        return "Atom"
    for py, name in _TYPE_NAMES:
        if annotation is py:
            return name
    return "%Undefined%"


def _metta_name(fn: Callable, name: str | None) -> str:
    """The MeTTa spelling: underscores read as hyphens unless overridden."""
    return name if name is not None else fn.__name__.replace("_", "-")


def _arities(fn: Callable, explicit: list[int] | None) -> tuple[list[int], list[inspect.Parameter]]:
    """Every arity the defaults allow, smallest first, plus the parameters.

    An explicit arities list overrides the derivation, which is how a
    variadic callable registers: the call sites it serves are named rather
    than inferred, since *args alone says nothing about MeTTa call forms.
    """
    sig = inspect.signature(fn)
    params = []
    variadic = False
    for p in sig.parameters.values():
        if p.kind is inspect.Parameter.VAR_KEYWORD:
            continue  # unreachable from MeTTa, harmless to ignore
        if p.kind is inspect.Parameter.VAR_POSITIONAL:
            variadic = True
            continue
        if p.kind is inspect.Parameter.KEYWORD_ONLY:
            raise TypeError(
                f"cannot register {fn.__name__}: keyword-only parameter "
                f"{p.name!r} is unreachable from a positional MeTTa call site"
            )
        params.append(p)
    if explicit is not None:
        return sorted(set(explicit)), params
    if variadic:
        raise TypeError(
            f"cannot register {fn.__name__}: *args has no single MeTTa call "
            f"form; pass arities=[...] naming the argument counts to serve"
        )
    required = sum(1 for p in params if p.default is inspect.Parameter.empty)
    return list(range(required, len(params) + 1)), params


def _type_declaration(name: str, params: list[inspect.Parameter], fn: Callable) -> Expr:
    """(: name (-> T1 .. Tn R)) from the annotations, arrow over full arity."""
    arg_types = [S[metta_type_for(p.annotation)] for p in params]
    returns = inspect.signature(fn).return_annotation
    ret = S[metta_type_for(returns if returns is not inspect.Signature.empty else Any)]
    return expr(S[":"], S[name], Expr([S["->"], *arg_types, ret]))


def register(
    runtime,
    fn: Callable,
    *,
    name: str | None = None,
    typed: bool = True,
    raw: bool = False,
    pass_atoms: bool = False,
    space: str = "&self",
    arities: list[int] | None = None,
) -> Callable:
    """Make fn callable from MeTTa. Returns fn unchanged.

    A generator function registers as nondeterministic: each yield is one
    answer, and MeTTa's collapse, superpose and let compose over them. A
    plain function is deterministic; returning None or raising Decline
    answers nothing. Defaults yield one registration per reachable arity;
    a variadic callable names its call forms with arities=[...].
    """
    metta_name = _metta_name(fn, name)
    arities, params = _arities(fn, arities)
    many = inspect.isgeneratorfunction(fn)
    kind = ("raw_many" if many else "raw_det") if raw else ("many" if many else "det")
    # One registry entry serves every arity: the engine passes however many
    # arguments the call site had, and the defaults absorb the difference.
    REGISTRY[metta_name] = Operation(
        name=metta_name, fn=fn, kind=kind, arity=max(arities), pass_atoms=pass_atoms
    )
    for arity in arities:
        runtime.once(
            "petta_py_register_op(Name, Arity, Kind)",
            Name=metta_name,
            Arity=arity,
            Kind=kind,
        )
    if typed and params:
        declaration = _type_declaration(metta_name, params, fn)
        runtime.once(
            "petta_py_add(Space, W)", Space=space, W=declaration.to_wire()
        )
    return fn


def unregister(runtime, name: str) -> None:
    """Remove every arity of a registered operation."""
    op = REGISTRY.pop(name, None)
    if op is None:
        return
    for arity_row in runtime.iter(
        "petta_py_op_spec(Name, Arity, _)", Name=name
    ):
        runtime.once(
            "petta_py_unregister_op(Name, Arity)", Name=name, Arity=arity_row["Arity"]
        )


def registered() -> dict[str, Operation]:
    """The live registry, name to operation."""
    return dict(REGISTRY)
