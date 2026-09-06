"""Purpose: arrays as atoms for every library speaking the standard
protocols, not one. Recognition is DLPack (__dlpack__), semantics are the
Python array API standard reached through array-api-compat, so one operation
set serves NumPy, PyTorch, CuPy, JAX, Dask and whatever conforms next, and a
mixed-library call converts through from_dlpack. Arrays cross the boundary
by reference with identity, DLTensor joins each array's own classes as a
type, and printing shows shape, dtype and device whatever the library.
Built entirely on the public integration interface; pettorch instantiates it
with torch as the constructor default and proves nothing here is
torch-shaped.
Guarantees:
  - _top_indices returns the highest finite scores first and resolves equal
    scores by insertion order [tested test_top_indices_match_full_order_and_stabilize_ties]
  - _top_indices uses 35.26% fewer instructions than the prior full sort for
    500 top-10 selections from 100,000 scores [measured 2026-08-14: minimum
    of three perf stat instructions:u runs]
  - the fixed public constructor vocabulary is marked Final to type
    checkers [tested test_policy_constants_are_final]
  - all 44 installed operation names own arity-accurate arrows, and
    broadcast-shape relates compatible dimensions before any array exists
    [tested: test_every_array_operation_is_typed_and_a_shape_is_a_constraint;
     commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - array transport and Atom-delivery choices use the same declaration
    surface as every registered operation [tested:
    test_no_decorator_flag_changes_the_return_shape_and_declarations_are_atoms;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - operations returning mutable arrays are writesState, scalar inspections
    are readOnlyLookup, random construction is oracleIO, and embedding search
    is nondeterministicReadOnly [tested:
    test_every_array_operation_is_typed_and_a_shape_is_a_constraint,
    test_embedding_store_runs_on_numpy;
    commit=3cfbe0d7417b1c453c2dc12d47e2e47e7de461f7]
  - constructor registrations use the backend namespace's fully qualified
    module name, so installing ``jax.numpy`` and then ``numpy`` cannot
    retarget the first space; random construction never borrows a different
    backend's hidden random state [tested:
    test_nested_backend_names_do_not_retarget_an_earlier_space,
    test_randn_never_borrows_another_backends_random_state;
    commit=de15573db164c24b9dcaa3e5b783e66dcb05d4d1]
  - a mixed call converts on the LIBRARY the operand belongs to and not on
    its Python class, so two classes of one namespace, a JAX tracer beside a
    concrete array among them, cross untouched [tested:
    test_an_operand_of_the_same_library_is_not_converted_through_dlpack,
    test_a_jax_tracer_crosses_a_binary_op_and_a_gradient_reaches_it]
  - install() and EmbeddingStore take a context or a space and register into
    the space either way [tested: test_install_takes_a_context_as_well_as_a_space,
    test_embedding_store_takes_a_context_as_well_as_a_space; commit=f25ac80f93e7c3626b87e593117d09b9c9bc8c95]
  - Shape metadata survives Python ``Annotated`` reflection, shaped tensors
    remain valid ``DLTensor`` arguments, broadcast arithmetic infers its
    output through ``broadcast-shape``, and rank-two ``matmul`` unifies its
    shared dimension before materialisation [tested:
    test_annotated_tensor_shapes_flow_through_broadcast_and_matmul;
    commit=4eaefdd8d40e53b2613722287302a14b41704662]
  - declared and observed shapes use one Annotated type expression; every
    registered head names its shape behavior and preserving arrows share their
    input shape [tested: test_declared_shape_variables_derive_the_result_without_execution,
    test_every_preserving_unary_head_keeps_symbolic_and_live_shapes;
    commit=4eaefdd8d40e53b2613722287302a14b41704662]
Guarded by:
  - _PROTOCOLS_LOCK serializes one-time protocol registration
    [tested test_array_protocol_registration_is_idempotent]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import importlib
import inspect
import itertools
import operator
import threading
from collections.abc import Iterable
from functools import wraps
from typing import Annotated, Any, Final, Literal, NewType, cast

from . import integrate as _integrate
from ._ops import REGISTRY
from ._optional import optional_module, require_module
from .atoms import (
    Atom,
    Expression,
    Grounded,
    S,
    V,
    Variable,
    _alpha_eq,
    _decode,
    _expr,
    ground,
)
from .errors import MettaError

__all__ = [
    "ARRAY_OPS",
    "SHAPE_RULES",
    "DLTensor",
    "EmbeddingStore",
    "Shape",
    "data_of",
    "install",
    "is_array",
    "namespace_of",
]

ARRAY_OPS: list[str] = []
# Shape behavior for every logical head; backend constructor aliases use the
# same entry. Only preserve, broadcast, and matmul derive unevaluated types.
# Other rules describe the runtime transformation whose result is observed by
# the grounded type protocol. A missing entry refuses registration.
SHAPE_RULES: Final[dict[str, str]] = {
    "tensor": "from-data",
    "zeros": "dimensions",
    "ones": "dimensions",
    "randn": "dimensions",
    "arange-t": "range-length",
    "eye": "square",
    "matmul": "matmul",
    "t+": "broadcast",
    "t-": "broadcast",
    "t*": "broadcast",
    "t/": "broadcast",
    "t-pow": "broadcast",
    "t-neg": "preserve",
    "t-exp": "preserve",
    "t-log": "preserve",
    "relu": "preserve",
    "sigmoid": "preserve",
    "softmax": "preserve",
    "tanh": "preserve",
    "t-as": "preserve",
    "reshape": "reshape",
    "t-transpose": "swap-axes",
    "unsqueeze": "insert-axis",
    "squeeze": "remove-unit-axis",
    "t-index": "index-leading-axis",
    "cat": "concatenate-axis",
    "stack": "stack-axis",
    "t-sum": "reduce-all",
    "t-mean": "reduce-all",
    "t-max": "reduce-all",
    "t-min": "reduce-all",
    "t-norm": "reduce-all",
    "t-argmax": "reduce-axis",
    "t-item": "scalar-observation",
    "t-tolist": "nested-observation",
    "t-shape": "shape-observation",
    "t-dtype": "dtype-observation",
    "t-device": "device-observation",
}
DLTensor = NewType("DLTensor", Any)  # type: ignore[valid-newtype]  # ty: ignore[invalid-newtype]
_PROTOCOLS_REGISTERED = threading.Event()
_PROTOCOLS_LOCK = threading.Lock()

# Constructor names aliased per space: the operation registers once per
# backend under name--lib, and each installed space carries equations
# routing its own (tensor ...) to its own backend, so two spaces with two
# default libraries coexist and a later install never retargets an earlier
# space's constructors. Reinstalling a space with another default replaces
# ITS aliases; (space, name) -> (library, arities) records what to remove.
_CONSTRUCTOR_NAMES: Final[tuple[str, ...]] = (
    "tensor",
    "zeros",
    "ones",
    "randn",
    "arange-t",
    "eye",
)
_SPACE_CONSTRUCTORS: dict[tuple[str, str], tuple[str, list[int]]] = {}
_SPACE_STORES: dict[tuple[str, str], tuple[str, str]] = {}
_STORE_SERIAL = itertools.count(1)

_BROADCAST_SHAPE_SOURCE: Final[str] = r"""
:- use_module(library(clpfd)).
:- metta_extension(metta_arrays_shape, [version('0.1.0')]).
:- metta_export("(: broadcast-shape (-> Expression Expression Expression Bool))").

