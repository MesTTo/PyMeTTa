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
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from typing import Any, Iterator

from .atoms import Atom, Expr, Gnd, S, Sym, decode, expr, val
from .errors import PettaError
from . import integrate as _integrate

__all__ = [
    "install",
    "is_array",
    "namespace_of",
    "EmbeddingStore",
    "ARRAY_OPS",
    "data_of",
]

ARRAY_OPS: list[str] = []
_PROTOCOLS_REGISTERED = False


def is_array(x: Any) -> bool:
    """Whether a value speaks DLPack, the exchange protocol array libraries share."""
    return hasattr(x, "__dlpack__")


def _compat():
    try:
        import array_api_compat
    except ImportError as exc:
        raise PettaError(
            "petta.arrays needs array-api-compat, the standard's "
            "compatibility layer over NumPy, PyTorch, CuPy, JAX and Dask. "
            "Install it with: pip install array-api-compat"
        ) from exc
    return array_api_compat


def namespace_of(x: Any):
    """The array API namespace an array belongs to: its own library, wrapped."""
    return _compat().array_namespace(x)


def _default_namespace(backend: Any):
    compat = _compat()
    if backend is None:
        import numpy

        return compat.array_namespace(numpy.zeros(0))
    if isinstance(backend, str):
        import importlib

        backend = importlib.import_module(backend)
    probe = backend.zeros(0) if hasattr(backend, "zeros") else backend.asarray([0])
    return compat.array_namespace(probe)


def _describe(x: Any) -> str:
    compat = _compat()
    dtype = str(x.dtype)
    dtype = dtype[dtype.rfind(".") + 1 :]
    shape = "x".join(str(d) for d in x.shape) or "scalar"
    try:
        device = str(compat.device(x))
    except Exception:
        device = "?"
    grad = " grad" if getattr(x, "requires_grad", False) else ""
    return f"<{type(x).__name__} {shape} {dtype} {device}{grad}>"


def _register_protocols() -> None:
    """DLTensor typing and protocol printing, once per process."""
    global _PROTOCOLS_REGISTERED
    if _PROTOCOLS_REGISTERED:
        return
    _integrate.register_object_type(is_array, "DLTensor")
    _integrate.register_repr(is_array, _describe)
    _PROTOCOLS_REGISTERED = True


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
    registered: list[str] = []

    def op(fn, *, name: str, raw: bool = True, types: list[str] | None = None, **kw):
        if m.is_function(name) and name not in _known_ops():
            raise PettaError(
                f"refusing to register {name!r}: the engine already has a "
                f"function by that name and it is not an array operation"
            )
        m.op(fn, name=name, raw=raw, typed=False, **kw)
        if types:
            m.add(expr(S[":"], S[name], Expr([S["->"], *(S[t] for t in types)])))
        registered.append(name)
        return fn

    def aligned(a, b):
        """Two operands in one library: convert the right into the left's."""
        if is_array(b):
            xp = namespace_of(a)
            if type(b) is not type(a):
                b = xp.from_dlpack(b)
            return a, b, xp
        return a, b, namespace_of(a)

    # ------------------------------------------------------------ constructors

    def make_tensor(data) -> Any:
        raw_data = data_of(data) if isinstance(data, Atom) else data
        if is_array(raw_data):
            return val(raw_data)
        return val(xp_default.asarray(raw_data, dtype=xp_default.float32))

    op(make_tensor, name="tensor", raw=False, pass_atoms=True,
       types=["%Undefined%", "DLTensor"])

    dims = [1, 2, 3, 4]
    op(lambda *s: xp_default.zeros(tuple(int(d) for d in s)), name="zeros", arities=dims)
    op(lambda *s: xp_default.ones(tuple(int(d) for d in s)), name="ones", arities=dims)
    op(_randn(xp_default), name="randn", arities=dims)
    op(lambda n: xp_default.arange(float(n)), name="arange-t")
    op(lambda n: xp_default.eye(int(n)), name="eye")

    # ---------------------------------------------------------------- algebra

    def binop(fn, name, typed=True):
        def call(a, b):
            a2, b2, xp = aligned(a, b)
            return fn(xp, a2, b2)

        op(call, name=name,
           types=["DLTensor", "DLTensor", "DLTensor"] if typed else None)

    binop(lambda xp, a, b: xp.matmul(a, b), "matmul")
    binop(lambda xp, a, b: xp.add(a, b), "t+")
    binop(lambda xp, a, b: xp.subtract(a, b), "t-")
    binop(lambda xp, a, b: xp.multiply(a, b), "t*")
    binop(lambda xp, a, b: xp.divide(a, b), "t/")
    op(lambda a: namespace_of(a).negative(a), name="t-neg")
    op(lambda a: namespace_of(a).exp(a), name="t-exp")
    op(lambda a: namespace_of(a).log(a), name="t-log")

    def power(a, p):
        xp = namespace_of(a)
        return xp.pow(a, xp.asarray(p, dtype=a.dtype)) if not is_array(p) else xp.pow(a, p)

    op(power, name="t-pow")

    # ------------------------------------------------------------------ shape

    op(lambda a, *ds: namespace_of(a).reshape(a, tuple(int(d) for d in ds)),
       name="reshape", arities=[2, 3, 4, 5])
    op(lambda a, d0, d1: _swap(namespace_of(a), a, int(d0), int(d1)), name="t-transpose")
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

    op(lambda a: namespace_of(a).sum(a), name="t-sum",
       types=["DLTensor", "%Undefined%"])
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
    op(lambda a: float(a), name="t-item", types=["%Undefined%", "Number"])

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
        import importlib

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
        import importlib

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
    from ._ops import REGISTRY

    return set(REGISTRY)


