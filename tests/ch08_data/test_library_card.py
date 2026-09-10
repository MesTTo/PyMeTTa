"""Purpose: pin the library card.

It is one query over a library's own sources, rendered, with what the live
engine says about each head beside it.

A card is a model card for a `lib_*`, and the two halves it joins are held
apart here on purpose. The static half must never load or run the library, so
a library whose backend this build has not got still describes itself and
asking for a card cannot register a head. The live half must be the ENGINE's
answers, so a card, `(explain ...)` and a bound function's docstring cannot
say different things about the same head.

Guarantees:
  - a companion README supplies escaped prose in every rendering and lib_he
    names its deliberate semantic differences [tested:
    test_a_companion_readme_supplies_the_summary_in_every_renderer,
    test_the_lib_he_card_names_its_shadowing_and_semantic_differences; commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427]
  - the nine heads lib_memo publishes through runnable registration forms are
    on its card, which the static reading alone could not see
    [tested: test_a_card_lists_the_heads_a_registration_form_publishes]
  - a card is built without running the library: a planted library whose
    runnable would RAISE is read to the end and registers nothing
    [tested: test_a_card_reads_a_library_without_running_it]
  - the effect class and cost class on a card are the engine's own
    resolutions, the same pair the head's own docstring prints
    [tested: test_a_card_carries_the_engines_own_effect_and_cost_answers]
  - the digest is the sha256 of every source file, sorted and joined, which
    anyone can recompute [tested:
    test_the_digest_composes_the_sha256_of_every_source]
  - a name outside the roster refuses with the roster, and a library with two
    MeTTa sources refuses with both
    [tested: test_a_card_for_a_name_outside_the_roster_refuses_with_it,
    test_a_library_with_two_metta_sources_is_refused]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import hashlib
from pathlib import Path

import pytest

from metta import library
from metta._errors.errors import MettaError

_MEMO_HEADS = (
    "memoize",
    "memoize-exact",
    "config-memoize",
    "get-memoize-config",
    "clear-memoize",
    "invalidate-memoize",
    "is-memoized",
    "get-memoize-stats",
    "clear-memoize-stats",
)


def _plant(root: Path, name: str, metta: str = "", prolog: str | None = None) -> Path:
    """One library under a fresh engine tree, for the refusals and the version."""
    directory = root / "lib" / name
    directory.mkdir(parents=True, exist_ok=True)
    if metta:
        (directory / f"{name}.metta").write_text(metta, encoding="utf-8")
    if prolog is not None:
        (directory / f"{name}.pl").write_text(prolog, encoding="utf-8")
    return directory


def test_a_card_lists_the_heads_a_registration_form_publishes():
    """lib_memo publishes nine heads through `!(import_prolog_function ...)`.

    Its MeTTa half declares nothing and defines nothing, so a reader that saw
    only `(: ...)` and `(= ...)` rows reported the library as empty while all
    nine were callable. The engine says which heads a registration form
    claims, so the card and the reference page both see them.
    """
    card = library.card("lib_memo")

    assert tuple(head.name for head in card.heads) == _MEMO_HEADS
    assert all(head.registered for head in card.heads)
    assert all(head.origin is not None for head in card.heads)


def test_a_card_reads_a_library_without_running_it(tmp_path, metta):
    """A planted library whose runnable would RAISE is read to the end.

    `!(import_prolog_function no-predicate-of-this-name)` refuses when it
    runs, because no Prolog predicate answers to that name; the card names it
    anyway, and the engine's own roster of callable names never gains it.
    Documentation that runs what it documents is not documentation.
    """
    _plant(
        tmp_path,
        "lib_planted",
        metta="!(import_prolog_function no-predicate-of-this-name)\n",
    )

    card = library.card("lib_planted", root=tmp_path)

    assert [head.name for head in card.heads] == ["no-predicate-of-this-name"]
    assert "no-predicate-of-this-name" not in metta.builtins()


def test_a_card_carries_the_engines_own_effect_and_cost_answers(metta):
    """`car-atom` is pureStructural and linear in the length of `$n`.

    The same class its own docstring prints, because both read the engine's
    one resolution rather than the catalog rows underneath it.
    """
    card = library.card("lib_builtin_types")
    heads = {head.name: head for head in card.heads}

    assert heads["car-atom"].effect == "pureStructural"
    assert heads["car-atom"].cost is not None
    assert heads["car-atom"].cost.cost_class == "linear"
    assert heads["car-atom"].cost.measure == "length"
    assert card.effects["car-atom"] == "pureStructural"
    assert "cost: linear in $n (length)" in metta.fn["car-atom"].__doc__
    assert str(heads["car-atom"].cost) == "car-atom: linear in $n (length)"


def test_a_head_the_engine_has_not_classified_says_so():
    """lib_memo's registered heads carry no effect until something declares one.

    A Prolog predicate published as a head is not a reviewed builtin, so the
    engine composes no class for it and the card says None rather than
    inventing the safe-looking answer.
    """
    card = library.card("lib_memo")

    assert all(head.effect is None for head in card.heads)
    assert card.effects == {}
    assert card.costs == ()


def test_the_digest_composes_the_sha256_of_every_source():
    """The digest is each file's sha256, listed under its path and hashed.

    Recomputed here with `hashlib` alone, which is also the claim that the
    engine's own `metta_source_digest` and a plain sha256 of the decoded text
    answer the same 64 characters.
    """
    card = library.card("lib_memo")
    listing = sorted(
        f"{path}\t"
        f"{hashlib.sha256(path.read_text(encoding='utf-8').encode('utf-8')).hexdigest()}"
        for path in card.files
    )
    expected = hashlib.sha256("\n".join(listing).encode("utf-8")).hexdigest()

    assert card.digest == expected
    assert library.digest("lib_memo") == expected
    assert len(card.files) == 2


def test_a_card_for_a_name_outside_the_roster_refuses_with_it():
    """A name that is not a shipped library is refused, naming the roster."""
    with pytest.raises(MettaError, match="is not a shipped library") as raised:
        library.card("lib_not_here")

    assert "lib_memo" in str(raised.value)
    assert "lib_he" in str(raised.value)


def test_a_library_with_two_metta_sources_is_refused(tmp_path):
    """`(library lib_x)` resolves to one file, so two are an ambiguity."""
    _plant(tmp_path, "lib_planted", metta="(: a (-> Number))\n")
    second = tmp_path / "lib" / "elsewhere"
    second.mkdir(parents=True)
    (second / "lib_planted.metta").write_text("(: b (-> Number))\n", encoding="utf-8")

    with pytest.raises(MettaError, match="more than one MeTTa source"):
        library.card("lib_planted", root=tmp_path)


def test_a_card_names_what_the_library_needs_from_the_platform():
    """A `:- metta_requires(...)` declaration reaches the card as a need."""
    assert library.card("lib_regex").needs == ("regex",)
    assert library.card("lib_thread").needs == ("concurrency",)
    assert library.card("lib_memo").needs == ()


def test_a_declared_version_reaches_the_card(tmp_path):
    """A library declaring its own extension version says so; others say the engine's."""
    _plant(
        tmp_path,
        "lib_planted",
        metta="(: planted (-> Number Number))\n",
        prolog=":- metta_extension(planted_ext, [version('2.1.0')]).\n",
    )

    assert library.card("lib_planted", root=tmp_path).since == "2.1.0"
    assert library.card("lib_memo").since == library.card("lib_he").since


