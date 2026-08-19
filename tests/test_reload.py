"""Purpose: a MeTTa source can be reloaded after editing, through either door.

The two doors used to fail in opposite directions, both silently. `load`
had no file identity, so a second load added the file's definitions on top
of the first and `(answer)` answered 1 and 2. `import!` had identity but no
change detection, so a second import was skipped and the edit was ignored.
Every test here drives the public surface and edits a real file on disk,
because the thing under test is what happens between two loads.

The two doors are SWI's own loading conditions and behave as they do:
`load` is `consult/1`, always loading and replacing what the file put
there before; `import!` is `if(changed)`, loading a file that is new or
edited and skipping one that is neither.

Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import uuid

import pytest

import petta
from petta import S, V
from petta.structures import LiveView


@pytest.fixture()
def source(tmp_path):
    """A .metta file with a name no other test shares, since the engine
    keys a load on its canonical path and the session shares one engine."""
    return tmp_path / f"reload_{uuid.uuid4().hex}.metta"


@pytest.fixture()
def scratch(metta):
    """A fresh anonymous space per test, on the shared engine."""
    return metta.new_space()


def fresh(name):
    """A function name no other test in the session has defined."""
    return f"{name}-{uuid.uuid4().hex}"


def test_a_reloaded_source_replaces_its_definitions_and_says_what_it_replaced(
    metta, source, capfd
):
    """The item's own scenario, measured 2026-08-18 as [1, 2] and unfixable
    from either door: a file `(= (answer) 1)` edited to `(= (answer) 2)`."""
    answer = fresh("answer")
    source.write_text(f"(= ({answer}) 1)\n")
    metta.load(source)
    assert metta.run(f"!(collapse ({answer}))") == [[petta.Expr([1])]]

    capfd.readouterr()
    source.write_text(f"(= ({answer}) 2)\n")
    metta.load(source)

    assert metta.run(f"!(collapse ({answer}))") == [[petta.Expr([2])]]
    said = capfd.readouterr().err
    assert str(source) in said, said
    assert "1 atom(s) withdrawn" in said, said


def test_both_doors_replace_a_files_definitions(metta, source):
    """load and import! end at the same place. They reach it differently,
    which is the point of the two conditions: import! skips an unchanged
    file where load reruns it, but neither ever accumulates."""
    for door in ("load", "import"):
        answer = fresh(f"door-{door}")
        source.write_text(f"(= ({answer}) 1)\n")
        if door == "load":
            metta.load(source)
        else:
            metta.run(f'!(import! &self "{source}")')
        assert metta.run(f"!(collapse ({answer}))") == [[petta.Expr([1])]]

        source.write_text(f"(= ({answer}) 2)\n")
        if door == "load":
            metta.load(source)
        else:
            metta.run(f'!(import! &self "{source}")')
        assert metta.run(f"!(collapse ({answer}))") == [[petta.Expr([2])]], door


def test_loading_the_same_file_twice_leaves_one_copy(scratch, source):
    """What `load` used to do instead: two copies, silently. Consult
    semantics run the directives again and replace the definitions."""
    source.write_text("(loaded-copy value)\n")
    scratch.add(S.existing(S.value))
    scratch.load(source)
    scratch.load(source)

    assert scratch.count() == 2
    assert len(scratch.query(S["loaded-copy"](V.value))) == 1


def test_a_stopped_load_leaves_the_space_as_it_found_it(scratch, source):
    """A load is all or nothing, because a file a space holds half of is not
    a file it can replace later. The engine's own door always rolled a
    stopped load back; the library's did not, which is the same two-doors
    disagreement in its other half."""
    source.write_text(
        "(before-the-stop landed)\n"
        "(= (spin $n) (spin (+ $n 1)))\n"
        "!(spin 0)\n"
    )
    with pytest.raises(petta.InferenceLimitError):
        scratch.load(source, inferences=50_000)

    assert list(scratch.atoms()) == []


def test_a_file_the_library_loaded_is_already_imported(metta, source):
    """The two doors share one record of what has been loaded, so an import!
    of a file `load` already read finds it loaded and unchanged and does not
    run it a second time."""
    marker = fresh("crossed")
    source.write_text(f"!(add-atom &self ({marker} once))\n")
    metta.load(source)
    metta.run(f'!(import! &self "{source}")')

    assert len(metta.query(S[marker](V.x))) == 1


def test_loading_a_fast_cache_twice_leaves_one_copy(metta, scratch, tmp_path):
    """`load` means one thing whatever the file's format. A trusted fast
    cache is a serialised space read by a format of its own, and it is
    replaced on a second load the same way a text program is: the format
    already carries the sha256 of its payload, which is the question the
    text path asks of a source's text."""
    cache = tmp_path / f"cache_{uuid.uuid4().hex}.fast"
    donor = metta.new_space()
    donor.add(S["cached-fact"](S.one))
    donor.save(cache, format="fast")

    scratch.load(cache)
    scratch.load(cache)

    assert scratch.count() == 1


