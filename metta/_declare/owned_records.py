"""Purpose: derive owned-record declarations and native access from row structure.

Assumes: callers retain exact declaration occurrences with the source program;
  owner and record keys are native atoms admitted by metta_check_owned_record/1
  [source: engine/spaces/owned_records.pl:metta_check_owned_record/1; commit=WORKTREE].
Guarantees: native reads validate original occurrence keys and cardinality;
  dependencies retain the full row around stored Error data
  [source: engine/spaces/owned_records.pl:'owned-record-read'/2;
  commit=WORKTREE].
Decides: a write evaluates its supplied source once after checking its owner;
  empty reads and deletes use the caller's missing-binding expression
  [source: extensions/python/metta/_declare/owned_records.py:OwnedRecord.write;
  commit=WORKTREE].
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from metta._atoms.factories import Atom, Expression, Grounded, S, _expr, fresh


@dataclass(frozen=True, slots=True)
class OwnedRecord:
    """One structural prefix whose current value belongs to a native owner."""

    owner_home: Atom
    owner: Atom
    storage: Atom
    prefix: Expression

    @property
    def declaration(self) -> Expression:
        """Publish the pattern once for the source program, before allocation."""
        return _expr(S["@owned-record"], self.owner_home, self.owner, self.storage, self.prefix)

    @property
    def owner_row(self) -> Expression:
        """Use the existing lifetime marker for every field of this owner."""
        return _expr(S["owned-by"], self.owner)

    def row(self, value: Atom) -> Expression:
        """Append the value to the key prefix without interpreting its contents."""
        return _expr(*self.prefix.children, value)

    def _select(self, present: Callable[[Atom], Atom], missing: Atom) -> Expression:
        rows = fresh()
        return _expr(S.chain, _expr(S["owned-record-read"], self.declaration), rows,
            _expr(S["if"], _expr(S["=="], _expr(S["size-atom"], rows), Grounded(0)),
                missing, present(_expr(S["car-atom"], rows))))

    def read(self, missing: Atom) -> Expression:
        """Return the stored value, or evaluate the caller's empty-cell refusal."""
        return self._select(
            lambda row: _expr(S["index-atom"], row, Grounded(len(self.prefix.children))), missing)

    def dependencies(self) -> Expression:
        """Return complete current rows so a stored Error remains dependency data."""
        # Scope treats only a top-level Error as a failed dependency query.
        # [source: lib/lib_thread/lib_thread.pl:scope_expression_answer_/2;
        # commit=WORKTREE]
        return self._select(lambda row: row, _expr(S.superpose, Expression([])))

    def write(self, value_source: Atom) -> Expression:
        """Replace the value atomically; pass held values through noeval.

        A refused read (a retired owner, a malformed original) is the answer,
        as the Error atom the class contract names, not an escaping exception:
        the caught refusal short-circuits before the source is evaluated.
        """
        checked, value, removed, added = fresh(), fresh(), fresh(), fresh()
        return _expr(S.transaction,
            _expr(S.chain, _expr(S.catch, _expr(S["owned-record-read"], self.declaration)), checked,
                _expr(S["if-error"], checked, checked,
                    _expr(S.chain, value_source, value,
                        _expr(S.chain, _expr(S["remove-atom"], self.storage, self.row(fresh())), removed,
                            _expr(S.chain, _expr(S["add-atom"], self.storage, self.row(value)), added,
                                Grounded(value=True)))))))

    def delete(self, missing: Atom) -> Expression:
        """Remove an initialized value atomically while preserving its owner."""
        return _expr(S.transaction, self._select(
            lambda _row: _expr(S.chain,
                _expr(S["remove-atom"], self.storage, self.row(fresh())), fresh(), Grounded(value=True)),
            missing))
