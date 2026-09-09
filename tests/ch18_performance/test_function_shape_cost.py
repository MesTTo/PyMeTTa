"""Purpose: keep the twin-arity check's index question off SWI's autoload search.

Declaring a Python twin of a Prolog predicate asks the engine for the
function's shape, and that walks the engine's name-wide `arity/2` register
asking `predicate_property(Module:Head, indexed(_))` for each arity. Most of
those pairs the reported module does not have, and `indexed/1` is one of the
properties SWI answers by running its undefined-procedure trap, which searches
the whole autoload library index before raising the existence error the caller
discards.

The lane lives here rather than in `tests/prolog/suites/host/shim.plt`, whose
documented load contract is engine-free: without the engine the asking module
carries almost no autoload declarations and the same miss costs 58 inferences
instead of 1,030, so a ratio asserted there cannot tell the two spellings apart
[measured 2026-09-06: engine-free 22 present against 58 missing, engine-loaded
8 against 1,030; commit=693b1bdb6ed06cd0ba01e901a8a6d774bc733d19].

Guarantees:
  - a name the module does not have is priced like one it does
    [tested: test_asking_the_shape_of_an_absent_name_costs_what_a_present_one_costs].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

# Every Prolog intermediate is _-prefixed because janus converts each NAMED
# variable of a query back to Python and an unbound one raises rather than
# arriving absent. Present and Missing are the two the test reads.
#
# SWI builds a JIT index on demand, so the plant is called as well as
# asserted; 400 clauses is what makes an index worth building.
_COST = r"""
( forall(between(1, 400, _I),
         ( atom_concat(shape_cost_key_, _I, _K),
           assertz(user:shape_cost_planted(_K, _I)) )),
  forall(between(1, 400, _I),
         ( atom_concat(shape_cost_key_, _I, _K),
           once(user:shape_cost_planted(_K, _)) )),
  statistics(inferences, _Before1),
  forall(between(1, 500, _),
         ( metta_py_index_quality(user, shape_cost_planted, 2, _, _)
         -> true ; true )),
  statistics(inferences, _After1),
  Present is (_After1 - _Before1 - 1500) // 500,
  statistics(inferences, _Before2),
  forall(between(1, 500, _),
         ( metta_py_index_quality(user, 'shape-cost-absent-name', 2, _, _)
         -> true ; true )),
  statistics(inferences, _After2),
  Missing is (_After2 - _Before2 - 1500) // 500,
  ( metta_py_index_quality(user, shape_cost_planted, 2, _Speedup, _)
  -> true ; _Speedup = 0.0 ),
  Speedup is _Speedup,
  retractall(user:shape_cost_planted(_, _)),
  catch(abolish(user:shape_cost_planted/2), _, true) )
"""


def test_asking_the_shape_of_an_absent_name_costs_what_a_present_one_costs(metta):
    """A ratio rather than a count, because clause layout moves the number.

    Asked with the bare property, the absent name cost 1,030 inferences
    against 8 for the planted one; the guard in
    `extensions/python/metta/_binding/shim.pl` reads 37 against 9.
    """
    answer = metta.runtime.once(_COST)
    present, missing, speedup = (
        int(answer["Present"]),
        int(answer["Missing"]),
        float(answer["Speedup"]),
    )
    # The plant really is indexed, so the branch being priced is the one that
    # answers rather than the one that gives up.
    assert speedup > 1.0, f"the planted predicate has no index: speedup {speedup}"
    assert present > 0
    assert missing <= 4 * present, (
        f"an absent name costs {missing} inferences against {present} for a "
        "present one, which is the autoload search back"
    )
