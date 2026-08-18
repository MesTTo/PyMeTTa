% Purpose: compile MeTTa expressions and equations into executable Prolog,
%   including dynamic dispatch, control forms, higher-order calls, and
%   branch-return optimization.
% Assumes:
%   - merge_branch_returns/3 does not bind variable keys until its assoc
%     lookups finish [source 2026-08-14:
%     https://www.swi-prolog.org/pldoc/doc/_SWI_/library/assoc.pl].
% Guarantees:
%   - User get-type equations extend the deduplicating type boundary through
%     get_type_rule/2 [tested 2026-08-15: translator_type_extensions].
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
%     even when builtin type declarations are loaded [tested 2026-08-15:
%     translator_evaluation_errors].
%   - Compiler diagnostics contain ANSI escapes only on terminal streams
%     [tested 2026-08-14: translator_terminal_output].
%   - A lambda's compiled clause lands in the space it was written in, so
%     every lambda form reaches that space's own functions [tested 2026-08-16:
%     translator_lambda_space_scope]. +10 inferences once per lambda
%     compiled, nothing per call [measured 2026-08-16: 1338 to 1348 for one
%     compile-and-run, 10,005 either way over 2,000 elements].
%   - Special forms dispatch through first-argument-indexed clauses
%     [tested 2026-08-14: translator_special_dispatch].
%   - The translatePredicate and call seams refuse a shape they cannot compile
%     rather than building a data list named after the form
%     [tested 2026-08-16: translator_special_dispatch:malformed_seam_is_refused].
%   - A translator rule whose expansion is built in Prolog compiles to the
%     goals it emits, including a constant folded at compile time, and is
%     refused when a quote leaves that expansion as data
%     [tested 2026-08-16: translator_prolog_authored_rules].
%   - Higher-arity dynamic calls bypass the operator-table lookup
%     [tested 2026-08-14: tests/performance/reduce_dispatch.pl].
%   - Prolog import forms have exactly one translation
%     [tested 2026-08-14: translator_prolog_imports].
%   - Space-headed translatePredicate forms use the space provider instead of
%     a predicate inherited from user [tested:
%     translator_special_dispatch:space_predicates_use_space_storage].
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
    retractall(fun_meta_clause(F, _, _)),
    retractall(fun_head_goals(F)).

% A head argument that is itself a function call is Curry's functional
% pattern: (= (halfof (dbl $n)) $n) compiles to halfof(A,B) :- dbl(B,A) and
% runs dbl backwards. constrain_args/3 turns it into a goal, so the retained
% equation no longer holds the whole head, and anything reading equations back
% has to know. src/duals.pl refuses to build a dual for such a function rather
% than negate a head it cannot see. Recording only the non-empty case keeps
% this to one == test per compiled equation, which costs no inference at all
% [measured 2026-08-15: ==/2 is compiled inline, a predicate call is not].
:- dynamic fun_head_goals/1.

note_head_goals(F) :- ( fun_head_goals(F)
                        -> true
                         ; assertz(fun_head_goals(F), Ref),
                           record_source_assertion(Ref) ).

%Pattern matching, structural and functional/relational constraints on arguments:
constrain_args(X, X, []) :- (var(X); atomic(X)), !.
%An IN-PLACE TYPE ANNOTATION in a head parameter position: `(: $x T)` matches
%anything whose type includes T and binds $x to it, and `(: $x $t)` binds $t to
%each applicable type, one branch each. hyperon-experimental issue #177's
%dynamic half, the point being to put a type where it can PRUNE rather than
%only in a top-level declaration.
%
%It desugars to a plain variable plus a type premise, and the premise is not a
%new relation: it is the SAME acceptance the engine already compiles for a
%typed argument position, `(has_type(V,T) *-> true ; get-metatype(V,T))`. So
%`(: $x T)` means exactly what a declared parameter of type T means, and anyone
%who knows one knows the other.
%
%That shape is also what makes the two fixtures work for the same reason. A
%declared type wins where there is one, `(: $x Person)` accepting Ann and
%refusing Rex; and a METATYPE restriction works because has_type/2 fails on a
%symbol with no declaration, so `(: $c Symbol)` falls through to get-metatype/2
%and accepts any symbol. Symbol, Variable, Grounded and Expression are subtypes
%of Atom, so that fallback is what makes the annotation reach all four atom
%kinds and not only declared types. Nondeterminism is native and free: with the
%type a VARIABLE, has_type/2 enumerates, so `(: $x $t)` gives one branch per
%declared type and the shared form `(: $x $t) (: $y $t)` constrains the two
%parameters to agree.
%
%`:` AND NOT A NEW SPELLING, which is the whole difficulty and was got wrong
%here twice before it was got right. Issue #177 raises the collision and
%proposes `::` "when position cannot distinguish the two uses"; this tree tried
%`::` and then `:>`, and both are worse than the collision they avoid. `::` is
%what metta-lang.dev's tutorials use as an ordinary cons constructor, in
%`(= (length (:: $x $xs)) (+ 1 (length $xs)))` and 63 places after it, so it
%silently reinterpreted anyone's list code into a non-terminating recursion.
%`:>` collides with nothing and reads as a SUBTYPE bound to anyone who has met
%Scala's `<:` and `>:`, which is a different lie.
%
%Position CAN distinguish the two uses, and LeaTTa proved it by implementing
%exactly this against a mechanised Hyperon semantics. Two gates:
%
%  1. a pattern that IS a colon expression stays structural, so
%     `(match &self (: $x Human) $x)` still retrieves stored declarations;
%  2. below that, only `(: $variable expected)` is an annotation, and a colon
%     whose value slot is not a variable is data the walk does not look inside.
%
%[source: LeaTTa/ai-report-inplace-annotations.md, Design]. That is enough for
%this corpus. examples/reasoning/nilbc.metta is a backward-chaining proof
%search whose subject matter IS `(: proof theorem)` terms, 134 of them, and
%gate 2 covers every one whose value slot is an expression while gate 1 covers
%its knowledge-base queries. It needed ONE clause changed, a base case that
%destructures its query in the body instead of the head
%[tested: translator_inplace_annotations, a_cons_list_is_ordinary_structure,
%examples/reasoning/nilbc.metta].
constrain_args([Colon, Var, Type], Var,
               [(has_type(Var, Type) *-> true ; 'get-metatype'(Var, Type))]) :-
    nonvar(Colon), Colon == ':', var(Var), !.
%GATE TWO: a colon form whose VALUE slot is not a variable is ordinary data,
%and the walk does not descend into it either. Both halves are load-bearing.
%LeaTTa needed the second for single_sided.metta's binary-tree constructor
%`(: (Sym (: (Sym (: $x $a)) $b)) $c)`, whose inner colons are structure inside
%a value slot: a recognizer that kept descending changed the constructor
%[source: LeaTTa/ai-report-inplace-annotations.md, Design]. It earns its keep
%here too: nilbc.metta's `(bc $kb (S $d) (: ($rule $premise) $theorem))` has an
%expression in the value slot and stays the proof term it is.
constrain_args([Colon, Value, Type], [Colon, Value, Type], []) :-
    nonvar(Colon), Colon == ':', nonvar(Value), !.
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
                                                                  flatten(GoalsA,GoalsPrefix),
                                                                  ( GoalsPrefix == [] -> true ; note_head_goals(F) )
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
                                                  resolve_dispatch(Base, CallInArgs, Out, Goal),
                                                  append(GoalsBody,[Goal],FinalGoals), append(Args1,ExtraArgs,HeadArgs),
                                                  drop_superseded_arity(F, Args1, HeadArgs)
                                               ; FinalGoals= GoalsBody , HeadArgs = Args1, Out = ExpOut ),
                                               append(HeadArgs, [Out], FinalArgs),
                                               compiled_function_name(F, Predicate),
                                               Head =.. [Predicate|FinalArgs],
                                               length(FinalArgs, CompiledArity),
                                               register_arity(F, CompiledArity),
                                               append(GoalsPrefix, FinalGoals, Goals),
                                               goals_list_to_conj(Goals, BodyConj0),
                                               merge_branch_returns(Head, BodyConj0, BodyConj1),
                                               demote_safe_occurs_checks(Head, BodyConj1, BodyConj, HasNegation),
                                               ( HasNegation == found
                                                 -> quantify_negations(Head, BodyConj)
                                                  ; true ).

%The eta-expansion above gives the clause MORE arguments than its equation's
%head has, so the arity the loader registered from the source shape names a
%predicate that will never exist. Left in place, a call at that arity compiled
%straight to it: `(= (pcap $k) (|-> ($a) (pair $a $k)))` registered pcap/2 from
%its head, compiled `pcap(A, B, C) :- lambda_2(A, B, C)`, and `(pcap 5)` then
%raised `Unknown procedure: pcap/2` where the same function written with a
%NON-capturing lambda curried cleanly. A capturing lambda not currying was the
%whole of F9c, and this is why.
%
%Dropping the superseded arity lets build_call_or_partial_dl/6 fall through to
%its partial branch, which is what partial/2 exists for: `(pcap 5)` answers
%`(partial pcap (5))` and `((pcap 5) 1)` reaches reduce/3's closure case and
%runs. The fully applied `(pcap 5 1)` is unaffected, because the compiled
%arity is still registered [tested: translator_capturing_lambda_curries].
%
%Only when nothing DEFINES that arity, because a function may genuinely be
%overloaded and another of its equations may have supplied it. That equation
%re-registers the arity when it compiles, whichever order the two arrive in.
%Called ONLY from the eta-expansion branch above, which is the only place the
%two arities can differ, so an ordinary equation pays nothing for this. Called
%unconditionally instead it cost five inferences on every compiled clause,
%+4,994 over source-load's thousand equations [measured 2026-08-16].
drop_superseded_arity(_, SourceArgs, HeadArgs) :-
    same_length(SourceArgs, HeadArgs),
    !.
drop_superseded_arity(F, SourceArgs, _) :-
    length(SourceArgs, SourceInputArity),
    SourceArity is SourceInputArity + 1,
    compiled_function_name(F, Predicate),
    functor(Probe, Predicate, SourceArity),
    (   catch(clause(Probe, _), _, fail)
    ->  true
    ;   retractall(arity(F, SourceArity))
    ).

%get-type owns the answer-stream boundary. User equations therefore compile
%behind that boundary instead of becoming sibling clauses that could bypass
%its deduplication. Every other function keeps its source name.
compiled_function_name('get-type', get_type_rule) :- !.
compiled_function_name(F, F).

%Record atoms compiled as plain symbol heads together with where they were compiled:
%a stored definition can be recompiled when the function arrives late, an already
%executed expression cannot, so late registration repairs the former and warns on the latter.
:- dynamic symbol_head/2.
:- thread_local translating_runnable/0.
%The names an importer form in the runnable being compiled registers, so the
%check after it runs knows whether the expression is worth walking at all.
:- thread_local runnable_import/1.
note_symbol_head(HV) :- atom(HV), !,
                        ( translating_runnable -> Ctx = runnable ; Ctx = clause ),
                        ( symbol_head(HV, Ctx) -> true
                        ; assertz(symbol_head(HV, Ctx), Ref),
                          record_source_assertion(Ref) ).
note_symbol_head(_).

