"""Purpose: what each derived method BUYS, one row per method. `ledger.py` derives
the classification from the code and reads these for the reasons; this file is
only the reasons.

A derived method is macro-expressible by another public method. That is not a
defect on its own: a named face of one mechanism is derived and should stay,
because collapsing it puts the mechanism's argument back at the call site.
What has no place is a derived method whose row cannot say what it buys, and the
gate exists to make that visible rather than arguable.

Assumes:
  - the reason is about the CALLER. "It is shorter" is not one; a projection,
    a cardinality contract, a lifetime, a different consumption model or a
    measured cost are.
Guarantees:
  - every derived method has exactly one row, checked against the class rather
    than against this file [tested: test_the_shrink_ledger_covers_every_derived_door]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

#: method -> what it buys that the method expressing it does not give.
DERIVED: dict[str, str] = {
    "add_tagged_fact": (
        "the tag threader's atom shape, so a caller writes the tag and the "
        "proposition rather than the `(fact tag proposition)` spelling, and "
        "gets the stored atom back where `add` answers nothing"
    ),
    "add_tagged_rule": (
        "the same for a rule, whose atom the algebra generates from a head "
        "and its premises rather than from a literal"
    ),
    "copy": (
        "one act for enumerate-and-store, and the space it answers is a new "
        "one rather than this handle rebound"
    ),
    "doc": (
        "the structured `(@doc ...)` answer decoded into its parts, where "
        "`eval` of `get-doc` answers the raw term"
    ),
    "eval": (
        "the EAGER path. It delegates to `answers` only for the carrier, the "
        "theory and the interpreter, and the split is measured rather than "
        "assumed: routing it through the cursor unconditionally left a "
        "memoized definition's call keys unrecorded, 13 entries on the eager "
        "path against 0 through the cursor"
    ),
    "ne": (
        "the negated relation as one term, `(not (== a b))`, so a caller "
        "spells the relation rather than its expansion"
    ),
    "pre_add": (
        "a HOOK rather than an equation: the definition it installs runs on "
        "the write path, which is a different moment from a call"
    ),
    "register_foreign_library": (
        "the library PATH handling around a registration, so a caller names "
        "a shared object rather than resolving it"
    ),
    "solve": (
        "the relational direction and the answer template. It derives the "
        "template from the pattern's variables followed by any new subject "
        "variables, which is what lets either direction introduce the "
        "bindings and removes `let`'s hand-written third argument"
    ),
    "subs": (
        "substitution keyed by ATOM, and an answer `Row` accepted directly. "
        "`map` takes a transform over every node; this is the transform, and "
        "the key carries whether a variable or a symbol is meant"
    ),
    "transaction": (
        "all-or-nothing over the block, which no sequence of evaluations "
        "gives: the engine's own transaction boundary is what makes a "
        "failure leave the space unchanged"
    ),
    "transactional": (
        "the DECORATOR shape, so each CALL of the wrapped function runs in "
        "its own transaction. `transaction` runs one callable now; decoration "
        "cannot await and cannot run anything"
    ),
    "type": (
        "the first `get-type` answer decoded, including the undefined case, "
        "where `eval` answers the raw term list"
    ),
    "watch": (
        "the ITERATOR form of the callback method, and a deadline. A caller "
        "who wants to pull events cannot use a callback, and the two "
        "consumption models are why both exist"
    ),
    "why": (
        "the question without the answers. It asks why a pattern matches "
        "nothing without the caller first materialising the match that did "
        "not happen"
    ),
}
