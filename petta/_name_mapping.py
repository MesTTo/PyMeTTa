"""Purpose: define the one catalog-aware Python-to-MeTTa name map.
Guarantees:
  - exact catalog names win before the underscore-to-hyphen and trailing-bang
    candidates [tested: test_bare_callees_ask_exact_then_mapped,
    test_banged_catalog_names_take_the_mechanical_fallback; commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
  - generated aliases are identifiers, non-keywords, NFKC-stable, and unique
    [tested: test_the_fn_namespace_is_generated; commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
  - Symbol attribute doors consult Python's operator word vocabulary before
    the mechanical name map, while composite operators refuse with their
    explicit images [tested: test_operator_words_precede_the_mechanical_name_map;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import keyword
from collections.abc import Callable, Iterable
from typing import Final

# Python's operator module owns these public words. ``neg`` and ``floordiv``
# are intentionally absent because each needs more than one engine head.
# [source: https://docs.python.org/3.14/library/operator.html; commit=WORKTREE]
OPERATOR_WORDS: Final[dict[str, str]] = {
    "eq": "==",
    "ne": "!=",
    "lt": "<",
    "le": "<=",
    "gt": ">",
    "ge": ">=",
    "add": "+",
    "sub": "-",
    "mul": "*",
    "mod": "%",
    "pow": "pow-math",
    "truediv": "/",
}

_COMPOSITE_OPERATOR_IMAGES: Final[dict[str, str]] = {
    "neg": "(- 0 x)",
    "floordiv": "floor-math over /",
}


def operator_attribute_target(identifier: str) -> str | None:
    """Resolve one operator word, refusing words without one target head."""
    image = _COMPOSITE_OPERATOR_IMAGES.get(identifier)
    if image is not None:
        msg = (
            f"operator word {identifier!r} has no single engine head; "
            f"its image is {image}"
        )
        raise AttributeError(msg)
    return OPERATOR_WORDS.get(identifier)


def attribute_name(identifier: str) -> str:
    """Map a Python factory attribute to MeTTa's hyphenated spelling."""
    if identifier == "_":
        # V._ is MeTTa's anonymous variable, a grammar role rather than a
        # word that participates in the factory's transliteration.
        return identifier
    return identifier.replace("_", "-")


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


def generated_aliases(names: Iterable[str]) -> dict[str, str]:
    """Return the collision-free attributes a closed generated namespace exposes.

    Python normalizes identifiers to NFKC while parsing. Omitting unstable
    spellings keeps the generated attribute bound to the text a reader sees;
    the exact bracket door remains available for every omitted catalog name.
    [source: https://docs.python.org/3/reference/lexical_analysis.html#identifiers;
    commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
    """
    catalog = set(names)
    candidates: dict[str, list[str]] = {}
    for target in catalog:
        source = target.removesuffix("!")
        if target.endswith("!") and source in catalog:
            # The unbanged target wins before rung 4's bang fallback.
            continue
        alias = source.replace("-", "_")
        safe = (
            alias.isidentifier(),
            not keyword.iskeyword(alias),
            not alias.startswith("_"),
            alias == alias.lower(),
            alias.isascii(),
            attribute_name(alias) == source,
        )
        if not all(safe):
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
    aliases.update(
        (word, target)
        for word, target in OPERATOR_WORDS.items()
        if target in catalog
    )
    return dict(sorted(aliases.items()))
