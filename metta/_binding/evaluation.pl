% Purpose: evaluate one target producer through the declared binding options.
% Assumes: options.pl expands the EvaluationOptions grammar from Door.Binding.
% Guarantees: all collections share metta_py_produce/4, which is the engine's
% host evaluation door and its WFS boundary, so every evaluation runs in the
% fuel scope [tested 2026-09-25T05:55:56+10:00: extensions/python/tests/ch20_extending_the_engine/test_binding_evaluation.py].
% Owns resources: retained counts enumerate on the caller thread; metta_host_hold/3
% owns replay cursors until metta_py_cursor_close/1 releases them
% [tested: test_a_retained_count_replays_the_bag_the_cursor_would_have_answered; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
% Guarantees: shipped algebra operations run through metta_apply_algebra_operation/5
%   with caller context and accounting, in the space's own module [tested:
%   test_visibility_operations_share_the_native_carrier; commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].

binding_evaluation.

%Every evaluation this seat makes is the engine's host evaluation door,
%metta_host_evaluate/5, which settles a definition batch open around it,
%translates the term, runs it inside the fuel scope and answers the symbol
%Empty as data, so the plain batch and every option share one scope
%[source 2026-09-25T05:56:02+10:00: engine/translator/runtime.pl, metta_host_evaluate/5].
%
%An answer crosses with its well-founded residue: an unconditional one as its
%wire, a conditional one as ["u", Wire, Why].
metta_py_produce(Format, Space, Term, Result) :-
    metta_host_evaluate(Space, true, Term, Out, Delays),
    (   Format == wire
    ->  metta_py_encode_truth(Out, Delays, Result)
    ;   Result = Out-Delays
    ).

metta_py_retained_encoded(Out-Delays, Encoded) :-
    metta_py_encode_truth(Out, Delays, Encoded).

metta_py_encode_truth(Out, Delays, Encoded) :-
    metta_py_wire_acyclic(Out),
    ( Delays == true
      -> metta_py_encode(Out, Encoded)
    ; metta_py_encode(Out, Inner),
      term_string(Delays, Why),
      Encoded = ["u", Inner, Why] ).

% Reducibility classifies the translated head without running its body.
metta_py_reducible(Space, Tagged, Reducible) :-
    metta_py_target_term(Space, Tagged, Term),
    metta_py_classify(Space, Term, Status),
    ( Status == value -> Reducible = true ; Reducible = false ).

%A call whose function's equations accept none of its arguments is
%not-reducible whatever its head's type says; the engine answers that from
%the dispatcher's own head test.
metta_py_classify(Space, Term, 'not-reducible') :-
    metta_host_unmatched(Space, Term),
    !.
metta_py_classify(Space, Term, Status) :-
    metta_py_module(Space, Module),
    ( metta_reducible_head(Module, Term) -> Status = value
                                          ; Status = 'not-reducible' ).

%One shipped algebra operation applied to two decoded operands in the space's
%module, answered with the work it cost, so the host's quota accounting reads
%the engine's own count rather than estimating one. Authored for the
%references package in the retired algebra unit; it lives here beside the
%other module-scoped accounted evaluations.
metta_py_algebra_operation_accounted(Space, Algebra0, OperationWire, [Wire, Used]) :-
    metta_py_work(open, Before),
    atom_string(Algebra, Algebra0),
    metta_py_decode_shared(OperationWire, [Operation, Left, Right], _),
    metta_py_module(Space, Module),
    metta_py_in_module(Module,
        metta_apply_algebra_operation(Algebra, Operation, Left, Right, Result)),
    metta_py_encode(Result, Wire),
    metta_py_work(close, After), Used is After - Before.

%The tagged program's least fixpoint under one carrier, computed by the
%engine's tabling (engine/metta/algebra_fixpoint.pl): every derived
%proposition matching the target, with its tag at the fixpoint, as
%[[PropositionWire, TagWire], ...] and the work it cost. The space's module
%is the evaluation module, so a carrier's operations that are equations of
%that space apply.
%The carrier is a name, or a wire term such as (product prob polynomial).
metta_py_algebra_fixpoint_accounted(Space, Algebra0, Target, [Rows, Used]) :-
    metta_py_work(open, Before),
    (   is_list(Algebra0)
    ->  metta_py_decode_shared(Algebra0, Algebra, _)
    ;   atom_string(Algebra, Algebra0)
    ),
    metta_py_target_term_bindings(Space, Target, Goal, _),
    metta_py_module(Space, Module),
    metta_py_in_module(Module,
        metta_algebra_fixpoint(Space, Algebra, Goal, Answers)),
    findall([PropositionWire, TagWire],
            ( member([Proposition, Tag], Answers),
              metta_py_encode(Proposition, PropositionWire),
              metta_py_encode(Tag, TagWire) ),
            Rows),
    metta_py_work(close, After), Used is After - Before.

%The weighted model count of a formula-carrier value under a carrier that
%declares a negation, and the variables the formula mentions with their
%weights, so a formula answer reinterprets exactly rather than by summing
%its proofs.
metta_py_algebra_model_count_accounted(Space, Algebra0, FormulaWire, [Wire, Used]) :-
    metta_py_work(open, Before),
    atom_string(Algebra, Algebra0),
    metta_py_decode_shared(FormulaWire, Formula, _),
    metta_py_module(Space, Module),
    metta_py_in_module(Module,
        metta_formula_model_count(Formula, Algebra, Count)),
    metta_py_encode(Count, Wire),
    metta_py_work(close, After), Used is After - Before.

metta_py_algebra_formula_witnesses(FormulaWire, Rows) :-
    metta_py_decode_shared(FormulaWire, Formula, _),
    metta_formula_witnesses(Formula, Witnesses),
    findall(RowWires,
            ( member(Witness, Witnesses),
              findall([KeyWire, WeightWire],
                      ( member([Key, Weight], Witness),
                        metta_py_encode(Key, KeyWire),
                        metta_py_encode(Weight, WeightWire) ),
                      RowWires) ),
            Rows).

metta_py_algebra_formula_variables(FormulaWire, Rows) :-
    metta_py_decode_shared(FormulaWire, Formula, _),
    metta_formula_variables(Formula, Variables),
    findall([KeyWire, WeightWire],
            ( member([Key, Weight], Variables),
              metta_py_encode(Key, KeyWire),
              metta_py_encode(Weight, WeightWire) ),
            Rows).
