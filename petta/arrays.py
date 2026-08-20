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
  - the fixed public constructor vocabulary is marked immutable to type
    checkers [tested test_policy_constants_are_final]
Guarded by:
  - _PROTOCOLS_LOCK serializes one-time protocol registration
    [tested test_array_protocol_registration_is_idempotent]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import importlib
import itertools
import operator
import threading
from collections.abc import Iterator
from typing import Any, Final

from . import integrate as _integrate
from ._ops import REGISTRY
from ._optional import optional_module, require_module
from .atoms import Atom, Expr, Gnd, S, Var, decode, expr, val
from .errors import PettaError

__all__ = [
    "ARRAY_OPS",
    "EmbeddingStore",
    "data_of",
    "install",
    "is_array",
    "namespace_of",
]

ARRAY_OPS: list[str] = []
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
            raise RuntimeError("an argpartition namespace must also provide nonzero")
        better = [int(index) for index in nonzero(scores > threshold)[0]]
        needed = count - len(better)
        tied = [int(index) for index in nonzero(scores == threshold)[0][:needed]]
        candidates = [*better, *tied]
    else:
        order = xp.argsort(scores)
        candidates = [int(order[-(offset + 1)]) for offset in range(count)]
    return sorted(candidates, key=lambda index: (-float(scores[index]), index))


def _alias_equation(name: str, library: str, arity: int) -> Expr:
    variables = [Var(f"a{i}") for i in range(1, arity + 1)]
    return Expr(
        [
            S["="],
            Expr([S[name], *variables]),
            Expr([S[f"{name}--{library}"], *variables]),
        ]
    )


def _route_equation(alias: str, target: str, arity: int) -> Expr:
    variables = [Var(f"a{i}") for i in range(1, arity + 1)]
    return Expr([S["="], Expr([S[alias], *variables]), Expr([S[target], *variables])])


def is_array(x: Any) -> bool:
    """Whether a value speaks DLPack, the exchange protocol array libraries share."""
    return hasattr(x, "__dlpack__")


def _compat():
    return require_module(
        "array_api_compat",
        "petta.arrays needs array-api-compat, the standard's compatibility "
        "layer over NumPy, PyTorch, CuPy, JAX and Dask; install petta[arrays]",
    )


def _numpy():
    return require_module(
        "numpy",
        "petta.arrays needs NumPy for default arrays and embedding storage; install petta[arrays]",
    )


def _faiss():
    return require_module(
        "faiss",
        "the faiss embedding backend needs faiss-cpu; install petta[arrays]",
    )


def namespace_of(x: Any):
    """The array API namespace an array belongs to: its own library, wrapped."""
    return _compat().array_namespace(x)


def _default_namespace(backend: Any):
    compat = _compat()
    if backend is None:
        numpy = _numpy()
        return compat.array_namespace(numpy.zeros(0))
    if isinstance(backend, str):
        backend = importlib.import_module(backend)
    probe = backend.zeros(0) if hasattr(backend, "zeros") else backend.asarray([0])
    return compat.array_namespace(probe)


def _describe(x: Any) -> str:
    compat = _compat()
    dtype = str(x.dtype)
    dtype = dtype[dtype.rfind(".") + 1 :]
    shape = "x".join(str(d) for d in x.shape) or "scalar"
    device = str(compat.device(x))
    grad = " grad" if getattr(x, "requires_grad", False) else ""
    return f"<{type(x).__name__} {shape} {dtype} {device}{grad}>"


def _register_protocols() -> None:
    """DLTensor typing and protocol printing, once per process."""
    if _PROTOCOLS_REGISTERED.is_set():
        return
    with _PROTOCOLS_LOCK:
        if _PROTOCOLS_REGISTERED.is_set():
            return
        _integrate.register_object_type(is_array, "DLTensor")
        _integrate.register_repr(is_array, _describe)
        _PROTOCOLS_REGISTERED.set()


def data_of(a: Any) -> Any:
    """Nested expression of numbers to nested lists; grounded values unwrap."""
    if isinstance(a, Expr):
        return [data_of(c) for c in a]
    if isinstance(a, Gnd):
        return decode(a)
    if isinstance(a, Atom):
        raise TypeError(f"tensor data may not contain {a.metatype}: {a}")
    return a