'broadcast-shape'(Left, Right, Shape, true) :-
    reverse(Left, LeftReversed),
    reverse(Right, RightReversed),
    metta_broadcast_reversed(LeftReversed, RightReversed, ShapeReversed),
    reverse(ShapeReversed, Shape).

metta_broadcast_reversed([], Shape, Shape) :- !.
metta_broadcast_reversed(Shape, [], Shape) :- !.
metta_broadcast_reversed([Left | Lefts], [Right | Rights], [Out | Outs]) :-
    metta_broadcast_dimension(Left, Right, Out),
    metta_broadcast_reversed(Lefts, Rights, Outs).

metta_broadcast_dimension(D2, D1, D) :-
    D1 #\= 1 #/\ D1 #= D #\ D1 #= 1 #/\ D2 #= D,
    D2 #\= 1 #/\ D2 #= D #\ D2 #= 1 #/\ D1 #= D.
"""

_SHAPED_TENSOR_RULE: Final[str] = (
    "!(add-typing-rule! metta-arrays-shaped-dltensor-base ordinary "
    "(Annotated DLTensor (Shape $shape)) DLTensor accept)"
)


def Shape(*dimensions: Any) -> Expression:  # noqa: N802  -- type-metadata constructors follow Python's type spelling
    """Build tensor dimension metadata.

    ``Annotated[DLTensor, Shape(...)]`` accepts integers or MeTTa variables.
    The dimensions stay in one expression so the same metadata is both a
    Python annotation claim and an input to ``broadcast-shape``.
    """
    return _expr(S.Shape, _expr(*dimensions))


def _shape_metadata(shape: Atom) -> Expression:
    """A Shape claim around an already assembled dimension expression."""
    return _expr(S.Shape, shape)


def _shaped_tensor(shape: Atom) -> Expression:
    """The MeTTa type carried by one Shape claim."""
    return _expr(S.Annotated, S.DLTensor, _shape_metadata(shape))


#: The shape reader every inference equation goes through. It exists for its
#: FIRST line: `(get-type $x)` is asked with an unbound subject as a matter of
#: course, `!(get-type $subject)` is one of the engine's own pinned questions,
#: and an equation whose head is `(get-type (t+ $l $r))` unifies with that
#: subject and then asks `(get-type $l)` about a variable it has just invented.
#: That descends forever. Reading the operand's metatype first refuses the
#: variable and the whole equation fails, which is the answer a shape rule owes
#: a subject that has no shape yet.
_SHAPE_READER: Final[str] = "metta-arrays-tensor-shape"


def _tensor_shape_equation() -> Expression:
    """The guarded reader: a bound operand's Shape metadata, or no answer."""
    subject = Variable("__arrays_subject")
    shape = Variable("__arrays_shape")
    return _expr(
        S["="],
        _expr(S[_SHAPE_READER], subject),
        _expr(
            S.let,
            ground(value=False),
            _expr(S["=="], _expr(S["get-metatype"], subject), S.Variable),
            _expr(
                S.let,
                _shaped_tensor(shape),
                _expr(S["get-type"], subject),
                shape,
            ),
        ),
    )


