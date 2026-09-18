% Purpose: evaluate one target producer through the declared binding options.
% Assumes: options.pl expands the EvaluationOptions grammar from Door.Binding.
% Guarantees: all collections share metta_py_solution/4 and its WFS boundary
% [tested: extensions/python/tests/ch20_extending_the_engine/test_binding_evaluation.py; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
% Owns resources: retained counts enumerate on the caller thread; metta_host_hold/3
% owns replay cursors until metta_py_cursor_close/1 releases them
% [tested: test_a_retained_count_replays_the_bag_the_cursor_would_have_answered; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
% Guarantees: shipped algebra operations run through metta_apply_algebra_operation/5
%   with caller context and accounting, in the space's own module [tested:
%   test_visibility_operations_share_the_native_carrier; commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].

binding_evaluation.

%Inside a definition batch (metta_py_transaction/2) reference publication and
%dependent recompilation wait for a door that reads them: an evaluating or
%planning door settles them first. Outside a batch this is one inference.
metta_py_settle_definitions :-
    (   filereader:active_source_program(_)
    ->  filereader:flush_source_program_analysis_if_needed
    ;   true
    ).

% Resolution and execution share the same space module and dispatch seam.
% call_delays stays inside enumeration, before findall can erase the residue.
metta_py_solution(Space, Term, Out, Delays) :-
    metta_py_module(Space, Module),
    metta_py_in_module(Module,
        ( metta_py_direct_goal(Module, Term, F, Args, Produced)
        -> translator:resolve_dispatch(F, Args, Produced, Goal),
           call_delays(call(Module:Goal), Delays)
        ; translate_cached_expr(Term, Goals, Produced),
          call_delays(metta_py_call_goals(Module, Goals), Delays)
        )),
    translator:metta_boundary_result(Term, Produced, Out).

metta_py_produce(Format, Fuel, Space, Term, Result) :-
    ( Fuel == true
    -> metta_run_with_fuel(metta_py_answer(Out-Delays), Held,
                          metta_py_solution(Space, Term, Out, Delays))
    ; metta_py_solution(Space, Term, Out, Delays),
      Held = metta_py_answer(Out-Delays)
    ),
    ( Format == wire -> metta_py_retained_encoded(Held, Result) ; Result = Held ).

metta_py_retained_encoded(metta_py_answer(Out-Delays), Encoded) :- !,
    metta_py_encode_truth(Out, Delays, Encoded).
metta_py_retained_encoded(Overflow, Encoded) :- metta_py_encode(Overflow, Encoded).

metta_py_encode_truth(Out, Delays, Encoded) :-
    metta_py_wire_acyclic(Out),
    ( Delays == true
      -> metta_py_encode(Out, Encoded)
    ; metta_py_encode(Out, Inner),
      term_string(Delays, Why),
      Encoded = ["u", Inner, Why] ).

%The fast path: a flat call of a compiled function whose arguments are all
%plain data needs no translation, just the call. translate_expr costs two
%orders more than the call itself on such terms, and they are what an API
%client evaluates all day. Anything with structure or evaluable arguments
%(a special form, a nested call, a symbol that names a function) takes the
%translator, whose judgment stays authoritative.
%Every head translate_expr treats structurally (its HV == chain and the
%stream rewrites): these must always take the translator, whatever their
%arguments look like.
%The translator's own registry, MATERIALIZED at load. The hand table this
%replaces lagged the engine: 'not-provable' gained a translate_special_dl
%clause and a bare same-name predicate, the stale table let the direct path
%claim the predicate, and the Python eval door answered [] where the
%engine's own directive answered True [measured 2026-09-01,
%examples/ch22-.../03-constructive_negation]. Consulting the registry per
%ask fixed that but taxed every eval crossing +2 inferences (+4,002 on the
%2,000-operation eval-arith lane, +4,000 on op-encoded), so the rows are
%asserted once here from metta_special_form_head/1, the enumerable face
%published for exactly this kind of reader: the ask stays one indexed
%lookup at the hand table's own cost (both lanes back on their pins under
%a plant/restore control [measured 2026-09-01]), and a form added to the
%engine's table is covered at the next boot, which is the table's own
%grain because translate_special_dl/5 is static engine source. The second
%forall is the RESIDUE the registry does not carry: rewrites owned by
%other dispatchers (the and-then/or-else pair and the stream set), and the
%trace! directive form. The findall completes the whole enumeration, the
%fallible part, before the retractall, so a reconsult swaps the set
%exactly (a form removed from the engine source leaves on the same
%reload that would have added one) and a failed enumeration leaves the
%previous set standing rather than an empty one. The current_predicate
%guard keeps the shim's engine-free consult (shim.plt's contract) loading
%clean: without the engine only the residue rows exist, and nothing
%engine-free can reach a special form anyway.
:- dynamic metta_py_special/1.
:- findall(F,
           ( current_predicate(translator:metta_special_form_head/1),
             translator:metta_special_form_head(F)
% policy-inventory-exempt: mechanism-internal; reason=the residue rows are the dispatch table's own content, heads owned by other rewrite dispatchers, not an operator choice; evidence=examples/ch06-many-answers/09-streamops.metta:1
           ; member(F, ['and-then', 'or-else', 'trace!', unique,
                        'alpha-unique', union, intersection, subtraction]) ),
           Forms),
   retractall(metta_py_special(_)),
   forall(member(F, Forms), assertz(metta_py_special(F))).

