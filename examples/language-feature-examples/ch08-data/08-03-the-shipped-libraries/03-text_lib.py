"""Purpose: examples/ch08-data/08-03-the-shipped-libraries/03-text_lib.metta in Python: lib_string and lib_file.

Guarantees: a short format argument list leaves later placeholders empty
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/03-text_lib.metta;
commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].

Both libraries are the subject, so every function here is named through the
function namespace, where a typo raises on the line that writes it. What Python
takes over is the plumbing around them: the `let` chain that threads a file
handle through three calls is three statements, the file space is queried
through the handle's own subscript door, and every answer is compared as
ordinary Python data.

Two heads keep their MeTTa spelling with a stated reason rather than
dissolving. `format-args` is MeTTa HE's own formatter and this file is HE's
example of it, including what it does with too few arguments, which an f-string
cannot reproduce; `sort-strings` is the library function under test, not a
request to sort a Python list.

A trailing `!` has no Python image, so `write_file` and its siblings resolve to
`write-file!`: rung 4 of the descent ladder, applied at the function namespace.

The file this writes is named for the twin rather than for the example, so the
two can never meet on one path, and it is a `pathlib.Path` rather than text:
a path crosses the call door as the atom its codec makes of it.
"""

from pathlib import Path

import metta
from metta import G, S, V, lib