def _broadcast_type_equation(name: str) -> Expression:
    """Infer the shaped result of one elementwise binary operation."""
    left = Variable("__arrays_left")
    right = Variable("__arrays_right")
    left_shape = Variable("__arrays_left_shape")
    right_shape = Variable("__arrays_right_shape")
    out_shape = Variable("__arrays_out_shape")
    return _expr(
        S["="],
        _expr(S["get-type"], _expr(S[name], left, right)),
        _expr(
            S.let,
            left_shape,
            _expr(S[_SHAPE_READER], left),
            _expr(
                S.let,
                right_shape,
                _expr(S[_SHAPE_READER], right),
                _expr(
                    S.let,
                    ground(value=True),
                    _expr(S["broadcast-shape"], left_shape, right_shape, out_shape),
                    _shaped_tensor(out_shape),
                ),
            ),
        ),
    )


def _matmul_type_equation() -> Expression:
    """Infer ``(rows, shared) x (shared, columns) -> (rows, columns)``."""
    left = Variable("__arrays_left")
    right = Variable("__arrays_right")
    rows = Variable("__arrays_rows")
    shared = Variable("__arrays_shared")
    columns = Variable("__arrays_columns")
    return _expr(
        S["="],
        _expr(S["get-type"], _expr(S.matmul, left, right)),
        _expr(
            S.let,
            _expr(rows, shared),
            _expr(S[_SHAPE_READER], left),
            _expr(
                S.let,
                _expr(shared, columns),
                _expr(S[_SHAPE_READER], right),
                _shaped_tensor(_expr(rows, columns)),
            ),
        ),
    )


def _top_indices(xp: Any, scores: Any, count: int) -> list[int]:
    """Top score indexes, best first, without sorting the full NumPy array."""
    size = int(scores.shape[0])
    if count <= 0:
        return []
    if count >= size:
        candidates = list(range(size))
    elif hasattr(xp, "argpartition"):
        boundary = size - count
        partition = xp.argpartition(scores, boundary)[boundary:]
        threshold = min(float(scores[int(index)]) for index in partition)
        nonzero = getattr(xp, "nonzero", None)
        if nonzero is None:
            msg = "an argpartition namespace must also provide nonzero"
            raise RuntimeError(msg)
        better = [int(index) for index in nonzero(scores > threshold)[0]]
        needed = count - len(better)
        tied = [int(index) for index in nonzero(scores == threshold)[0][:needed]]
        candidates = [*better, *tied]
    else:
        order = xp.argsort(scores)
        candidates = [int(order[-(offset + 1)]) for offset in range(count)]
    return sorted(candidates, key=lambda index: (-float(scores[index]), index))


def _alias_equation(name: str, library: str, arity: int) -> Expression:
    _variables = [Variable(f"a{i}") for i in range(1, arity + 1)]
    return Expression(
        [
            S["="],
            Expression([S[name], *_variables]),
            Expression([S[f"{name}--{library}"], *_variables]),
        ]
    )


def _route_equation(alias: str, target: str, arity: int) -> Expression:
    _variables = [Variable(f"a{i}") for i in range(1, arity + 1)]
    return Expression([S["="], Expression([S[alias], *_variables]), Expression([S[target], *_variables])])


def is_array(x: Any) -> bool:
    """Whether a value speaks DLPack, the exchange protocol array libraries share."""
    return hasattr(x, "__dlpack__")


def _compat():
    return require_module(
        "array_api_compat",
        "metta.arrays needs array-api-compat, the standard's compatibility "
        "layer over NumPy, PyTorch, CuPy, JAX and Dask; install pymetta[arrays]",
    )


def _numpy():
    return require_module(
        "numpy",
        "metta.arrays needs NumPy for default arrays and embedding storage; install pymetta[arrays]",
    )


def _faiss():
    return require_module(
        "faiss",
        "the faiss embedding backend needs faiss-cpu; install pymetta[arrays]",
    )


def namespace_of(x: Any):
    """The array API namespace an array belongs to: its own library, wrapped."""
    return _compat().array_namespace(x)


def _into(namespace: Any, like: Any, value: Any):
    """``value`` as an array of ``namespace``, converted only when it is not.

    Which LIBRARY a value belongs to is the question, and Python type identity
    is not that question. JAX's tracer and its concrete array are two classes
    of ONE namespace, and a tracer carries ``__dlpack__`` without the
    ``__dlpack_device__`` half, so converting one was both unnecessary and
    impossible: ``from_dlpack`` refuses it with "The array passed to
    from_dlpack must have __dlpack__ and __dlpack_device__ methods", which
    took every traced call through ``jax.jit`` and ``jax.grad`` down with it
    [measured 2026-09-04 on jax 0.11.0: ``namespace_of(tracer)`` IS
    ``namespace_of(concrete)`` while ``type`` reads DynamicJaxprTracer against
    ArrayImpl].

    The type test stays in front of the namespace one as a fast path, because
    two values of one Python type are always of one library and
    ``array_namespace`` is a dispatch this saves on every same-library call.
    """
    if type(value) is type(like) or namespace_of(value) is namespace:
        return value
    return namespace.from_dlpack(value)


