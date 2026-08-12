"""Purpose: similarity as a match modality. An EmbeddingStore keeps vectors
for keys, mirrors them into the space as (embedding key <tensor>) facts, and
registers a nondeterministic knn operation: (<name>-knn $query $k) yields
(key score) pairs best-first, so a MeTTa program matches on meaning the way
it matches on structure.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: a FAISS-backed index behind the same operations once
    stores outgrow torch.topk; PeTTa's own faiss_ffi spaces already cover the
    engine-side variant when built.
"""

from __future__ import annotations

from typing import Any

from petta import Atom, S, Sym, decode, expr, val

from ._torch import torch

__all__ = ["EmbeddingStore"]


class EmbeddingStore:
    """Vectors by key, searchable from MeTTa.

        store = pettorch.EmbeddingStore(m)
        store.add(S.dog, dog_vector)
        store.add(S.cat, cat_vector)
        m.run("!(collapse (emb-knn (tensor (...)) 2))")
        # ((dog 0.98) (cat 0.83))

    Cosine similarity over torch.topk; the matrix is rebuilt on write and
    cached between writes, which suits stores up to the tens of thousands of
    rows a symbolic program actually holds.
    """

    def __init__(self, m, name: str = "emb", mirror: bool = True) -> None:
        self._t = torch()
        self._m = m
        self._name = name
        self._mirror = mirror
        self._keys: list[Atom] = []
        self._vectors: list[Any] = []
        self._matrix = None

        def knn(query, k):
            # Encoded, not raw: the yielded pairs carry the stored key atom,
            # so a symbol stays a symbol on the way out.
            yield from self._search(decode(query), int(decode(k)))

        def embed(key):
            atom = key if isinstance(key, Atom) else S[str(key)]
            for stored, vector in zip(self._keys, self._vectors):
                if stored == atom:
                    return val(vector)
            return None  # semidet: an absent key answers nothing

        m.op(knn, name=f"{name}-knn", raw=False, typed=False, pass_atoms=True)
        m.op(embed, name=f"{name}-embed", raw=False, typed=False, pass_atoms=True)

    def add(self, key: Any, vector: Any) -> None:
        """Store one vector; the key is a symbol or any atom."""
        atom = key if isinstance(key, Atom) else S[str(key)]
        tensor = vector if isinstance(vector, self._t.Tensor) else self._t.tensor(vector)
        self._keys.append(atom)
        self._vectors.append(tensor.detach().float())
        self._matrix = None
        if self._mirror:
            self._m.add(expr(S.embedding, atom, val(self._vectors[-1])))

    def __len__(self) -> int:
        return len(self._keys)

    def _search(self, query, k: int):
        if not self._keys:
            return
        t = self._t
        if self._matrix is None:
            stacked = t.stack(self._vectors)
            self._matrix = t.nn.functional.normalize(stacked, dim=-1)
        q = query if isinstance(query, t.Tensor) else t.tensor(query)
        q = t.nn.functional.normalize(q.detach().float().reshape(-1), dim=-1)
        scores = self._matrix @ q
        k = min(k, len(self._keys))
        top = t.topk(scores, k)
        for score, index in zip(top.values.tolist(), top.indices.tolist()):
            yield expr(self._keys[index], round(score, 6))

    def keys(self) -> list[Atom]:
        return list(self._keys)

    def vector_for(self, key: Any):
        atom = key if isinstance(key, Atom) else S[str(key)]
        for stored, vector in zip(self._keys, self._vectors):
            if stored == atom:
                return vector
        raise KeyError(f"no embedding stored for {atom}")