class EmbeddingStore:
    """Vectors by key, searchable from MeTTa, in whichever library the
    vectors arrive from.

        store = petta.arrays.EmbeddingStore(m, name="emb")
        store.add(S.dog, numpy.array([1.0, 0.0]))
        m.run("!(collapse (emb-knn (tensor (1.0 0.0)) 1))")

    Cosine similarity over the array API's own operations; the matrix caches
    between writes. (name-knn $q $k) is nondeterministic retrieval, best
    first; (name-embed $key) answers the stored vector or nothing.
    """

    def __init__(self, m, name: str = "emb", mirror: bool = True) -> None:
        self._m = m
        self._name = name
        self._mirror = mirror
        self._keys: list[Atom] = []
        self._vectors: list[Any] = []
        self._matrix = None

        def knn(query, k) -> Iterator[Any]:
            yield from self._search(decode(query), int(decode(k)))

        def embed(key):
            atom = key if isinstance(key, Atom) else S[str(key)]
            for stored, vector in zip(self._keys, self._vectors):
                if stored == atom:
                    return val(vector)
            return None

        m.op(knn, name=f"{name}-knn", raw=False, typed=False, pass_atoms=True)
        m.op(embed, name=f"{name}-embed", raw=False, typed=False, pass_atoms=True)

    def add(self, key: Any, vector: Any) -> None:
        atom = key if isinstance(key, Atom) else S[str(key)]
        if not is_array(vector):
            import numpy

            vector = numpy.asarray(vector, dtype=numpy.float32)
        self._keys.append(atom)
        self._vectors.append(vector)
        self._matrix = None
        if self._mirror:
            self._m.add(Expr([S.embedding, atom, val(vector)]))

    def __len__(self) -> int:
        return len(self._keys)

    def keys(self) -> list[Atom]:
        return list(self._keys)

    def vector_for(self, key: Any) -> Any:
        atom = key if isinstance(key, Atom) else S[str(key)]
        for stored, vector in zip(self._keys, self._vectors):
            if stored == atom:
                return vector
        raise KeyError(f"no embedding stored for {atom}")

    def _search(self, query: Any, k: int):
        if not self._keys:
            return
        xp = namespace_of(self._vectors[0])
        if self._matrix is None:
            rows = [
                xp.from_dlpack(v) if type(v) is not type(self._vectors[0]) else v
                for v in self._vectors
            ]
            stacked = xp.stack([xp.astype(r, xp.float32) for r in rows])
            norms = xp.sqrt(xp.sum(stacked * stacked, axis=-1, keepdims=True))
            self._matrix = stacked / norms
        q = query if is_array(query) else xp.asarray(query, dtype=xp.float32)
        if type(q) is not type(self._vectors[0]):
            q = xp.from_dlpack(q)
        q = xp.reshape(xp.astype(q, xp.float32), (-1,))
        q = q / xp.sqrt(xp.sum(q * q))
        scores = self._matrix @ q
        order = xp.argsort(scores)
        count = min(k, len(self._keys))
        for i in range(count):
            index = int(order[-(i + 1)])
            yield expr(self._keys[index], round(float(scores[index]), 6))
