"""Purpose: map Python name roles to their native spellings.
Guarantees:
  - Python binding labels preserve identity without changing native anonymous
    variables [tested: test_python_underscore_bindings_retain_their_values,
    test_native_underscore_patterns_remain_anonymous; commit=69d1511c099eb6aa80c38d898da49487c42470f0]
  - exact catalog names win before the underscore-to-hyphen and trailing-bang
    candidates [tested: test_bare_callees_ask_exact_then_mapped,
    test_banged_catalog_names_take_the_mechanical_fallback; commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
  - generated aliases are identifiers, non-keywords, NFKC-stable, and unique
    [tested: test_the_fn_namespace_is_generated; commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
  - Symbol attribute doors consult Python's operator word vocabulary before
    the mechanical name map, and ``neg`` builds its canonical composite image
    through the same generated roster [tested:
    test_operator_words_precede_the_mechanical_name_map;
    commit=f866cc992295171a9a9e97417514f31597181e7b]
  - ``python_name`` is ``attribute_name``'s inverse and lives beside it, so
    the stub renderer and the import hook's module answer one rule for one
    head and a name Python cannot spell is refused by both [tested:
    test_a_head_python_cannot_spell_is_named_not_dropped,
    test_a_head_python_cannot_spell_keeps_its_exact_name; commit=d7ab3cb20fe2353872139ecb36710f7e880c1451]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import keyword
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Final

import metta._atoms.operators as _lowerings


@dataclass(frozen=True)
class OperatorRecipe:
    """A Python operator word whose MeTTa image has more than one child."""

    word: str
    lowering: _lowerings.OperatorLowering

    @property
    def arity(self) -> int:
        """The operand count supplied by the source operation."""
        return self.lowering.arity

    @property
    def image(self) -> str:
        """Display the canonical template with visible operand positions."""
        from metta._atoms.factories import (  # noqa: PLC0415 -- resolve the atom factory after its name grammar initializes
            Symbol,
        )

        return str(self(*(Symbol(f"x{index + 1}") for index in range(self.arity))))

    def __call__(self, *args: object, **kwargs: object):
        """Build the canonical term while retaining a normal callable door."""
        if kwargs:
            names = ", ".join(sorted(kwargs))
            msg = f"operator word {self.word!r} takes no keyword arguments: {names}"
            raise TypeError(msg)
        if len(args) != self.arity:
            msg = f"operator word {self.word!r} takes exactly {self.arity} operand(s)"
            raise TypeError(msg)
        from metta._atoms.model import (  # noqa: PLC0415 -- the shared atom image emitter reads the name grammar while initializing
            _apply_operator_lowering,
            encode,
        )

        return _apply_operator_lowering(self.lowering, encode(args[0]), *args[1:])

    def __repr__(self) -> str:
        return f"<operator word {self.word}: {self.image}>"


# Python's operator module owns these public words, and WHICH words is the one
# operator table's `word` column: a row marked there opens `S.<selector>` onto
# that row's own MeTTa head, so the head is spelled once. `neg`'s settled image
# is composite, which is what its policy row carries. A composite row without
# a word door is refused with that row's canonical image [source:
# extensions/python/metta/_atoms/operators.py:OPERATOR_LOWERINGS;
# commit=f866cc992295171a9a9e97417514f31597181e7b].
OPERATOR_WORDS: Final[dict[str, str | OperatorRecipe]] = {
    _lowerings.selector(entry): (
        OperatorRecipe(_lowerings.selector(entry), entry)
        if entry.kind == "template" else entry.word_head or str(entry.form)
    )
    for entry in _lowerings.OPERATOR_LOWERINGS
    if entry.word
}

_COMPOSITE_OPERATOR_IMAGES: Final[dict[str, OperatorRecipe]] = {
    _lowerings.selector(entry): OperatorRecipe(_lowerings.selector(entry), entry)
    for entry in _lowerings.OPERATOR_LOWERINGS if entry.kind == "template" and not entry.word
}


def operator_attribute_target(identifier: str) -> str | OperatorRecipe | None:
    """Resolve one operator word, refusing unsettled composite spellings."""
    image = _COMPOSITE_OPERATOR_IMAGES.get(identifier)
    if image is not None:
        msg = (
            f"operator word {identifier!r} has no single engine head; "
            f"its image is {image.image}"
        )
        #No obj: the refusal names the image rather than a near miss, so there
        #is nothing for the interpreter to suggest and no receiver to draw one
        #from. The name is set because it is what was asked for.
        raise AttributeError(msg, name=identifier)
    return OPERATOR_WORDS.get(identifier)


def binding_name(identifier: str) -> str:
    """Keep a Python binder distinct from the native anonymous variable.

    Python's `_` is an ordinary identifier outside a case pattern. Its native
    name must therefore share occurrences, unlike `$_`. The hyphen keeps this
    escape outside Python's identifier grammar and the existing SSA allocator
    handles subsequent bindings. Explicit Variable atoms never use this map.
    [source: https://docs.python.org/3.14/reference/lexical_analysis.html#reserved-classes-of-identifiers;
    extensions/python/metta/_binding/wire.pl:metta_py_decode_shared_tagged/5;
    commit=69d1511c099eb6aa80c38d898da49487c42470f0]
    """
    return "_-" if identifier == "_" else identifier


def attribute_name(identifier: str) -> str:
    """Map a Python factory attribute to MeTTa's hyphenated spelling."""
    if identifier == "_":
        # V._ is MeTTa's anonymous variable, a grammar role rather than a
        # word that participates in the factory's transliteration.
        return identifier
    if identifier.endswith("_") and not identifier.endswith("__"):
        # PEP 8's keyword escape, which the naming ladder ranks ABOVE the
        # mechanical map: `S.not_` is how Python spells a head the grammar
        # reserves, so it reaches `not`. Mapping it instead would answer
        # `not-`, and no head in this tree ends in a hyphen, so that spelling
        # can never match anything and nothing would say so. The exact form
        # stays reachable through the bracket door for a head that really
        # does end in an underscore.
        identifier = identifier[:-1]
    return identifier.replace("_", "-")