def _default_namespace(backend: Any):
    compat = _compat()
    if backend is None:
        numpy = _numpy()
        return compat.array_namespace(numpy.zeros(0))
    if isinstance(backend, str):
        backend = importlib.import_module(backend)
    probe = backend.zeros(0) if hasattr(backend, "zeros") else backend.asarray([0])
    return compat.array_namespace(probe)


def _backend_name(namespace: Any) -> str:
    """The stable, fully qualified module identity used in MeTTa aliases."""
    return str(getattr(namespace, "__name__", namespace))


def _describe(x: Any) -> str:
    compat = _compat()
    dtype = str(x.dtype)
    dtype = dtype[dtype.rfind(".") + 1 :]
    shape = "x".join(str(d) for d in x.shape) or "scalar"
    device = str(compat.device(x))
    grad = " grad" if getattr(x, "requires_grad", False) else ""
    return f"<{type(x).__name__} {shape} {dtype} {device}{grad}>"


def _array_type(value: Any) -> Expression:
    """Observe shape on each type query, including an array resized in place."""
    return _shaped_tensor(_expr(*value.shape))


def _register_protocols() -> None:
    """DLTensor typing and protocol printing, once per process."""
    if _PROTOCOLS_REGISTERED.is_set():
        return
    with _PROTOCOLS_LOCK:
        if _PROTOCOLS_REGISTERED.is_set():
            return
        _integrate.register_object_type(is_array, "DLTensor")
        _integrate.register_object_type(is_array, _array_type)
        _integrate.register_repr(is_array, _describe)
        _PROTOCOLS_REGISTERED.set()


def data_of(a: Any) -> Any:
    """Nested expression of numbers to nested lists; grounded values unwrap."""
    if isinstance(a, Expression):
        return [data_of(c) for c in a]
    if isinstance(a, Grounded):
        return _decode(a)
    if isinstance(a, Atom):
        msg = f"tensor data may not contain {a.metatype}: {a}"
        raise TypeError(msg)
    return a


