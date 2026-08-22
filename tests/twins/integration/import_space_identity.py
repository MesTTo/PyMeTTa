"""The Python twin of examples/integration/import_space_identity.metta.

Two spaces import the same payload, and the file's point is that each importing
space runs its own copy exactly once while the CALLER imported nothing, so the
name stays data there.

`bind!` is evaluated rather than replaced by a Python name binding, because what
is being bound is a fresh SPACE the later forms address by name, and the forms
that address it are `m.eval` terms in the same space. The imported paths are
absolute for the P14.13 reason the sibling import twins record.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
BUDGET = 9672


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(bind! &import-space-a (new-space))
    yield m.eval(S["bind!"](S["&import-space-a"], S["new-space"]()))

    # !(bind! &import-space-b (new-space))
    yield m.eval(S["bind!"](S["&import-space-b"], S["new-space"]()))

    # !(import! &import-space-a _fixtures/imports/overhaul/space_payload)
    yield m.eval(
        S["import!"](S["&import-space-a"],
            S["examples/integration/_fixtures/imports/overhaul/space_payload"])
    )

    # !(import! &import-space-b _fixtures/imports/overhaul/space_payload)
    yield m.eval(
        S["import!"](S["&import-space-b"],
            S["examples/integration/_fixtures/imports/overhaul/space_payload"])
    )

    # !(test (collapse (match &import-space-a (import-space-marker) present)) (present))
    yield m.eval(
        S.test(S.collapse(S.match(S["&import-space-a"], S["import-space-marker"](), S.present)),
            (S.present,))
    )

    # !(test (collapse (match &import-space-b (import-space-marker) present)) (present))
    yield m.eval(
        S.test(S.collapse(S.match(S["&import-space-b"], S["import-space-marker"](), S.present)),
            (S.present,))
    )

    # !(test (collapse (metta (import-space-function) %Undefined% &import-space-a)) (one-result))
    yield m.eval(
        S.test(S.collapse(S.metta(S["import-space-function"](),
                    S["%Undefined%"],
                    S["&import-space-a"])),
            (S["one-result"],))
    )

    # !(test (collapse (metta (import-space-function) %Undefined% &import-space-b)) (one-result))
    yield m.eval(
        S.test(S.collapse(S.metta(S["import-space-function"](),
                    S["%Undefined%"],
                    S["&import-space-b"])),
            (S["one-result"],))
    )

    # !(test (collapse (import-space-function)) ((import-space-function)))
    yield m.eval(
        S.test(S.collapse(S["import-space-function"]()),
            (S["import-space-function"](),))
    )
