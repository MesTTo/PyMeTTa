"""Purpose: emit scoped Prolog macros with indexed source-goal heads.

Guarantees: importing binding macros adds no inferences to expansion of
unrelated goals [tested: test_binding_macros_do_not_tax_unrelated_goals;
commit=WORKTREE].
"""

from collections.abc import Iterable


def scoped_goal_expansions(
    module: str, sentinel: str, rules: Iterable[tuple[str, str, str]]
) -> str:
    """Emit each input, replacement and body with its matching scoped hook."""
    rules = tuple(rules)
    clauses = [f"{sentinel}({goal}, {result})" + (f" :-\n{body}." if body else ".")
               for goal, result, body in rules]
    clauses.append(":- multifile system:goal_expansion/2.")
    # SWI's debug.pl indexes the hook by the input goal before policy runs.
    # https://github.com/SWI-Prolog/swipl-devel/blob/fc7ef84b949378b729052c3ade79c90ce5416abb/library/debug.pl#L424
    clauses.extend(f"""system:goal_expansion({goal}, Expanded) :-
    prolog_load_context(module, Module),
    Module \\== {module},
    predicate_property(Module:{sentinel}(_, _), imported_from({module})),
    {sentinel}({goal}, Expanded).""" for goal, _, _ in rules)
    return "\n\n".join(clauses) + "\n"