def python_name(head: str) -> str | None:
    """The Python spelling of a MeTTa head, or None when there is none.

    Python's convention is snake_case, so MeTTa's hyphens become underscores
    and the map inverts exactly: `attribute_name` has to send the candidate
    back to the head it came from, which is what keeps a program that declares
    both `to-list` and `to_list` from silently answering one entry for two
    heads. A head Python reserves takes PEP 8's own escape, `not` reaching
    `not_`, because that spelling round-trips too.

    This is the inverse of `attribute_name`, which is why it lives beside it:
    the stub renderer and the import hook's module both need the same answer
    for the same head, and a second copy of the rule could differ from this
    one without anything saying so.
    """
    candidate = head.replace("-", "_")
    if keyword.iskeyword(candidate):
        candidate = f"{candidate}_"
    if not candidate.isidentifier() or attribute_name(candidate) != head:
        return None
    return candidate


def resolve_known_name(
    identifier: str,
    known: Callable[[str], bool],
    *,
    allow_mapped: bool = True,
    allow_bang: bool = True,
) -> str | None:
    """Ask for exact, mechanical, then unambiguous side-effect spelling."""
    if known(identifier):
        return identifier
    mapped = attribute_name(identifier)
    if allow_mapped and mapped != identifier and known(mapped):
        return mapped
    if allow_bang:
        banged = f"{mapped if allow_mapped else identifier}!"
        if known(banged):
            return banged
    return None


def generated_aliases(
    names: Iterable[str], *, operators: bool = True
) -> dict[str, str]:
    """Return the collision-free attributes a closed generated namespace exposes.

    Python normalizes identifiers to NFKC while parsing. Omitting unstable
    spellings keeps the generated attribute bound to the text a reader sees;
    the exact bracket door remains available for every omitted catalog name.
    [source: https://docs.python.org/3/reference/lexical_analysis.html#identifiers;
    commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]

    `operators` says whether Python's own `operator` module words map into this
    namespace. They do for a namespace over the ENGINE's catalog, where `add`
    naming `+` is the whole point. They do not for a namespace over ONE
    library's own heads: the words would name heads that library never
    declares, and a library that declares `add` itself would find `+` answering
    in its place.
    """
    catalog = set(names)
    candidates: dict[str, list[str]] = {}
    for target in catalog:
        source = target.removesuffix("!")
        if target.endswith("!") and source in catalog:
            # The unbanged target wins before rung 4's bang fallback.
            continue
        # `python_name` is the one rule, so a closed namespace accepts exactly
        # the spellings the open factory does. It used to be restated here as
        # five conditions, and two of them were narrower than the rule: a head
        # Python reserves was dropped instead of taking PEP 8's trailing
        # underscore, and a head already in CamelCase was dropped for not being
        # lowercase. `S.not_` and `S.assertEqual` both answered while `fn.not_`
        # and `fn.assertEqual` refused, over seven keyword heads and fifteen
        # CamelCase ones in the shipped catalog [measured 2026-09-08].
        alias = python_name(source)
        if alias is None or alias.startswith("_") or not alias.isascii():
            continue
        candidates.setdefault(alias, []).append(target)

    collisions = {
        alias: sorted(set(targets))
        for alias, targets in candidates.items()
        if len(set(targets)) != 1
    }
    if collisions:
        details = ", ".join(
            f"{alias} <- {targets!r}" for alias, targets in sorted(collisions.items())
        )
        msg = f"catalog names have ambiguous Python aliases: {details}"
        raise ValueError(msg)
    aliases = {alias: targets[0] for alias, targets in sorted(candidates.items())}
    if operators:
        aliases.update(
            (word, word if isinstance(target, OperatorRecipe) else target)
            for word, target in OPERATOR_WORDS.items()
            if isinstance(target, OperatorRecipe) or target in catalog
        )
    return dict(sorted(aliases.items()))