def install(m, default: Any = None) -> list[str]:  # noqa: C901  -- install keeps the array backend registration table together so its branches share one state
    """Register the array operation set on the shared engine.

    default names the library the constructors build in: a module, a module
    name, or None for NumPy. Every other operation dispatches on its
    argument's own namespace, so arrays from any conforming library flow
    through the same MeTTa functions, and a mixed binary call converts the
    right operand into the left's library through from_dlpack.

    Every installed name has one or more arrow declarations. Constructors
    with optional or variadic dimensions have one arrow per accepted arity.

    broadcast-shape is the CLP(FD) relation over shape expressions. It can
    compute a result before any tensor exists, infer an unknown input
    dimension from a required result, or reject incompatible shapes:

        !(let True (broadcast-shape (4 1) (3) $shape) $shape)  ; (4 3)
        !(let True (broadcast-shape ($d 1) (1 3) (4 3)) $d)   ; 4
        !(broadcast-shape (2 3) (4 3) (4 3))                  ; no answer

    t-shape remains observation of an existing tensor. Use broadcast-shape
    when compatibility or inference must happen before materialisation.

    ``Shape`` carries those expressions through Python ``Annotated`` claims.
    User operation arrows retain the claim: argument dimensions unify and
    bind shared result dimensions. Live values report the same type expression.
    ``SHAPE_RULES`` names every installed head's behavior; preserving heads
    share their entire input shape with the result. Other transformations
    expose their actual shape when their result value exists.
    A declared ``(Annotated DLTensor (Shape ...))`` remains a valid DLTensor
    argument, elementwise binary operations derive their output shape with
    ``broadcast-shape``, and rank-two matmul unifies the two inner dimensions:

        (: image (Annotated DLTensor (Shape (4 1))))
        (: bias  (Annotated DLTensor (Shape (3))))
        !(get-type (t+ image bias))  ; (Annotated DLTensor (Shape (4 3)))

    m may be a context or a space. The operations are registered into the
    space either way, which is the object whose storage and introspection
    doors this needs; `install(m)` on a context used to raise
    `MeTTa has no 'is_function'` and leave every operation unregistered.
    """
    m = _integrate.space_of(m)
    _register_protocols()
    backend = _numpy() if default is None else default
    if isinstance(backend, str):
        backend = importlib.import_module(backend)
    xp_default = _default_namespace(backend)
    library = _backend_name(backend)
    registered: list[str] = []

    m.register_prolog(_BROADCAST_SHAPE_SOURCE)
    typing_rule_result = m.run(_SHAPED_TENSOR_RULE)
    if typing_rule_result != [[True]]:
        msg = f"could not install the shaped DLTensor typing rule: {typing_rule_result!r}"
        raise MettaError(msg)

    def add_type_equation(equation: Expression) -> None:
        if not any(_alpha_eq(equation, atom) for atom in m.atoms()):
            # Definitions must pass through the source runner so the engine
            # compiles them as reduction clauses. Space.add stores an ``=``
            # atom as data, which looks identical in ``atoms()`` but cannot
            # participate in ``get-type`` reduction.
            m.run(str(equation))

    add_type_equation(_tensor_shape_equation())

    def op(
        fn,
        *,
        name: str,
        effect: str,
        # policy-inventory-exempt: mechanism-internal; reason=encoded and raw are the registration transport's two wire-crossing modes, decoded once into the (op ...) kind; evidence=extensions/python/metta/ops.py:_operation_kind
        transport: Literal["encoded", "raw"] = "raw",
        **kw,
    ):
        if (
            m.is_function(name)
            and name not in _known_ops()
            and name not in _CONSTRUCTOR_NAMES
        ):
            msg = (
                f"refusing to register {name!r}: the engine already has a "
                f"function by that name and it is not an array operation"
            )
            raise MettaError(
                msg
            )
        rule = SHAPE_RULES[name.split("--", 1)[0]]
        if rule == "preserve":
            original = fn

            @wraps(original)
            def preserving(a, *args, **kwargs):
                # NumPy elementwise functions can return scalars for rank-zero arrays.
                result = original(a, *args, **kwargs)
                return result if is_array(result) else namespace_of(a).asarray(result)

            fn = preserving
            tensor = Annotated[DLTensor, _shape_metadata(V.shape)]
            parameter = next(iter(inspect.signature(fn).parameters))
            fn.__annotations__[parameter] = tensor
            fn.__annotations__["return"] = tensor
        elif rule == "broadcast":
            add_type_equation(_broadcast_type_equation(name))
        elif rule == "matmul":
            add_type_equation(_matmul_type_equation())
        m.op(fn, name=name, effect=effect, transport=transport, **kw)
        registered.append(name)
        return fn

    def constructor(
        fn,
        *,
        name: str,
        effect: str,
        arities: list[int] | None = None,
        # policy-inventory-exempt: mechanism-internal; reason=encoded and raw are the registration transport's two wire-crossing modes, decoded once into the (op ...) kind; evidence=extensions/python/metta/ops.py:_operation_kind
        transport: Literal["encoded", "raw"] = "raw",
        **kw,
    ):
        """A constructor registers per backend as name--library, and THIS
        space routes its bare name there through per-space equations, so
        the default is the space's, never the process's. Installing the
        space again with another default replaces its aliases.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        namespaced = f"{name}--{library}"
        declarations = [
            _expr(declaration.head, S[namespaced], *declaration.args[1:])
            if (
                isinstance(declaration, Expression)
                and declaration.args
                and declaration.args[0] == S[name]
            )
            else declaration
            for declaration in kw.pop("declarations", ())
        ]
        op(
            fn,
            name=namespaced,
            effect=effect,
            transport=transport,
            arities=arities,
            declarations=declarations,
            **kw,
        )
        key = (m.name, name)
        previous = _SPACE_CONSTRUCTORS.get(key)
        if previous is not None:
            old_library, old_arities = previous
            for arity in old_arities:
                m.remove(_alias_equation(name, old_library, arity))
        for arity in arities or [1]:
            m.add(_alias_equation(name, library, arity))
        _SPACE_CONSTRUCTORS[key] = (library, list(arities or [1]))
        operation = REGISTRY[namespaced]
        for declaration in operation.declarations:
            if (
                declaration.head == S[":"]
                and declaration.args[0] == S[namespaced]
                and isinstance(declaration.args[1], Expression)
                and declaration.args[1].head == S["->"]
            ):
                alias_type = _expr(S[":"], S[name], declaration.args[1])
                if alias_type not in m:
                    m.add(alias_type)
        registered.append(name)
        return fn

    def aligned(a, b):
        """Two operands in one library: the right converts into the left's,
        through DLPack when it is an array and by lifting when it is a bare
        number, since the standard's functions take arrays on both sides.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        xp = namespace_of(a)
        b = _into(xp, a, b) if is_array(b) else xp.asarray(b, dtype=a.dtype)
        return a, b, xp

    # ------------------------------------------------------------ constructors

    def make_tensor(data: Any) -> DLTensor:
        raw_data = data_of(data) if isinstance(data, Atom) else data
        if is_array(raw_data):
            return DLTensor(ground(raw_data))
        return DLTensor(ground(xp_default.asarray(raw_data, dtype=xp_default.float32)))

    constructor(
        make_tensor,
        name="tensor",
        effect="writesState",
        transport="encoded",
        declarations=[_expr(S.arguments, S.tensor, S.atoms)],
    )

    dims = [1, 2, 3, 4]

    def zeros(*shape: int) -> DLTensor:
        return xp_default.zeros(tuple(int(dimension) for dimension in shape))

    def ones(*shape: int) -> DLTensor:
        return xp_default.ones(tuple(int(dimension) for dimension in shape))

    def arange_tensor(n: float) -> DLTensor:
        return xp_default.arange(float(n))

    def identity(n: int) -> DLTensor:
        return xp_default.eye(int(n))

    constructor(zeros, name="zeros", effect="writesState", arities=dims)
    constructor(ones, name="ones", effect="writesState", arities=dims)
    constructor(_randn(xp_default), name="randn", effect="oracleIO", arities=dims)
    constructor(arange_tensor, name="arange-t", effect="writesState")
    constructor(identity, name="eye", effect="writesState")

    # ---------------------------------------------------------------- algebra

    def binop(fn, name: str):
        def call(a: DLTensor, b: Any) -> DLTensor:
            a2, b2, xp = aligned(a, b)
            return fn(xp, a2, b2)

        op(call, name=name, effect="writesState")

    def matmul(
        a: DLTensor,
        b: DLTensor,
    ) -> DLTensor:
        a2, b2, xp = aligned(a, b)
        return xp.matmul(a2, b2)

    op(matmul, name="matmul", effect="writesState")
    binop(lambda xp, a, b: xp.add(a, b), "t+")
    binop(lambda xp, a, b: xp.subtract(a, b), "t-")
    binop(lambda xp, a, b: xp.multiply(a, b), "t*")
    binop(lambda xp, a, b: xp.divide(a, b), "t/")

    def negative(a: DLTensor) -> DLTensor:
        return namespace_of(a).negative(a)

    def exponential(a: DLTensor) -> DLTensor:
        return namespace_of(a).exp(a)

    def logarithm(a: DLTensor) -> DLTensor:
        return namespace_of(a).log(a)

    op(negative, name="t-neg", effect="writesState")
    op(exponential, name="t-exp", effect="writesState")
    op(logarithm, name="t-log", effect="writesState")

    def power(a: DLTensor, p: Any) -> DLTensor:
        # Through aligned() like every other binary operation, so a mixed
        # pair (a torch base, a NumPy exponent) converts before the call.
        a2, p2, xp = aligned(a, p)
        return xp.pow(a2, p2)

    op(power, name="t-pow", effect="writesState")

    # ------------------------------------------------------------------ shape

    def reshape(a: DLTensor, *dimensions: int) -> DLTensor:
        return namespace_of(a).reshape(
            a,
            tuple(int(dimension) for dimension in dimensions),
        )

    def transpose(a: DLTensor, d0: int, d1: int) -> DLTensor:
        return _swap(namespace_of(a), a, int(d0), int(d1))

    def unsqueeze(a: DLTensor, dimension: int) -> DLTensor:
        return namespace_of(a).expand_dims(a, axis=int(dimension))

    def squeeze(a: DLTensor, dimension: int) -> DLTensor:
        return namespace_of(a).squeeze(a, axis=int(dimension))

    def tensor_index(a: DLTensor, index: int) -> Any:
        return cast(Any, a)[int(index)]

    op(reshape, name="reshape", effect="writesState", arities=[2, 3, 4, 5])
    op(transpose, name="t-transpose", effect="writesState")
    op(unsqueeze, name="unsqueeze", effect="writesState")
    op(squeeze, name="squeeze", effect="writesState")
    op(tensor_index, name="t-index", effect="writesState")

    # The tensor list is a VALUE these two decode member by member, so the
    # parameter is annotated by what it iterates rather than by the MeTTa atom
    # kind. `Expression` in a parameter position is the evaluation mask: it
    # hands the operand over AS WRITTEN, and `(cat ((tensor ((1 2)))) 0)` then
    # reaches the operation as two unrun `(tensor ...)` calls
    # [source: LeaTTa MettaHyperonFull/Core/Modifiers.lean:118-124].
    def cat_op(tensors: Iterable[Atom], dim: int = 0) -> DLTensor:
        parts = [_decode(c) for c in tensors]
        dimension = _decode(dim) if isinstance(dim, Atom) else dim
        return DLTensor(
            ground(namespace_of(parts[0]).concat(parts, axis=int(dimension)))
        )

    def stack_op(tensors: Iterable[Atom], dim: int = 0) -> DLTensor:
        parts = [_decode(c) for c in tensors]
        dimension = _decode(dim) if isinstance(dim, Atom) else dim
        return DLTensor(
            ground(namespace_of(parts[0]).stack(parts, axis=int(dimension)))
        )

    op(cat_op, name="cat", effect="writesState", transport="encoded")
    op(stack_op, name="stack", effect="writesState", transport="encoded")

    # ------------------------------------------------------------- reductions

    def tensor_sum(a: DLTensor) -> Any:
        return namespace_of(a).sum(a)

    def tensor_mean(a: DLTensor) -> Any:
        return namespace_of(a).mean(a)

    def tensor_max(a: DLTensor) -> Any:
        return namespace_of(a).max(a)

    def tensor_min(a: DLTensor) -> Any:
        return namespace_of(a).min(a)

    op(tensor_sum, name="t-sum", effect="writesState")
    op(tensor_mean, name="t-mean", effect="writesState")
    op(tensor_max, name="t-max", effect="writesState")
    op(tensor_min, name="t-min", effect="writesState")

    def argmax(a: DLTensor, dim: int = -1) -> Any:
        xp = namespace_of(a)
        out = xp.argmax(a, axis=int(dim))
        return int(out) if cast(Any, a).ndim <= 1 else out

    def tensor_norm(a: DLTensor) -> Any:
        return namespace_of(a).linalg.vector_norm(a)

    op(argmax, name="t-argmax", effect="writesState")
    op(tensor_norm, name="t-norm", effect="writesState")

    # ------------------------------------------------------------ activations

    def relu(a: DLTensor) -> DLTensor:
        xp = namespace_of(a)
        raw = cast(Any, a)
        return xp.where(raw > 0, raw, xp.zeros_like(raw))

    def sigmoid(a: DLTensor) -> DLTensor:
        xp = namespace_of(a)
        return 1.0 / (1.0 + xp.exp(-cast(Any, a)))

    def softmax(a: DLTensor, dim: int = -1) -> DLTensor:
        xp = namespace_of(a)
        shifted = xp.exp(a - xp.max(a, axis=int(dim), keepdims=True))
        return shifted / xp.sum(shifted, axis=int(dim), keepdims=True)

    def hyperbolic_tangent(a: DLTensor) -> DLTensor:
        return namespace_of(a).tanh(a)

    op(relu, name="relu", effect="writesState")
    op(sigmoid, name="sigmoid", effect="writesState")
    op(softmax, name="softmax", effect="writesState")
    op(hyperbolic_tangent, name="tanh", effect="writesState")

    # ------------------------------------------------------------------ exits

    # A reduction answers a zero-dimensional array in some libraries and a
    # scalar in others, so the readout accepts either shape honestly.
    def item(a: Any) -> float:
        return float(a)

    op(item, name="t-item", effect="readOnlyLookup")

    def tolist(a: DLTensor) -> Any:
        data: Any = _decode(a) if isinstance(a, Atom) else a
        listed = data.tolist() if hasattr(data, "tolist") else list(data)
        return _expr(*listed) if isinstance(listed, list) else listed

    op(tolist, name="t-tolist", effect="readOnlyLookup", transport="encoded")

    def shape(a: DLTensor) -> Expression:
        data: Any = _decode(a) if isinstance(a, Atom) else a
        return _expr(*[int(dimension) for dimension in data.shape])

    op(shape, name="t-shape", effect="readOnlyLookup", transport="encoded")

    def dtype(a: DLTensor) -> str:
        return str(cast(Any, a).dtype)

    def device(a: DLTensor) -> str:
        return str(_compat().device(a))

    op(dtype, name="t-dtype", effect="readOnlyLookup")
    op(device, name="t-device", effect="readOnlyLookup")

    def convert(a: DLTensor, lib: str) -> DLTensor:
        """(t-as $x numpy): the same values in another library, via DLPack."""
        target = importlib.import_module(str(lib))
        probe = target.zeros(0) if hasattr(target, "zeros") else target.asarray([0])
        return _compat().array_namespace(probe).from_dlpack(a)

    op(convert, name="t-as", effect="oracleIO")

    ARRAY_OPS[:] = registered
    return registered


