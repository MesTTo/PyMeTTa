% Purpose: specialize higher-order MeTTa calls and invalidate generated
%   functions when their source equations change.
% Guarantees:
%   - Specializer assertions made while loading a source participate in source
%     rollback [tested 2026-08-14:
%     specializer:compound_partial_key_has_stable_anonymous_variables].
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

:- dynamic ho_specialization/2.
:- dynamic ho_specialization_failed/3.

% Specialize HV(AVs), or fold an exact recursive specialization back to the
% predicate currently being generated. A same-function call with a different
% key stays generic, which retains the termination guard for growing keys such
% as (evolve (twice $r) ...).
maybe_specialize_call(HV, AVs, Out, Goal) :-
    specialization_plan(HV, AVs, CleanBindSet, MetaList, HasDirectBenefit),
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
    ( ho_specialization(HV, SpecName)
    ; ( register_fun(SpecName),
        assertz(ho_specialization(HV, SpecName), SpecializationRef),
        record_source_assertion(SpecializationRef),
        register_arity(SpecName, Arity),
        ( findall(TypeChain,
                  catch_recover(type_declaration(HV, TypeChain), fail),
                  TypeChains),
          forall(member(TypeChain, TypeChains),
                 add_sexp('&self', [':', SpecName, TypeChain])),
          ( HasDirectBenefit == true
            -> nb_setval('$petta_spec_needed', true)
          ; true ),
          maplist({SpecName}/[fun_meta(ArgsNorm,BodyExpr),clause_info(Input,Clause)]>>
                  ( Input = [=,[SpecName|ArgsNorm],BodyExpr],
                    translate_clause(Input,Clause,false) ),
                  MetaList, ClauseInfos),
          nb_getval('$petta_spec_needed', true),
          forall(member(clause_info(Input, Clause), ClauseInfos),
                 ( asserta(Clause, Ref),
                   record_source_assertion(Ref),
                   assertz(translated_from(Ref, Input), SourceRef),
                   record_source_assertion(SourceRef),
                   add_sexp('&self', Input, SpaceRef),
                   record_source_assertion(SpaceRef),
                   format(atom(Label), "metta specialization (~w)", [SpecName]),
                   maybe_print_compiled_clause(Label, Input, Clause) ))
        -> true
        ; ( silent(true) -> true
          ; format("Not specialized ~w~n", [SpecName/Arity]) ),
          forget_symbol(SpecName),
          retractall(ho_specialization(HV, SpecName)),
          ( ho_specialization_failed(HV, Arity, CleanBindSet)
            -> true
          ; assertz(ho_specialization_failed(HV, Arity, CleanBindSet), FailedRef),
            record_source_assertion(FailedRef) ),
          fail ) ) ), !,
    specialization_goal(SpecName, AVs, Out, Goal).

specialization_goal(SpecName, AVs, Out, Goal) :-
    append(AVs, [Out], CallArgs),
    Goal =.. [SpecName|CallArgs].

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
forget_symbol(Name) :- retractall('&self'(=, [Name|_], _)),
                       retractall('&self'(:, Name, _)),
                       findall(Ref, ( current_predicate(Name/A), functor(H, Name, A), clause(H, _, Ref) ), Refs),
                       forall(member(R, Refs), erase(R)),
                       forall(metta_on_function_removed(Name), true),
                       retractall(arity(Name,_)),
                       retractall(fun(Name)),
                       clear_fun_meta(Name),
                       retractall(ho_specialization(Name,_)).

%Invalidate all specializations:
invalidate_specializations(F) :-
    retractall(ho_specialization_failed(_,_,_)),
    findall(Spec, ho_specialization(F, Spec), Specs),
    forall(member(S, Specs), invalidate_specializations(S)),
    forall(member(S, Specs), forget_symbol(S)),
    retractall(ho_specialization(F,_)).