%Translate an expression that executes immediately, marking its data uses as unrepairable.
%once/1 closes the translation before the goals run, so nested imports triggered by the
%execution compile their definitions under the clause context again:
%A runnable has no head, so a variable of its own is local to it the same way a
%clause variable that is not in the head is: only the answer it produces is
%read from outside.
%
%A runnable has no occurs-check pass to thread the flag through, so this one
%costs a call. It is a thread_local with no clauses in the ordinary case, which
%is the cheapest cross-cutting signal Prolog has: one inference, against two
%for flag/3 [measured 2026-08-15].
translate_runnable_expr(C, Goals, Out) :- setup_call_cleanup(assertz(translating_runnable, Ref),
                                                             once(translate_expr(C, Goals, Out)),
                                                             erase(Ref)),
                                          ( runnable_import(_)
                                            -> refuse_call_to_own_import(C)
                                             ; true ),
                                          ( runnable_negation
                                            -> retractall(runnable_negation),
                                               quantify_negations(Out, Goals)
                                             ; true ).

%A runnable is compiled WHOLE before any of it runs, so a registration inside
%one cannot affect its own compilation. The call compiles while the name is
%still unregistered, falls through to data dispatch, and the runnable answers
%the expression instead of the value with nothing said: (d23-double 21) rather
%than 42. Both C-extension examples in the tree carry a comment warning the
%next reader to split the runnable, which is the shape of a trap rather than
%of a rule.
%
%The expression is walked only when the translation ALREADY met an importer
%form, which translate_prolog_import_dl/5 records as it goes. A directive that
%imports nothing therefore pays one lookup on an empty thread_local, the same
%signal runnable_negation uses above and for the same reason: it is the
%cheapest cross-cutting flag Prolog has.
refuse_call_to_own_import(Expr) :-
    findall(N, runnable_import(N), Names0),
    retractall(runnable_import(_)),
    sort(Names0, Names),
    (   member(Name, Names),
        \+ fun_here(Name),
        calls_head(Expr, Name)
    ->  throw(error(petta_call_to_own_import(Name),
                    context(translate_runnable_expr/3,
                            'a runnable compiles before it runs')))
    ;   true
    ).

%A call whose head is Name, anywhere below this expression. An importer's own
%name list is data rather than a call, so the search does not descend into one.
calls_head([Head|Args], Name) :-
    (   Head == Name
    ->  true
    ;   atom(Head),
        prolog_function_importer(Head)
    ->  fail
    ;   member(Sub, Args),
        is_list(Sub),
        calls_head(Sub, Name)
    ).

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