%The resolved goal, for every caller that wants one. Resolution goes through
%the engine's OWN resolve_dispatch so a compiled call site and this one make
%the same decision: seam:dispatch_call/4 is offered the call first, which is
%where lib_memo binds a cache lookup. Building the goal here instead was a
%second copy of resolve_dispatch's else-branch and skipped the seam entirely.
metta_py_direct_goal(Module, Term, Goal, Out) :-
    metta_py_direct_goal(Module, Term, F, Args, Out),
    metta_py_in_module(Module, translator:resolve_dispatch(F, Args, Out, Goal)).

%Whether the fast path applies at all, and the parts a resolution needs.
metta_py_direct_goal(Module, [F|Args], F, Args, _Out) :-
    atom(F),
    fun(F),
    \+ metta_py_special(F),
    %A declared callee, any installed USER typing rule, or a translator
    %rule means call-site machinery owns this call: the raw compiled clause
    %carries no argument checks, so the direct goal would skip a refusal
    %the same call written as a ! form makes -- (typing-rule-demo
    %unknown-demo) answered (seen unknown-demo) here while the runnable
    %answered the declared BadArgType with its TypingRuleRefusal. Shipped
    %rules ride the clause-compile route and need no per-call gate. The
    %question is the engine's (metta/types.pl documents both owners and
    %the measured cost); the shim used to carry its own copy of the
    %disjunction, and a three-state A/B on the eval-arith lane measured
    %the declaration walk and a raw &self read within two inferences per
    %LANE, so there is nothing to buy by narrowing the walk. The gate runs
    %OUTSIDE metta_py_in_module, which is why the module-parameterized
    %door is the right one: an ambient read like type_declaration/2 would
    %inspect the wrong module.
    \+ metta_typed_dispatch_applies(Module, F),
    metta_py_plain_args(Args),
    length(Args, N),
    Arity is N + 1,
    %The direct-goal guard reads the registry, so a deferred function fell
    %to the slow path until something else forced it.
    spaces:metta_ensure_compiled(F),
    arity(F, Arity),
    current_predicate(Module:F/Arity).

metta_py_plain_args([]).
metta_py_plain_args([A|As]) :-
    ( number(A) -> true
    ; string(A) -> true
    ; A == true -> true
    ; A == false -> true
    ; atom(A), \+ fun(A) -> true
    ; py_is_object(A) ),
    metta_py_plain_args(As).

metta_py_call_goals(_, []).
metta_py_call_goals(Module, [G|Gs]) :-
    call(Module:G),
    metta_py_call_goals(Module, Gs).


