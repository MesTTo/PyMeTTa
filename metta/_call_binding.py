"""Purpose: bind Python call-site keywords to a known positional MeTTa signature.
Guarantees:
  - known parameter names are validated with Python's Signature.bind and
    returned in declaration order [tested:
    test_known_call_site_keywords_bind_to_positional_metta_arguments;
    commit=26d052a6179bc0e0a536b7d585e79d6beef266a2]
  - a head with no known signature refuses keywords with an actionable
    positional spelling [tested:
    test_unknown_symbol_keywords_refuse_with_the_positional_remedy;
    commit=26d052a6179bc0e0a536b7d585e79d6beef266a2]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import inspect
from collections.abc import Mapping, Sequence
from typing import Any


def bind_positional_call(
    name: str,
    parameters: Sequence[str],
    args: Sequence[Any],
    kwargs: Mapping[str, Any],
) -> tuple[Any, ...]:
    """Return one known call in the positional order MeTTa applications carry.

    ``Signature.bind`` is the standard Python mechanism for detecting missing,
    duplicate, and unexpected arguments; ``BoundArguments.args`` then exposes
    every positional-or-keyword value in declaration order. [source:
    https://docs.python.org/3.13/library/inspect.html#inspect.Signature.bind;
    commit=26d052a6179bc0e0a536b7d585e79d6beef266a2]
    """
    signature = inspect.Signature(
        tuple(
            inspect.Parameter(parameter, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            for parameter in parameters
        )
    )
    try:
        bound = signature.bind(*args, **kwargs)
    except TypeError as error:
        declared = ", ".join(parameters)
        remedy = ", ".join(f"<{parameter}>" for parameter in parameters)
        msg = (
            f"{name} has positional signature ({declared}); {error}. "
            f"Write {name}({remedy}) in that order."
        )
        raise TypeError(msg) from error
    return bound.args


def refuse_unknown_keywords(name: str, keywords: Sequence[str]) -> TypeError:
    """Build the refusal for a keyword-bearing head with no parameter names."""
    written = ", ".join(f"<{keyword}>" for keyword in keywords)
    plural = "arguments" if len(keywords) != 1 else "argument"
    return TypeError(
        f"{name} has no known signature, so its keyword {plural} cannot be "
        f"placed in a positional MeTTa application. Write {name}({written}) "
        "positionally in the target's declared order."
    )
