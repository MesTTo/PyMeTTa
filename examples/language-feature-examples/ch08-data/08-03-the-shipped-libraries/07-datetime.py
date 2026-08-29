"""examples/ch08-data/08-03-the-shipped-libraries/07-datetime.metta in Python: clocks and calendars.

`now`, `day-of-week` and `format-date` are lib_datetime's own and the subject
of the file, so the twin names them. Everything around them is Python: the
example's `let` and `let*` bindings are assignments and its comparison of two
readings is Python's `==`.

Two of the example's three bare demonstration forms bind an intermediate name
and hand it to the claim written just below them, so the Python that says both
is the claim itself, with the `let*` it translates on the line. The third has
no claim under it and reads the clock in local time, so it PRINTS, which is
what a top-level `!` form does in the example's own run.

What is checkable about a clock is that it runs forward from a date already
past and that formatting one reading twice is stable; the fixed timestamps
check `format-date`'s output itself.
"""

from metta import G, S, lib

#: 2025-01-01T00:00:00Z, a date already past, so a live clock is after it.
NEW_YEAR_2025 = 1735689600

#: strftime patterns are text, and text is what a string is for.
ISO_DAY, CLOCK, MONTH_NAME = G("%Y-%m-%d"), G("%H:%M:%S"), G("%B")


def twin(m):
    """Read the clock, then format and name three fixed timestamps."""
    m += lib.datetime

    now = m.fn.now
    # (let $ts (now) (< 1735689600 $ts))
    assert now().one() > NEW_YEAR_2025

    # One reading, formatted twice: a live clock is stable within one reading
    # and would not be across two.
    format_date = m.fn.format_date
    reading = now().one()
    assert format_date(reading, ISO_DAY).one() == format_date(reading, ISO_DAY).one()

    # (let* (($ts 1766188800) ($dow (day-of-week $ts))) ($dow))
    a_saturday = 1766188800
    assert m.fn.day_of_week(a_saturday) == [S.Saturday]

    # (let* (($ts1 ...) ($ts2 ...) ($diff (- $ts2 $ts1))) ($diff)): both
    # operands are ground, so the subtraction is Python's own.
    assert 1736294400 - NEW_YEAR_2025 == 604800

    # (let* (($ts 1735725045) ($time-only (format-date $ts "%H:%M:%S"))) ($time-only)):
    # a wall-clock reading, so what it prints moves with the machine's zone.
    print(format_date(1735725045, CLOCK))

    assert format_date(NEW_YEAR_2025, MONTH_NAME) == [S.January]


#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 24796 to 24948, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 24948 to 24957, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 24957 to 24973, on the release tree:
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
#: RE-PINNED 2026-08-26, 24973 to 24419 (-554), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 24419
