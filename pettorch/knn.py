"""Purpose: compatibility re-export. The embedding store is library-agnostic
now and lives in petta.arrays; pettorch keeps the old import path working.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from petta.arrays import EmbeddingStore

__all__ = ["EmbeddingStore"]
