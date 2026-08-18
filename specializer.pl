% Purpose: specialize higher-order MeTTa calls and invalidate generated
%   functions when their source equations change.
% Guarantees:
%   - Specializer assertions made while loading a source participate in source
%     rollback [tested 2026-08-14:
%     specializer:compound_partial_key_has_stable_anonymous_variables].
%   - Concurrent translation creates one specialization for a function and
%     normalized key [tested 2026-08-15:
%     specializer:concurrent_translation_creates_one_specialization].
%   - A recursive specialization returns to neither the generic predicate nor
%     the reducer after its first step, so the saving is per step
%     [tested 2026-08-18:
%     specializer:exact_recursive_key_folds_to_specialized_predicate,
%     specializer:the_recursive_specialization_never_re_enters_the_reducer]
%     [measured 2026-08-18: 8,004 against 24,004 inferences over 1,000 steps,
%     the same third at 100].
% Guarded by: '$petta_specializer' serializes the existence check and the
%   transaction that publishes a specialization.
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

:- dynamic ho_specialization/3.
:- dynamic ho_specialization_failed/3.
%Verified once per specialization, under the checking mode only.
:- dynamic ho_specialization_agrees/1.
%Recorded when the generic side could not be run inside the bound.
:- dynamic ho_specialization_unverified/2.
%Held while a specialization's own check is running, so the recursive
%calls inside it do not each start another check.
:- dynamic ho_specialization_checking/1.

% Specialize HV(AVs), or fold an exact recursive specialization back to the
% predicate currently being generated. A same-function call with a different
% key stays generic, which retains the termination guard for growing keys such
% as (evolve (twice $r) ...).
maybe_specialize_call(HV, AVs, Out, Goal) :-
    specialization_plan(HV, AVs, CleanBindSet, MetaList, HasDirectBenefit),
    %A tabled function must never specialize: the clone would carry the
    %recursion without the tabling, turning SLG termination back into
    %divergence. Found 2026-08-18 as a 27,525-frame loop in
    %linkage-closure_Spec_[d]/3, reached whenever a tabled closure was
    %called with an argument that happened to NAME a defined function (a
    %graph node called d, with (= (d $x) ...) defined elsewhere). The
    %(tabled Space Name Arity) reflection facts lib_tabling keeps in
    %&petta are the module-agnostic record of what is tabled. AFTER the
    %plan on purpose: the plan is the fail-fast for the overwhelming
    %non-higher-order case, and putting this probe first taxed every
    %translated call (+364 inferences per op on handle-round-trip,
    %measured 2026-08-18); on a formed plan it is one indexed probe.
    \+ get_native_atom('&petta', [tabled, _, HV, _]),
    length(AVs, N),
    Arity is N + 1,
    \+ ho_specialization_failed(HV, Arity, CleanBindSet),
    format(atom(SpecName), "~w_Spec_~w", [HV, CleanBindSet]),
    ( nb_current('$petta_spec_stack', Stack) -> true ; Stack = [] ),
    ( active_specialization(HV, Stack, ActiveKey, ActiveSpecName)
      -> CleanBindSet =@= ActiveKey,
         specialization_goal(ActiveSpecName, AVs, Out, Goal),
         nb_setval('$petta_spec_needed', true)
    ; capture_nb_state('$petta_spec_needed', PreviousNeeded),
      setup_call_cleanup(
          ( nb_setval('$petta_spec_needed', false),
            nb_setval('$petta_spec_stack',
                      [specializing(HV, CleanBindSet, SpecName)|Stack]) ),
          specialize_call(HV, AVs, Out, Goal, CleanBindSet, MetaList,
                          HasDirectBenefit, SpecName, Arity),
          ( nb_setval('$petta_spec_stack', Stack),
            restore_nb_state('$petta_spec_needed', PreviousNeeded) )),
      nb_setval('$petta_spec_needed', true)
    ).

active_specialization(HV, [specializing(ActiveHV, Key, SpecName)|_],
                      Key, SpecName) :-
    ActiveHV == HV, !.
active_specialization(HV, [_|Stack], Key, SpecName) :-
    active_specialization(HV, Stack, Key, SpecName).