def install(m, default: Any = None) -> list[str]:
    """Register the array operation set on the shared engine.

    default names the library the constructors build in: a module, a module
    name, or None for NumPy. Every other operation dispatches on its
    argument's own namespace, so arrays from any conforming library flow
    through the same MeTTa functions, and a mixed binary call converts the
    right operand into the left's library through from_dlpack.
    """
    _register_protocols()
    xp_default = _default_namespace(default)
    library = getattr(xp_default, "__name__", str(xp_default)).rsplit(".", 1)[-1]
    registered: list[str] = []

    def op(fn, *, name: str, raw: bool = True, types: list[str] | None = None, **kw):
        if (
            m.is_function(name)
            and name not in _known_ops()
            and name not in _CONSTRUCTOR_NAMES
        ):
            raise PettaError(
                f"refusing to register {name!r}: the engine already has a "
                f"function by that name and it is not an array operation"
            )
        m.register_op(fn, name=name, raw=raw, typed=False, **kw)
        if types:
            m.add(expr(S[":"], S[name], Expr([S["->"], *(S[t] for t in types)])))
        registered.append(name)
        return fn

    def constructor(
        fn,
        *,
        name: str,
        arities: list[int] | None = None,
        raw: bool = True,
        types: list[str] | None = None,
        **kw,
    ):
        """A constructor registers per backend as name--library, and THIS
        space routes its bare name there through per-space equations, so
        the default is the space's, never the process's. Installing the
        space again with another default replaces its aliases.
        """
        namespaced = f"{name}--{library}"
        op(fn, name=namespaced, raw=raw, arities=arities, **kw)
        key = (m.space_name, name)
        previous = _SPACE_CONSTRUCTORS.get(key)
        if previous is not None:
            old_library, old_arities = previous
            for arity in old_arities:
                m.remove(_alias_equation(name, old_library, arity))
        for arity in arities or [1]:
            m.add(_alias_equation(name, library, arity))
        _SPACE_CONSTRUCTORS[key] = (library, list(arities or [1]))
        if types and previous is None:
            m.add(expr(S[":"], S[name], Expr([S["->"], *(S[t] for t in types)])))
        registered.append(name)
        return fn

    def aligned(a, b):
        """Two operands in one library: the right converts into the left's,
        through DLPack when it is an array and by lifting when it is a bare
        number, since the standard's functions take arrays on both sides.
        """
        xp = namespace_of(a)
        if is_array(b):
            if type(b) is not type(a):
                b = xp.from_dlpack(b)
        else:
            b = xp.asarray(b, dtype=a.dtype)
        return a, b, xp

    # ------------------------------------------------------------ constructors

    def make_tensor(data) -> Any:
        raw_data = data_of(data) if isinstance(data, Atom) else data
        if is_array(raw_data):
            return val(raw_data)
        return val(xp_default.asarray(raw_data, dtype=xp_default.float32))

    constructor(
        make_tensor,
        name="tensor",
        raw=False,
        pass_atoms=True,
        types=["%Undefined%", "DLTensor"],
    )

    dims = [1, 2, 3, 4]
    constructor(
        lambda *s: xp_default.zeros(tuple(int(d) for d in s)),
        name="zeros",
        arities=dims,
    )
    constructor(
        lambda *s: xp_default.ones(tuple(int(d) for d in s)), name="ones", arities=dims
    )
    constructor(_randn(xp_default), name="randn", arities=dims)
    constructor(lambda n: xp_default.arange(float(n)), name="arange-t")
    constructor(lambda n: xp_default.eye(int(n)), name="eye")

    # ---------------------------------------------------------------- algebra

    def binop(fn, name, second="%Undefined%"):
        def call(a, b):
            a2, b2, xp = aligned(a, b)
            return fn(xp, a2, b2)

        # The second operand's declared type states what aligned() accepts:
        # elementwise operations lift a bare number, so their declaration
        # must not claim DLTensor for it; matmul genuinely needs two arrays.
        op(call, name=name, types=["DLTensor", second, "DLTensor"])

    binop(lambda xp, a, b: xp.matmul(a, b), "matmul", second="DLTensor")
    binop(lambda xp, a, b: xp.add(a, b), "t+")
    binop(lambda xp, a, b: xp.subtract(a, b), "t-")
    binop(lambda xp, a, b: xp.multiply(a, b), "t*")
    binop(lambda xp, a, b: xp.divide(a, b), "t/")
    op(lambda a: namespace_of(a).negative(a), name="t-neg")
    op(lambda a: namespace_of(a).exp(a), name="t-exp")
    op(lambda a: namespace_of(a).log(a), name="t-log")

    def power(a, p):
        # Through aligned() like every other binary operation, so a mixed
        # pair (a torch base, a NumPy exponent) converts before the call.
        a2, p2, xp = aligned(a, p)
        return xp.pow(a2, p2)

    op(power, name="t-pow")

    # ------------------------------------------------------------------ shape

    op(
        lambda a, *ds: namespace_of(a).reshape(a, tuple(int(d) for d in ds)),
        name="reshape",
        arities=[2, 3, 4, 5],
    )
    op(
        lambda a, d0, d1: _swap(namespace_of(a), a, int(d0), int(d1)),
        name="t-transpose",
    )
    op(lambda a, d: namespace_of(a).expand_dims(a, axis=int(d)), name="unsqueeze")
    op(lambda a, d: namespace_of(a).squeeze(a, axis=int(d)), name="squeeze")
    op(lambda a, i: a[int(i)], name="t-index")

    def cat_op(tensors, dim=0):
        parts = [decode(c) for c in tensors]
        return val(namespace_of(parts[0]).concat(parts, axis=int(decode(dim))))

    def stack_op(tensors, dim=0):
        parts = [decode(c) for c in tensors]
        return val(namespace_of(parts[0]).stack(parts, axis=int(decode(dim))))

    op(cat_op, name="cat", raw=False, pass_atoms=True)
    op(stack_op, name="stack", raw=False, pass_atoms=True)

    # ------------------------------------------------------------- reductions

    op(
        lambda a: namespace_of(a).sum(a),
        name="t-sum",
        types=["DLTensor", "%Undefined%"],
    )
    op(lambda a: namespace_of(a).mean(a), name="t-mean")
    op(lambda a: namespace_of(a).max(a), name="t-max")
    op(lambda a: namespace_of(a).min(a), name="t-min")

    def argmax(a, dim=-1):
        xp = namespace_of(a)
        out = xp.argmax(a, axis=int(dim))
        return int(out) if a.ndim <= 1 else out

    op(argmax, name="t-argmax")
    op(lambda a: namespace_of(a).linalg.vector_norm(a), name="t-norm")

    # ------------------------------------------------------------ activations

    def relu(a):
        xp = namespace_of(a)
        return xp.where(a > 0, a, xp.zeros_like(a))

    def sigmoid(a):
        xp = namespace_of(a)
        return 1.0 / (1.0 + xp.exp(-a))

    def softmax(a, dim=-1):
        xp = namespace_of(a)
        shifted = xp.exp(a - xp.max(a, axis=int(dim), keepdims=True))
        return shifted / xp.sum(shifted, axis=int(dim), keepdims=True)

    op(relu, name="relu", types=["DLTensor", "DLTensor"])
    op(sigmoid, name="sigmoid")
    op(softmax, name="softmax", types=["DLTensor", "DLTensor"])
    op(lambda a: namespace_of(a).tanh(a), name="tanh")

    # ------------------------------------------------------------------ exits

    # The input stays undeclared on purpose: a reduction's answer is a 0-d
    # array in some libraries and a scalar in others (NumPy answers a
    # float32, which speaks no DLPack), and both read out through float().
    op(float, name="t-item", types=["%Undefined%", "Number"])

    def tolist(a) -> Any:
        data = decode(a)
        listed = data.tolist() if hasattr(data, "tolist") else list(data)
        return expr(*listed) if isinstance(listed, list) else listed

    op(tolist, name="t-tolist", raw=False, types=["DLTensor", "Expression"])

    def shape(a) -> Any:
        return expr(*[int(d) for d in decode(a).shape])

    op(shape, name="t-shape", raw=False, types=["DLTensor", "Expression"])

    op(lambda a: str(a.dtype), name="t-dtype")
    op(lambda a: str(_compat().device(a)), name="t-device")

    def convert(a, lib):
        """(t-as $x numpy): the same values in another library, via DLPack."""
        target = importlib.import_module(str(lib))
        probe = target.zeros(0) if hasattr(target, "zeros") else target.asarray([0])
        return _compat().array_namespace(probe).from_dlpack(a)

    op(convert, name="t-as")

    ARRAY_OPS[:] = registered
    return registered