%A handler that caches by function has to know which module the call site
%lives in, because a named space compiles its own equations into its own
%module and the same name is a different function there. The handler reads
%current_metta_module/1 for itself rather than being handed it: this runs on
%every compiled call site and every reduced call, and resolving the module
%here cost between +0.09% and +0.41% inferences across six benchmarks
%[measured 2026-08-15: weighted-relation 483521 -> 485517].
resolve_dispatch(Fun, Args, Out, Goal) :-
    ( metta_dispatch_call(Fun, Args, Out, Goal)
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
%The four evaluation outcomes of the Hyperon specification are value, Empty,
%NotReducible and Error, and PeTTa already produces all four: an answer, a
%failed goal, a term handed back unevaluated, and a thrown error. Only the
%third was unreportable, because the term it yields is indistinguishable from
%data. reduce/3 carries which of the two happened and reduce/2 keeps its exact
%behaviour, so every compiled call site is unchanged
%[source: /home/user/Dev/LeaTTa/MettaHyperonFull/Core/Result.lean, EvalStatus]
%[tested: translator_reduction_status].
reduce(X, Out) :- reduce(X, Out, _).

%The cut sits immediately after each head, which is The Craft of Prolog's rule
%and the one SWI's =>/2 mechanises: Head :- Guard, !, Body, guard as early as
%possible [source: SWI-Prolog 10.1 Reference Manual, section 5.6]. It commits
%to the clause only. Choice points the BODY creates survive it, which they must,
%because a MeTTa function is nondeterministic and reduce/3 answers its whole
%answer set.
%
%Before this, the last clause had a variable first argument, so nothing could
%index it away and every reduce/3 call returned holding a choice point. That
%defeats last call optimisation in the caller: a 200,000 element map-atom
%through the dynamic dispatch path retained 86,400,000 bytes of local stack,
%432 bytes per element, for a choice point that could never yield an answer.
%Measured 2026-08-15. The last clause is now reachable only for a term that is
%neither [] nor [_|_], which is exactly what non_list/1 tested, so the test is
%gone with the choice point.
reduce([], Out, Status) :- !, Out = [], Status = 'not-reducible'.
%The parentheses around the whole if-then-else are load-bearing. Without them
%the cut is read as the first goal of the CONDITION, because , binds tighter
%than ->, and a cut inside a condition is local to that condition and commits
%to nothing.
reduce([F|Args], Out, Status) :- !,
    (   nonvar(F), atom(F),
        ( fun(F), \+ fun_scoped(F) -> Module = user
        ; current_metta_module(Module), fun_here_in(Module, F) )
    ->  % --- Case 1: callable predicate ---
        length(Args, N),
        Arity is N + 1,
        %arity/2 rather than current_predicate/1, which is what
        %build_call_or_partial_dl/6 already asks, so the compiled path and the
        %reducer now agree about what is callable. It is also the only one of
        %the two that can be right here: current_predicate/1 sees whatever a
        %library exported into user, and library(yall) exports //2 through
        %//9, so (let $g / ($g 1 2 3)) resolved to yall's lambda and answered
        %`type_error(lambda_free, 1)`. register_prolog_arities/1 no longer
        %records those arities, and reading the registry is free where asking
        %predicate_property/2 per operator cost 2.39% on the typed-call
        %counter [measured 2026-08-17].
        (   ( Module == user -> arity(F, Arity)
                              ; current_predicate(Module:F/Arity) ),
            \+ (Arity =< 2, current_op(_, _, F))
        ->  resolve_dispatch(F, Args, Out, Goal),
            ( Module == user -> CallGoal = Goal ; CallGoal = Module:Goal ),
            call(CallGoal),
            Status = reduced
        ;   incomplete_application_kind(F, Arity, partial)
        ->  Out = partial(F,Args),
            Status = reduced
        ;   throw_function_overapplication(F, N) )
    ;   % --- Case 2: partial closure ---
        compound(F), F = partial(Base, Bound)
    ->  append(Bound, Args, NewArgs),
        reduce([Base|NewArgs], Out, Status)
    ;   % --- Case 3: an APPLICABLE GROUNDED ATOM ---
        % MeTTa says a Grounded atom "may contain any binary object, for
        % example operation", and an operation is a thing you call. Nothing
        % here knows what makes one applicable: a bridge claims its own values
        % through metta_grounded_apply/3 and the engine applies whatever it
        % claims [source: metta-lang.dev/docs/learn, Atom kinds and types].
        %
        % Reached only for a head that is neither a function name nor a
        % partial, which used to fall straight through to case 4, so a Python
        % callable held in a MeTTa variable could not be applied at all and
        % ((py-atom numpy.absolute) -5) answered itself.
        %atomic/1 rather than \+ is_list/1, and the difference is not style: a
        %data head IS a list, so is_list/1 walked every one of them to decide
        %it was not this case. That cost 20% of the alpha-unique benchmark's
        %instructions [measured 2026-08-16: 3.70 to 4.45 billion]. A grounded
        %value is atomic, so one O(1) test excludes every list and compound.
        atomic(F), \+ atom(F),
        metta_grounded_apply(F, Args, Applied)
    ->  Out = Applied,
        Status = reduced
    ;   % --- Case 4: leave unevaluated ---
        Out = [F|Args],
        acyclic_term(Out),
        Status = 'not-reducible'
    ).
reduce(Culprit, _, _) :-
    throw_metta_type_error(reduce, list, Culprit).



%Calling reduce from aggregate function foldall needs this argument wrapping
agg_reduce(AF, Acc, Val, NewAcc) :- reduce([AF, Acc, Val], NewAcc, _).

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
                                             translate_expr_dl(Gs, AfterArgs, Goals, Out),
                                             refuse_seam_expanded_to_data(HV, Out)
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
            -> ( runtime_guarded_builtin_call(Fun)
                 -> UniqueTypeChains = []
                  ; findall(TypeChain,
                            catch_recover(type_declaration(Fun, TypeChain),
                                          fail),
                            TypeChains),
                    list_to_set(TypeChains, UniqueTypeChains) ),
               ( typed_functioncall_dl(Fun, UniqueTypeChains, T, IsPartial, Bound, Out, AfterHead, Goals)
                 -> true
              ; translate_args_dl(T, AfterHead, AfterArgs, AVs),
                ( IsPartial -> append(Bound, AVs, AllAVs) ; AllAVs = AVs ),
                build_call_or_partial_dl(Fun, AllAVs, Out, AfterArgs, Goals, []))
          %Literals (numbers, strings, etc.), known non-function atom => data:
          %A grounded head that is an OPERATION is a call, not data. Without
          %this it fell into the data branch below and never reached reduce/3,
          %so a token bound to a Python function built `(<fn> -5)` as a term
          %instead of calling it: the language's own idiom, `(bind! abs
          %(py-atom numpy.absolute))` then `(abs -5)`.
          ; ( atomic(HV), \+ atom(HV) , \+ metta_grounded_applicable(HV)
            ; atom(HV), \+ fun_here(HV) ) -> note_symbol_head(HV),
                                                                       translate_data_args_dl(HV, T, AfterHead, Goals, AVs),
                                                                       Out = [HV|AVs]
          %Plain data list: evaluate inner fun-sublists
          ; is_list(HV) -> translate_args_dl(T, AfterHead, AfterArgs, AVs),
                           eval_data_term_dl(HV, AfterArgs, Goals, HV1),
                           Out = [HV1|AVs]
          %Unknown head (var/compound) => runtime dispatch:
          ; translate_args_dl(T, AfterHead, BeforeReduce, AVs),
            BeforeReduce = [reduce([HV|AVs], Out, _)|Goals] )).

%The declarations a CONSTRUCTOR compiles against, and there are two registers
%of them. type_declaration/2 holds what the program and its spaces declared;
%builtin_type_declaration/2 holds the engine's own surface, parsed out of
%lib_builtin_types.metta at startup.
%
%Reading the engine's register here and NOT on the function path above is
%deliberate, and it was measured rather than chosen. `Atom` in a parameter
%position says the argument is not reduced before the call, which is exactly
%what a constructor like `(: Error (-> Atom Atom ErrorType))` wants. It is NOT
%what several of the engine's own declarations want: `(: maplist (-> Atom
%%Undefined% %Undefined%))` says its first argument is a closure the caller
%wrote, and the call site has to BUILD that closure, so masking it hands
%maplist/3 a list where it needs a goal. Those declarations describe the
%argument a caller writes rather than the value the predicate receives, and
%honouring them at every call site broke every one
%[measured 2026-08-16: examples/functions/lambda.metta, maplist/3 called with
%'[|]'/4].
%
%A constructor has no such gap, because there is no predicate underneath it to
%disagree with the declaration.
call_site_type_chains(Fun, UniqueTypeChains) :-
    findall(TypeChain, catch_recover(type_declaration(Fun, TypeChain), fail),
            TypeChains),
    (   TypeChains \== []
    ->  list_to_set(TypeChains, UniqueTypeChains)
    ;   findall(Masked,
                ( builtin_type_declaration(Fun, Chain),
                  chain_masks_an_argument(Chain),
                  atom_positions_only(Chain, Masked) ),
                MaskedChains),
        list_to_set(MaskedChains, UniqueTypeChains)
    ).

%A CONSTRUCTOR can mask too, and this is where the language's rule is wider
%than "function": it is about what a head DECLARES, not about whether it has
%equations. `(: Error (-> Atom Atom ErrorType))` is a declaration on a data
%head, and it is the whole reason an error term can carry the malformed
%expression that caused it. Without it `(Error (+ 1 2) (+ 1 +))` raised while
%evaluating its own argument, which is an error channel unable to report the
%one thing it exists to report.
%
%The cheap test comes first: an ordinary constructor has no declaration in
%either register and fails an indexed lookup, so nothing else runs for it.
translate_data_args_dl(HV, Args, Goals0, Goals, AVs) :-
    (   atom(HV), is_list(Args), data_head_masks(HV, Args, ArgTypes)
    ->  translate_args_by_type_dl(Args, ArgTypes, Goals0, Goals, AVs)
    ;   translate_args_dl(Args, Goals0, Goals, AVs)
    ).

%ONE indexed lookup, and the index is why. Deriving this per head cost 21
%inferences, 16 of them inside type_declaration/2, and a data head is the
%commonest thing in a MeTTa program: the alpha-unique benchmark compiles ten
%thousand of them and paid 20% more instructions for it
%[measured 2026-08-16: 3.70 to 4.45 billion]. The engine's declaration surface
%is static once loaded, so the masking heads are computed once and looked up
%by name after that.
data_head_masks(HV, Args, ArgTypes) :-
    masking_data_head(HV, ArgTypes),
    same_length(ArgTypes, Args),
    !.

%Built from the engine's own declaration register after it loads. A program's
%own `(: MyErr (-> Atom Atom MyType))` is NOT indexed here, so a user-declared
%constructor does not mask; that is a real limit and it is here rather than
%hidden, because closing it means testing every add-atom for a declaration and
%the measurement above is what that costs.
:- dynamic masking_data_head/2.

index_masking_data_heads :-
    retractall(masking_data_head(_, _)),
    forall(( builtin_type_declaration(Name, Chain),
             chain_masks_an_argument(Chain),
             atom_positions_only(Chain, [->|Masked]),
             append(ArgTypes, [_], Masked) ),
           ( masking_data_head(Name, ArgTypes)
             -> true
             ;  assertz(masking_data_head(Name, ArgTypes)) )).

chain_masks_an_argument([->|Types]) :-
    append(Args, [_], Types),
    memberchk('Atom', Args).

atom_positions_only([->|Types], [->|Masked]) :-
    append(Args, [Out], Types), !,
    maplist(atom_position_or_undefined, Args, MaskedArgs),
    append(MaskedArgs, [Out], Masked).
atom_positions_only(Chain, Chain).

atom_position_or_undefined(T, Masked) :-
    ( T == 'Atom' -> Masked = 'Atom' ; Masked = '%Undefined%' ).

%A name alone is not enough: a user or named-space equation can override a
%builtin and must retain reflective type checks. Only the unmodified runtime
%predicate owns the complete input contract.
runtime_guarded_builtin_call(Fun) :-
    runtime_type_guarded(Fun),
    \+ fun_in(user, Fun),
    current_metta_module(Module),
    \+ fun_in(Module, Fun).

%A special form is compiled by the translator instead of being defined by
%equations, and most are not registered as functions either: of the special
%forms, case, if, collapse, quote, sealed, once, forall, foldall, chain,
%and-then and or-else all answer false to fun/1. So "no equations" does not
%mean "nothing can prove it", and reading it that way made
%(not-provable (case 1 ((1 True)))) answer True beside its correct False
%[measured 2026-08-15]. Asked of translate_special_dl/5 rather than kept as a
%list, so a form added below is covered the day it is added.
metta_special_form(Name) :-
    clause(user:translate_special_dl(Name, _, _, _, _), _),
    !.

%Every head the translator gives meaning to, across BOTH of its compilation
%routes. metta_special_form/1 above answers for one of them and is the
%narrower question its callers want; this is the wider one, and the
%difference is the six stream ops, which safe_rewrite_streamops/2 rewrites at
%translate_expr_dl/4 one line before any special form or function dispatch is
%tried. Asked of the clause heads for the same reason as above, so a rewrite
%added at rewrite_streamops/2 is covered the day it is added.
%
%Written for the linter, whose possibly-undefined-reference check asks "does
%anything in the engine give this head meaning". Answering that with fun/1
%alone reported 1623 findings over PeTTa/examples, 712 of them special forms
%used correctly, `if` alone accounting for 378 [measured 2026-08-17]
%[tested: test_calling_a_special_form_is_not_an_undefined_reference].
%The nonvar guard is load-bearing. rewrite_streamops/2's last clause is the
%identity fallthrough, whose head argument is a bare variable, so asking
%clause/2 for rewrite_streamops([Name|_], _) unifies with it for ANY Name and
%answers true for every symbol in the language. Binding the pattern first and
%testing it afterwards reads only the six real rewrites
%[tested: translator_special_dispatch:an_ordinary_name_is_not_a_translated_head].
metta_translated_head(Name) :- metta_special_form(Name), !.
metta_translated_head(Name) :-
    clause(user:rewrite_streamops(Pattern, _), _),
    nonvar(Pattern),
    Pattern = [Name|_],
    !.

%First-argument indexing keeps each special form independent of the number of
%other forms. A clause fails on an unsupported arity so ordinary function or
%data dispatch can still handle that expression.
%A builtin a program has taken over. The engine's own compilation of a form
%must give way to a user or named-space equation of the same name, which is the
%guard runtime_guarded_builtin_call/1 uses for the same reason.
metta_builtin_overridden(Fun) :-
    (   fun_in(user, Fun)
    ->  true
    ;   current_metta_module(Module), fun_in(Module, Fun)
    ).

%THE ATOM MASK, for the two forms that are entirely about it.
%
%`Atom` in a parameter position says the argument is NOT REDUCED before the
%call, and only the compiler can act on that. The engine's declarations say so
%for both of these and the call site could not read them: `(get-metatype
%(+ 1 2))` answered Grounded where the language says Expression, and
%`(noeval (+ 1 2))` answered `(noeval 3)`
%[source: metta-lang-docs/learn__tutorials__types_basics__metatypes.md, which
%uses get-metatype as its worked example of the mask and says of the other
%"this is the way noeval function is implemented"].
%
%Compiled here rather than by honouring the declaration register wholesale,
%because several of the engine's own `Atom` declarations describe the argument
%a CALLER writes rather than the value the predicate receives: `(: maplist
%(-> Atom %Undefined% %Undefined%))` needs its closure built, not masked. The
%reasoning is at call_site_type_chains/2.
%
%A user equation still wins, the same guard runtime_guarded_builtin_call/1
%uses, so redefining either name in a program or a named space keeps working.
translate_special_dl('get-metatype', [Arg], AfterHead, Goals, Out) :-
    \+ metta_builtin_overridden('get-metatype'),
    AfterHead = ['get-metatype'(Arg, Out)|Goals].
%noeval is the mask twice: the argument is not reduced going in, and the Atom
%return type stops the answer being reduced coming out. Both are this clause.
translate_special_dl(noeval, [Arg], AfterHead, Goals, Out) :-
    \+ metta_builtin_overridden(noeval),
    AfterHead = Goals,
    Out = Arg.

translate_special_dl(superpose, [Args], AfterHead, Goals, Out) :-
    is_list(Args),
    build_superpose_branches(Args, Out, Branches),
    disj_list(Branches, Disj),
    AfterHead = [Disj|Goals].
%Empty is the branch remover: a finished result that IS the symbol Empty
%"is not returned among other results when interpreting is finished", no
%operation exempt [source: LeaTTa MettaHyperonFull/Minimal/
%Interpreter.lean:3090, quoting the pinned minimal-metta.md]. Every
%runnable and every collapse aggregates here, so this is the door. A
%literal value decides at compile time and pays nothing; a computed
%value keeps the findall EXACTLY as it always compiled and prunes the
%collected list afterwards. The filter deliberately does NOT ride inside
%the findall goal: wrapping the conjunction changed the goal's compiled
%shape and cost nilbc 2.1x upstream's instructions where this form
%measures at parity [measured 2026-08-17: 24.7e9 against 12.0e9 net for
%the identical example].
translate_special_dl(collapse, [Expr], AfterHead, Goals, Out) :-
    translate_expr_to_conj(Expr, Conj, ExprValue),
    (   ExprValue == 'Empty'
    ->  AfterHead = [Out = []|Goals]
    ;   nonvar(ExprValue)
    ->  AfterHead = [findall(ExprValue, Conj, Out)|Goals]
    ;   AfterHead = [(findall(ExprValue, Conj, All),
                      petta_prune_empty(All, Out))|Goals]
    ).
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
%(take K Expr): at most K answers of Expr. once took one and collapse took
%all, and nothing took k, while the space seam has had the concept one level
%down all along in BoundedMatcher's limit.
%
%The two forms differ only in whether the bound also reaches the PROVIDER, and
%that is decided HERE because the shape is what decides it. A conjunction, a
%guard or a function call compiles to the plain bound; exactly one match over
%one space compiles to the pushdown. Deciding it at run time would mean
%inspecting a compiled goal, and deciding it later would mean not knowing the
%expression was a single match at all.
translate_special_dl(take, [CountExpr, Expr], AfterHead, Goals, Out) :-
    translate_expr_dl(CountExpr, AfterHead, AfterCount, Count),
    translate_expr_to_conj(Expr, Conj, Out),
    (   Conj = match(Space, Pattern, Out, Out)
    ->  Bounded = metta_take_match(Count, Space, Pattern, Out)
    ;   Bounded = metta_take(Count, Conj)
    ),
    AfterCount = [Bounded|Goals].
%(annotation): the current answer's annotation, the k the seam carried
%with the last answer produced in this derivation, 1 outside any.
translate_special_dl(annotation, [], AfterHead, Goals, Out) :-
    AfterHead = [petta_annotation(Out)|Goals].
%(explain Query): the seam's route for Query, answered as atoms rather
%than run. The query arrives UNEVALUATED, like quote's argument, because
%the route is a fact about the expression, not about its answers.
translate_special_dl(explain, [Query], AfterHead, Goals, Out) :-
    AfterHead = [petta_explain(Query, Out)|Goals].
%(top K Expr): the K BEST of Expr by answer annotation, in the context's
%declared semiring order, where take is any K. The same shape decision:
%exactly one match over one space is the form that can check the context's
%order and push the bound under the three declarations; everything else
%collects and orders here.
translate_special_dl(top, [CountExpr, Expr], AfterHead, Goals, Out) :-
    translate_expr_dl(CountExpr, AfterHead, AfterCount, Count),
    translate_expr_to_conj(Expr, Conj, Out),
    (   Conj = match(Space, Pattern, Out, Out)
    ->  Ordered = metta_top_match(Count, Space, Pattern, Out)
    ;   Ordered = metta_top(Count, Conj, Out)
    ),
    AfterCount = [Ordered|Goals].
translate_special_dl(hyperpose, [List], AfterHead, Goals, Out) :-
    ( nonvar(List), is_list(List)
      -> build_hyperpose_branches(List, Branches),
         length(Branches, BranchCount),
         hyperpose_pool_size(BranchCount, Jobs),
         current_metta_module(Module),
         AfterHead = [concurrent_and(member((Goal, Result), Branches),
                                     hyperpose_branch(Module, Goal, Result,
                                                      Out),
                                     [threads(Jobs)])|Goals]
      ; translate_expr_dl(List, AfterHead, BeforeHyperpose, ListValue),
        BeforeHyperpose = [hyperpose_runtime(ListValue, Out)|Goals] ).
translate_special_dl(with_mutex, [Mutex, Expr], AfterHead, Goals, Out) :-
    translate_expr_to_conj(Expr, Conj, Out),
    AfterHead = [with_mutex(Mutex, Conj)|Goals].
%timeout and elapsed are special forms for the same reason with_mutex is: the
%expression must reach them UNEVALUATED. As ordinary functions their argument
%would be evaluated first, so the bound would be applied to finished work and
%the clock would start after the work it is meant to time [measured 2026-08-15:
%(elapsed (spin 200000)) reported 12us for a 19ms call].
translate_special_dl(timeout, [Seconds, Expr], AfterHead, Goals, Out) :-
    translate_expr_to_conj(Expr, Conj, Out),
    translate_expr_dl(Seconds, AfterHead, BeforeTimeout, SecondsValue),
    BeforeTimeout = [metta_timeout(SecondsValue, Conj, Out)|Goals].
translate_special_dl('with-pragma!', [Settings, Expr], AfterHead, Goals, Out) :-
    translate_expr_to_conj(Expr, Conj, Out),
    translate_expr_dl(Settings, AfterHead, BeforeScope, SettingsValue),
    BeforeScope = [metta_with_pragmas(SettingsValue, Conj, Out)|Goals].
translate_special_dl(inferences, [CountExpr, Expr], AfterHead, Goals, Out) :-
    translate_expr_to_conj(Expr, Conj, Out),
    translate_expr_dl(CountExpr, AfterHead, BeforeBound, Count),
    BeforeBound = [metta_inferences(Count, Conj, Out)|Goals].
translate_special_dl(elapsed, [Expr], AfterHead, Goals, Out) :-
    translate_expr_to_conj(Expr, Conj, Value),
    AfterHead = [metta_elapsed(Conj, Value, Out)|Goals].
translate_special_dl(transaction, [Expr], AfterHead, Goals, Out) :-
    translate_expr_to_conj(Expr, Conj, Out),
    AfterHead = [petta_transaction(Conj)|Goals].

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
%unify: the stdlib's matching conditional. All four arguments are typed
%Atom, so the two operands cross unevaluated exactly as quote's argument
%does, and only the selected branch runs [source: LeaTTa
%tests/semantics/matching/unify_branch_evaluation.metta, branch markers
%measured 2026-08-11]. Every solution of petta_match_atoms/2 is one
%binding set and instantiates its own then-branch answer; the soft cut
%runs the else-branch exactly when no binding set exists. Bindings made
%by the match flow into the branch through the shared variables, which
%is how (unify &kb (friend $who Alice) $who no-friends) answers each
%friend.
translate_special_dl(unify, [A, B, Then, Else], AfterHead, Goals, Out) :-
    translate_expr_to_conj(Then, ThenConj, ThenValue),
    translate_expr_to_conj(Else, ElseConj, ElseValue),
    build_branch(ThenConj, ThenValue, Out, ThenBranch),
    build_branch(ElseConj, ElseValue, Out, ElseBranch),
    AfterHead = [(petta_match_atoms(A, B) *-> ThenBranch ; ElseBranch)|Goals].
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
%sealed renames the listed variables inside the expression so they are local to
%it, which is HE's own wording: "Replaces all occurrences of any var from var
%list inside atom by unique variable. Can be used to create locally scoped
%variables."
%
%TWO DIVERGENCES from the current corelib dump, both pinned by
%examples/control/sealed.metta so neither can drift silently.
%
%The first argument's ROLE is inverted. The wording quoted above is HE's own
%older one and this implements exactly it: the LISTED variables are renamed.
%The current dump says the opposite, "any var inside atom, EXCEPT list of
%variables to ignore" [source: LeaTTa/stdlib.md, the sealed entry], so upstream
%renames everything you did NOT name. This reading is what makes every use in
%this tree work, seal_lambda_locals/3 below included: you name the variable you
%want local. Under upstream's, the same call localises the surrounding
%variables instead and the outer binding is lost.
%
%And this EVALUATES the sealed expression where upstream answers the renamed
%atom as data: upstream prints `[(pair $x#19 $x#19)]` with nothing reduced,
%while `(sealed ($v) (+ 1 2))` is 3 here. Evaluating is consistent with the
%rest of PeTTa, and `quote` is how to get the atom instead.
%
%The rename happens HERE, at compile time, on the source expression.
%copy_term/4 renames exactly the variables of its first argument that occur in
%its second and shares everything else [source: SWI-Prolog 10.1 Reference
%Manual, copy_term(+VarsIn, +In, -VarsOut, -Out)], which is the operation
%sealed wants.
%
%It used to be emitted as a RUNTIME goal over the already-translated body, and
%that cannot work for the case sealed exists for. By the time the goal runs,
%an outer binding has bound the variable being sealed, so there is no variable
%left to rename: (let $x 1 (sealed ($x) (let $x 2 $x))) copied [1] instead of
%[$x], ran the inner let as (let 1 2 1), and answered NOTHING. Measured
%2026-08-15; it answers 2 now. The form had no test and no example anywhere in
%the tree, which is how that survived.
translate_special_dl(sealed, [Vars, Expr], AfterHead, Goals, Out) :-
    copy_term(Vars, Expr, _, SealedExpr),
    translate_expr_dl(SealedExpr, AfterHead, Goals, Out).

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
                     reduce(GeneratorList, GeneratedValue, _)),
    translate_expr_dl(Test, AfterHead, BeforeForall, TestHeadValue),
    %Stops on FALSE, not on "anything that is not true". The example's own
    %comment has always said so, "an item returning false breaks the loop", and
    %the two readings only came apart once the effectful operations started
    %answering the unit value the specification types them with: a body of
    %`(add-atom &s (num $x))` answers `()`, which is an effect that happened and
    %not a failed test, and requiring `true` stopped the loop after one item
    %[tested: examples/control/metta4_streams.metta].
    BeforeForall = [(forall(GeneratorGoal,
                            (reduce(TestList, Truth, _), Truth \== false))
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
                              reduce(GeneratorList, Value, _), Initial, Out)|Goals].

%The three collection forms take a variable and a body, which is a lambda
%written without the word. Each compiles its body into a closure predicate
%through the '|->' clause below and then calls maplist/3, include/3 or foldl/4
%on it, so the body is an ordinary compiled call.
%
%They used to inline the body into a yall lambda instead. That was wrong twice
%over. It cost 3.6 to 4.7 times the inferences and 7 to 11 times the cpu,
%because yall copy_terms the lambda for every element and assertz/1 does not
%run the goal expansion that would have removed it [measured 2026-08-15,
%100,000 elements: maplist 1301283 -> 300004, include 1250004 -> 350004,
%foldl 1400004 -> 300004]. And it captured nothing, so (map-atom $l $x ($x $u))
%answered ((a $_0) (b $_1)) while the same map written (map-atom $l (|-> ($x)
%($x $u))) answered ((a $_0) (b $_0)). One spelling of one map, two answers.
%examples/lambda.metta settles which is right: it binds $k outside a lambda,
%reads it inside, and expects the value, so capturing is the specified
%behaviour and these forms now share the predicate that implements it.
translate_special_dl('foldl-atom', [ListExpr, InitialExpr, AccVar, ItemVar,
                                    Body], AfterHead, Goals, Out) :-
    translate_expr_to_conj(ListExpr, ListConj, List),
    translate_expr_to_conj(InitialExpr, InitialConj, Initial),
    collection_closure([ItemVar, AccVar], Body, Closure),
    exclude(==(true), [ListConj, InitialConj], PrefixGoals),
    append(PrefixGoals, [foldl(Closure, List, Initial, Out)|Goals], AfterHead).
translate_special_dl('map-atom', [ListExpr, ItemVar, Body],
                     AfterHead, Goals, Out) :-
    translate_expr_to_conj(ListExpr, ListConj, List),
    collection_closure([ItemVar], Body, Closure),
    exclude(==(true), [ListConj], PrefixGoals),
    append(PrefixGoals, [maplist(Closure, List, Out)|Goals], AfterHead).
translate_special_dl('filter-atom', [ListExpr, ItemVar, Condition],
                     AfterHead, Goals, Out) :-
    translate_expr_to_conj(ListExpr, ListConj, List),
    collection_closure([ItemVar], Condition, Closure),
    exclude(==(true), [ListConj], PrefixGoals),
    append(PrefixGoals,
           [include(metta_condition_holds(Closure), List, Out)|Goals],
           AfterHead).

translate_special_dl('|->', [Args, Body0], AfterHead, Goals, Out) :-
    %Apply every nested sealed's rename BEFORE deciding which variables are
    %free. A variable that a sealed form localises is not free in the enclosing
    %lambda, and counting it as one made the lambda capture it as an extra
    %parameter: (= (mk) (|-> ($a) (sealed ($v) (pair $a $v)))) compiled mk to
    %arity 2 while every call to it was arity 1, so the function was simply
    %uncallable. Measured 2026-08-15, and it behaved the same before sealed's
    %rename moved to compile time, so it is not that change's doing.
    seal_lambda_locals(Body0, Body, SealedLocals),
    next_lambda_name(Function),
    term_variables(Body, AllVars),
    term_variables(Args, ArgVars),
    append(ArgVars, SealedLocals, NotFree),
    exclude({NotFree}/[Var]>>memberchk_eq(Var, NotFree), AllVars, FreeVars),
    append(FreeVars, Args, FullArgs),
    translate_clause([=, [Function|FullArgs], Body], Clause),
    %Into the space's own module, the way filereader.pl asserts every other
    %compiled equation. A bare assertz/2 puts the lambda in `user`, and a
    %module inherits from `user` rather than the other way round, so the
    %lambda could not see the space it was written in: inside a named space,
    %`(= (local-double $x) (* $x 2))` followed by
    %`!(map-atom (1 2 3) $x (local-double $x))` raised
    %`apply:maplist_/3: Unknown procedure: 'local-double'/2` while the same
    %call written directly answered 42. That is every lambda form, `|->`,
    %`map-atom`, `filter-atom` and `foldl-atom`, unusable on a space-local
    %function; and since every space PyPeTTa creates is a named one, it was
    %the whole Python surface [tested: translator_lambda_space_scope].
    %
    %+10 inferences once per lambda COMPILED and nothing per call [measured
    %2026-08-16: 1338 to 1348 for one map-atom compile-and-run, 10,005 either
    %way for a compiled map-atom over 2,000 elements].
    current_metta_module(Module),
    register_fun_in(Module, Function),
    assert_function_clause(Module, Clause, Ref),
    record_source_assertion(Ref),
    format(atom(Label), "metta lambda (~w)", [Function]),
    maybe_print_compiled_clause(Label, ['|->', Args, Body], Clause),
    length(FullArgs, InputArity),
    Arity is InputArity + 1,
    register_arity(Function, Arity),
    ( FreeVars == [] -> Out = Function ; Out = partial(Function, FreeVars) ),
    AfterHead = Goals.

%The five write forms, by one rule rather than one clause each. Every one of
%them is `(operation Space Atom)`: the space is an expression to evaluate and
%the atom is passed as WRITTEN, which is what their shared type
%`(-> Symbol Atom (->))` says and what the standard library means by "the added
%atom is added as is without reduction".
%
%The three plural and reducing ones were compiled as ordinary calls when they
%were added, so their argument was reduced before they saw it, and
%`(add-reduct &self (= (foo) (+ 3 4)))` reached add-reduct as `false`: `=` is
%this engine's equality operator as well as a definition head, so reducing an
%equation TESTS it [tested: examples/libraries/he_atomspace.metta].
%One clause each, and NOT one clause matching a list of names, because the
%head here is the interface: metta_special_form/1 reads these clause heads to
%decide what a special form is, so a variable in that position makes EVERY name
%one. It did, and the damage was nowhere near this file: duals refused to build
%a dual for an ordinary undefined function, reporting it as "a builtin or a
%special form" [tested: a_name_no_equation_defines_is_not_provable_at_all].
translate_special_dl('add-atom', Args, AfterHead, Goals, Out) :-
    translate_space_update_dl('add-atom', Args, AfterHead, Goals, Out).
translate_special_dl('remove-atom', Args, AfterHead, Goals, Out) :-
    translate_space_update_dl('remove-atom', Args, AfterHead, Goals, Out).
translate_special_dl('add-atoms', Args, AfterHead, Goals, Out) :-
    translate_space_update_dl('add-atoms', Args, AfterHead, Goals, Out).
translate_special_dl('add-reduct', Args, AfterHead, Goals, Out) :-
    translate_space_update_dl('add-reduct', Args, AfterHead, Goals, Out).
translate_special_dl('add-reducts', Args, AfterHead, Goals, Out) :-
    translate_space_update_dl('add-reducts', Args, AfterHead, Goals, Out).
%A literal (superpose (&a &b ...)) space argument is the multi-context
%idiom, and the SHAPE decides it at translation exactly as take's bound
%does: those queries route through petta_merged_match/3, where the
%declared (merge <pattern> <policy>) chooses the strategy. A computed
%space expression keeps the space-after-space path.
translate_special_dl(match, [SpaceExpr, Pattern0, Body], AfterHead, Goals,
                     Out) :-
    SpaceExpr = [superpose, SpaceList],
    is_list(SpaceList), SpaceList = [_, _|_],
    forall(member(Space, SpaceList), atom(Space)), !,
    lift_pattern_modifiers(Pattern0, Pattern, Guards),
    append([petta_merged_match(SpaceList, Pattern, Out)|Guards],
           AfterMatch, AfterHead),
    translate_expr_dl(Body, AfterMatch, Goals, Out).
translate_special_dl(match, [SpaceExpr, Pattern0, Body], AfterHead, Goals,
                     Out) :-
    translate_expr_dl(SpaceExpr, AfterHead, BeforeMatch, Space),
    lift_pattern_modifiers(Pattern0, Pattern, Guards),
    append([match(Space, Pattern, Out, Out)|Guards], AfterMatch, BeforeMatch),
    translate_expr_dl(Body, AfterMatch, Goals, Out).

translate_special_dl(translatePredicate, [[Predicate|Args]], AfterHead, Goals,
                     _Out) :-
    translate_args_dl(Args, AfterHead, BeforePredicate, ArgValues),
    metta_predicate_goal([Predicate|ArgValues], Goal),
    BeforePredicate = [Goal|Goals].
%The two Prolog seams are the exception to the fall-through documented above.
%No program means (translatePredicate ...) or (call ...) as data, so a shape
%the clause above cannot compile is a mistake worth reporting rather than a
%list worth building. Falling through instead compiled
%(translatePredicate (p $x) (p $x)) into the data list [translatePredicate,A,B]
%after evaluating both arguments, and answered it without complaint
%[tested translator.plt:malformed_seam_is_refused].
translate_special_dl(translatePredicate, Args, _, _, _) :-
    refuse_uncompilable_seam(translatePredicate, Args).
translate_special_dl(call, [[Function|Args]], AfterHead, Goals, Out) :-
    translate_args_dl(Args, AfterHead, BeforeCall, ArgValues),
    append(ArgValues, [Out], CallArgs),
    Goal =.. [Function|CallArgs],
    BeforeCall = [Goal|Goals].
translate_special_dl(call, Args, _, _, _) :-
    refuse_uncompilable_seam(call, Args).
translate_special_dl(reduce, [Expr], AfterHead, Goals, Out) :-
    ( Expr == []
      -> Out = [],
         AfterHead = Goals
      ; var(Expr)
      -> translate_expr_dl(Expr, AfterHead, BeforeReduce, ExprValue),
         BeforeReduce = [reduce(ExprValue, Out, _)|Goals]
      ; Expr = [Function|Args],
        translate_args_dl(Args, AfterHead, BeforeReduce, ArgValues),
        ExprValue = [Function|ArgValues],
        BeforeReduce = [reduce(ExprValue, Out, _)|Goals] ).
translate_special_dl(eval, [Arg], AfterHead, Goals, Out) :-
    AfterHead = [eval(Arg, Out)|Goals].
%evalc hands its first argument over unevaluated, exactly as eval does, or the
%expression would already have been reduced in the calling space before the
%space argument could select another one. The space itself is evaluated, so a
%function that answers a space name, or (context-space), can name it.
translate_special_dl(evalc, [Arg, Space], AfterHead, Goals, Out) :-
    translate_expr_dl(Space, AfterHead, BeforeEval, SpaceValue),
    BeforeEval = [evalc(Arg, SpaceValue, Out)|Goals].
translate_special_dl(quote, [Expr], Goals, Goals, Expr).
%not-provable keeps its head literal and evaluates its arguments, exactly as
%an ordinary call does. Which function is being negated has to be known
%without running it, because the answer comes from that function's dual rather
%than from a failed proof of it [source: src/duals.pl].
:- thread_local runnable_negation/0.

translate_special_dl('not-provable', [Expr], AfterHead, Goals, Out) :-
    metta_not_provable_goal(Expr, Goal, Out),
    (   translating_runnable, \+ runnable_negation
    ->  assertz(runnable_negation)
    ;   true
    ),
    AfterHead = [Goal|Goals].
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

%Both seams take exactly one argument: the goal to compile, written as a list
%whose head names the Prolog predicate. Reporting the argument rather than only
%the form matters, because the two ways to get this wrong look nothing alike.
%Writing (translatePredicate p) names a predicate without a goal around it, and
%wrapping a well-formed seam in quote, which a macro returning a term built in
%Prolog does not need, hands the translator a list it can only treat as data.
:- multifile prolog:error_message//1.

refuse_uncompilable_seam(Form, Args) :-
    ( Args = [Goal] -> Offender = Goal ; Offender = Args ),
    throw(error(petta_uncompilable_seam(Form, Offender),
                context(Form/1, 'a Prolog seam compiles one goal'))).

%The same mistake reaches the translator by a second route that the clauses
%above cannot see. A rule whose expansion is built in Prolog returns the form
%itself, so a quote around it is not consumed by the rule body the way it is
%when the rule is written in MeTTa source; it survives into the expansion, and
%quote hands back the seam it wraps as data. Nothing downstream can compile
%that, and before this the rule answered an unbound variable
%[tested translator.plt:quoted_seam_expansion_is_refused].
refuse_seam_expanded_to_data(Rule, Out) :-
    (   nonvar(Out), Out = [Seam|_],
        ( Seam == translatePredicate ; Seam == call )
    ->  throw(error(petta_seam_expansion_as_data(Rule, Seam),
                    context(Rule, 'a translator rule expanded to data')))
    ;   true ).

prolog:error_message(petta_uncompilable_seam(Form, Offender)) -->
    [ '~w compiles one Prolog goal and needs it written as a list naming the \c
       predicate, as (~w (name $arg ...)), but it was given ~p. A translator \c
       rule that builds this form in Prolog returns it directly; quoting it \c
       there yields a list the translator can only read as data.'-[Form, Form,
                                                                   Offender] ].