capture_nb_state(Name, present(Value)) :- nb_current(Name, Value), !.
capture_nb_state(_, absent).

restore_nb_state(Name, present(Value)) :- !, nb_setval(Name, Value).
restore_nb_state(Name, absent) :-
    ( nb_current(Name, _) -> nb_delete(Name) ; true ).

% Build a stable, variant-normalized specialization key.
%
% This intentionally descends through arbitrary compound terms (including
% partial/2 closures).  A shallow list-only variable replacement leaves fresh
% Prolog variable ids inside compound terms, producing unstable specialization
% names such as app_Spec_[partial(lambda_1,[_17896])].
normalize_specialization_key(Term, Normalized) :-
    copy_term(Term, Normalized),
    numbervars(Normalized, 0, _, [singletons(true)]).

% Build one global key from all higher-order positions, while binding every
% retained clause independently. The key is ordered by call argument and path,
% so equation order cannot select a different partial reduction.
specialization_plan(HV, AVs, CleanBindSet, MetaList, HasDirectBenefit) :-
    fun_meta_clauses(HV, SourceMetaList),
    maplist(bind_specialization_clause(AVs), SourceMetaList,
            MetaList, BindingLists),
    append(BindingLists, Bindings),
    ( member(binding(_, _, _, direct), Bindings)
      -> HasDirectBenefit = true
    ; HasDirectBenefit = false ),
    canonical_specialization_bindings(Bindings, BindSet),
    BindSet \== [],
    normalize_specialization_key(BindSet, CleanBindSet).

bind_specialization_clause(AVs, fun_meta(Args, Body),
                           fun_meta(Args, Body), Bindings) :-
    ( same_length(AVs, Args)
      -> bind_specialization_args(AVs, Args, Body, 1, Bindings)
    ; Bindings = [] ).

bind_specialization_args([], [], _, _, []).
bind_specialization_args([Value|Values], [Arg|Args], Body, Index, Bindings) :-
    ( specializable_vars(Body, Value, Arg, _, PathBindings)
      -> index_bindings(PathBindings, Index, IndexedBindings)
    ; IndexedBindings = [] ),
    NextIndex is Index + 1,
    bind_specialization_args(Values, Args, Body, NextIndex, RestBindings),
    append(IndexedBindings, RestBindings, Bindings).

index_bindings([], _, []).
index_bindings([path_binding(Path, Value, Use)|Bindings], Index,
               [binding(Index, Path, Value, Use)|Indexed]) :-
    index_bindings(Bindings, Index, Indexed).

canonical_specialization_bindings(Bindings, BindSet) :-
    maplist(binding_pair, Bindings, Pairs),
    keysort(Pairs, SortedPairs),
    unique_binding_values(SortedPairs, BindSet).

binding_pair(binding(Index, Path, Value, _), (Index-Path)-Value).

unique_binding_values([], []).
unique_binding_values([Key-Value|Pairs], [Value|Values]) :-
    skip_same_binding(Pairs, Key, Value, Rest),
    unique_binding_values(Rest, Values).

skip_same_binding([OtherKey-OtherValue|Pairs], Key, Value, Rest) :-
    OtherKey == Key, !,
    ( OtherValue =@= Value
      -> skip_same_binding(Pairs, Key, Value, Rest)
    ; throw(error(representation_error(specialization_binding),
                  context(canonical_specialization_bindings/2,
                          'one call path produced conflicting bindings'))) ).
skip_same_binding(Pairs, _, _, Pairs).

% Create a specialization once, or reuse the completed predicate for the same
% key. MetaList already carries the explicit per-clause bindings.
specialize_call(HV, AVs, Out, Goal, CleanBindSet, MetaList,
                HasDirectBenefit, SpecName, Arity) :-
    %The mutex must be acquired before transaction/1 takes its snapshot. If
    %the order is reversed, a waiting transaction can still see the database
    %from before the first worker committed and publish a duplicate.
    with_mutex('$petta_specializer',
               transaction(specialize_call_locked(
                   HV, CleanBindSet, MetaList, HasDirectBenefit,
                   SpecName, Arity, Outcome))),
    Outcome == ready, !,
    specialization_goal(SpecName, AVs, Out, Goal).