def _randn(xp_default):
    module = xp_default.__name__.rsplit(".", 1)[-1]

    def randn(*shape):
        dims = tuple(int(d) for d in shape)
        if hasattr(xp_default, "randn"):
            return xp_default.randn(*dims)
        native = importlib.import_module(module)
        if hasattr(native, "random"):
            return xp_default.asarray(
                native.random.standard_normal(dims), dtype=xp_default.float32
            )
        raise PettaError(f"{module} offers no normal sampler for randn")

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

        store = petta.arrays.EmbeddingStore(m, name="emb")
        store.add(S.dog, numpy.array([1.0, 0.0]))
        m.run("!(collapse (emb-knn (tensor (1.0 0.0)) 1))")

    Cosine similarity uses the array API's own operations, and the matrix
    caches between writes. add() has map semantics: adding an existing key
    replaces its vector in its first-seen position. (name-knn $q $k) is
    nondeterministic retrieval, best first; (name-embed $key) answers the
    stored vector or nothing. Public operation names route through equations
    in this space to unique internal operations, so the same store name in a
    different space cannot retarget this store.
    """

    def __init__(
        self, m, name: str = "emb", mirror: bool = True, backend: str = "auto"
    ) -> None:
        if backend not in ("auto", "argsort", "faiss"):
            raise PettaError(f"backend is auto, argsort or faiss, not {backend!r}")
        if backend == "faiss":
            _faiss()
        self._m = m
        self._name = name
        self._mirror = mirror
        self._backend = backend
        self._keys: list[Atom] = []
        self._vectors: list[Any] = []
        self._matrix = None
        self._index = None
        self._width: int | None = None

        def knn(query, k) -> Iterator[Any]:
            yield from self._search(decode(query), decode(k))

        def embed(key):
            atom = key if isinstance(key, Atom) else S[str(key)]
            for stored, vector in zip(self._keys, self._vectors, strict=True):
                if stored == atom:
                    return val(vector)
            return None

        serial = next(_STORE_SERIAL)
        internal_knn = f"{name}--store-{serial}-knn"
        internal_embed = f"{name}--store-{serial}-embed"
        m.register_op(knn, name=internal_knn, raw=False, typed=False, pass_atoms=True)
        m.register_op(
            embed, name=internal_embed, raw=False, typed=False, pass_atoms=True
        )

        key = (m.space_name, name)
        previous = _SPACE_STORES.get(key)
        if previous is not None:
            m.remove(_route_equation(f"{name}-knn", previous[0], 2))
            m.remove(_route_equation(f"{name}-embed", previous[1], 1))
        m.add(
            _route_equation(f"{name}-knn", internal_knn, 2),
            _route_equation(f"{name}-embed", internal_embed, 1),
        )
        _SPACE_STORES[key] = (internal_knn, internal_embed)

    def add(self, key: Any, vector: Any) -> None:
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
                self._m.remove(Expr([S.embedding, atom, val(old)]))
            self._vectors[index] = vector
        self._matrix = None
        self._index = None
        if self._mirror:
            self._m.add(Expr([S.embedding, atom, val(vector)]))

    def _checked_vector(self, vector: Any, *, copy: bool = False) -> Any:
        if not is_array(vector):
            numpy = _numpy()
            vector = numpy.asarray(vector, dtype=numpy.float32)
        if vector.ndim != 1:
            raise ValueError(
                f"embedding vectors must be one-dimensional, got shape {tuple(vector.shape)}"
            )
        width = int(vector.shape[0])
        if self._width is not None and width != self._width:
            raise ValueError(
                f"embedding vector width must be {self._width}, got {width}"
            )
        xp = namespace_of(vector)
        if not bool(xp.all(xp.isfinite(vector))):
            raise ValueError("embedding vectors must contain only finite values")
        as_float = xp.astype(vector, xp.float32)
        norm = float(xp.linalg.vector_norm(as_float))
        if norm == 0.0:
            raise ValueError("embedding vectors must have a nonzero norm")
        if self._width is None:
            self._width = width
        return xp.asarray(vector, copy=True) if copy else vector

    def __len__(self) -> int:
        return len(self._keys)

    def keys(self) -> list[Atom]:
        return self._keys.copy()

    def vector_for(self, key: Any) -> Any:
        atom = key if isinstance(key, Atom) else S[str(key)]
        for stored, vector in zip(self._keys, self._vectors, strict=True):
            if stored == atom:
                return vector
        raise KeyError(f"no embedding stored for {atom}")

    def _normalized_query(self, query: Any):
        xp = namespace_of(self._vectors[0])
        if self._matrix is None:
            rows = [
                xp.from_dlpack(v) if type(v) is not type(self._vectors[0]) else v
                for v in self._vectors
            ]
            stacked = xp.stack([xp.astype(r, xp.float32) for r in rows])
            norms = xp.sqrt(xp.sum(stacked * stacked, axis=-1, keepdims=True))
            self._matrix = stacked / norms
        q = self._checked_vector(query)
        if type(q) is not type(self._vectors[0]):
            q = xp.from_dlpack(q)
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
        """
        if isinstance(k, bool):
            raise TypeError(f"k must be a positive integer, got {k!r}")
        try:
            k = operator.index(k)
        except TypeError:
            raise TypeError(f"k must be a positive integer, got {k!r}") from None
        if k <= 0:
            raise ValueError(f"k must be a positive integer, got {k}")
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
                raise RuntimeError("FAISS index construction produced no index")
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
            yield expr(key, score)

    def _resolve(self, query: Any) -> Any:
        """A query as a vector: an array or sequence stands as itself, a
        stored key answers its vector.
        """
        if is_array(query) or isinstance(query, (list, tuple)):
            return query
        return self.vector_for(query)