def twin(m):
    """Walk lib_string's measuring, slicing, testing and padding, then lib_file."""
    m += lib.string
    m += lib.file

    # temp-path! mints a unique fresh path in the system temporary
    # directory, exclusively created, so concurrent twins cannot collide;
    # the twin owns the file, and delete_file at the end is its removal.
    scratch = Path(str(m.fn.temp_path(G("metta-text-twin")).one()))

    # Measuring and slicing. string-slice is half-open, From included, To not.
    string_length = m.fn.string_length
    assert string_length(G("hello")) == [5]
    string_slice = m.fn.string_slice
    assert string_slice(G("hello world"), 0, 5) == [G("hello")]
    # An over-long end clamps instead of erroring, as slicing does everywhere.
    assert string_slice(G("hello"), 3, 999) == [G("lo")]
    assert string_slice(G("hello"), 99, 120) == [G("")]

    # Splitting and joining are inverses.
    [pieces] = m.fn.string_split(G(","), G("a,b,c"))
    assert list(pieces) == [G("a"), G("b"), G("c")]
    assert m.fn.string_join(G(", "), (G("a"), G("b"), G("c"))) == [G("a, b, c")]
    assert m.fn.string_trim(G("  padded  ")) == [G("padded")]
    string_upper = m.fn.string_upper
    assert string_upper(G("shout")) == [G("SHOUT")]
    assert m.fn.string_lower(G("QUIET")) == [G("quiet")]

    # The tests answer True or False, so they guard a query.
    assert m.fn.string_starts_with(G("hello"), G("he")) == [True]
    assert m.fn.string_ends_with(G("hello"), G("lo")) == [True]
    contains = m.fn.string_contains
    assert contains(G("hello"), G("ell")) == [True]
    assert contains(G("hello"), G("zzz")) == [False]

    # index-of answers -1 rather than failing: asking "where is it" deserves an
    # answer either way.
    index_of = m.fn.string_index_of
    assert index_of(G("hello"), G("l")) == [2]
    assert index_of(G("hello"), G("z")) == [-1]

    # replace changes every occurrence.
    assert m.fn.string_replace(G("banana"), G("a"), G("X")) == [G("bXnXnX")]

    # chars are one-character STRINGS, not char symbols, so the pieces are the
    # same kind of thing as the whole and feed straight back in.
    [chars] = m.fn.string_chars(G("abc"))
    assert list(chars) == [G("a"), G("b"), G("c")]
    assert m.fn.string_from_chars(chars) == [G("abc")]
    assert m.fn.string_repeat(G("ab"), 3) == [G("ababab")]
    assert m.fn.string_pad_left(G("7"), 3, G("0")) == [G("007")]
    assert m.fn.string_pad_right(G("7"), 3, G(".")) == [G("7..")]

    # rung: format-args is MeTTa HE's own formatter and this is HE's example of
    # it; an f-string cannot show what it does with too few arguments, which is
    # the second claim.
    format_args = m.fn.format_args
    assert format_args(G("Probability of {} is {}%"), (S.head, 50)) == [
        G("Probability of head is 50%")
    ]
    # A short argument list produces NOTHING for the placeholders it cannot
    # fill, which is the dyn_fmt formatter upstream interpolates through.
    assert format_args(G("{} and {}"), (G("only"),)) == [G("only and ")]

    [sorted_strings] = m.fn.sort_strings((G("pear"), G("apple"), G("fig")))  # rung: sort-strings is the library function under test, not a request to sort a Python list
    assert list(sorted_strings) == [G("apple"), G("fig"), G("pear")]
    assert m.fn.parse_number(G("42")) == [42]
    assert m.fn.number_to_string(42) == [G("42")]

    # Text operations accept a Symbol or a Number where a String is wanted,
    # because a symbol arriving where a string was meant is ordinary in MeTTa.
    assert string_length(S.hello) == [5]
    assert string_upper(S.hello) == [G("HELLO")]

    # Files.
    assert m.fn.write_file(scratch, G("one\ntwo\nthree\n")) == [True]
    assert m.fn.read_file(scratch) == [G("one\ntwo\nthree\n")]
    # file-lines! drops the trailing empty line a final newline would produce.
    file_lines = m.fn.file_lines
    [lines] = file_lines(scratch)
    assert list(lines) == [G("one"), G("two"), G("three")]
    assert m.fn.append_file(scratch, G("four\n")) == [True]
    [lines] = file_lines(scratch)
    assert list(lines) == [G("one"), G("two"), G("three"), G("four")]

    # The handle surface is MeTTa HE's exactly: r read, w write, c create,
    # a append, t truncate. The example's `let` chain is three statements.
    handle = m.fn.file_open(scratch, G("r")).one()
    head = m.fn.file_read_exact(handle, 3).one()
    m.fn.file_close(handle).one()
    assert head == G("one")

    # file-space! is the mettafied reading of reading a file: its lines become
    # (line Number Text) atoms in a space, so the file is QUERYABLE rather than
    # one long string you then have to take apart. The line number is kept
    # because a space is unordered.
    log = metta.space(m.fn.file_space(scratch).one())
    assert [(row.n, row.t) for row in log[S.line(V.n, V.t)]] == [
        (1, G("one")), (2, G("two")), (3, G("three")), (4, G("four")),
    ]
    # Asking for one line is a match, not a scan.
    assert [row.t for row in log[S.line(2, V.t)]] == [G("two")]

    assert m.fn.delete_file(scratch) == [True]