def test_loading_one_file_into_many_spaces_replaces_none_of_them(metta, source):
    """A file going into a space that does not hold it is a first load, not a
    reload of the spaces that do. Reading it the other way made every new
    destination withdraw and repopulate every earlier one."""
    fact = fresh("many-spaces")
    source.write_text(f"({fact} value)\n")
    spaces = [metta.new_space() for _ in range(4)]
    for space in spaces:
        space.load(source)

    assert [space.count() for space in spaces] == [1, 1, 1, 1]


def test_a_cleared_space_forgets_what_a_file_put_in_it(metta, source):
    """Space names are pooled, so a record of what a file contributed has to
    go when the space is cleared: the next life of that name would otherwise
    be told it already holds the file."""
    fact = fresh("cleared")
    source.write_text(f"({fact} value)\n")
    scratch = metta.new_space()
    scratch.load(source)
    scratch.clear()

    scratch.load(source)

    assert scratch.count() == 1


def test_an_unchanged_repeat_import_does_not_run_the_source_again(metta, source):
    """import! is if(not_loaded) widened to if(changed), not to if(true).
    The arbiter measures a second import of an unchanged module reusing the
    loaded instance and executing its source once, and that still holds
    [source: LeaTTa tests/semantics/modules/30-resolution-loaded, M30]."""
    marker = fresh("import-ran")
    source.write_text(f"!(add-atom &self ({marker} once))\n")

    metta.run(f'!(import! &self "{source}")')
    metta.run(f'!(import! &self "{source}")')
    metta.run(f'!(import! &self "{source}")')

    assert len(metta.query(S[marker](V.x))) == 1


def test_an_edited_import_is_not_skipped(metta, source):
    """The second door's own defect: idempotent by path, so the edit was
    ignored and the program went on running the stale definition."""
    answer = fresh("edited-import")
    source.write_text(f"(= ({answer}) stale)\n")
    metta.run(f'!(import! &self "{source}")')
    source.write_text(f"(= ({answer}) fresh)\n")
    metta.run(f'!(import! &self "{source}")')

    assert metta.run(f"!(collapse ({answer}))") == [[petta.Expr([S.fresh])]]


def test_a_reload_drops_a_definition_the_new_source_no_longer_has(metta, source):
    """Replacement, not merge. A rule deleted from the file is a rule the
    program stops answering, which is the half a retract-and-assert reload
    written as 'add the new ones' would miss. An undefined call stays
    unreduced, so the witness is the equation leaving the space and the
    call no longer answering yes."""
    kept, dropped = fresh("kept"), fresh("dropped")
    source.write_text(f"(= ({kept}) yes)\n(= ({dropped}) yes)\n")
    metta.load(source)
    assert metta.run(f"!(collapse ({dropped}))") == [[petta.Expr([S.yes])]]

    source.write_text(f"(= ({kept}) yes)\n")
    metta.load(source)

    assert metta.run(f"!(collapse ({kept}))") == [[petta.Expr([S.yes])]]
    assert metta.query(S["="](S[dropped](), V.v)) == []
    assert metta.run(f"!(collapse ({dropped}))") == [
        [petta.Expr([petta.Expr([S[dropped]])])]
    ]


def test_a_reload_replaces_that_files_definitions_and_no_others(metta, tmp_path):
    """Replacement is per file. Two sources that define one name both
    contribute, and reloading one takes back its own equation and leaves the
    other's, which is the boundary of what this means by replace: a function
    two files define answers twice, and that is a name collision rather than
    a reload."""
    shared = fresh("shared-name")
    first = tmp_path / f"one_{uuid.uuid4().hex}.metta"
    second = tmp_path / f"two_{uuid.uuid4().hex}.metta"
    first.write_text(f"(= ({shared}) from-first)\n")
    second.write_text(f"(= ({shared}) from-second)\n")
    metta.load(first)
    metta.load(second)
    answers = metta.run(f"!({shared})")[0]
    assert sorted(str(a) for a in answers) == ["from-first", "from-second"]

    first.write_text(f"(= ({shared}) from-first-again)\n")
    metta.load(first)

    answers = metta.run(f"!({shared})")[0]
    assert sorted(str(a) for a in answers) == ["from-first-again", "from-second"]