prolog:error_message(petta_call_to_own_import(Name)) -->
    [ 'this runnable imports ~w and calls it, and a runnable is compiled \c
       whole before any of it runs, so the call compiles while ~w is still \c
       unregistered and answers the expression instead of the value. Put the \c
       import in its own runnable, before the one that calls it.'-[Name, Name] ].
prolog:error_message(petta_seam_expansion_as_data(Rule, Seam)) -->
    [ 'the translator rule ~w expanded to a ~w form left as data, which \c
       nothing can compile. A rule written in MeTTa evaluates its own quote \c
       and expands to what quote returned; a rule that builds the form in \c
       Prolog is already holding that term, so it returns (~w ...) without \c
       the quote around it.'-[Rule, Seam, Seam] ].

%A let unifies its pattern with its value under an occurs check, so a binding
%cannot build a term that contains itself. Where that check is emitted decides
%whether it can fire at all.
%
%Emitted before the goals that compute the value, which is where it used to
%go, it runs on a result that is still an unbound variable, and two fresh
%variables cannot fail an occurs check. The cycle is then built by the goals
%that follow: (let $x (cons-atom $x ()) $x) was accepted and left $x bound to
%a rational tree. The check was live only when the value needed no goals of
%its own, which is the case tests/prolog/translator.plt covered.
%
%Emitting it after the value's goals is not free. It then walks an
%instantiated term on every let, and let is the third most called predicate in
%the engine after arithmetic: measured on a let-heavy workload at 2.7x wall
%clock, 0.0062s to 0.0169s over five runs each, with the inference count
%identical at 248706, so neither the benchmark gate nor any other
%inference-based measure sees the difference.
%
%A value that shares no variable with the pattern cannot be built out of the
%pattern's own variables by this let, so for it the early position loses
%nothing and stays. Only a value that does share one pays for the late check.
translate_let_dl([Pattern, Value, In], AfterHead, Goals, Out) :-
    ( shares_variable(Pattern, Value)
      -> translate_expr_dl(Pattern, AfterHead, AfterPattern, PatternValue),
         translate_expr_dl(Value, AfterPattern, AfterValue, ValueResult),
         AfterValue = [unify_with_occurs_check(PatternValue, ValueResult)|AfterUnify]
       ; AfterHead = [unify_with_occurs_check(PatternValue, ValueResult)|BeforePattern],
         translate_expr_dl(Pattern, BeforePattern, AfterPattern, PatternValue),
         translate_expr_dl(Value, AfterPattern, AfterUnify, ValueResult) ),
    translate_expr_dl(In, AfterUnify, Goals, Out).

%An occurs check whose left side is a variable that has appeared NOWHERE
%earlier in the clause cannot fail. That variable is unbound when the goal
%runs, and it cannot occur inside the value, because it has not yet been
%anywhere that could have put it there. Those become =/2.
%
%What this removes is not small and the inference counter cannot see it, since
%it counts both as one goal. unify_with_occurs_check/2 walks the whole value,
%so NAMING a term costs time proportional to the term's SIZE. A let* chain of
%four bindings over one list, 20,000 times, measured 2026-08-15 at 0.0081s for
%a 10 element list, 0.0931s for 200 and 0.8730s for 2000; with the safe checks
%demoted it is a flat 0.0025s at every size. O(n) becomes O(1).
%
%translate_let_dl/4 below already avoids what it can by emitting the check
%before the value's goals, where the value is still unbound. That does nothing
%when the value IS an already-bound variable, which is what (let $y $l ...)
%over an argument compiles to, and it is the common shape.
%Cost, since the counter gate measures compilation. The first version built a
%seen-SET eagerly, calling term_variables/2 per goal, and cost 12,001
%inferences of source-load. Guarding it behind a scan for the functor made that
%worse rather than better: the scan alone accounted for the whole remaining
%regression, because it walks every clause body while only a few contain a let.
%Threading the prefix as a list of goals and inspecting it only when an occurs
%check is actually found leaves source-load at its baseline and run-source
%+998 over 1000 directives, which is one inference per compiled clause and the
%floor for any post-pass [measured 2026-08-15].
%Found comes back bound when the body holds a negation, so quantify_negations/2
%walks only the clauses that have one. It is threaded through this pass rather
%than tested for separately because a separate test is not free: a predicate
%call costs one inference and flag/3 costs two, while comparing an argument
%costs none [measured 2026-08-15, 100,000 iterations: bare loop 100002
%inferences, the same loop plus X == [] 100002, plus a dynamic call 300002,
%plus flag/3 400003]. One inference per compiled clause is what the last
%post-pass here cost, and this one costs zero.
demote_safe_occurs_checks(Head, Body0, Body, Found) :-
    demote_occurs(Body0, Body, [Head], _, Found).

%Prefix is the clause head plus every goal that can run before this one,
%newest first. It is inspected ONLY when an occurs check is actually found, so
%an ordinary goal costs one cons rather than a term_variables/2 walk. Building
%the set eagerly instead cost 5,004 inferences of source-load on its own.
demote_occurs(Goal, Goal, Prefix0, [Goal|Prefix0], _) :- var(Goal), !.
demote_occurs((A0, B0), (A, B), Prefix0, Prefix, Found) :- !,
    demote_occurs(A0, A, Prefix0, Prefix1, Found),
    demote_occurs(B0, B, Prefix1, Prefix, Found).
%The else branch runs only when the condition FAILED, which undid the
%condition's bindings, so it starts from where the condition started.
demote_occurs((C0 -> T0 ; E0), (C -> T ; E), Prefix0, Prefix, Found) :- !,
    demote_occurs(C0, C, Prefix0, PrefixC, Found),
    demote_occurs(T0, T, PrefixC, _, Found),
    demote_occurs(E0, E, Prefix0, _, Found),
    Prefix = [(C0 -> T0 ; E0)|Prefix0].
demote_occurs((C0 *-> T0 ; E0), (C *-> T ; E), Prefix0, Prefix, Found) :- !,
    demote_occurs(C0, C, Prefix0, PrefixC, Found),
    demote_occurs(T0, T, PrefixC, _, Found),
    demote_occurs(E0, E, Prefix0, _, Found),
    Prefix = [(C0 *-> T0 ; E0)|Prefix0].
demote_occurs((C0 -> T0), (C -> T), Prefix0, Prefix, Found) :- !,
    demote_occurs(C0, C, Prefix0, PrefixC, Found),
    demote_occurs(T0, T, PrefixC, _, Found),
    Prefix = [(C0 -> T0)|Prefix0].
demote_occurs((A0 ; B0), (A ; B), Prefix0, Prefix, Found) :- !,
    demote_occurs(A0, A, Prefix0, _, Found),
    demote_occurs(B0, B, Prefix0, _, Found),
    Prefix = [(A0 ; B0)|Prefix0].
%Wrappers whose argument is an ordinary goal. Bindings made inside findall/3
%and \+/1 do not escape, so counting their variables as possibly bound
%afterwards is conservative: it costs an optimisation, never soundness.
demote_occurs(findall(T, G0, L), findall(T, G, L), Prefix0, Prefix, Found) :- !,
    demote_occurs(G0, G, Prefix0, _, Found),
    Prefix = [findall(T, G0, L)|Prefix0].
demote_occurs(forall(C0, A0), forall(C, A), Prefix0, Prefix, Found) :- !,
    demote_occurs(C0, C, Prefix0, PrefixC, Found),
    demote_occurs(A0, A, PrefixC, _, Found),
    Prefix = [forall(C0, A0)|Prefix0].
demote_occurs(\+ G0, \+ G, Prefix0, Prefix, Found) :- !,
    demote_occurs(G0, G, Prefix0, _, Found),
    Prefix = [\+ G0|Prefix0].
demote_occurs(once(G0), once(G), Prefix0, Prefix, Found) :- !,
    demote_occurs(G0, G, Prefix0, _, Found),
    Prefix = [once(G0)|Prefix0].
demote_occurs(unify_with_occurs_check(Pattern, Value), Out, Prefix0, Prefix, _) :- !,
    (   var(Pattern),
        \+ occurs_in(Pattern, Prefix0),
        \+ occurs_in(Pattern, Value)
    ->  Out = (Pattern = Value)
    ;   Out = unify_with_occurs_check(Pattern, Value)
    ),
    Prefix = [unify_with_occurs_check(Pattern, Value)|Prefix0].
%A negation is the only goal this pass reports rather than rewrites. Its own
%functor gives it an index bucket of its own, so recognising it costs the
%goals that are not negations nothing.
demote_occurs(metta_negation(L, S, T, D, O), metta_negation(L, S, T, D, O),
              Prefix0, [metta_negation(L, S, T, D, O)|Prefix0], Found) :- !,
    ( var(Found) -> Found = found ; true ).
%Anything else is opaque. Its own goals are left alone and every variable it
%mentions counts as possibly bound from here on.
demote_occurs(Goal, Goal, Prefix0, [Goal|Prefix0], _).

occurs_in(Var, Term) :- term_variables(Term, Vars), memberchk_eq(Var, Vars).

%Rewrite every (sealed <vars> <expr>) inside a term so its named variables are
%renamed apart, and report the variables that rename produced. Renaming the
%whole (sealed ...) form, var list included, keeps the form consistent for the
%later translation, which renames again and finds nothing left to do.
%
%The rename alone is not enough, and that was the first attempt: a renamed
%variable is still a variable of the body, so it still counted as free and the
%lambda still captured it. What the rename buys is the ability to TELL the two
%apart, so a variable used both inside a sealed form and outside it stays free
%for its outside occurrences and is excluded only for its inside ones.
seal_lambda_locals(Term, Sealed, Locals) :-
    (   nonvar(Term), Term = [Head, Vars, Expr], Head == sealed
    ->  seal_lambda_locals(Expr, Inner, InnerLocals),
        copy_term(Vars, [sealed, Vars, Inner], _, Sealed),
        Sealed = [_, SealedVars, _],
        term_variables(SealedVars, Renamed),
        append(Renamed, InnerLocals, Locals)
    ;   nonvar(Term), Term = [_|_]
    ->  seal_lambda_locals_list(Term, Sealed, Locals)
    ;   Sealed = Term, Locals = []
    ).

seal_lambda_locals_list(Term, Sealed, Locals) :-
    (   Term == []
    ->  Sealed = [], Locals = []
    ;   nonvar(Term), Term = [Head|Tail]
    ->  seal_lambda_locals(Head, SealedHead, HeadLocals),
        seal_lambda_locals_list(Tail, SealedTail, TailLocals),
        Sealed = [SealedHead|SealedTail],
        append(HeadLocals, TailLocals, Locals)
    ;   Sealed = Term, Locals = []
    ).

%Whether two terms have a variable in common.
shares_variable(A, B) :- term_variables(A, VarsA),
                         VarsA \== [],
                         term_variables(B, VarsB),
                         member(Var, VarsA),
                         memberchk_eq(Var, VarsB), !.

translate_space_update_dl(Operation, [SpaceExpr, Atom], AfterHead, Goals,
                          Out) :-
    translate_expr_dl(SpaceExpr, AfterHead, BeforeOperation, Space),
    Goal =.. [Operation, Space, Atom, Out],
    BeforeOperation = [Goal|Goals].

%All four spellings of one operation, so all four keep their name list as
%data. lib_zar's two were missing, and a list holding a name that had ALREADY
%become a function then compiled to a call: (zar_add zar_typo) became a
%partial application of zar_add, the declared Expression check on it failed,
%and the whole import answered nothing at all, with no error
%[tested: an_importer_name_list_stays_data].
prolog_function_importer(import_prolog_functions_from_file).
prolog_function_importer(import_prolog_functions_from_module).
prolog_function_importer(import_prolog_functions_from_file_pred).
prolog_function_importer(import_prolog_functions_from_module_pred).

translate_prolog_import_dl(Importer, [File, FunctionNames], Goals0, Goals, Out) :-
    atom(Importer),
    prolog_function_importer(Importer),
    note_runnable_import(FunctionNames),
    translate_expr_dl(File, Goals0, BeforeImport, ResolvedFile),
    Goal =.. [Importer, ResolvedFile, FunctionNames, Out],
    BeforeImport = [Goal|Goals].

%Recorded only while a runnable is being compiled, which is the only place the
%mistake this guards against can happen: a stored equation is compiled once
%and repaired by the change hooks when a name it calls arrives later.
note_runnable_import(Names) :-
    (   translating_runnable,
        is_list(Names)
    ->  forall(( member(Name, Names), atom(Name) ),
               assertz(runnable_import(Name)))
    ;   true
    ).

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
      -> resolve_dispatch(Fun, AVs, Out, Goal),
         append([Goal|Extra], Goals, Goals0)
    ; incomplete_application_kind(Fun, Arity, partial)
      -> Out = partial(Fun, AVs),
         Goals0 = Goals
    ; Goals0 = [throw_function_overapplication(Fun, N)|Goals] ).

%Type function call generation, returns function call plus typechecks for input and output:
%Translate a call against every type declaration that fits it.
%
%A symbol may carry several declarations at different arities, which is
%ordinary nondeterminism over declarations rather than a conflict, so a
%declaration whose shape does not fit THIS call simply does not contribute a
%branch. Collecting the branches with findall is what makes that true. It was
%a maplist, which meant one inapplicable declaration failed the entire form:
%with both (: g (-> A Atom B)) and (: g (-> A Atom Number B)) declared,
%(g x y 1) did not translate at all, while the same two equations with no
%declarations worked [tested: translator_multi_arity_declarations].
%
%Failing when no branch fits is deliberate: the caller falls back to the
%untyped translation, which is what a call carrying no usable declaration
%should get.
%
%The branches are collected by recursion rather than findall/3, because
%findall COPIES its template and every branch has to keep sharing the caller's
%Out and argument variables. Collecting them with findall compiled cleanly and
%answered an unbound variable for every typed call.
typed_functioncall_dl(Fun, UniqueTypeChains, T, IsPartial, Bound, Out, AfterHead, Goals) :-
    UniqueTypeChains \== [],
    length(T, NewInputArity),
    length(Bound, BoundArity),
    InputArity is BoundArity + NewInputArity,
    Arity is InputArity + 1,
    (   incomplete_application_kind(Fun, Arity, ApplicationKind),
        ApplicationKind == overapplied
    ->  AfterHead = [throw_function_overapplication(Fun, InputArity)|Goals]
    ;   fitting_type_chains(UniqueTypeChains, InputArity, FittingChains),
        applicable_typed_branches(FittingChains, Fun, T, IsPartial, Bound,
                                  Out, Branches),
        Branches \== [],
        disj_list(Branches, Disj),
        AfterHead = [Disj|Goals]
    ).

%When some declaration has exactly this call's arity, only those apply. A
%wider declaration would otherwise also build a branch for a shorter call and
%answer the same thing twice: with (: g (-> A Atom B)) and
%(: g (-> A Atom Number B)) both declared, (g x y) answered (x y) twice.
%
%When NOTHING has the exact arity the call is a partial application, and every
%declaration stays a candidate so currying keeps working.
fitting_type_chains(Chains, InputArity, Fitting) :-
    include(type_chain_takes(InputArity), Chains, Exact),
    ( Exact == [] -> Fitting = Chains ; Fitting = Exact ).

type_chain_takes(InputArity, [->|Types]) :-
    length(Types, Count),
    InputArity =:= Count - 1.

applicable_typed_branches([], _, _, _, _, _, []).
applicable_typed_branches([TypeChain|Rest], Fun, T, IsPartial, Bound, Out,
                          Branches) :-
    (   typed_functioncall_branch(Fun, TypeChain, T, [], IsPartial, Bound, Out,
                                  BranchGoal)
    ->  Branches = [BranchGoal|More]
    ;   Branches = More
    ),
    applicable_typed_branches(Rest, Fun, T, IsPartial, Bound, Out, More).

typed_functioncall_branch(Fun, TypeChain, T, GsH, IsPartial, Bound, Out, BranchGoal) :-
    TypeChain = [->|Xs],
    append(ArgTypes0, [OutType], Xs), !,
    drop_unconstraining_types(TypeChain, ArgTypes0, ArgTypes),
    translate_args_by_type(T, ArgTypes, GsT2, AVsTmp0, ArgChecks),
    ( IsPartial -> append(Bound, AVsTmp0, AVsTmp) ; AVsTmp = AVsTmp0 ),
    append(GsH, GsT2, InnerEval),
    %The output check asks whether the result has the declared type, and
    %nothing reads OutType afterwards, so one witness is the whole answer. A
    %soft cut here instead enumerates every derivation and succeeds once per
    %derivation, which repeats the call's answer: with (: (a b) (A B)) declared
    %alongside (: a A) and (: b B), a function returning (a b) answered twice.
    %The argument checks above keep their soft cut, because a shared type
    %variable there does have to backtrack to find a consistent assignment.
    ( (OutType == '%Undefined%' ; OutType == '_' ; OutType == 'Atom')
       -> OutCheck = []
        ; type_check_goal(Out, OutType,
                          ( has_type(Out, OutType) -> true
                          ; 'get-metatype'(Out, OutType) ),
                          OutGoal),
          OutCheck = [OutGoal] ),
    place_type_checks(ArgTypes, OutType, ArgChecks, OutCheck, InnerEval, Inner, Extra),
    build_call_or_partial(Fun, AVsTmp, Out, Inner, Extra, GoalsList),
    goals_list_to_conj(GoalsList, BranchGoal).

%An argument whose declared type is a type variable occurring NOWHERE else in
%the chain constrains nothing, and its check is pure waste. The check is
%(has_type(A,T) *-> true ; get-metatype(A,T)), so with T unbound it enumerates
%the argument's types, binds T to the first, and cannot fail: get-metatype/2
%answers for every term. Nothing then reads T.
%
%(: == (-> $a $b Bool)) is the shape, and it is what the builtin type file
%declares for ==, != and =alpha. Measured 2026-08-15 over 1000 calls of a
%two-argument function: 683 inferences undeclared, 1620 declared with two free
%type variables, 1562 declared with concrete types. The free variables were
%the MOST expensive of the three, for checks that decide nothing.
%
%A variable occurring twice is a real constraint and stays: (-> $a $a Bool)
%requires both arguments to have a consistent type, and (-> $a Bool $a) ties an
%argument to the result. Only a bare singleton variable is dropped, so
%(-> (List $a) Bool) keeps its check on the list.
%A chain with no type variables at all has nothing to drop, and that is most
%of them: every arithmetic, comparison and math declaration in
%lib_builtin_types.metta is concrete. term_variables/2 answers that in one
%call, where the occurrence walk below cost 72 inferences per compiled call
%site [measured 2026-08-15].
drop_unconstraining_types(TypeChain, ArgTypes0, ArgTypes) :-
    term_variables(TypeChain, TypeVariables),
    (   TypeVariables == []
    ->  ArgTypes = ArgTypes0
    ;   type_variable_occurrences(TypeChain, Occurrences),
        maplist(drop_unconstraining_type(Occurrences), ArgTypes0, ArgTypes)
    ).

drop_unconstraining_type(Occurrences, Type, Dropped) :-
    (   var(Type),
        occurrence_count(Occurrences, Type, 1)
    ->  Dropped = '_'
    ;   Dropped = Type
    ).

%Every variable OCCURRENCE, duplicates kept, which is what term_variables/2
%cannot report.
type_variable_occurrences(Term, [Term]) :- var(Term), !.
type_variable_occurrences(Term, Occurrences) :-
    compound(Term),
    !,
    Term =.. [_|Args],
    maplist(type_variable_occurrences, Args, Lists),
    append(Lists, Occurrences).
type_variable_occurrences(_, []).

occurrence_count(Occurrences, Variable, Count) :-
    include(==(Variable), Occurrences, Same),
    length(Same, Count).

%One commit covers every check that constrains the same type variables.
%
%Where the output type shares no variable with the arguments, the argument
%checks commit as a group before the call, so an ill-typed call never runs the
%body, and the output check commits separately after it.
%
%Where the output shares one, as in (-> $a $a), committing before the call
%picks a witness the output cannot satisfy: with (: at A), (: at T), (: t T)
%and (= (testf at) t), the argument check binds $a to A and the answer t, of
%type T, is then rejected. Both halves solve together after the call instead,
%which is the only order in which a shared variable can be assigned
%consistently [tested: examples/types/types.metta,
%a_shared_type_variable_is_assigned_after_the_call].
place_type_checks(ArgTypes, OutType, ArgChecks, OutCheck, InnerEval, Inner, Extra) :-
    term_variables(ArgTypes, ArgVars),
    term_variables(OutType, OutVars),
    ( shares_a_variable(ArgVars, OutVars)
      -> Inner = InnerEval,
         append(ArgChecks, OutCheck, Both),
         commit_checks(Both, Extra)
       ; commit_checks(ArgChecks, Committed),
         append(InnerEval, Committed, Inner),
         Extra = OutCheck ).

commit_checks([], []) :- !.
commit_checks(Checks, [once(Conj)]) :- goals_list_to_conj(Checks, Conj).

shares_a_variable(As, Bs) :- member(A, As), member(B, Bs), A == B, !.


%Selectively apply translate_args for non-Expression args while Expression args stay as data input:
%The argument checks are collected and committed as ONE group, after the
%argument evaluations. Checking each argument under its own commit cannot
%satisfy a type variable the arguments share: the first witness for one
%argument binds it, and nothing backtracks to the assignment the next
%argument needs. Committing per argument loses answers, and not committing
%at all repeats them once per consistent assignment, so the group is the
%unit: find one assignment that satisfies every argument, then stop looking.
%The evaluations stay outside the commit, because a nondeterministic
%argument must keep every answer it produces
%[tested: a_parametric_expected_type_enumerates_its_witnesses,
%translator_typed_checks].
translate_args_by_type([], _, [], [], []) :- !.
translate_args_by_type(Args, Types, GsOut, AVs, Checks) :-
    translate_args_by_type_dl(Args, Types, GsOut, [], AVs, Checks, []).

translate_args_by_type_dl(Args, Types, Goals0, Goals, AVs) :-
    translate_args_by_type_dl(Args, Types, Goals0, Tail, AVs, Checks, []),
    ( Checks == []
      -> Tail = Goals
       ; goals_list_to_conj(Checks, CheckConj),
         Tail = [once(CheckConj)|Goals] ).

translate_args_by_type_dl([], _, Goals, Goals, [], Checks, Checks) :- !.
translate_args_by_type_dl([A|As], [T|Ts], Goals0, Goals, [AV|AVs], Checks0, Checks) :-
    ( T == 'Atom'
      -> AV = A,
         AfterArg = Goals0,
         AfterCheck = Checks0
    ; translate_expr_dl(A, Goals0, AfterArg, AV),
      ( (T == '%Undefined%' ; T == '_' ; statically_typed_literal(AV, T))
        -> AfterCheck = Checks0
      ; type_check_goal(AV, T,
                        ( has_type(AV, T) *-> true ; 'get-metatype'(AV, T) ),
                        ArgGoal),
        Checks0 = [ArgGoal|AfterCheck] ) ),
    translate_args_by_type_dl(As, Ts, AfterArg, Goals, AVs, AfterCheck, Checks).

%A check that cannot be DROPPED can still be SPECIALISED. Three types are
%decided by a single Prolog builtin, and when the declared type is one of them
%the compiler knows so, because the type is a compile-time constant. Putting
%that test in front turns the common case from a walk through
%current_metta_module/1, has_type_in/3, once/1 and type_candidate_in/3 into one
%builtin call [measured 2026-08-17: an output check of type Number, 8.00
%inferences per call to 1.00].
%
%The fallback is untouched and reached whenever the fast test fails, so this
%decides nothing the general check would decide differently. It only answers
%the common case sooner. That matters because the fast test is INCOMPLETE on
%purpose: `(: mysym Number)` makes has_type(mysym, 'Number') true while
%number(mysym) is false, and the second disjunct is what still says so.
%
%Soundness in the other direction is what makes the shortcut legal at all, and
%it is a property of the engine rather than an assumption: both
%get_type_candidate/2 and get_type_candidate_in/3 open with a CUTTING clause
%for each of these three, so number(V) implies has_type(V, 'Number') in every
%module, whatever a get-type extension adds later [source: src/metta.pl:904 and
%the get_type_candidate_in/3 clauses beside it].
%
%This is the other half of what statically_typed_literal/2 below does, from the
%same compile-time fact. A compiler holding type information "remov[es] type
%and mode checks and ... call[s] specialized versions of some builtins"
%[source: Morales, Carro and Hermenegildo, Improved Compilation of Prolog to C
%Using Moded Types]; the removal is the literal case and this is the
%specialisation case.
%
%nonvar/1 first, and it is not defensive: a parametric declaration leaves the
%type a VARIABLE here, and intrinsic_type_test/3's head would bind it to
%'Number' and emit a number/1 test for a type nobody wrote. That is the same
%trap intrinsic_literal_type/2 below carries a note about, from the same shape.
%[tested: translator_literal_type_checks:an_intrinsic_type_check_is_specialised].
type_check_goal(Value, Type, General, Goal) :-
    (   nonvar(Type),
        intrinsic_type_test(Type, Value, Fast)
    ->  Goal = ( Fast -> true ; General )
    ;   Goal = General
    ).

intrinsic_type_test('Number', V, number(V)).
intrinsic_type_test('String', V, string(V)).
intrinsic_type_test('Bool',   V, (V == true ; V == false)).

%A literal argument's type is settled while the call site is being COMPILED,
%so the check emitted for it can only ever succeed and every inference it
%spends is spent on a foregone conclusion. `(: f (-> Number Number Number))`
%called as `(f 1 2)` compiled two has_type/2 goals over the constants 1 and 2,
%and they cost as much as the same call on two unknown variables: 31
%inferences per call against 6 for the same function undeclared, the whole 25
%being the checks [measured 2026-08-16, 20,000 calls of a site compiled once].
%Dropping every check leaves no once/1 wrapper either, so the fully literal
%call compiles to exactly what the untyped one does.
%
%Only four literals qualify, and only because get_type_candidate/2's first
%clauses CUT: a number is Number and nothing else, a string is String, and
%true and false are Bool, whatever a user's get-type extension adds later.
%
%This only ever DROPS a check that must pass; it never rejects. `(f "s")`
%against a Number parameter still compiles its check and still refuses at run
%time, because a get-type extension may legitimately give a literal a second
%type and deciding THAT statically would be unsound
%[tested: translator_literal_type_checks].
statically_typed_literal(Value, Type) :-
    nonvar(Type),
    nonvar(Value),
    intrinsic_literal_type(Value, Type).

%nonvar/1 above and ==/2 rather than head unification below, because BOTH are
%needed and the second is what a reader would skip. Written as
%`intrinsic_literal_type(true, 'Bool')`, a call with an unbound Value and
%Type = 'Bool' UNIFIES the head and binds Value to true. The argument being
%bound there is the call site's compile-time variable, so
%`(= (f $a $b) (g $a $b))` against `(: g (-> Bool Atom Bool))` compiled its
%head as `f(true, A, B)` and `(f False ...)` then matched no clause and
%answered nothing at all [reproduced 2026-08-16].
%
%Caught by a hand probe rather than by the gate, because the shape needs a
%Bool, Number or String parameter reached from ANOTHER function's body with a
%variable, and no example in the corpus had one
%[tested: translator_literal_type_checks:a_typed_parameter_is_not_frozen_at_compile_time].
intrinsic_literal_type(Value, 'Number') :- number(Value), !.
intrinsic_literal_type(Value, 'String') :- string(Value), !.
intrinsic_literal_type(Value, 'Bool') :- ( Value == true ; Value == false ).

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

%A variable goal is opaque and can only be walked as a term, which is what the
%catch-all clause at the bottom does. It needs saying here because a variable
%unifies with every control structure below: the conjunction clause bound it to
%a fresh (A , B) whose own left branch was again a variable, the cut committed,
%and the walk recursed on manufactured conjunctions forever. Reproduced
%2026-08-15: an unbound goal exceeded a depth limit of 3000 where `true`
%finishes at depth 2, and importing a library whose body held one exhausted the
%7.5Gb stack at 24,403,140 frames.
mbr_goal(Goal, _, _, P0, P, Goal, Bs, Bs) :- var(Goal), !,
    mbr_advance_term(Goal, P0, P).
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

%Build one disjunct per branch: (Conj, Out = Val). A literal Empty member
%is the branch remover and contributes no branch at all, minimal MeTTa's
%"is not returned among other results" applied where it is free; a
%COMPUTED Empty is pruned at the collapse aggregation instead.
build_superpose_branches([], _, []).
build_superpose_branches([E|Es], Out, Bs) :- E == 'Empty', !,
                                             build_superpose_branches(Es, Out, Bs).
build_superpose_branches([E|Es], Out, [B|Bs]) :- translate_expr_to_conj(E, Conj, Val),
                                                 build_branch(Conj, Val, Out, B),
                                                 build_superpose_branches(Es, Out, Bs).

%Build hyperpose branch as a goal list for concurrent_and/3 to consume:
build_hyperpose_branches([], []).
build_hyperpose_branches([E|Es], [(Goal, Res)|Bs]) :- translate_expr_to_conj(E, Goal, Res),
                                                      build_hyperpose_branches(Es, Bs).

%Never ask for more workers than there are branches. library(thread)'s jobs/2
%defaults the pool to the cpu_count flag and concurrent_and/3 creates that many
%workers plus a generator on EVERY call, so a three-branch hyperpose was
%creating 33 OS threads on this 32-core box regardless of its width
%[measured 2026-08-15: 30 three-branch calls created 990 threads; sizing to the
%branch count made it 120 and 11.6x faster on the same answers].
hyperpose_pool_size(BranchCount, Jobs) :-
    ( current_prolog_flag(cpu_count, Cores), integer(Cores), Cores > 0
      -> Jobs is max(1, min(BranchCount, Cores))
    ; Jobs is max(1, BranchCount) ).

%Run each branch under the module captured by the caller. SWI global variables
%are thread-local, so a concurrent_and/2 worker otherwise defaults to user and
%cannot resolve functions compiled into a named space.
hyperpose_branch(Module, Goal, Res, Out) :-
    with_metta_module(Module, (call(Module:Goal), Out = Res)).

%Runtime hyperpose path for variable/computed list arguments.
hyperpose_runtime(Exprs, Out) :-
    is_list(Exprs),
    current_metta_module(Module),
    length(Exprs, BranchCount),
    hyperpose_pool_size(BranchCount, Jobs),
    concurrent_and(member(Expr, Exprs),
                   eval_metta_in_module(Module, Expr, Out),
                   [threads(Jobs)]).

eval_metta_in_module(Module, Expr, Out) :-
    with_metta_module(Module,
                      ( translate_expr(Expr, Goals, Out),
                        call_goals_in_(Module, Goals) )).

%Compile Params and Body into a closure predicate and give back a Prolog
%callable that takes the body's own arguments after the captured ones. This is
%'|->' itself, which already names the predicate, captures the free variables
%and registers the arity; the difference-list arguments are the same variable
%because a lambda contributes no runtime goals of its own.
collection_closure(Params, Body, Closure) :-
    translate_special_dl('|->', [Params, Body], Tail, Tail, Lambda),
    (   Lambda = partial(Function, Captured)
    ->  Closure =.. [Function|Captured]
    ;   Closure = Lambda
    ).

%include/3's test for filter-atom. The condition's VALUE decides, so unify it
%with true rather than calling it. Calling it is what the yall version did, and
%(filter-atom (1 2 3) $x 42) then died with "callable expected, found (, true
%42)" where the same filter written (filter-atom (1 2 3) notbool) answered ().
%Unifying is also what the builtin 'filter-atom'/3 in metta.pl has always done.
metta_condition_holds(Closure, Item) :- call(Closure, Item, true).
%Declared meta so the lambda survives the hop through here. include/3 qualifies
%its own closure argument, which reaches this predicate's clause in the calling
%module, but Closure inside the clause is then a bare atom and call/3 resolves
%it in `user`. maplist/3 and foldl/4 never showed this because library(apply)
%declares them meta and this predicate is the only hand-written link in the
%chain: with the lambda in the space's module, filter-atom raised
%`metta_condition_holds/2: Unknown procedure: lambda_3/2` where map-atom and
%foldl-atom over the same lambda answered
%[tested: translator_lambda_space_scope]. Free: 10,013 inferences either way
%for a compiled filter-atom over 2,000 elements [measured 2026-08-16].
:- meta_predicate metta_condition_holds(2, ?).
%(:= X) inside a match pattern is the match-by-EQUALITY modifier: the atom
%matches only where it is already identical to X, so a free variable does not
%match it. lib/minimal_metta_lib.pl has implemented it for unify-mod all along
%and the engine's own match/4 did not know it, so the same modifier meant two
%different things depending on which matcher read it.
%
%Lifted at COMPILE time rather than taught to match/4, and that is the whole
%design. The modifier position is replaced by a fresh variable, so the space
%read keeps its ordinary shape and its clause indexing, and the equality is
%emitted as a ==/2 goal after the match. A pattern with no modifier in it
%produces no guards and an unchanged pattern, so match/4 pays NOTHING: the walk
%happens once, while the call site compiles.
%
%That also matches what the modifier means. The reference states that the
%guard "does not receive the match state, so bindings accumulated earlier in
%the same match cannot affect it", which is exactly a ==/2 over the operand as
%written [source: LeaTTa/MettaHyperonFull/Proofs/Modifiers.lean, the checked
%matcher's modifier law].
%
%THE ARITY GATE IS COPIED, NOT INVENTED. The reference recognises a modifier
%only at `Atom.expr [Atom.sym s, x]`, exactly two elements
%[source: LeaTTa/MettaHyperonFull/Core/Modifiers.lean, registeredMod?], and
%the reason is in this repository too: examples/libraries/minimal_metta.metta
%asserts that the THREE-element (:= a b) is ordinary data and matches the
%pattern (:= $x $y) structurally. Recognising := by name alone would
%reinterpret it [tested: translator_match_modifiers].
%GATE ONE: a pattern that IS a colon expression is a query for stored type
%declarations, not an annotation. `(match &self (: $x Human) $x)` retrieves the
%atoms somebody wrote, which is the reading a knowledge base needs and the one
%issue #177 names as the collision to avoid. An annotation is therefore always
%NESTED: `(match &self (knows (: $x Human) (: $y Human)) ($x $y))`
%[source: LeaTTa/ai-report-inplace-annotations.md, Design, gate 1].
lift_pattern_modifiers(Pattern, Lifted, Guards) :-
    (   colon_expression(Pattern)
    ->  Lifted = Pattern, Guards = []
    ;   lift_pattern_modifiers_(Pattern, Lifted, Guards, [])
    ).

lift_pattern_modifiers_(Pattern, Lifted, Guards0, Guards) :-
    (   pattern_modifier(Pattern, Lifted, Guard)
    ->  Guards0 = [Guard|Guards]
    %GATE TWO: a colon whose VALUE slot is not a variable is data, and the walk
    %does not look inside it. Without the second half a constructor that nests
    %colons inside a value, as LeaTTa's single_sided.metta does with
    %`(: (Sym (: (Sym (: $x $a)) $b)) $c)`, would have its inner colons
    %reinterpreted [source: LeaTTa/ai-report-inplace-annotations.md, Design].
    ;   colon_expression(Pattern)
    ->  Lifted = Pattern,
        Guards0 = Guards
    ;   nonvar(Pattern), Pattern = [_|_]
    ->  lift_pattern_modifiers_list(Pattern, Lifted, Guards0, Guards)
    ;   Lifted = Pattern,
        Guards0 = Guards
    ).

colon_expression(Pattern) :- nonvar(Pattern),
                             Pattern = [Colon, _, _],
                             nonvar(Colon),
                             Colon == ':'.

lift_pattern_modifiers_list([], [], Guards, Guards).
lift_pattern_modifiers_list([Item|Rest], [Lifted|LiftedRest], Guards0, Guards) :-
    lift_pattern_modifiers_(Item, Lifted, Guards0, Guards1),
    lift_pattern_modifiers_list(Rest, LiftedRest, Guards1, Guards).

%The two modifiers a pattern position can carry, each replaced by a fresh
%variable and a guard over it. `(:= X)` matches by EQUALITY, so a free
%variable does not match it; `(: $x T)` matches anything of type T and is the
%same acceptance a declared parameter of type T compiles, so a match query can
%restrict by type where only a top-level declaration could before.
pattern_modifier(Pattern, Fresh, Fresh == Wanted) :-
    nonvar(Pattern),
    Pattern = [Head, Wanted],
    nonvar(Head),
    Head == ':=',
    !.
pattern_modifier(Pattern, Fresh,
                 (has_type(Fresh, Type) *-> true ; 'get-metatype'(Fresh, Type))) :-
    nonvar(Pattern),
    Pattern = [Head, Fresh, Type],
    nonvar(Head),
    Head == ':',
    %An annotation annotates a VARIABLE, so anything else in that position
    %stays structural. Not a nicety: tests/prolog/duals.plt writes
    %`(= (pat-starts-a (: a $rest)) True)` as an ordinary cons-shaped pattern,
    %and without this gate it would be read as "the atom a has type $rest".
    var(Fresh).

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