def test_a_card_names_the_examples_that_import_the_library():
    """Every example on a card really imports the library, read from its forms."""
    card = library.card("lib_memo")

    assert card.examples
    for path in card.examples:
        assert "(library lib_memo)" in Path(path).read_text(encoding="utf-8")


def test_a_card_documents_what_the_library_documents():
    """A documented head carries the same prose `help()` prints for it."""
    card = library.card("lib_file")
    documented = {head.name: head.doc for head in card.documented}

    assert len(card.documented) == 18
    assert "file-exists" in documented
    assert "True when a regular file exists at the path" in documented["file-exists"]
    assert documented["file-exists"].startswith("file-exists: ")


def test_a_card_renders_as_text_a_table_and_html():
    """The three renderings are the same card, and the HTML escapes its cells."""
    pytest.importorskip("rich")
    card = library.card("lib_builtin_types")
    text = str(card)
    rendered = card._repr_html_()

    assert text.startswith("lib_builtin_types ")
    assert f"digest sha256:{card.digest}" in text
    assert "car-atom" in text
    assert "&gt;" in rendered
    assert rendered.startswith("<table") and rendered.endswith("</table>")
    assert card.__rich__().row_count == len(card.heads)


def test_a_needed_capability_this_build_has_not_got_is_marked_absent(monkeypatch):
    """A card's text says which of its needs are missing HERE, asked when rendered."""
    card = library.card("lib_regex")
    monkeypatch.setattr(type(card), "_absent", lambda _self: frozenset({"regex"}))

    assert "needs: regex (absent here)" in str(card)


def test_the_summary_is_the_librarys_own_opening_prose():
    """A library's card says what its own header says, or nothing at all."""
    assert library.card("lib_memo").doc == (
        "expose the resident automatic and explicit memoization controls."
    )
    assert library.card("lib_vector").doc is None


def test_a_companion_readme_supplies_the_summary_in_every_renderer(tmp_path):
    """A library caveat remains literal in text, Rich and HTML output."""
    directory = _plant(tmp_path, "lib_planted", metta="; Source prose.\n(: planted Type)\n")
    (directory / "README.md").write_text(
        "# Library\n\nA caveat with <markup>\nand [literal] brackets.\n\nLater paragraph.\n",
        encoding="utf-8",
    )
    card = library.card("lib_planted", root=tmp_path)
    assert card.doc == "A caveat with <markup> and [literal] brackets."
    assert card.doc in str(card)
    assert "A caveat with &lt;markup&gt; and [literal] brackets." in card._repr_html_()
    assert card.doc in card.__rich__().caption.plain


def test_the_lib_he_card_names_its_shadowing_and_semantic_differences():
    """The card distinguishes upstream assertions and add-reduct results."""
    card = library.card("lib_he")
    assert "shadows the prelude in the receiving space" in card.doc
    assert "engine prelude compares answer bags" in card.doc
    assert "returns the add-atom Boolean" in card.doc
    assert "returns that atom" in card.doc


def test_rows_are_the_query_the_reference_page_renders():
    """`rows()` is the one query; the card is one renderer over it."""
    rows = library.rows("lib_file")
    card = library.card("lib_file")

    assert [row.name for row in rows] == [head.name for head in card.heads]
    assert [row.documentation is not None for row in rows] == [
        head.doc is not None for head in card.heads
    ]
