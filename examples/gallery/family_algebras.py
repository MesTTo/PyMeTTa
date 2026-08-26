"""Purpose: run one family relation in every logical direction under every carrier.

Assumes: answer order is unspecified, so each shown bag is sorted without
  removing duplicates.
Guarantees:
  - all four ground/free direction combinations run under counting, tropical,
    provenance, ranking, and probability carriers
    [tested: test_a_gallery_program_runs; commit=4b6f6bf075e80f794ebcb46a5748dba46dcd3522]
Owns resources: one named family space; drop() releases it after all carrier
  queries complete, while process exit releases it after a failed claim.
"""

from _common import claim, doctest, done

from metta import MeTTa, S, V, counting, match, prob, prov, ranked, tropical
from metta.atoms import substitute


def family_ancestor(ancestor, descendant):
    """Relate each ancestor to every descendant below it."""
    yield match((S.Parent, ancestor, descendant), True)  # noqa: FBT003 -- the staged result is the MeTTa truth atom
    yield family_ancestor(match((S.Parent, ancestor, V.middle), V.middle), descendant)


def next_generation(generation: int) -> int:
    """Advance one generation.

    >>> !(next-generation 2)
    [3]
    """
    return generation + 1


def _under(space, pattern, carrier):
    """Render one algebra query as a deterministic, multiplicity-preserving bag."""
    answers = space.answers(pattern, under=carrier)
    if carrier is counting:
        return [S.Count(answers.one())]
    tagged = list(answers)
    if pattern.vars:
        rows = list(answers.rows)
        rendered = [
            S.Answer(substitute(pattern, row.asdict()), answer.annotation)
            for answer, row in zip(tagged, rows, strict=True)
        ]
    else:
        rendered = [S.Answer(pattern, answer.annotation) for answer in tagged]
    return [S.Answers(*sorted(rendered))]


family = MeTTa().space("&gallery-family")
family.add(
    S.Parent(S.Tom, S.Bob),
    S.Parent(S.Pam, S.Bob),
    S.Parent(S.Bob, S.Ann),
    S.Parent(S.Bob, S.Pat),
    S.Parent(S.Pat, S.Jim),
)
ancestor = family.define(family_ancestor)
generation = family.define(next_generation)
doctest("family relation doctest", generation)

claim(
    "counting: ground to ground",
    S.family_ancestor(S.Tom, S.Jim),
    lambda term: _under(family, term, counting),
)
# -> (family-ancestor Tom Jim)
# => (Count 1)
claim(
    "counting: free ancestor",
    S.family_ancestor(V.ancestor, S.Jim),
    lambda term: _under(family, term, counting),
)
# -> (family-ancestor $ancestor Jim)
# => (Count 4)
claim(
    "counting: free descendant",
    S.family_ancestor(S.Tom, V.descendant),
    lambda term: _under(family, term, counting),
)
# -> (family-ancestor Tom $descendant)
# => (Count 4)
claim(
    "counting: both free",
    S.family_ancestor(V.ancestor, V.descendant),
    lambda term: _under(family, term, counting),
)
# -> (family-ancestor $ancestor $descendant)
# => (Count 12)

claim(
    "tropical: ground to ground",
    S.family_ancestor(S.Tom, S.Jim),
    lambda term: _under(family, term, tropical),
)
# -> (family-ancestor Tom Jim)
# => (Answers (Answer (family-ancestor Tom Jim) 0))
claim(
    "tropical: free ancestor",
    S.family_ancestor(V.ancestor, S.Jim),
    lambda term: _under(family, term, tropical),
)
# -> (family-ancestor $ancestor Jim)
# => (Answers (Answer (family-ancestor Bob Jim) 0) (Answer (family-ancestor Pam Jim) 0) (Answer (family-ancestor Pat Jim) 0) (Answer (family-ancestor Tom Jim) 0))
claim(
    "tropical: free descendant",
    S.family_ancestor(S.Tom, V.descendant),
    lambda term: _under(family, term, tropical),
)
# -> (family-ancestor Tom $descendant)
# => (Answers (Answer (family-ancestor Tom Ann) 0) (Answer (family-ancestor Tom Bob) 0) (Answer (family-ancestor Tom Jim) 0) (Answer (family-ancestor Tom Pat) 0))
claim(
    "tropical: both free",
    S.family_ancestor(V.ancestor, V.descendant),
    lambda term: _under(family, term, tropical),
)
# -> (family-ancestor $ancestor $descendant)
# => (Answers (Answer (family-ancestor Bob Ann) 0) (Answer (family-ancestor Bob Jim) 0) (Answer (family-ancestor Bob Pat) 0) (Answer (family-ancestor Pam Ann) 0) (Answer (family-ancestor Pam Bob) 0) (Answer (family-ancestor Pam Jim) 0) (Answer (family-ancestor Pam Pat) 0) (Answer (family-ancestor Pat Jim) 0) (Answer (family-ancestor Tom Ann) 0) (Answer (family-ancestor Tom Bob) 0) (Answer (family-ancestor Tom Jim) 0) (Answer (family-ancestor Tom Pat) 0))