#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 75180 to 75940, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 75940 to 75949, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 75949 to 76031, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 76031 to 75571 (-460), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-09-01, 75571 to 80442 (+4871), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 80442 to 80360 (-82), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 80360 to 80574 (+214), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 80574 to 80936 (+362), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 80936 to 100146 (+19210), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 100146 to 104669 (+4523), trunk's own movement since
#: each twin's pin was taken on the base its own branch had: twenty-two first-
#: parent steps between the 0.8.0 release re-pin and this tree, the prelude's
#: move into Prolog the largest of them at +39 to +115 a twin and -65,806 on
#: the error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 104669 to 104662 (-7), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 104662 to 104547 (-115), the evaluation-fuel scope
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
#: RE-PINNED 2026-09-08, 104547 to 111312 (+6765), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 111312 to 111921 (+609), the module boundary merged
#: with trunk's later packages (refactor/engine-and-libraries-as-modules at
#: b64291369): every space now resolves through one more chain link, prelude ->
#: metta_engine -> user, the engine's measured export list is imported into the
#: host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-PINNED 2026-09-09, 111921 to 112692 (+771), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 111921 to 113264 (+1343), Trailing occurrence
#: arguments, token allocation in native writes, exact source withdrawal and
#: transaction-safe shared-table guards change the engine work priced by this
#: twin; answer bags retain the upstream law [measured 2026-09-08: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 113264 to 114035 (+771), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 111921 to 111889 (-32), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 111889 to 114003 (+2114), the compiled vocabulary
#: seed, the membership index, base-module type lookups and the singleton
#: decoder landed (perf/cross-engine-waivers merged): boot publishes the
#: initial vocabulary types from a compiled payload through the tokenized
#: funnel, a warm membership read touches only its own clauses, a base-module
#: type lookup skips the prelude, and a Python decode with one named variable
#: builds no index; per-operation costs of a mint, write, read, drop, run, save
#: and load are unchanged against the trunk in fresh processes; measured on the
#: merged tree, -32 against the trunk's own pin of 114035 at da0e5755d; the
#: previous number is the branch's cut-time price, and the remaining +2146 is
#: what landed on the trunk between the cut f0d33dcad and da0e5755d, tokens as
#: storage above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-09, 114003 to 37233 (-76770), a library's Prolog half
#: compiles beside itself on its first import and loads from the artifact after
#: (metta_load_source/2, seam:compiled_source/1): a twin whose example imports
#: a library with a Prolog half pays the artifact load where both sides paid
#: the source consult and its compile-time expansion in every process,
#: lib_thread's import 278,309 to 5,925 inferences; every import now resolves
#: its spec and asks the boot's claim, about 180 inferences an import, and the
#: boot's content moved (the door, the seam and the three library imports the
#: tokens, receipts and seed units gained), which shifts clause layout by tens;
#: measured on this tree with the artifacts warm [measured 2026-09-09: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f26de01fbf3e0e3c64bb691c66a59fa959fee7f3].
#: RE-PINNED 2026-09-11, 37233 to 37228 (-5), Explicit
#: filereader:source_pending_definition/2 in
#: translator:runnable_head_awaits_its_definition/1 removes one inherited-
#: resolution retry. The same-physical-path qualifier-only toggle has 102
#: successful children, three identical samples per arm, unchanged source/twin
#: bodies and semantic fields, and no instrumentation (ai-tmp/ai-qualified-
#: boundaries-analysis.json and ai-tmp/ai-qualified-
#: boundaries-{unqualified,qualified}.json). This point was already four below
#: its declaration in the e93f2028d ten-round full lane; qualification saves
#: one more, crossing the unchanged four-inference allowance. All instruction
#: pins, bands, bodies, assertions and stored-content oracles stay. Foldall
#: retains 17904. The end-of-wave battery re-pins the whole lane on the merged
#: tree under the normalised protocol; these are this tree's measured prices
#: [measured 2026-09-11: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: RE-PINNED 2026-09-11, 37228 to 110303 (+73075), String now imports its
#: complete typed native surface and checks its declared native inputs; an
#: unchanged-cut control with identical engine and MORK binaries attributes
#: these exact movements to the String provider and shared native_object/6
#: dependency argument [measured 2026-09-11: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=3aaad3435292e4c7d5cc3a01bfda39430aacc6e8].
#: RE-PINNED 2026-09-12, 110303 to 140561 (+30258), The File library publishes
#: 56 documented heads at 60 arities where it published 32, so every direct and
#: transitive importer pays the larger generated face and the module's own
#: export list. An identical-binary control at 8eb04b55a with artifacts purged
#: measured each of these ten twins before the change (ai-tmp/ai-lib2-file-
#: importers-before.log) and attributes the whole movement to that face:
#: +22,479 on the four twins that only import it through another library,
#: +24,552 to +24,862 where the example also calls it, and +30,258 and +30,687
#: on the two whose own claims are file operations [measured 2026-09-12: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 140561