metta_py_repeatable(Space, Term) :-
    metta_py_module(Space, Module),
    catch_recover(
        (   (   metta_py_direct_goal(Module, Term, Goal, _)
            ->  Body = Goal
            ;   metta_py_in_module(
                    Module,
                    ( translate_cached_expr(Term, Goals, _),
                      goals_list_to_conj(Goals, Body) ))
            ),
            metta_host_goal_repeatable(Module, Body)
        ),
        fail).

%A direct compiled predicate that fails can mean either that its written head
%did not match or that a matching body's answer set was empty. Only the first
%is an unreduced original. Classify after an empty aggregate so the successful
%hot path retains the old direct goal and its exact inference cost.
metta_py_preserve_unmatched(Space, [F|Args], Encoded) :-
    atom(F),
    metta_py_module(Space, Module),
    translator:fun_meta_module(Module, F, _),
    \+ translator:dispatch_any_head_matches(Module, F, Args),
    translator:dispatch_no_match_result(F, Args, Produced),
    translator:metta_boundary_result([F|Args], Produced, Out),
    metta_py_encode(Out, Encoded).

% Reducibility classifies the translated head without running its body.
metta_py_reducible(Space, Tagged, Reducible) :-
    metta_py_target_term(Space, Tagged, Term),
    metta_py_module(Space, Module),
    metta_py_classify(Module, Term, Status),
    ( Status == value -> Reducible = true ; Reducible = false ).

metta_py_classify(Module, [F|Args], 'not-reducible') :-
    atom(F),
    %A deferred function has no fun_meta rows until its equations
    %translate, and this door's whole question is about those rows.
    spaces:metta_ensure_compiled(F),
    translator:fun_meta_module(Module, F, _),
    \+ translator:dispatch_any_head_matches(Module, F, Args),
    !.
metta_py_classify(Module, Term, Status) :-
    ( metta_reducible_head(Module, Term) -> Status = value
                                          ; Status = 'not-reducible' ).

%One shipped algebra operation applied to two decoded operands in the space's
%module, answered with the work it cost, so the host's quota accounting reads
%the engine's own count rather than estimating one. Authored for the
%references package in the retired algebra unit; it lives here beside the
%other module-scoped accounted evaluations.
metta_py_algebra_operation_accounted(Space, Algebra0, OperationWire, [Wire, Used]) :-
    metta_py_work(Before),
    atom_string(Algebra, Algebra0),
    metta_py_decode_shared(OperationWire, [Operation, Left, Right], _),
    metta_py_module(Space, Module),
    metta_py_in_module(Module,
        metta_apply_algebra_operation(Algebra, Operation, Left, Right, Result)),
    metta_py_encode(Result, Wire),
    metta_py_work(After), Used is After - Before.

%The tagged program's least fixpoint under one carrier, computed by the
%engine's tabling (engine/metta/algebra_fixpoint.pl): every derived
%proposition matching the target, with its tag at the fixpoint, as
%[[PropositionWire, TagWire], ...] and the work it cost. The space's module
%is the evaluation module, so a carrier's operations that are equations of
%that space apply.
%The carrier is a name, or a wire term such as (product prob polynomial).
metta_py_algebra_fixpoint_accounted(Space, Algebra0, Target, [Rows, Used]) :-
    metta_py_work(Before),
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
    metta_py_work(After), Used is After - Before.

%The weighted model count of a formula-carrier value under a carrier that
%declares a negation, and the variables the formula mentions with their
%weights, so a formula answer reinterprets exactly rather than by summing
%its proofs.
metta_py_algebra_model_count_accounted(Space, Algebra0, FormulaWire, [Wire, Used]) :-
    metta_py_work(Before),
    atom_string(Algebra, Algebra0),
    metta_py_decode_shared(FormulaWire, Formula, _),
    metta_py_module(Space, Module),
    metta_py_in_module(Module,
        metta_formula_model_count(Formula, Algebra, Count)),
    metta_py_encode(Count, Wire),
    metta_py_work(After), Used is After - Before.

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