%Keyed by module as well as by call shape. Keyed by shape alone, a named
%space reused the specialization &self had already published, so the same
%program answered twice there and once in &self, and which you got depended
%on what had run earlier in the process.
specialize_call_locked(HV, _, _, _, SpecName, _, ready) :-
    current_metta_module(Module),
    ho_specialization(Module, HV, SpecName), !.
%The specialization belongs to the space whose code triggered it. This runs
%during translation, inside with_metta_module/2, so the current module is the
%one whose functions the generated body references. Registering globally and
%asserting into user left the clause calling functions that do not exist
%there: (= (twice $f $x) ($f ($f $x))) with (= (bump $n) (+ $n 1)) crashed on
%the first call in a named space with Unknown procedure: bump/2, and gave a
%duplicate answer when an earlier &self engine had compiled the same name.
%add_function_atom/5 in spaces.pl is the same job done correctly
%[tested: higher_order_code_runs_inside_a_named_space].
specialize_call_locked(HV, CleanBindSet, MetaList, HasDirectBenefit,
                       SpecName, Arity, Outcome) :-
    current_metta_module(Module),
    current_metta_space(Space),
    register_fun_in(Module, SpecName),
    assertz(ho_specialization(Module, HV, SpecName), SpecializationRef),
    record_source_assertion(SpecializationRef),
    register_arity(SpecName, Arity),
    ( findall(TypeChain,
              catch_recover(type_declaration(HV, TypeChain), fail),
              TypeChains),
      forall(member(TypeChain, TypeChains),
             add_sexp(Space, [':', SpecName, TypeChain])),
      ( HasDirectBenefit == true
        -> nb_setval('$petta_spec_needed', true)
      ; true ),
      maplist({SpecName}/[fun_meta(ArgsNorm,BodyExpr),clause_info(Input,Clause)]>>
              ( Input = [=,[SpecName|ArgsNorm],BodyExpr],
                translate_clause(Input,Clause,false) ),
              MetaList, ClauseInfos),
      nb_getval('$petta_spec_needed', true),
      forall(member(clause_info(Input, Clause), ClauseInfos),
             ( asserta(Module:Clause, Ref),
               record_source_assertion(Ref),
               record_translated_from(Ref, Input, SourceRef),
               record_source_assertion(SourceRef),
               add_sexp(Space, Input, SpaceRef),
               record_source_assertion(SpaceRef),
               format(atom(Label), "metta specialization (~w)", [SpecName]),
               maybe_print_compiled_clause(Label, Input, Clause) ))
    -> Outcome = ready
    ; ( silent(true) -> true
      ; format("Not specialized ~w~n", [SpecName/Arity]) ),
      forget_symbol(SpecName),
      retractall(ho_specialization(Module, HV, SpecName)),
      ( ho_specialization_failed(HV, Arity, CleanBindSet)
        -> true
      ; assertz(ho_specialization_failed(HV, Arity, CleanBindSet), FailedRef),
        record_source_assertion(FailedRef) ),
      Outcome = failed
    ).

specialization_goal(SpecName, AVs, Out, Goal) :-
    append(AVs, [Out], CallArgs),
    Spec =.. [SpecName|CallArgs],
    (   petta_verifying_specializations
    ->  Goal = petta_verified_specialization(SpecName, Spec)
    ;   Goal = Spec
    ).

%The specializer's whole claim is that a specialized call answers exactly
%what the generic one answers. MeTTaLog makes that self-enforcing at run
%time (metta_improve.pl compares interpreter against compiler on first
%use and demotes the loser), and the shape transfers, but running both
%ways in production would run a function's EFFECTS twice, which is worse
%than the optimisation is worth. So it is a checking MODE instead: off,
%the emitted goal is byte-identical to what it always was and costs
%nothing; on, every specialization is compared against the generic call
%the first time it runs, and a disagreement THROWS rather than silently
%demoting, because a checking mode that hides the defect it found is
%worth less than no check. The mode is what turns the workspace's
%"validate every optimisation with a differential that runs it both
%ways" from a thing tests must remember into a property the whole
%example corpus asserts on every gate run.
petta_verifying_specializations :-
    (   metta_pragma('verify-specializations', V), V \== false, V \== none
    ->  true
    ;   getenv('PETTA_VERIFY_SPECIALIZATIONS', Set), Set \== '0'
    ).