def _randn(xp_default):
    module = _backend_name(xp_default)

    def randn(*shape: int) -> DLTensor:
        dims = tuple(int(d) for d in shape)
        if hasattr(xp_default, "randn"):
            return xp_default.randn(*dims)
        random = getattr(xp_default, "random", None)
        if random is not None and hasattr(random, "standard_normal"):
            return xp_default.asarray(
                random.standard_normal(dims), dtype=xp_default.float32
            )
        msg = f"{module} offers no normal sampler for randn"
        raise MettaError(msg)

    return randn


def _swap(xp, a, d0: int, d1: int):
    order = list(range(a.ndim))
    order[d0], order[d1] = order[d1], order[d0]
    return xp.permute_dims(a, tuple(order))


def _known_ops() -> set[str]:
    return set(REGISTRY)


class EmbeddingStore:
    """Vectors by key, searchable from MeTTa, in whichever library the
    vectors arrive from.

        store = metta.arrays.EmbeddingStore(m, name="emb")
        store.add(S.dog, numpy.array([1.0, 0.0]))
        m.run("!(collapse (emb-knn (tensor (1.0 0.0)) 1))")

    Cosine similarity uses the array API's own operations, and the matrix
    caches between writes. add() has map semantics: adding an existing key
    replaces its vector in its first-seen position. (name-knn $q $k) is
    nondeterministic retrieval, best first; (name-embed $key) answers the
    stored vector or nothing. Public operation names route through equations
    in this space to unique internal operations, so the same store name in a
    different space cannot retarget this store.

    m may be a context or a space, as ``install`` takes either.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self, m, name: str = "emb", mirror: bool = True, backend: str = "auto"  # noqa: FBT001, FBT002  -- the boolean is established API data and positional compatibility is part of the call shape
    ) -> None:
        if backend not in ("auto", "argsort", "faiss"):
            msg = f"backend is auto, argsort or faiss, not {backend!r}"
            raise MettaError(msg)
        if backend == "faiss":
            _faiss()
        m = _integrate.space_of(m)
        self._m = m
        self._name = name
        self._mirror = mirror
        self._backend = backend
        self._keys: list[Atom] = []
        self._vectors: list[Any] = []
        self._matrix = None
        self._index = None
        self._width: int | None = None

        def knn(query, k):
            yield from self._search(_decode(query), _decode(k))

        def embed(key):
            atom = key if isinstance(key, Atom) else S[str(key)]
            for stored, vector in zip(self._keys, self._vectors, strict=True):
                if stored == atom:
                    return ground(vector)
            return None

        serial = next(_STORE_SERIAL)
        internal_knn = f"{name}--store-{serial}-knn"
        internal_embed = f"{name}--store-{serial}-embed"
        m.op(
            knn,
            name=internal_knn,
            effect="nondeterministicReadOnly",
            declarations=[_expr(S.arguments, S[internal_knn], S.atoms)],
        )
        m.op(
            embed,
            name=internal_embed,
            effect="readOnlyLookup",
            declarations=[_expr(S.arguments, S[internal_embed], S.atoms)],
        )

        key = (m.name, name)
        previous = _SPACE_STORES.get(key)
        if previous is not None:
            m.remove(_route_equation(f"{name}-knn", previous[0], 2))
            m.remove(_route_equation(f"{name}-embed", previous[1], 1))
        m.add(
            _route_equation(f"{name}-knn", internal_knn, 2),
            _route_equation(f"{name}-embed", internal_embed, 1),
        )
        _SPACE_STORES[key] = (internal_knn, internal_embed)

    def add(self, key: Any, vector: Any) -> None:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        atom = key if isinstance(key, Atom) else S[str(key)]
        vector = self._checked_vector(vector, copy=True)
        try:
            index = self._keys.index(atom)
        except ValueError:
            self._keys.append(atom)
            self._vectors.append(vector)
        else:
            old = self._vectors[index]
            if self._mirror:
                self._m.remove(Expression([S.embedding, atom, ground(old)]))
            self._vectors[index] = vector
        self._matrix = None
        self._index = None
        if self._mirror:
            self._m.add(Expression([S.embedding, atom, ground(vector)]))

    def _checked_vector(self, vector: Any, *, copy: bool = False) -> Any:
        if not is_array(vector):
            numpy = _numpy()
            vector = numpy.asarray(vector, dtype=numpy.float32)
        if vector.ndim != 1:
            msg = f"embedding vectors must be one-dimensional, got shape {tuple(vector.shape)}"
            raise ValueError(
                msg
            )
        width = int(vector.shape[0])
        if self._width is not None and width != self._width:
            msg = f"embedding vector width must be {self._width}, got {width}"
            raise ValueError(
                msg
            )
        xp = namespace_of(vector)
        if not bool(xp.all(xp.isfinite(vector))):
            msg = "embedding vectors must contain only finite values"
            raise ValueError(msg)
        as_float = xp.astype(vector, xp.float32)
        norm = float(xp.linalg.vector_norm(as_float))
        if norm == 0.0:
            msg = "embedding vectors must have a nonzero norm"
            raise ValueError(msg)
        if self._width is None:
            self._width = width
        return xp.asarray(vector, copy=True) if copy else vector

    def __len__(self) -> int:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return len(self._keys)

    def keys(self) -> list[Atom]:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        return self._keys.copy()

    def vector_for(self, key: Any) -> Any:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        atom = key if isinstance(key, Atom) else S[str(key)]
        for stored, vector in zip(self._keys, self._vectors, strict=True):
            if stored == atom:
                return vector
        msg = f"no embedding stored for {atom}"
        raise KeyError(msg)

    def _normalized_query(self, query: Any):
        xp = namespace_of(self._vectors[0])
        if self._matrix is None:
            rows = [_into(xp, self._vectors[0], v) for v in self._vectors]
            stacked = xp.stack([xp.astype(r, xp.float32) for r in rows])
            norms = xp.sqrt(xp.sum(stacked * stacked, axis=-1, keepdims=True))
            self._matrix = stacked / norms
        q = _into(xp, self._vectors[0], self._checked_vector(query))
        q = xp.reshape(xp.astype(q, xp.float32), (-1,))
        return xp, q / xp.sqrt(xp.sum(q * q))

    def _use_faiss(self) -> bool:
        if self._backend == "argsort":
            return False
        if self._backend == "faiss":
            return True
        return optional_module("faiss") is not None

    def ranked(self, query: Any, k: int):
        """(key atom, cosine) pairs best first: the raw retrieval every
        surface (knn, the matcher) formats its own way. With faiss present
        (or asked for), an exact IndexFlatIP over the normalized matrix
        answers, byte-agreeing with the array path by a differential test.
        NumPy-like namespaces use argpartition for the candidate set;
        namespaces exposing only the Array API use argsort.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if isinstance(k, bool):
            msg = f"k must be a positive integer, got {k!r}"
            raise TypeError(msg)
        try:
            k = operator.index(k)
        except TypeError:
            msg = f"k must be a positive integer, got {k!r}"
            raise TypeError(msg) from None
        if k <= 0:
            msg = f"k must be a positive integer, got {k}"
            raise ValueError(msg)
        if not self._keys:
            return
        xp, q = self._normalized_query(self._resolve(query))
        count = min(k, len(self._keys))
        if self._use_faiss():
            faiss = _faiss()
            numpy = _numpy()
            if self._index is None:
                matrix = numpy.ascontiguousarray(
                    numpy.asarray(self._matrix, dtype=numpy.float32)
                )
                built_index = faiss.IndexFlatIP(matrix.shape[1])
                built_index.add(matrix)
                self._index = built_index
            index = self._index
            if index is None:
                msg = "FAISS index construction produced no index"
                raise RuntimeError(msg)
            probe = numpy.ascontiguousarray(
                numpy.asarray(q, dtype=numpy.float32).reshape(1, -1)
            )
            scores, indexes = index.search(probe, count)
            for score, index in zip(scores[0], indexes[0], strict=True):
                yield self._keys[int(index)], round(float(score), 6)
            return
        scores = self._matrix @ q
        for index in _top_indices(xp, scores, count):
            yield self._keys[index], round(float(scores[index]), 6)

    def _search(self, query: Any, k: int):
        for key, score in self.ranked(query, k):
            yield _expr(key, score)

    def _resolve(self, query: Any) -> Any:
        """A query as a vector: an array or sequence stands as itself, a
        stored key answers its vector.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if is_array(query) or isinstance(query, (list, tuple)):
            return query
        return self.vector_for(query)