claim(
    "provenance: ground to ground",
    S.family_ancestor(S.Tom, S.Jim),
    lambda term: _under(family, term, prov),
)
# -> (family-ancestor Tom Jim)
# => (Answers (Answer (family-ancestor Tom Jim) one))
claim(
    "provenance: free ancestor",
    S.family_ancestor(V.ancestor, S.Jim),
    lambda term: _under(family, term, prov),
)
# -> (family-ancestor $ancestor Jim)
# => (Answers (Answer (family-ancestor Bob Jim) one) (Answer (family-ancestor Pam Jim) one) (Answer (family-ancestor Pat Jim) one) (Answer (family-ancestor Tom Jim) one))
claim(
    "provenance: free descendant",
    S.family_ancestor(S.Tom, V.descendant),
    lambda term: _under(family, term, prov),
)
# -> (family-ancestor Tom $descendant)
# => (Answers (Answer (family-ancestor Tom Ann) one) (Answer (family-ancestor Tom Bob) one) (Answer (family-ancestor Tom Jim) one) (Answer (family-ancestor Tom Pat) one))
claim(
    "provenance: both free",
    S.family_ancestor(V.ancestor, V.descendant),
    lambda term: _under(family, term, prov),
)
# -> (family-ancestor $ancestor $descendant)
# => (Answers (Answer (family-ancestor Bob Ann) one) (Answer (family-ancestor Bob Jim) one) (Answer (family-ancestor Bob Pat) one) (Answer (family-ancestor Pam Ann) one) (Answer (family-ancestor Pam Bob) one) (Answer (family-ancestor Pam Jim) one) (Answer (family-ancestor Pam Pat) one) (Answer (family-ancestor Pat Jim) one) (Answer (family-ancestor Tom Ann) one) (Answer (family-ancestor Tom Bob) one) (Answer (family-ancestor Tom Jim) one) (Answer (family-ancestor Tom Pat) one))

claim(
    "ranking: ground to ground",
    S.family_ancestor(S.Tom, S.Jim),
    lambda term: _under(family, term, ranked),
)
# -> (family-ancestor Tom Jim)
# => (Answers (Answer (family-ancestor Tom Jim) 1))
claim(
    "ranking: free ancestor",
    S.family_ancestor(V.ancestor, S.Jim),
    lambda term: _under(family, term, ranked),
)
# -> (family-ancestor $ancestor Jim)
# => (Answers (Answer (family-ancestor Bob Jim) 1) (Answer (family-ancestor Pam Jim) 1) (Answer (family-ancestor Pat Jim) 1) (Answer (family-ancestor Tom Jim) 1))
claim(
    "ranking: free descendant",
    S.family_ancestor(S.Tom, V.descendant),
    lambda term: _under(family, term, ranked),
)
# -> (family-ancestor Tom $descendant)
# => (Answers (Answer (family-ancestor Tom Ann) 1) (Answer (family-ancestor Tom Bob) 1) (Answer (family-ancestor Tom Jim) 1) (Answer (family-ancestor Tom Pat) 1))
claim(
    "ranking: both free",
    S.family_ancestor(V.ancestor, V.descendant),
    lambda term: _under(family, term, ranked),
)
# -> (family-ancestor $ancestor $descendant)
# => (Answers (Answer (family-ancestor Bob Ann) 1) (Answer (family-ancestor Bob Jim) 1) (Answer (family-ancestor Bob Pat) 1) (Answer (family-ancestor Pam Ann) 1) (Answer (family-ancestor Pam Bob) 1) (Answer (family-ancestor Pam Jim) 1) (Answer (family-ancestor Pam Pat) 1) (Answer (family-ancestor Pat Jim) 1) (Answer (family-ancestor Tom Ann) 1) (Answer (family-ancestor Tom Bob) 1) (Answer (family-ancestor Tom Jim) 1) (Answer (family-ancestor Tom Pat) 1))

claim(
    "probability: ground to ground",
    S.family_ancestor(S.Tom, S.Jim),
    lambda term: _under(family, term, prob),
)
# -> (family-ancestor Tom Jim)
# => (Answers (Answer (family-ancestor Tom Jim) 1))
claim(
    "probability: free ancestor",
    S.family_ancestor(V.ancestor, S.Jim),
    lambda term: _under(family, term, prob),
)
# -> (family-ancestor $ancestor Jim)
# => (Answers (Answer (family-ancestor Bob Jim) 1) (Answer (family-ancestor Pam Jim) 1) (Answer (family-ancestor Pat Jim) 1) (Answer (family-ancestor Tom Jim) 1))
claim(
    "probability: free descendant",
    S.family_ancestor(S.Tom, V.descendant),
    lambda term: _under(family, term, prob),
)
# -> (family-ancestor Tom $descendant)
# => (Answers (Answer (family-ancestor Tom Ann) 1) (Answer (family-ancestor Tom Bob) 1) (Answer (family-ancestor Tom Jim) 1) (Answer (family-ancestor Tom Pat) 1))
claim(
    "probability: both free",
    S.family_ancestor(V.ancestor, V.descendant),
    lambda term: _under(family, term, prob),
)
# -> (family-ancestor $ancestor $descendant)
# => (Answers (Answer (family-ancestor Bob Ann) 1) (Answer (family-ancestor Bob Jim) 1) (Answer (family-ancestor Bob Pat) 1) (Answer (family-ancestor Pam Ann) 1) (Answer (family-ancestor Pam Bob) 1) (Answer (family-ancestor Pam Jim) 1) (Answer (family-ancestor Pam Pat) 1) (Answer (family-ancestor Pat Jim) 1) (Answer (family-ancestor Tom Ann) 1) (Answer (family-ancestor Tom Bob) 1) (Answer (family-ancestor Tom Jim) 1) (Answer (family-ancestor Tom Pat) 1))

family.drop()
done("family_algebras")