%Answers exactly what the specialization answers, after establishing once
%per specialization that the generic call agrees. The comparison is over
%COMPLETE answer lists with variant equality, so a renaming is not a
%difference and a missing, extra or reordered answer is.
petta_verified_specialization(SpecName, Spec) :-
    (   ho_specialization_agrees(SpecName)
    ->  call(Spec)
    ;   ho_specialization_unverified(SpecName, _)
    ->  call(Spec)
    ;   ho_specialization_checking(SpecName)
    ->  %Re-entry: the clone under check calls itself, which is what a
        %recursive specialization IS. Checking again from inside its own
        %check nests a full comparison per recursive step, so the cost is
        %exponential in the recursion depth rather than paid once: with
        %the marker holbenchmark's four specializations verify in under a
        %second, without it the same file did not finish in ninety
        %[measured 2026-08-18]. The specializer's own compile-time
        %recursion guard ($petta_spec_stack) is the same pattern.
        call(Spec)
    ;   setup_call_cleanup(assertz(ho_specialization_checking(SpecName)),
                           petta_check_specialization(SpecName, Spec),
                           retractall(ho_specialization_checking(SpecName))),
        call(Spec)
    ).

%The check, run once per specialization and BOUNDED WHOLE. Both sides are
%bounded, not just the slow one: comparing answer sets means forcing all
%answers of a call the program may only have wanted one of, so the
%specialized side can blow up exactly as the generic side can, and a
%generator with infinitely many answers would never return from either.
%Exceeding the bound records the specialization as unverified and leaves
%the call to run normally, lazily, as it always did; the count is
%REPORTED so coverage is a number rather than a claim of completeness.
%This is translation validation's own shape: the check is bounded and
%says what it could not check, instead of being trusted or being
%unbounded [source: Pnueli, Siegel and Singerman, Translation Validation,
%TACAS 1998].
petta_check_specialization(SpecName, Spec) :-
    Spec =.. [_|Args],
    copy_term(Args, SpecArgs),
    copy_term(Args, PlainArgs),
    SpecCopy =.. [SpecName|SpecArgs],
    petta_specialization_generic(SpecName, PlainArgs, Generic),
    petta_specialization_budget(Budget),
    catch(
        (   call_with_inference_limit(
                (   findall(SpecArgs, call(SpecCopy), Specialized),
                    findall(PlainArgs, call(Generic), Plain)
                ), Budget, Result),
            (   Result == inference_limit_exceeded
            ->  Outcome = unbounded
            ;   Outcome = both(Specialized, Plain)
            )
        ),
        Error,
        (   control_exception(Error) -> throw(Error) ; Outcome = raised(Error) )),
    petta_specialization_verdict(SpecName, Outcome).

