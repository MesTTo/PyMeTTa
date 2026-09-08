"""examples/ch08-data/08-03-the-shipped-libraries/16-the_prolog_rung.metta in Python: the rung under five libraries.

Every underscore name here is a Prolog predicate a library imported, and the
hyphenated MeTTa name above it is one equation over it. Python's own map
turns an underscore into a hyphen, so every one of these comes through the
exact subscript door and the pairs that compare them are what says the two
spellings are one operation.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from pathlib import Path

from metta import G, S, lib

#: The provider the conformance kit is asked about, as a host path.
_REPO = Path(__file__).resolve().parents[6]
PROVIDER = _REPO / Path(
    "examples/ch08-data/08-03-the-shipped-libraries/_fixtures/demo_provider.pl"
)

#: What a healthy provider reports about itself, in the engine's own prose.
REPORT = (
    G("match: declared, seam:foreign_match/3 has clauses"),
    G("enumerate: declared, seam:foreign_atoms/2 has clauses"),
    G("match: over-approximation holds over 2 atoms and their pattern families"),
    G("source: repeated, two enumerations agree"),
    G(
        "round trip: not asked, the provider does not declare add, remove and "
        "enumerate together"
    ),
    G("pushdown: 0 of 2 patterns claimed exact, and are"),
    G("plan: not declared, so a conjunction takes the engine's split"),
)

TEXT_SHA256 = G("982d9e3eb996f559e633f4d194def3761d909f5a3b647d1a851fead67c32c9d1")


def twin(m):
    """Regex, hashes, dates and the conformance kit, called one rung down."""
    for library in (lib.string, lib.regex, lib.crypto, lib.datetime, lib.conformance):
        m += library

    # lib_regex's six. `re-match` is one equation over `regex_match`.
    assert m.fn["regex_match"](G("(?i)^needle"), G("Needle in a haystack")) == [True]
    assert m.fn["regex_match"](G("^x"), G("abc")) == m.fn["re-match"](G("^x"), G("abc"))
    assert m.fn["regex_find"](G(r"\d+"), G("a1 b22 c333")) == [G("1"), G("22"), G("333")]
    assert m.fn["regex_captures"](G(r"(?<y_I>\d+)"), G("n 42")) == [
        ((0, G("42")), S.y(42))
    ]
    assert m.fn["regex_split"](G(r":\s*"), G("Age: 33")) == [(G("Age"), G(": "), G("33"))]
    assert m.fn["regex_replace"](G("a"), G("X"), G("banana")) == [G("bXnana")]
    assert m.fn["regex_replace_all"](G("a"), G("X"), G("banana")) == [G("bXnXnX")]

    # lib_crypto's two. A digest is a content key.
    assert m.fn["crypto_hash"](S.sha256, G("text")) == [TEXT_SHA256]
    assert m.fn["crypto_hash"](S.sha256, G("text")) == m.fn["crypto-hash"](
        S.sha256, G("text")
    )
    assert m.fn["crypto_hash"](S.sha256, G("other")) != [TEXT_SHA256]

    # Randomness is the other way round: two hex characters per byte asked
    # for, and never the same ones twice.
    assert m.fn["string-length"](m.fn["crypto-random-hex"](8)[0]) == [16]
    assert m.fn["string-length"](m.fn["crypto_random_hex"](16)[0]) == [32]
    assert m.fn["crypto-random-hex"](16) != m.fn["crypto-random-hex"](16)

    # lib_datetime's two, over Unix time. The epoch is a Thursday, which is
    # the one date this can assert without asking what day it is.
    assert m.fn["day_of_week"](0) == [S.Thursday]
    assert m.fn["format_date"](0, G("%Y-%m-%d")) == [S["1970-01-01"]]
    assert m.fn["day_of_week"](0) == m.fn["day-of-week"](0)
    assert m.fn["format_date"](0, G("%H:%M:%S")) == m.fn["format-date"](0, G("%H:%M:%S"))

    # lib_conformance's one, which is the whole library.
    m.register_prolog(path=PROVIDER)
    provider = m.metta.space(S["demo_provider"])
    assert m.fn["metta_check_space_provider"](provider) == [REPORT]
    assert m.fn["metta_check_space_provider"](provider) == m.fn[
        "check-space-provider"
    ](provider)


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 131980 inferences, 0.9699x the example's 136076; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 131980 to 132023 (+43), the merges between this lane's
#: burn-down base (dfd5003f) and the tree that merged it, placed by a first-
#: parent ladder through the lane's own driver over ten twins at f8c4b672,
#: 4af59757, 90c08119, ad762ee7, 72f9cdf2 and 249389cb (ai-
#: tmp/integrator-849a9e/mergeTW-twin-ladder.log): the catalog-types merge
#: (1a3579fa) moves every twin by a lookup-and-layout step of about +5 for a
#: twin that makes no typed call and about +35 for one that does, plus about +6
#: per compiled definition through the argument-delivery check at the write
#: (the authoring fit re-measured 1370+1307 to 1406+1309), and +1411 for the
#: catalog twin that enumerates the 280 new rows; the two-sided-fragments merge
#: (4af59757) moves the sequence-variable twins by what their fixed rows now
#: compute (+2604 for the two-sided fragments, -217 for the fence, +19 for
#: restricted spaces); the every-atom merge (90c08119) re-authored the reading-
#: forms twin into the sread half (+3017) and added forty-six twins pinned on
#: its own base 31d54e19, which the merges since moved by the same clusters;
#: the gate-hygiene merge (ad762ee7) makes the tabling twins cheaper by the wfs
#: library no longer loading eagerly. Every twin here re-reads its budget on
#: the merged tree, minimum of three fresh processes [measured 2026-09-08: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
#: RE-PINNED 2026-09-08, 132023 to 131982 (-41), metta_substitute_self/3 probes
#: the term for the text &self before walking it, one C write and one C
#: substring probe, where the twins-lane merge's one-equation door (08f6f4df)
#: walked every natively added equation in a named space unconditionally, so
#: every twin that adds or defines an equation in a named space drops by about
#: that equation's size in inferences; the same probe now guards the reader's
#: per-form door (record_translated_from/4), the deferred door's fallback
#: (stored_equation_source/4), a batch's arriving equations
#: (mark_or_translate_equation/5) and the removal probe (remove_equation/6),
#: where the walk is new and skipped for a term that never says &self, and a
#: twin that only removes or re-adds such equations pays the two-inference
#: probe per door crossing instead. Every twin here re-reads its budget on this
#: tree, minimum of three fresh processes [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-PINNED 2026-09-08, 131982 to 131900 (-82), the evaluation-fuel scope
#: marker is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 131900 to 139247 (+7347), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 139247 to 139693 (+446), the module boundary merged
#: with trunk's later packages (refactor/engine-and-libraries-as-modules at
#: b64291369): every space now resolves through one more chain link, prelude ->
#: metta_engine -> user, the engine's measured export list is imported into the
#: host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 139693
