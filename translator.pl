% Purpose: compile MeTTa expressions and equations into executable Prolog,
%   including dynamic dispatch, control forms, higher-order calls, and
%   branch-return optimization.
% Assumes:
%   - merge_branch_returns/3 does not bind variable keys until its assoc
%     lookups finish [source 2026-08-14:
%     https://www.swi-prolog.org/pldoc/doc/_SWI_/library/assoc.pl].
% Guarantees:
%   - Branch-return merging preserves shared and pre-bound variables while
%     restoring private tail returns [tested 2026-08-14:
%     translator_branch_returns].
%   - A typed function remains partially applicable until it has produced a
%     return value [tested 2026-08-14: translator_typed_currying].
%   - Arity selection does not compile typed arguments before their branch
%     translation [tested 2026-08-14: translator_typed_single_pass].
%   - Empty special-form inputs have explicit identity or failure semantics
%     [tested 2026-08-14: translator_empty_forms].
%   - Dynamic and compiled calls surface the same runtime errors
%     [tested 2026-08-14: translator_evaluation_errors].
%   - Compiler diagnostics contain ANSI escapes only on terminal streams
%     [tested 2026-08-14: translator_terminal_output].
%   - Special forms dispatch through first-argument-indexed clauses
%     [tested 2026-08-14: translator_special_dispatch].
%   - Higher-arity dynamic calls bypass the operator-table lookup
%     [tested 2026-08-14: tests/performance/reduce_dispatch.pl].
%   - Prolog import forms have exactly one translation
%     [tested 2026-08-14: translator_prolog_imports].
%   - Source-load rollback removes retained metadata, generated lambdas, and
%     symbol-head notes [tested 2026-08-14: filereader_source_rollback].
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

:- use_module(library(assoc)).
:- use_module(library(ansi_term)).

% Function source retained for higher-order specialization. Each equation is
% one independently indexed fact, so compiling a new equation does not copy
% every older equation for the same function.
:- dynamic fun_meta_clause/3.

record_fun_meta(F, Args, Body) :-
    asserta(fun_meta_clause(F, Args, Body), Ref),
    record_source_assertion(Ref).

fun_meta_clauses(F, Clauses) :-
    findall(fun_meta(Args, Body), fun_meta_clause(F, Args, Body), Clauses),
    Clauses \== [].

% Remove one variant-equivalent retained equation. Retraction must not bind the
% caller's variables, and duplicate equations are removed one at a time.
drop_fun_meta(F, Args, Body) :-
    ( once(( clause(fun_meta_clause(F, StoredArgs, StoredBody), true, Ref),
             (StoredArgs-StoredBody) =@= (Args-Body),
             erase(Ref) ))
    -> true
    ; true ).

clear_fun_meta(F) :-
    retractall(fun_meta_clause(F, _, _)).

%Pattern matching, structural and functional/relational constraints on arguments:
constrain_args(X, X, []) :- (var(X); atomic(X)), !.
constrain_args([F, A, B], Out, Goals) :- nonvar(F),
                                         F == cons,
                                         constrain_args(A, A1, G1),
                                         constrain_args(B, B1, G2),
                                         Out = [A1|B1],
                                         append(G1, G2, Goals), !.
constrain_args([F|Args], Var, Goals) :- atom(F),
                                        fun_here(F), !,
                                        translate_expr([F|Args], GoalsExpr, Var),
                                        flatten(GoalsExpr, Goals).
constrain_args(In, Out, Goals) :- maplist(constrain_args, In, Out, NestedGoalsList),
                                  flatten(NestedGoalsList, Goals), !.

%Flatten (= Head Body) MeTTa function into Prolog Clause:
translate_clause(Input, (Head :- BodyConj)) :- translate_clause(Input, (Head :- BodyConj), true).
translate_clause(Input, (Head :- BodyConj), ConstrainArgs) :-
                                               Input = [=, [F|Args0], BodyExpr],
                                               ( ConstrainArgs -> maplist(constrain_args, Args0, Args1, GoalsA),
                                                                  flatten(GoalsA,GoalsPrefix)
                                                                ; Args1 = Args0, GoalsPrefix = [] ),
                                               record_fun_meta(F, Args1, BodyExpr),
                                               ( declared_output_type(F, 'Atom')
                                                 -> GoalsBody = [],
                                                    ExpOut = BodyExpr
                                                  ; translate_expr(BodyExpr, GoalsBody, ExpOut) ),
                                               (  nonvar(ExpOut) , ExpOut = partial(Base,Bound)
                                               -> length(Bound, N),
                                                  MinimumArity is N + 1,
                                                  setof(A, (arity(Base, A), A > MinimumArity), [Arity|_]),
                                                  M is (Arity - N) - 1,
                                                  length(ExtraArgs, M), append(Bound, ExtraArgs, CallInArgs),
                                                  resolve_memoization(Base, CallInArgs, Out, Goal),
                                                  append(GoalsBody,[Goal],FinalGoals), append(Args1,ExtraArgs,HeadArgs)
                                               ; FinalGoals= GoalsBody , HeadArgs = Args1, Out = ExpOut ),
                                               append(HeadArgs, [Out], FinalArgs),
                                               Head =.. [F|FinalArgs],
                                               length(FinalArgs, CompiledArity),
                                               register_arity(F, CompiledArity),
                                               append(GoalsPrefix, FinalGoals, Goals),
                                               goals_list_to_conj(Goals, BodyConj0),
                                               merge_branch_returns(Head, BodyConj0, BodyConj).

%Record atoms compiled as plain symbol heads together with where they were compiled:
%a stored definition can be recompiled when the function arrives late, an already
%executed expression cannot, so late registration repairs the former and warns on the latter.
:- dynamic symbol_head/2.
:- thread_local translating_runnable/0.
note_symbol_head(HV) :- atom(HV), !,
                        ( translating_runnable -> Ctx = runnable ; Ctx = clause ),
                        ( symbol_head(HV, Ctx) -> true
                        ; assertz(symbol_head(HV, Ctx), Ref),
                          record_source_assertion(Ref) ).
note_symbol_head(_).

%Translate an expression that executes immediately, marking its data uses as unrepairable.
%once/1 closes the translation before the goals run, so nested imports triggered by the
%execution compile their definitions under the clause context again:
translate_runnable_expr(C, Goals, Out) :- setup_call_cleanup(assertz(translating_runnable, Ref),
                                                             once(translate_expr(C, Goals, Out)),
                                                             erase(Ref)).

%Print compiled clause:
maybe_print_compiled_clause(_, _, _) :- silent(true), !.
maybe_print_compiled_clause(Label, FormTerm, Clause) :-
    swrite(FormTerm, FormStr),
    ansi_format([fg(yellow)], "-->  ~w  -->~n", [Label]),
    ansi_format([fg(cyan)], "~w~n", [FormStr]),
    ansi_format([fg(yellow)], "--> prolog clause -->~n", []),
    ansi_format([fg(green)], "~@", [portray_clause(current_output, Clause)]),
    ansi_format([fg(yellow)], "^^^^^^^^^^^^^^^^^^^^^~n", []).

%Conjunction builder, turning goals list to a flat conjunction:
goals_list_to_conj([], true)      :- !.
goals_list_to_conj([G], G)        :- !.
goals_list_to_conj([G|Gs], (G,R)) :- goals_list_to_conj(Gs, R).

resolve_memoization(Fun, Args, Out, Goal) :-
    ( metta_memoized_dispatch_call(Fun, Args, Out, Goal)
    -> true
    ; append(Args, [Out], DirectArgs),
      Goal =.. [Fun|DirectArgs]
    ).
incomplete_application_kind(Fun, Arity, partial) :- ( arity(Fun, KnownArity), KnownArity >= Arity
                                                     ; \+ arity(Fun, _) ), !.
incomplete_application_kind(_, _, overapplied).

throw_function_overapplication(Fun, ActualInputArity) :-
    findall(InputArity, (arity(Fun, Arity), InputArity is Arity - 1), InputArities),
    sort(InputArities, KnownInputArities),
    throw(error(domain_error(function_input_arities(Fun, KnownInputArities), ActualInputArity), none)).

% Runtime dispatcher: call F if it's a registered fun/1, else keep as list.
%
% Resolution follows the current space's module, because that is where the
% space's equations were compiled. Looking in the calling module instead found
% nothing for them, so a function defined in a named space and reached through
% reduce/2 came back as a partial application instead of running: `(map-atom
% (1 2 3) double)` answered `((partial double (1)) ...)`. A builtin still
% resolves, through the module's own inheritance from user.
reduce([], []) :- !.
reduce([F|Args], Out) :- nonvar(F), atom(F),
                         ( fun(F), \+ fun_scoped(F) -> Module = user
                         ; current_metta_module(Module), fun_here_in(Module, F) )
                         -> % --- Case 1: callable predicate ---
                            length(Args, N),
                            Arity is N + 1,
                            ( ( Module == user -> current_predicate(F/Arity)
                                               ; current_predicate(Module:F/Arity) ),
                              \+ (Arity =< 2, current_op(_, _, F))
                              -> resolve_memoization(F, Args, Out, Goal),
                                 ( Module == user -> CallGoal = Goal ; CallGoal = Module:Goal ),
                                 call(CallGoal)
                            ; incomplete_application_kind(F, Arity, partial)
                              -> Out = partial(F,Args)
                            ; throw_function_overapplication(F, N) )
                          ; % --- Case 2: partial closure ---
                            compound(F), F = partial(Base, Bound) -> append(Bound, Args, NewArgs),
                                                                     reduce([Base|NewArgs], Out)
                          ; % --- Case 3: leave unevaluated ---
                            Out = [F|Args],
                            acyclic_term(Out).

%Calling reduce from aggregate function foldall needs this argument wrapping
agg_reduce(AF, Acc, Val, NewAcc) :- reduce([AF, Acc, Val], NewAcc).

%Combined expr translation to goals list
translate_expr_to_conj(Input, Conj, Out) :- translate_expr(Input, Goals, Out),
                                            goals_list_to_conj(Goals, Conj).

%Special stream operation rewrite rules before main translation
rewrite_streamops(['trace!', Arg1, Arg2],
                  [progn, ['println!', Arg1], Arg2]) :- !.
rewrite_streamops([unique, Arg],
                  [call, [superpose, ['unique-atom', [collapse, Arg]]]]) :- !.
rewrite_streamops(['alpha-unique', Arg],
                  [call, [superpose, ['alpha-unique-atom', [collapse, Arg]]]]) :- !.
rewrite_streamops([union, [superpose|A], [superpose|B]],
                  [call, [superpose, ['union-atom', [collapse, [superpose|A]],
                                                    [collapse, [superpose|B]]]]]) :- !.
rewrite_streamops([intersection, [superpose|A], [superpose|B]],
                  [call, [superpose, ['intersection-atom', [collapse, [superpose|A]],
                                                           [collapse, [superpose|B]]]]]) :- !.
rewrite_streamops([subtraction, [superpose|A], [superpose|B]],
                  [call, [superpose, ['subtraction-atom', [collapse, [superpose|A]],
                                                          [collapse, [superpose|B]]]]]) :- !.
rewrite_streamops(X, X).

%Guarded stream ops rewrite rule application, successfully avoiding copy_term:
safe_rewrite_streamops(In, Out) :- ( compound(In), In = [Op|_], atom(Op) -> rewrite_streamops(In, Out)
                                                                          ; Out = In).

%Turn a MeTTa S-expression into a goal list. The internal difference list
%keeps a nested call from copying every goal produced below it.
translate_expr(Input, Goals, Out) :-
    translate_expr_dl(Input, Goals, [], Out).

translate_expr_dl(X, Goals, Goals, X) :-
    ((var(X) ; atomic(X)) ; X = partial(_,_)), !.
translate_expr_dl([H0|T0], Goals0, Goals, Out) :-
        safe_rewrite_streamops([H0|T0],[H|T]),
        translate_expr_dl(H, Goals0, AfterHead, HV),
        %--- Translator rules ---:
        ( nonvar(HV), translator_rule(HV) -> ( catch_recover(type_declaration(HV, TypeChain), fail)
                                               -> TypeChain = [->|Xs],
                                                  append(ArgTypes, [_], Xs),
                                                  translate_args_by_type_dl(T, ArgTypes, AfterHead, AfterArgs, T1)
                                                ; translate_args_dl(T, AfterHead, AfterArgs, T1) ),
                                             append(T1,[Gs],Args),
                                             HookCall =.. [HV|Args],
                                             call(HookCall),
                                             translate_expr_dl(Gs, AfterArgs, Goals, Out)
        ; atom(HV), translate_special_dl(HV, T, AfterHead, Goals, Out) -> true
        %The Prolog importer consumes its function-name list as data. Keeping
        %that argument literal makes its translation stable after those names
        %have become registered functions during an earlier space life.
        ; translate_prolog_import_dl(HV, T, AfterHead, Goals, Out) -> true
        %--- Automatic 'smart' dispatch, translator deciding when to create a predicate call, data list, or dynamic dispatch: ---
        ; %Known function => direct call:
          ( is_list(T),
            ( atom(HV), fun_here(HV), Fun = HV, IsPartial = false, Bound = []
            ; compound(HV), HV = partial(Fun, Bound), IsPartial = true
            ) % Check for type definition [:,HV,TypeChain]
            -> findall(TypeChain, catch_recover(type_declaration(Fun, TypeChain), fail), TypeChains),
               list_to_set(TypeChains, UniqueTypeChains),
               ( UniqueTypeChains \= []
                 -> length(T, NewInputArity),
                    length(Bound, BoundArity),
                    InputArity is BoundArity + NewInputArity,
                    Arity is InputArity + 1,
                    ( incomplete_application_kind(Fun, Arity, ApplicationKind), ApplicationKind == overapplied
                      -> AfterHead = [throw_function_overapplication(Fun, InputArity)|Goals]
                       ; maplist({Fun,T,IsPartial,Bound,Out}/[TypeChain,BranchGoal]>>(
                                 typed_functioncall_branch(Fun, TypeChain, T, [], IsPartial, Bound, Out, BranchGoal)), UniqueTypeChains, Branches),
                         disj_list(Branches, Disj),
                         AfterHead = [Disj|Goals] )
              ; translate_args_dl(T, AfterHead, AfterArgs, AVs),
                ( IsPartial -> append(Bound, AVs, AllAVs) ; AllAVs = AVs ),
                build_call_or_partial_dl(Fun, AllAVs, Out, AfterArgs, Goals, []))
          %Literals (numbers, strings, etc.), known non-function atom => data:
          ; ( atomic(HV), \+ atom(HV) ; atom(HV), \+ fun_here(HV) ) -> note_symbol_head(HV),
                                                                       translate_args_dl(T, AfterHead, Goals, AVs),
                                                                       Out = [HV|AVs]
          %Plain data list: evaluate inner fun-sublists
          ; is_list(HV) -> translate_args_dl(T, AfterHead, AfterArgs, AVs),
                           eval_data_term_dl(HV, AfterArgs, Goals, HV1),
                           Out = [HV1|AVs]
          %Unknown head (var/compound) => runtime dispatch:
          ; translate_args_dl(T, AfterHead, BeforeReduce, AVs),
            BeforeReduce = [reduce([HV|AVs], Out)|Goals] )).

%First-argument indexing keeps each special form independent of the number of
%other forms. A clause fails on an unsupported arity so ordinary function or
%data dispatch can still handle that expression.
translate_special_dl(superpose, [Args], AfterHead, Goals, Out) :-
    is_list(Args),
    build_superpose_branches(Args, Out, Branches),
    disj_list(Branches, Disj),
    AfterHead = [Disj|Goals].
translate_special_dl(collapse, [Expr], AfterHead, Goals, Out) :-
    translate_expr_to_conj(Expr, Conj, ExprValue),
    AfterHead = [findall(ExprValue, Conj, Out)|Goals].
translate_special_dl(cut, [], AfterHead, Goals, true) :-
    AfterHead = [(!)|Goals].
translate_special_dl(test, [Expr, Expected], AfterHead, Goals, Out) :-
    translate_expr_to_conj(Expr, Conj, Value),
    TestGoal = ( findall(Value, Conj, Results),
                 test_answer_value(Results, Actual) ),
    AfterHead = [TestGoal|AfterFindall],
    translate_expr_dl(Expected, AfterFindall, BeforeTest, ExpectedValue),
    BeforeTest = [test(Actual, ExpectedValue, Out)|Goals].
translate_special_dl('test-no-answer', [Expr], AfterHead, Goals, Out) :-
    translate_expr_to_conj(Expr, Conj, Value),
    AfterHead = [findall(Value, Conj, Results),
                 'test-no-answer'(Results, Out)|Goals].
translate_special_dl(once, [Expr], AfterHead, Goals, Out) :-
    translate_expr_to_conj(Expr, Conj, Out),
    AfterHead = [once(Conj)|Goals].
translate_special_dl(hyperpose, [List], AfterHead, Goals, Out) :-
    ( nonvar(List), is_list(List)
      -> build_hyperpose_branches(List, Branches),
         current_metta_module(Module),
         AfterHead = [concurrent_and(member((Goal, Result), Branches),
                                     hyperpose_branch(Module, Goal, Result,
                                                      Out))|Goals]
      ; translate_expr_dl(List, AfterHead, BeforeHyperpose, ListValue),
        BeforeHyperpose = [hyperpose_runtime(ListValue, Out)|Goals] ).
translate_special_dl(with_mutex, [Mutex, Expr], AfterHead, Goals, Out) :-
    translate_expr_to_conj(Expr, Conj, Out),
    AfterHead = [with_mutex(Mutex, Conj)|Goals].
translate_special_dl(transaction, [Expr], AfterHead, Goals, Out) :-
    translate_expr_to_conj(Expr, Conj, Out),
    AfterHead = [transaction(Conj)|Goals].

translate_special_dl(progn, [], Goals, Goals, []).
translate_special_dl(progn, Exprs, AfterHead, Goals, Out) :-
    Exprs = [_|_],
    translate_args_dl(Exprs, AfterHead, Goals, Outs),
    last(Outs, Out).
translate_special_dl(prog1, [First|Rest], AfterHead, Goals, Out) :-
    translate_expr_dl(First, AfterHead, AfterFirst, Out),
    translate_args_dl(Rest, AfterFirst, Goals, _).

translate_special_dl(if, [Cond, Then], AfterHead, Goals, Out) :-
    translate_expr_to_conj(Cond, CondConj, CondValue),
    translate_expr_to_conj(Then, ThenConj, ThenValue),
    build_branch(ThenConj, ThenValue, Out, ThenBranch),
    ( CondConj == true
      -> AfterHead = [(CondValue == true -> ThenBranch)|Goals]
      ; AfterHead = [(CondConj,
                      (CondValue == true -> ThenBranch))|Goals] ).
translate_special_dl(if, [Cond, Then, Else], AfterHead, Goals, Out) :-
    translate_expr_to_conj(Cond, CondConj, CondValue),
    translate_expr_to_conj(Then, ThenConj, ThenValue),
    translate_expr_to_conj(Else, ElseConj, ElseValue),
    build_branch(ThenConj, ThenValue, Out, ThenBranch),
    build_branch(ElseConj, ElseValue, Out, ElseBranch),
    ( CondConj == true
      -> AfterHead = [(CondValue == true -> ThenBranch ; ElseBranch)|Goals]
      ; AfterHead = [(CondConj,
                      (CondValue == true -> ThenBranch ; ElseBranch))|Goals] ).
translate_special_dl(case, [KeyExpr, PairsExpr], AfterHead, Goals, Out) :-
    ( select(Found, PairsExpr, Rest),
      subsumes_term(['Empty', _], Found),
      Found = ['Empty', DefaultExpr],
      NormalCases = Rest
      -> translate_expr_to_conj(KeyExpr, KeyConj, KeyValue),
         translate_case(NormalCases, KeyValue, Out, CaseGoal, KeyGoals),
         translate_expr_to_conj(DefaultExpr, DefaultConj, DefaultValue),
         build_branch(DefaultConj, DefaultValue, Out, DefaultBranch),
         %The soft cut runs the key once. Writing this as
         %`(KeyConj, CaseGoal) ; \+ KeyConj, DefaultBranch` evaluates the key a
         %second time to decide the default, so a key with a side effect ran it
         %twice and an expensive key cost twice as much. A hard `->` would run
         %it once but commit to the first key value, which loses the other
         %answers of a nondeterministic key such as (superpose (1 2)).
         Combined = ( KeyConj *-> CaseGoal
                    ; DefaultBranch ),
         append(KeyGoals, [Combined|Goals], AfterHead)
      ; translate_expr_dl(KeyExpr, AfterHead, AfterKey, KeyValue),
        translate_case(PairsExpr, KeyValue, Out, CaseGoal, KeyGoals),
        append(KeyGoals, [CaseGoal|Goals], AfterKey) ).

translate_special_dl('and-then', [A, B], AfterHead, Goals, Out) :-
    translate_expr_to_conj(A, ConjA, ValueA),
    translate_expr_to_conj(B, ConjB, ValueB),
    AfterHead = [(ConjA,
                  (ValueA == true -> (ConjB, Out = ValueB)
                                    ; Out = false))|Goals].
translate_special_dl('or-else', [A, B], AfterHead, Goals, Out) :-
    translate_expr_to_conj(A, ConjA, ValueA),
    translate_expr_to_conj(B, ConjB, ValueB),
    AfterHead = [(ConjA,
                  (ValueA == true -> Out = true
                                    ; (ConjB, Out = ValueB)))|Goals].

translate_special_dl(let, Args, AfterHead, Goals, Out) :-
    translate_let_dl(Args, AfterHead, Goals, Out).
translate_special_dl(chain, Args, AfterHead, Goals, Out) :-
    translate_let_dl(Args, AfterHead, Goals, Out).
translate_special_dl('let*', [Binds, Body], AfterHead, Goals, Out) :-
    letstar_to_rec_let(Binds, Body, RecursiveLet),
    translate_expr_dl(RecursiveLet, AfterHead, Goals, Out).
translate_special_dl(sealed, [Vars, Expr], AfterHead, Goals, Out) :-
    translate_expr_to_conj(Expr, Conj, Value),
    AfterHead = [copy_term(Vars, [Conj, Value], _, [CopiedConj, Out]),
                 CopiedConj|Goals].

translate_special_dl('forall', [Generator, Test], AfterHead, Goals, Out) :-
    ( is_list(Generator)
      -> Generator = [GeneratorHead|GeneratorArgs],
         translate_expr(GeneratorHead, HeadGoals, GeneratorHeadValue),
         translate_args(GeneratorArgs, ArgGoals, GeneratorArgValues),
         append(HeadGoals, ArgGoals, GeneratorGoals),
         GeneratorList = [GeneratorHeadValue|GeneratorArgValues]
      ; translate_expr(Generator, GeneratorGoals, GeneratorHeadValue),
        GeneratorList = [GeneratorHeadValue] ),
    TestList = [TestHeadValue, GeneratedValue],
    goals_list_to_conj(GeneratorGoals, GeneratorPrefix),
    GeneratorGoal = (GeneratorPrefix,
                     reduce(GeneratorList, GeneratedValue)),
    translate_expr_dl(Test, AfterHead, BeforeForall, TestHeadValue),
    BeforeForall = [(forall(GeneratorGoal,
                            (reduce(TestList, Truth), Truth == true))
                     -> Out = true
                      ; Out = false)|Goals].
translate_special_dl('foldall', [Accumulator, Generator, InitialExpr],
                     AfterHead, Goals, Out) :-
    translate_expr_to_conj(InitialExpr, InitialConj, Initial),
    translate_expr_dl(Accumulator, AfterHead, AfterAccumulator,
                      AccumulatorValue),
    ( Generator = [Mode|_],
      (Mode == match ; Mode == let ; Mode == 'let*')
      -> Lambda = ['|->', [], Generator],
         translate_expr_dl(Lambda, AfterAccumulator, AfterGenerator,
                           GeneratorHeadValue),
         GeneratorList = [GeneratorHeadValue]
      ; is_list(Generator)
      -> Generator = [GeneratorHead|GeneratorArgs],
         translate_expr_dl(GeneratorHead, AfterAccumulator,
                           AfterGeneratorHead, GeneratorHeadValue),
         translate_args_dl(GeneratorArgs, AfterGeneratorHead,
                           AfterGenerator, GeneratorArgValues),
         GeneratorList = [GeneratorHeadValue|GeneratorArgValues]
      ; translate_expr_dl(Generator, AfterAccumulator, AfterGenerator,
                          GeneratorHeadValue),
        GeneratorList = [GeneratorHeadValue] ),
    AfterGenerator = [InitialConj,
                      foldall(agg_reduce(AccumulatorValue, Value),
                              reduce(GeneratorList, Value), Initial, Out)|Goals].

translate_special_dl('foldl-atom', [ListExpr, InitialExpr, AccVar, ItemVar,
                                    Body], AfterHead, Goals, Out) :-
    translate_expr_to_conj(ListExpr, ListConj, List),
    translate_expr_to_conj(InitialExpr, InitialConj, Initial),
    translate_expr_to_conj(Body, BodyConj, BodyValue),
    exclude(==(true), [ListConj, InitialConj], PrefixGoals),
    append(PrefixGoals,
           [foldl([ItemVar, AccVar, Next]>>(BodyConj, Next = BodyValue),
                  List, Initial, Out)|Goals],
           AfterHead).
translate_special_dl('map-atom', [ListExpr, ItemVar, Body],
                     AfterHead, Goals, Out) :-
    translate_expr_to_conj(ListExpr, ListConj, List),
    translate_expr_to_conj(Body, BodyConj, BodyValue),
    exclude(==(true), [ListConj], PrefixGoals),
    append(PrefixGoals,
           [maplist([ItemVar, ItemOut]>>(BodyConj, ItemOut = BodyValue),
                    List, Out)|Goals],
           AfterHead).
translate_special_dl('filter-atom', [ListExpr, ItemVar, Condition],
                     AfterHead, Goals, Out) :-
    translate_expr_to_conj(ListExpr, ListConj, List),
    translate_expr_to_conj(Condition, CondConj, CondValue),
    exclude(==(true), [ListConj], PrefixGoals),
    append(PrefixGoals,
           [include([ItemVar]>>(CondConj, CondValue), List, Out)|Goals],
           AfterHead).
translate_special_dl('|->', [Args, Body], AfterHead, Goals, Out) :-
    next_lambda_name(Function),
    term_variables(Body, AllVars),
    term_variables(Args, ArgVars),
    exclude({ArgVars}/[Var]>>memberchk_eq(Var, ArgVars), AllVars, FreeVars),
    append(FreeVars, Args, FullArgs),
    translate_clause([=, [Function|FullArgs], Body], Clause),
    register_fun(Function),
    assertz(Clause, Ref),
    record_source_assertion(Ref),
    format(atom(Label), "metta lambda (~w)", [Function]),
    maybe_print_compiled_clause(Label, ['|->', Args, Body], Clause),
    length(FullArgs, InputArity),
    Arity is InputArity + 1,
    register_arity(Function, Arity),
    ( FreeVars == [] -> Out = Function ; Out = partial(Function, FreeVars) ),
    AfterHead = Goals.

translate_special_dl('add-atom', Args, AfterHead, Goals, Out) :-
    translate_space_update_dl('add-atom', Args, AfterHead, Goals, Out).
translate_special_dl('remove-atom', Args, AfterHead, Goals, Out) :-
    translate_space_update_dl('remove-atom', Args, AfterHead, Goals, Out).
translate_special_dl(match, [SpaceExpr, Pattern, Body], AfterHead, Goals,
                     Out) :-
    translate_expr_dl(SpaceExpr, AfterHead, BeforeMatch, Space),
    BeforeMatch = [match(Space, Pattern, Out, Out)|AfterMatch],
    translate_expr_dl(Body, AfterMatch, Goals, Out).
translate_special_dl(translatePredicate, [[Predicate|Args]], AfterHead, Goals,
                     _Out) :-
    translate_args_dl(Args, AfterHead, BeforePredicate, ArgValues),
    Goal =.. [Predicate|ArgValues],
    BeforePredicate = [Goal|Goals].
translate_special_dl(call, [[Function|Args]], AfterHead, Goals, Out) :-
    translate_args_dl(Args, AfterHead, BeforeCall, ArgValues),
    append(ArgValues, [Out], CallArgs),
    Goal =.. [Function|CallArgs],
    BeforeCall = [Goal|Goals].
translate_special_dl(reduce, [Expr], AfterHead, Goals, Out) :-
    ( Expr == []
      -> Out = [],
         AfterHead = Goals
      ; var(Expr)
      -> translate_expr_dl(Expr, AfterHead, BeforeReduce, ExprValue),
         BeforeReduce = [reduce(ExprValue, Out)|Goals]
      ; Expr = [Function|Args],
        translate_args_dl(Args, AfterHead, BeforeReduce, ArgValues),
        ExprValue = [Function|ArgValues],
        BeforeReduce = [reduce(ExprValue, Out)|Goals] ).
translate_special_dl(eval, [Arg], AfterHead, Goals, Out) :-
    AfterHead = [eval(Arg, Out)|Goals].
translate_special_dl(quote, [Expr], Goals, Goals, Expr).
translate_special_dl('catch', [Expr], AfterHead, Goals, Out) :-
    translate_expr(Expr, ExprGoals, ExprOut),
    goals_list_to_conj(ExprGoals, Conj),
    CatchGoal = catch((Conj, Out = ExprOut),
                      Exception,
                      ( control_exception(Exception)
                        -> throw(Exception)
                        ; Exception = error(Type, Context)
                        -> Out = ['Error', Type, Context]
                        ; Out = ['Error', Exception] )),
    AfterHead = [CatchGoal|Goals].

translate_let_dl([Pattern, Value, In], AfterHead, Goals, Out) :-
    AfterHead = [unify_with_occurs_check(PatternValue, ValueResult)|AfterUnify],
    translate_expr_dl(Pattern, AfterUnify, AfterPattern, PatternValue),
    translate_expr_dl(Value, AfterPattern, AfterValue, ValueResult),
    translate_expr_dl(In, AfterValue, Goals, Out).

translate_space_update_dl(Operation, [SpaceExpr, Atom], AfterHead, Goals,
                          Out) :-
    translate_expr_dl(SpaceExpr, AfterHead, BeforeOperation, Space),
    Goal =.. [Operation, Space, Atom, Out],
    BeforeOperation = [Goal|Goals].

prolog_function_importer(import_prolog_functions_from_file).
prolog_function_importer(import_prolog_functions_from_module).

translate_prolog_import_dl(Importer, [File, FunctionNames], Goals0, Goals, Out) :-
    atom(Importer),
    prolog_function_importer(Importer),
    translate_expr_dl(File, Goals0, BeforeImport, ResolvedFile),
    Goal =.. [Importer, ResolvedFile, FunctionNames, Out],
    BeforeImport = [Goal|Goals].

%Generate actual function call or partial if arity not complete:
build_call_or_partial(Fun, AVs, Out, Inner, Extra, Goals) :-
    append(Inner, AfterInner, Goals),
    build_call_or_partial_dl(Fun, AVs, Out, AfterInner, [], Extra).

build_call_or_partial_dl(Fun, AVs, Out, Goals0, Goals, Extra) :-
    length(AVs, N),
    Arity is N + 1,
    ( maybe_specialize_call(Fun, AVs, Out, Goal)
      -> append([Goal|Extra], Goals, Goals0)
    ; arity(Fun, Arity)
      -> resolve_memoization(Fun, AVs, Out, Goal),
         append([Goal|Extra], Goals, Goals0)
    ; incomplete_application_kind(Fun, Arity, partial)
      -> Out = partial(Fun, AVs),
         Goals0 = Goals
    ; Goals0 = [throw_function_overapplication(Fun, N)|Goals] ).

%Type function call generation, returns function call plus typechecks for input and output:
typed_functioncall_branch(Fun, TypeChain, T, GsH, IsPartial, Bound, Out, BranchGoal) :-
    TypeChain = [->|Xs],
    append(ArgTypes, [OutType], Xs), !,
    translate_args_by_type(T, ArgTypes, GsT2, AVsTmp0),
    ( IsPartial -> append(Bound, AVsTmp0, AVsTmp) ; AVsTmp = AVsTmp0 ),
    append(GsH, GsT2, InnerTmp),
    %The output check asks whether the result has the declared type, and
    %nothing reads OutType afterwards, so one witness is the whole answer. A
    %soft cut here instead enumerates every derivation and succeeds once per
    %derivation, which repeats the call's answer: with (: (a b) (A B)) declared
    %alongside (: a A) and (: b B), a function returning (a b) answered twice.
    %The argument checks above keep their soft cut, because a shared type
    %variable there does have to backtrack to find a consistent assignment.
    ( (OutType == '%Undefined%' ; OutType == '_' ; OutType == 'Atom')
       -> Extra = [] ; Extra = [('get-type'(Out, OutType) -> true ; 'get-metatype'(Out, OutType))] ),
    build_call_or_partial(Fun, AVsTmp, Out, InnerTmp, Extra, GoalsList),
    goals_list_to_conj(GoalsList, BranchGoal).


%Selectively apply translate_args for non-Expression args while Expression args stay as data input:
translate_args_by_type([], _, [], []) :- !.
translate_args_by_type([A|As], [T|Ts], GsOut, [AV|AVs]) :-
    translate_args_by_type_dl([A|As], [T|Ts], GsOut, [], [AV|AVs]).

translate_args_by_type_dl([], _, Goals, Goals, []) :- !.
translate_args_by_type_dl([A|As], [T|Ts], Goals0, Goals, [AV|AVs]) :-
    ( T == 'Atom'
      -> AV = A,
         AfterArg = Goals0
    ; translate_expr_dl(A, Goals0, AfterTranslation, AV),
      ( (T == '%Undefined%' ; T == '_')
        -> AfterArg = AfterTranslation
      ; AfterTranslation = [('get-type'(AV, T) *-> true ; 'get-metatype'(AV, T))|AfterArg] ) ),
    translate_args_by_type_dl(As, Ts, AfterArg, Goals, AVs).

%Handle data list:
eval_data_term_dl(X, Goals, Goals, X) :- (var(X); atomic(X)), !.
eval_data_term_dl([F|As], Goals0, Goals, Val) :-
    ( atom(F), fun_here(F) -> translate_expr_dl([F|As], Goals0, Goals, Val)
                           ; eval_data_list_dl([F|As], Goals0, Goals, Val) ).

%Handle data list entry:
eval_data_list_dl([], Goals, Goals, []).
eval_data_list_dl([E|Es], Goals0, Goals, [V|Vs]) :-
    ( is_list(E) -> eval_data_term_dl(E, Goals0, AfterEntry, V)
                 ; V = E, AfterEntry = Goals0 ),
    eval_data_list_dl(Es, AfterEntry, Goals, Vs).


%Convert let* to recursive let:
letstar_to_rec_let([], Body, Body) :- !.
letstar_to_rec_let([[Pat,Val]],Body,[let,Pat,Val,Body]).
letstar_to_rec_let([[Pat,Val]|Rest],Body,[let,Pat,Val,Out]) :- letstar_to_rec_let(Rest,Body,Out).

% Constructs the goal for a single branch of an if-then-else/case.
build_branch(true, Val, Out, (Out = Val)) :- !.
%A variable-valued branch unifies with the output at RUNTIME, inside the
%branch. Unifying at translate time (Val = Out) is only sound when Val is
%private to the branch, and it is not when the branch's value is a clause
%parameter (an if arm of (let* (($c $a)) $a) collapses to the parameter $a):
%aliasing the head's output with the parameter makes the other arm's
%unification corrupt it, so the clause fails wherever that arm runs.
%merge_branch_returns/3 restores the translate-time binding afterwards,
%exactly where the whole clause proves it private.
build_branch(Con, Val, Out, (Con, Out = Val)) :- var(Val), !.
build_branch(Con, Val, Out, (Val = Out, Con)).

%Restore last-call optimization where it is safe: a branch ending with the
%runtime unification (Out = V) keeps a tail-recursive loop from running in
%constant stack, since the recursive call is no longer last. The first pass
%records each variable's total occurrences and first/last traversal positions.
%The second pass knows each branch's position interval, so two AVL lookups prove
%that V is absent from the head, confined to this branch, and produced before
%the final unification. No branch re-scans the whole clause.
%
%Unbound variables are valid assoc keys while their standard-order relation is
%unchanged. All return bindings are therefore delayed until every lookup has
%finished: https://www.swi-prolog.org/pldoc/doc/_SWI_/library/assoc.pl
merge_branch_returns(Head, Body0, Body) :-
    empty_assoc(Empty),
    mbr_collect_stats(Head, 0, _HeadEnd, Empty, HeadStats),
    mbr_collect_stats(Body0, 0, End, Empty, Stats),
    mbr_goal(Body0, HeadStats, Stats, 0, WalkEnd, Body, Bindings, []),
    WalkEnd =:= End,
    mbr_bind_returns(Bindings).

mbr_goal((A , B), H, Stats, P0, P, (A1 , B1), Bs0, Bs) :- !,
    mbr_goal(A, H, Stats, P0, P1, A1, Bs0, Bs1),
    mbr_goal(B, H, Stats, P1, P, B1, Bs1, Bs).
mbr_goal((C -> T ; E), H, Stats, P0, P, (C -> T1 ; E1), Bs0, Bs) :- !,
    mbr_advance_term(C, P0, P1),
    mbr_branch(T, H, Stats, P1, P2, T1, Bs0, Bs1),
    mbr_branch(E, H, Stats, P2, P, E1, Bs1, Bs).
mbr_goal((A ; B), H, Stats, P0, P, (A1 ; B1), Bs0, Bs) :- !,
    mbr_goal(A, H, Stats, P0, P1, A1, Bs0, Bs1),
    mbr_goal(B, H, Stats, P1, P, B1, Bs1, Bs).
mbr_goal((C -> T), H, Stats, P0, P, (C -> T1), Bs0, Bs) :- !,
    mbr_advance_term(C, P0, P1),
    mbr_branch(T, H, Stats, P1, P, T1, Bs0, Bs).
mbr_goal(G, _, _, P0, P, G, Bs, Bs) :-
    mbr_advance_term(G, P0, P).

mbr_branch(B0, H, Stats, P0, P, B, Bs0, Bs) :-
    mbr_goal(B0, H, Stats, P0, P, B1, Bs0, Bs1),
    ( mbr_merge_candidate(B0, H, Stats, P0, P, V, Out)
      -> mbr_split(B1, B, _),
         Bs1 = [V-Out|Bs]
    ; B = B1,
      Bs1 = Bs ).

mbr_merge_candidate(B0, HeadStats, Stats, P0, P, V, Out) :-
    mbr_split(B0, _Prefix, (Out = V)),
    var(V),
    var(Out),
    V \== Out,
    \+ get_assoc(V, HeadStats, _),
    get_assoc(V, Stats, var_stat(Count, First, Last)),
    Count > 1,
    First >= P0,
    Last < P.

mbr_bind_returns([]).
mbr_bind_returns([V-Out|Bindings]) :-
    V = Out,
    mbr_bind_returns(Bindings).

%Split a conjunction into everything-but-last and its last conjunct:
mbr_split((A , B), Prefix, Last) :- !,
    ( mbr_split(B, P1, Last), ( P1 == true -> Prefix = A ; Prefix = (A , P1) ) ).
mbr_split(G, true, G).

%Collect every variable's occurrence count and traversal interval in one pass.
mbr_collect_stats(T, P0, P, Stats0, Stats) :-
    ( var(T)
      -> ( get_assoc(T, Stats0, var_stat(Count0, First, _))
           -> Count is Count0 + 1,
              put_assoc(T, Stats0, var_stat(Count, First, P0), Stats)
         ; put_assoc(T, Stats0, var_stat(1, P0, P0), Stats) ),
         P is P0 + 1
    ; compound(T)
      -> functor(T, _, N),
         mbr_collect_stats_args(1, N, T, P0, P, Stats0, Stats)
    ; P = P0,
      Stats = Stats0 ).

mbr_collect_stats_args(I, N, _, P, P, Stats, Stats) :- I > N, !.
mbr_collect_stats_args(I, N, T, P0, P, Stats0, Stats) :-
    arg(I, T, Arg),
    mbr_collect_stats(Arg, P0, P1, Stats0, Stats1),
    I1 is I + 1,
    mbr_collect_stats_args(I1, N, T, P1, P, Stats1, Stats).

%Advance over the same depth-first variable positions without rebuilding the
%association. This pass also reconstructs only the control nodes it changes.
mbr_advance_term(T, P0, P) :-
    ( var(T) -> P is P0 + 1
    ; compound(T) -> functor(T, _, N), mbr_advance_args(1, N, T, P0, P)
    ; P = P0 ).

mbr_advance_args(I, N, _, P, P) :- I > N, !.
mbr_advance_args(I, N, T, P0, P) :-
    arg(I, T, Arg),
    mbr_advance_term(Arg, P0, P1),
    I1 is I + 1,
    mbr_advance_args(I1, N, T, P1, P).

%Translate case expression recursively into nested if:
translate_case([], _, _, fail, []) :- !.
translate_case([[K,VExpr]|Rs], Kv, Out, Goal, KGo) :- translate_expr_to_conj(VExpr, ConV, VOut),
                                                      constrain_args(K, Kc, Gc),
                                                      build_branch(ConV, VOut, Out, Then),
                                                      ( Rs == [] -> Goal = ((Kv = Kc) -> Then), KGi=[]
                                                                  ; translate_case(Rs, Kv, Out, Next, KGi),
                                                                    Goal = ((Kv = Kc) -> Then ; Next) ),
                                                      append([Gc,KGi], KGo).

%Translate arguments recursively:
translate_args([], [], []).
translate_args([X|Xs], Goals, [V|Vs]) :-
    translate_args_dl([X|Xs], Goals, [], [V|Vs]).

translate_args_dl([], Goals, Goals, []).
translate_args_dl([X|Xs], Goals0, Goals, [V|Vs]) :-
    translate_expr_dl(X, Goals0, AfterExpr, V),
    translate_args_dl(Xs, AfterExpr, Goals, Vs).

%Build A ; B ; C ... from a list:
disj_list([], fail) :- !.
disj_list([G], G) :- !.
disj_list([G|Gs], (G ; R)) :- disj_list(Gs, R).

%Build one disjunct per branch: (Conj, Out = Val):
build_superpose_branches([], _, []).
build_superpose_branches([E|Es], Out, [B|Bs]) :- translate_expr_to_conj(E, Conj, Val),
                                                 build_branch(Conj, Val, Out, B),
                                                 build_superpose_branches(Es, Out, Bs).

%Build hyperpose branch as a goal list for concurrent_maplist to consume:
build_hyperpose_branches([], []).
build_hyperpose_branches([E|Es], [(Goal, Res)|Bs]) :- translate_expr_to_conj(E, Goal, Res),
                                                      build_hyperpose_branches(Es, Bs).

%Run each branch under the module captured by the caller. SWI global variables
%are thread-local, so a concurrent_and/2 worker otherwise defaults to user and
%cannot resolve functions compiled into a named space.
hyperpose_branch(Module, Goal, Res, Out) :-
    with_metta_module(Module, (call(Module:Goal), Out = Res)).

%Runtime hyperpose path for variable/computed list arguments.
hyperpose_runtime(Exprs, Out) :-
    is_list(Exprs),
    current_metta_module(Module),
    concurrent_and(member(Expr, Exprs),
                   hyperpose_eval(Module, Expr, Out)).

hyperpose_eval(Module, Expr, Out) :-
    with_metta_module(Module,
                      ( translate_expr(Expr, Goals, Out),
                        call_goals_in_(Module, Goals) )).

%Like membercheck but with direct equality rather than unification
memberchk_eq(V, [H|_]) :- V == H, !.
memberchk_eq(V, [_|T]) :- memberchk_eq(V, T).

%Generate a readable lambda name. The counter has to be process-wide: SWI
%global variables are thread-local, so a counter kept in one gave every
%hyperpose worker its own sequence starting at 1, and two threads compiling a
%lambda both produced lambda_1. assertz then added the second body to the first
%lambda's predicate rather than defining a new one, and one lambda answered
%with every colliding branch's result. gensym/2 counts in a process-wide flag
%and is the same generator filereader.pl already uses for load ids.
next_lambda_name(Name) :- gensym(lambda_, Name).

declared_output_type(F, OutType) :- atom(F),
									nonvar(OutType),
									catch_recover(type_declaration(F, TypeChain), fail),
									TypeChain = [->|Types],
									append(_, [DeclaredOutType], Types),
									DeclaredOutType == OutType.