def test_a_reload_that_fails_leaves_the_previous_definitions_standing(metta, source):
    """The cycle this exists for is fix-and-reload, and a person in that
    cycle writes broken sources. A reload that raises must not also cost
    them the definitions that were working."""
    answer = fresh("survives")
    source.write_text(f"(= ({answer}) 1)\n")
    metta.load(source)

    source.write_text(f"(= ({answer}) 2)\n(= (unbalanced\n")
    with pytest.raises(petta.MettaSyntaxError):
        metta.load(source)
    assert metta.run(f"!(collapse ({answer}))") == [[petta.Expr([1])]]

    source.write_text(f"(= ({answer}) 3)\n")
    metta.load(source)
    assert metta.run(f"!(collapse ({answer}))") == [[petta.Expr([3])]]


def test_reloading_invalidates_a_memoized_answer(metta, source):
    """A reload is not retract-and-assert: everything derived from the
    definitions it replaces has to go with them. lib_memo caches by
    generation and hangs its invalidation on metta_on_function_removed/1,
    which the removal funnel fires."""
    answer = fresh("memoed")
    source.write_text(f"(= ({answer}) 1)\n!(memoize {answer})\n")
    metta.load(source)
    assert metta.run(f"!(collapse ({answer}))") == [[petta.Expr([1])]]
    assert metta.run(f"!(collapse ({answer}))") == [[petta.Expr([1])]]

    source.write_text(f"(= ({answer}) 2)\n!(memoize {answer})\n")
    metta.load(source)

    assert metta.run(f"!(collapse ({answer}))") == [[petta.Expr([2])]]


def test_reloading_invalidates_a_tabled_answer(metta, source):
    """lib_tabling abolishes its tables on the same hook."""
    answer = fresh("tabled")
    source.write_text(f"(= ({answer}) 1)\n!(table {answer})\n")
    metta.load(source)
    assert metta.run(f"!(collapse ({answer}))") == [[petta.Expr([1])]]

    source.write_text(f"(= ({answer}) 2)\n!(table {answer})\n")
    metta.load(source)

    assert metta.run(f"!(collapse ({answer}))") == [[petta.Expr([2])]]


def test_reloading_invalidates_a_specialization(metta, source):
    """The specializer's clones are written from the definitions being
    replaced, so a reload that left them would answer through the previous
    program while the space showed the new one."""
    bump, twice = fresh("bump"), fresh("twice")
    body = f"(= ({twice} $f $x) ($f ($f $x)))\n"
    source.write_text(f"(= ({bump} $n) (+ $n 1))\n" + body)
    metta.load(source)
    assert metta.run(f"!({twice} {bump} 1)") == [[3]]

    source.write_text(f"(= ({bump} $n) (+ $n 10))\n" + body)
    metta.load(source)

    assert metta.run(f"!({twice} {bump} 1)") == [[21]]


def test_a_live_view_follows_a_reload(scratch, source):
    """A LiveView subscribes to the space's own write events, and the
    withdrawal is a write, so the view is current without re-seeding."""
    source.write_text("(live-fact one)\n")
    with LiveView(scratch, S["live-fact"](V.x)) as view:
        scratch.load(source)
        assert sorted(str(a) for a in view) == ["(live-fact one)"]

        source.write_text("(live-fact two)\n")
        scratch.load(source)

        assert sorted(str(a) for a in view) == ["(live-fact two)"]


def test_a_reload_replaces_the_file_in_every_space_that_holds_it(metta, source):
    """A file's equations compile once into a shared module while its atoms
    are stored per space, so replacing one space's copy and leaving another
    would leave that other space listing definitions its module no longer
    answers."""
    fact = fresh("shared")
    source.write_text(f"({fact} first)\n")
    first, second = metta.new_space(), metta.new_space()
    first.load(source)
    metta.run(f'!(import! {second.space_name} "{source}")')
    assert len(second.query(S[fact](V.x))) == 1

    source.write_text(f"({fact} second)\n")
    first.load(source)

    assert [str(a) for a in first.atoms()] == [f"({fact} second)"]
    assert [str(a) for a in second.atoms()] == [f"({fact} second)"]