petta_specialization_verdict(SpecName, both(Specialized, Plain)) :-
    (   Specialized =@= Plain
    ->  assertz(ho_specialization_agrees(SpecName))
    ;   throw(error(petta_specialization_disagrees(SpecName, Specialized, Plain),
                    context(petta_verified_specialization/2,
                            'a specialization answered differently from \c
                             the generic call')))
    ).
petta_specialization_verdict(SpecName, unbounded) :-
    assertz(ho_specialization_unverified(SpecName, inference_limit)).
petta_specialization_verdict(SpecName, raised(Error)) :-
    throw(error(petta_specialization_disagrees(SpecName, raised, Error),
                context(petta_verified_specialization/2,
                        'one side raised where the other answered'))).

%The bound, in inferences, tunable for a deeper sweep.
petta_specialization_budget(Budget) :-
    (   getenv('PETTA_VERIFY_BUDGET', Text), atom_number(Text, N), N > 0
    ->  Budget = N
    ;   Budget = 200000
    ).

%The generic twin of a specialized call: the same arguments through the
%function the specialization was cloned from, which is exactly what would
%have run had the plan been refused.
petta_specialization_generic(SpecName, Args, Generic) :-
    ho_specialization(_, HV, SpecName), !,
    Generic =.. [HV|Args].

%Extracts clause-head variables and their call-site copies, producing eligible Var–Copy pairs for specialization:
specializable_vars(BodyExpr, Value, Arg, HoVars) :-
    specializable_vars(BodyExpr, Value, Arg, HoVars, _).

specializable_vars(BodyExpr, Value, Arg, HoVars, Bindings) :-
    term_variables(Arg, Vars),
    maplist(variable_first_path(Arg), Vars, Paths),
    copy_term(Arg-Vars, ArgCopy-VarsCopy),
    traverse_list([A,V]>>(nonvar(V) -> V = A ; true), ArgCopy, Value),
    eligible_var_pairs(Vars, VarsCopy, Paths, BodyExpr, HoVars, Bindings).

variable_first_path(Term, Var, Path) :-
    variable_path(Term, Var, [], ReversePath), !,
    reverse(ReversePath, Path).

variable_path(Term, Var, Path, Path) :-
    var(Term),
    Term == Var, !.
variable_path(Term, Var, Prefix, Path) :-
    compound(Term),
    functor(Term, _, Arity),
    between(1, Arity, Index),
    arg(Index, Term, Arg),
    variable_path(Arg, Var, [Index|Prefix], Path).

traverse_list(Pred, From, Into) :- (is_list(From),is_list(Into) -> maplist(traverse_list(Pred),From,Into)
                                                                 ; call(Pred, From, Into)).

% Select and unify variables used as higher-order operands. The six-argument
% form also retains their structural paths for the global specialization key.
eligible_var_pairs(Vars, Copies, BodyExpr, HoVars) :-
    same_length(Vars, Paths),
    maplist(=([]), Paths),
    eligible_var_pairs(Vars, Copies, Paths, BodyExpr, HoVars, _).

eligible_var_pairs([], [], [], _, [], []).
eligible_var_pairs([Var|Vars], [Copy|Copies], [Path|Paths], BodyExpr,
                   HoVars, Bindings) :-
    ( specializable_arg(Copy),
      specialization_use(Var, BodyExpr, Use)
      -> Var = Copy,
         HoVars = [Var|RestHoVars],
         Bindings = [path_binding(Path, Copy, Use)|RestBindings]
    ; HoVars = RestHoVars,
      Bindings = RestBindings ),
    eligible_var_pairs(Vars, Copies, Paths, BodyExpr,
                       RestHoVars, RestBindings).

specialization_use(Var, BodyExpr, direct) :-
    var_use_check(head, Var, BodyExpr), !.
specialization_use(Var, BodyExpr, propagated) :-
    var_use_check(ho, Var, BodyExpr).

%If Var appears at list head it means function call, meaning specialization is needed, and detect when used as HOL arg
var_use_check(head, Var, [Head|_]) :- Var == Head.
var_use_check(ho, Var, [Head|Args]) :- specializable_arg(Head),
                                       member(Arg, Args),
                                       ( Var == Arg
                                       ; is_list(Arg),
                                         var_use_check(ho, Var, Arg) ).
var_use_check(Mode, Var, L) :- is_list(L),
                               member(E, L),
                               is_list(E),
                               var_use_check(Mode, Var, E).

%Tests whether an argument represents a specializable function or partial application:
specializable_arg(Arg) :- nonvar(Arg), 
                          ( fun(Arg) ; Arg = partial(_, _) ).

%Forget function symbol:
%
%The clauses are in the module of the space whose code triggered the
%specialization, which is what specialize_call_locked/7 registers and what
%fun_in/2 and ho_specialization/3 both record. Asking current_predicate/1 and
%clause/3 UNQUALIFIED read the engine's own module, which found &self's
%clauses only for as long as &self WAS that module and never found a named
%space's at all. A stale specialization then outlived the equation it cloned
%and answered beside the new one: removing one of two equations for a
%higher-order function gave (2 2 42) where (2) was asked for
%[tested: examples/functions/functionremoval.metta,
%specializer:a_removed_equation_forgets_its_specialization].
%
%clause_property(module/1) is the filter that keeps this from erasing a
%PARENT's clauses: clause/3 sees inherited ones through the base chain, and a
%named space asking to forget a name &self defines must not erase &self's.
forget_symbol(Name) :- forall(forget_symbol_space(Name, Space),
                                     ( remove_sexp(Space, [=, [Name|_], _]),
                                       remove_sexp(Space, [':', Name, _]) )),
                       findall(Ref,
                               ( forget_symbol_module(Name, Module),
                                 current_predicate(Module:Name/A),
                                 functor(H, Name, A),
                                 clause(Module:H, _, Ref),
                                 clause_property(Ref, module(Module)) ),
                               Refs0),
                       sort(Refs0, Refs),
                       %The provenance record dies with the clause it names.
                       %Erasing without retracting it left translated_from/2
                       %pointing at a dead reference, and remove_equation/6
                       %then found that reference, called erase/1 on it and
                       %FAILED, so removing the specialization's own atom
                       %failed and every caller of it failed with it
                       %[tested: python/tests/test_import_reuse.py::
                       %test_import_translation_leaves_variable_heads_dynamic].
                       forall(member(R, Refs),
                              ( erase(R), retractall(translated_from(R, _)) )),
                       forall(metta_on_function_removed(Name), true),
                       retractall(arity(Name,_)),
                       retractall(fun(Name)),
                       clear_fun_meta(Name),
                       retractall(ho_specialization(_, Name, _)),
                       retractall(ho_specialization(_, _, Name)).

%Both registries are consulted because they are written at different moments:
%register_fun_in/2 records the module before the clauses are asserted, and
%ho_specialization/3 records it beside them. The failure branch retracts the
%second one immediately after calling this, so neither alone is total.
forget_symbol_module(Name, Module) :- fun_in(Module, Name).
forget_symbol_module(Name, Module) :- ho_specialization(Module, _, Name).

%And the space each of those modules serves, because a specialization's SOURCE
%atoms were written into the space whose code triggered it
%(specialize_call_locked/7 adds them with current_metta_space/1), not into
%&self. Naming &self here left every named space holding the source atoms of
%a specialization whose clauses were gone.
forget_symbol_space(Name, Space) :-
    distinct(Space,
             ( ( forget_symbol_module(Name, Module),
                 metta_module_space(Module, Space)
               ; Space = '&self' ) )).

%Invalidate all specializations:
%The recursion carries a visited set. It retracts only AFTER descending, so a
%cycle among ho_specialization/3 facts would not terminate, and this runs
%unguarded on the register-an-operation path now: a non-terminating
%invalidation there is a hang rather than a swallowed failure. No cycle is
%reachable today, because the recursive-specialization fold reuses the active
%name rather than recording a new fact, so this guards a reachability one
%change away rather than claiming one exists
%[tested: an_invalidation_cycle_terminates].
invalidate_specializations(F) :-
    %The blanket memo clear is deliberate cross-function conservatism: a
    %change to g can flip whether specializing f succeeds (the failed
    %binding may have named g), so per-F clearing would be unsound. On an
    %empty table it costs almost nothing. The spec walk behind it IS
    %guarded, because nearly no function has specializations and this now
    %runs once per compiled equation through the one compile door.
    %Unguarded, source-load's own counter assertion measured the walk at
    %+19,994 inferences over 1000 forms; guarded, the lane passes its
    %unchanged 944,158 floor [measured 2026-08-18].
    retractall(ho_specialization_failed(_,_,_)),
    (   ho_specialization(_, F, _)
    ->  findall(Spec, ho_specialization(_, F, Spec), Specs),
        forall(member(S, Specs), invalidate_specializations(S, [F])),
        forall(member(S, Specs), forget_symbol(S)),
        retractall(ho_specialization(_, F, _))
    ;   true
    ).

%The visited set rides on the DESCENT only, so the entry point above is
%unchanged and a function with no specializations, which is nearly all of
%them, pays nothing: routing the top level through here instead cost one
%inference on every compiled equation [measured 2026-08-16: source-load
%6921403 to 6922400 over a thousand].
invalidate_specializations(F, Seen) :-
    (   memberchk(F, Seen)
    ->  true
    ;   findall(Spec, ho_specialization(_, F, Spec), Specs),
        forall(member(S, Specs), invalidate_specializations(S, [F|Seen])),
        forall(member(S, Specs), forget_symbol(S)),
        retractall(ho_specialization(_, F, _))
    ).
