% Purpose: evaluate terms with shared fuel, residue and answer policies.
% Assumes: loaded through _binding/shim.pl in its host module.

%%%%%%%%%% Evaluation %%%%%%%%%%
%
% Evaluation is the engine's own translate_expr/3 over the term, then its
% goals, exactly what a ! directive runs: compiled and called in the space's
% module, so the space's own equations answer. Answers enumerate on
% backtracking.

%Every answer carries its Well Founded Semantics truth: call_delays is
%one '$wfs_call' around the goal, answering true for an unconditional
%derivation and the conjunction of unknown tabled goals otherwise, per
%answer, INSIDE the enumeration, which is the only place the condition
%exists (findall erases it). An unconditional answer encodes exactly as
%before; an undefined one crosses under the u tag so the third truth
%value reaches Python instead of masquerading as an ordinary answer.
%The wrapper is unconditional on purpose: every gate on "tabling in use"
%has a first-tabled-call window that would answer silently wrong exactly
%once, and callees make per-predicate checks unsound. Measured cost on
%the trivial-eval crossing: five to ten percent (interleaved A/B against
%a plain twin, 222-236k against 248-249k calls per second); real
%evaluations amortize it below that.
%One module wrap for resolution AND execution. Resolution went through
%metta_py_direct_goal/4, whose own metta_py_in_module made this door pay the
%context switch twice per eval; the compiled call sites resolve_dispatch
%serves pay it zero times, because they are already in their module. Folding
%resolution inside the execution wrap keeps the seam offer and the module
%context identical and returns ~10 of the +18 inferences the seam routing
%added [measured 2026-09-01: eval-arith 292,604 -> see baseline comment].
metta_py_eval(Space, Tagged, Encoded) :-
    metta_py_target_term(Space, Tagged, Term),
    metta_py_module(Space, Module),
    metta_py_in_module(Module,
        (   metta_py_direct_goal(Module, Term, F, Args, Produced)
        ->  translator:resolve_dispatch(F, Args, Produced, Goal),
            call_delays(call(Module:Goal), Delays)
        ;   translate_cached_expr(Term, Goals, Produced),
            call_delays(metta_py_call_goals(Module, Goals), Delays)
        )),
    translator:metta_boundary_result(Term, Produced, Out),
    metta_py_encode_truth(Out, Delays, Encoded).

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

%%%%%%%%%% Every evaluation door opens a fuel scope %%%%%%%%%%
%
%m.eval's own docstring says it is "what !(...) runs, minus the printing", and
%a runnable form runs inside the fuel scope engine/translator.pl wraps its
%conjunction in [source: engine/translator.pl, translate_runnable_expr/4's
%metta_run_with_fuel/3 call]. This door opened none, so `max-stack-depth` did
%not apply through it: the same two equations that answer
%`[120, (Error -3 StackOverflow)]` through `!` instead ran until SWI's stack
%gave out, 28.7 million inferences deep, and took the process with them
%[measured 2026-08-22 on identical string-loaded equations, both doors in one
%process each]. A bound the language offers has to hold at every door that
%claims to run the same thing
%[tested: test_the_same_source_answers_the_same_error_through_both_doors].
%
%The wrapper is metta_run_with_fuel/3's own contract: it answers the Value it
%was given for each ordinary solution, and then replays each branch that ran
%out of fuel as `(Error <culprit> StackOverflow)`. So an ordinary answer
%arrives inside metta_py_answer/1 and is unwrapped, and anything else is a
%fuel error atom that still has to cross as an encoded answer. Reentry is
%free: metta_run_with_fuel/3 calls the goal directly when a scope is already
%open, so m.eval from inside a runnable spends the runnable's fuel rather than
%opening a second budget.
metta_py_eval_all(Space, Tagged, Encoded) :-
    findall(E, metta_py_eval_bounded(Space, Tagged, E), Answers),
    ( Answers == [],
      metta_py_target_term(Space, Tagged, Term),
      metta_py_preserve_unmatched(Space, Term, Original)
      -> Encoded = [Original]
      ;  Encoded = Answers ).

%The measurement sits inside the limited call and beside the work it reports.
%A Space.stats() block would cross twice around every algebra operation, making
%the observer cost more engine work than a small operation and then leaving
%that observer work outside the quota it exists to enforce.
metta_py_eval_accounted(Space, Tagged, [Encoded, Used]) :-
    metta_py_work(Before),
    metta_py_eval_all(Space, Tagged, Encoded),
    metta_py_work(After),
    Used is After - Before.

metta_py_eval_bounded(Space, Tagged, Encoded) :-
    metta_run_with_fuel(metta_py_answer(Raw), Answer,
                        metta_py_eval(Space, Tagged, Raw)),
    metta_py_fuel_encoded(Answer, Encoded).

metta_py_fuel_encoded(metta_py_answer(Encoded), Encoded) :- !.
metta_py_fuel_encoded(Overflow, Encoded) :- metta_py_encode(Overflow, Encoded).

%eval with named host values, the same door metta_py_run_using opens for
%run: each Name-Value pair substitutes the bare symbol Name throughout the
%target before it evaluates, so a tensor or any other object reaches a
%rule by name and by IDENTITY rather than through a printed form. The
%target is read first, because substitution is over the term
%[tested test_run_using_carries_identity].
metta_py_eval_using_all(Space, Target, Pairs, Encoded) :-
    metta_py_target_term(Space, Target, Term0),
    maplist(metta_py_using_pair, Pairs, Bindings),
    metta_host_substitute(Bindings, Term0, Term),
    %The substituted TERM evaluates directly. Re-encoding it to a wire and
    %handing that back to the ordinary entry point looks tidier and is
    %wrong: a substituted host value is a boxed reference, and a round
    %trip through the encoder is exactly the copy `using` exists to
    %avoid.
    findall(E, metta_py_eval_term_bounded(Space, Term, E), Answers),
    ( Answers == [], metta_py_preserve_unmatched(Space, Term, Original)
      -> Encoded = [Original]
      ;  Encoded = Answers ).

%The lazy Answers door shares target decoding with eager eval, then holds one
%SWI engine so each Python pull resumes the producer rather than materializing
%it. These predicates live in the boot-consulted shim: consulting them on the
%first pull charged every fresh process for loading infrastructure rather than
%for its query.
metta_py_eval_target(Space, Target, Pairs, Term, Bindings) :-
    metta_py_target_term_bindings(Space, Target, Term0, Bindings),
    (   Pairs == []
    ->  Term = Term0
    ;   maplist(metta_py_using_pair, Pairs, Substitutions),
        metta_host_substitute(Substitutions, Term0, Term)
    ).

metta_py_eval_cursor_open(Space, Target, Pairs, VarNames, Inf, TimeS,
                          prolog(Engine)) :-
    metta_py_eval_cursor_open_controlled(
        Space, Target, Pairs, VarNames, Inf, TimeS, none, prolog(Engine)).

metta_py_eval_cursor_open_controlled(
        Space, Target, Pairs, VarNames, Inf, TimeS, Policy, prolog(Engine)) :-
    metta_py_eval_target(Space, Target, Pairs, Term, Bindings),
    Goal = ( statistics(inferences, Before),
             metta_py_eval_term_bounded(Space, Term, Encoded),
             metta_py_row(VarNames, Bindings, Row),
             statistics(inferences, Now), Used is Now - Before ),
    metta_host_time_budget(Goal, TimeS, Timed),
    metta_host_inference_budget(Timed, Inf, Bounded),
    metta_py_open_controlled_cursor(
        Policy, [Encoded, Row, Used], Bounded, Engine).

metta_py_eval_cursor_open_under(Space, Target, Pairs, VarNames, Inf, Algebra,
                                Direction, TimeS, prolog(Engine)) :-
    metta_py_eval_cursor_open_under_controlled(
        Space, Target, Pairs, VarNames, Inf, Algebra, Direction, TimeS, none,
        prolog(Engine)).

metta_py_eval_cursor_open_under_controlled(
        Space, Target, Pairs, VarNames, Inf, Algebra, Direction, TimeS, Policy,
        prolog(Engine)) :-
    metta_py_eval_target(Space, Target, Pairs, Term, Bindings),
    (   Direction \== none
    ->  Core = metta_py_ordered_eval_under(
                   Space, Term, VarNames, Direction, TimeS,
                   Bindings, Encoded, Row, K, Used)
    ;   Core = ( statistics(inferences, Before),
                 metta_algebra_one(Space, One),
                 b_setval('$metta_answer_k', One),
                 metta_py_eval_term_bounded(Space, Term, Encoded),
                 metta_py_row(VarNames, Bindings, Row),
                 b_getval('$metta_answer_k', K),
                 statistics(inferences, Now), Used is Now - Before )
    ),
    Goal = ( metta_with_evaluation_context(
                 evaluation_context(Algebra, 0, Direction), Core),
             metta_py_encode(K, KWire) ),
    metta_host_time_budget(Goal, TimeS, Timed),
    metta_host_inference_budget(Timed, Inf, Bounded),
    metta_py_open_controlled_cursor(
        Policy, [Encoded, Row, KWire, Used], Bounded, Engine).

metta_py_ordered_eval_under(Space, Term, VarNames, Direction, TimeS, Bindings,
                            Encoded, Row, K, Used) :-
    statistics(inferences, Before),
    metta_algebra_one(Space, One),
    metta_py_ordered_within_time(
        TimeS, Direction, K0-[Encoded0, Row0],
        ( b_setval('$metta_answer_k', One),
          metta_py_eval_term_bounded(Space, Term, Encoded0),
          metta_py_row(VarNames, Bindings, Row0),
          b_getval('$metta_answer_k', K0) ), Ordered),
    statistics(inferences, Now),
    Used is Now - Before,
    member(K-[Encoded, Row], Ordered).

metta_py_eval_count(Space, Target, Pairs, Count) :-
    metta_py_eval_target(Space, Target, Pairs, Term, _),
    metta_py_eval_count_term(Space, Term, Count).

%A count is a second evaluation. It is a free cardinality probe for an
%effect-safe goal, but executing an effectful operation here and then opening
%the held answer cursor fires the operation twice. Reuse the engine's table /
%memo admission walk as the decision: it follows user definitions, recognizes
%host operation declarations, and fails closed on an unknown effect. Unsafe
%answers return [] so Answers.__len__ materializes its one cursor instead.
metta_py_eval_count_if_repeatable(Space, Target, Pairs, Answer) :-
    metta_py_eval_target(Space, Target, Pairs, Term, _),
    (   metta_py_eval_repeatable(Space, Term)
    ->  metta_py_eval_count_term(Space, Term, Count), Answer = [Count]
    ;   Answer = []
    ).

metta_py_eval_repeatable(Space, Term) :-
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

metta_py_eval_count_term(Space, Term, Count) :-
    aggregate_all(
        count,
        metta_run_with_fuel(metta_py_answer(Out), _,
                            metta_py_eval_solution(Space, Term, Out, _)),
        Count).

%A count is a second evaluation, which an effect-bearing goal must not pay.
%Evaluate ONCE instead: hold every answer one step short of the wire, answer
%the count, and hand back a cursor that replays what was held. A count nobody
%turns into values then crosses one integer, where the materializing pass it
%replaces encoded and crossed every answer to reach that number; a later value
%demand encodes exactly the answers it pulls. Encoding is the whole per-answer
%cost here, measured on examples/ch07-control-flow/07-05-recursion/06-peano.metta's 301 answers: 2029719
%inferences counting without it, 2392138 counting with it, and 2393864 for the
%full materializing pass, so deferring the encode recovers 99.5% of the gap
%while the boundary walk it keeps costs one inference per answer.
%This is the held-portal shape a SQL engine uses to answer a count over an
%open cursor without re-running the query: PostgreSQL materializes a SCROLL
%cursor once and MOVE FORWARD ALL reports the row count with no row reaching
%the client [source: PostgreSQL 17 manual, SQL-DECLARE and SQL-MOVE].
%
%This is the one budget site that does NOT run in an engine: findall/3 drives
%the whole enumeration here, on the calling thread, so the counter it reads
%has been growing since the process started. That is why
%metta_host_inference_budget/3 takes a base when the goal starts rather than
%comparing the raw counter, and why the base cannot be dropped as dead weight
%on the grounds that an engine's counter starts near zero.
metta_py_eval_count_retaining(Space, Target, Pairs, VarNames, Inf,
                              [Count, prolog(Engine)]) :-
    metta_py_eval_target(Space, Target, Pairs, Term, Bindings),
    Collect = ( metta_py_eval_retained(Space, Term, Retained),
                metta_py_row(VarNames, Bindings, Row) ),
    metta_host_inference_budget(Collect, Inf, Bounded),
    findall(Retained-Row, Bounded, Bag),
    length(Bag, Count),
    %Same cumulative-inference report the evaluating cursor makes, so a
    %replayed view still tells its enclosing stats block what the held engine
    %spent. The evaluation's own inferences were spent on the caller's engine
    %and are already in that thread's counter.
    Replay = ( statistics(inferences, Before),
               member(Held-HeldRow, Bag),
               metta_py_retained_encoded(Held, Encoded),
               statistics(inferences, Now), Used is Now - Before ),
    metta_host_hold([Encoded, HeldRow, Used], Replay, Engine).

%One held answer: the fuel-scope result before its wire form exists.
metta_py_eval_retained(Space, Term, Retained) :-
    metta_run_with_fuel(metta_py_answer(Out-Delays), Retained,
                        metta_py_eval_solution(Space, Term, Out, Delays)).

%The encoding metta_py_eval_term_bounded/3 does eagerly, deferred to the pull
%that wants the answer. Mirrors metta_py_fuel_encoded/2: a fuel overflow
%answer is its own term rather than a held value-and-delays pair.
metta_py_retained_encoded(metta_py_answer(Out-Delays), Encoded) :- !,
    metta_py_encode_truth(Out, Delays, Encoded).
metta_py_retained_encoded(Overflow, Encoded) :- metta_py_encode(Overflow, Encoded).

metta_py_eval_count_under(Space, Target, Pairs, Algebra, Count) :-
    metta_with_under(
        Algebra,
        metta_py_eval_count(Space, Target, Pairs, Count)).

%The carrier count keeps the repeatability guard: counting is a second
%evaluation whatever algebra tags it, so an effect-unsafe goal answers []
%and the Python side counts through its one materializing pass.
metta_py_eval_count_under_if_repeatable(Space, Target, Pairs, Algebra, Answer) :-
    metta_with_under(
        Algebra,
        metta_py_eval_count_if_repeatable(Space, Target, Pairs, Answer)).

%metta_py_eval_term/3 is this dispatch plus metta_py_encode_truth/3, written
%out there rather than calling here so the eager answer path pays no extra
%frame. The two are held in step by
%test_a_retained_count_replays_the_bag_the_cursor_would_have_answered, which
%runs the same programs through both and compares the answer bags.
metta_py_eval_solution(Space, Term, Out, Delays) :-
    metta_py_module(Space, Module),
    ( metta_py_direct_goal(Module, Term, Goal, Produced)
      -> metta_py_in_module(Module, call_delays(call(Module:Goal), Delays))
    ; metta_py_in_module(Module, ( translate_cached_expr(Term, Goals, Produced),
                                   call_delays(metta_py_call_goals(Module, Goals),
                                               Delays) )) ),
    translator:metta_boundary_result(Term, Produced, Out).

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

metta_py_eval_term_bounded(Space, Term, Encoded) :-
    metta_run_with_fuel(metta_py_answer(Raw), Answer,
                        metta_py_eval_term(Space, Term, Raw)),
    metta_py_fuel_encoded(Answer, Encoded).

metta_py_eval_term(Space, Term, Encoded) :-
    metta_py_module(Space, Module),
    ( metta_py_direct_goal(Module, Term, Goal, Produced)
      -> metta_py_in_module(Module, call_delays(call(Module:Goal), Delays))
    ; metta_py_in_module(Module, ( translate_cached_expr(Term, Goals, Produced),
                                   call_delays(metta_py_call_goals(Module, Goals),
                                               Delays) )) ),
    translator:metta_boundary_result(Term, Produced, Out),
    metta_py_encode_truth(Out, Delays, Encoded).

%Which of MeTTa's own evaluation paths produced each answer, reported without
%changing what the ordinary entry points return:
%
%  value           an equation, builtin or special form applied
%  not-reducible   no rule applied, so the answer is the written term itself,
%                  which is what MeTTa does with any head it cannot call
%  empty           the goal produced no answer at all, which is what (empty)
%                  and a match with no candidates do
%
%MeTTa had no name for these, so the taxonomy was taken from the mechanised
%Hyperon specification, which is the only part borrowed [assumed: the four
%status names were taken from an earlier reference semantics, not re-measured
%against upstream PeTTa].
%The distinction that matters is the one that surface behaviour hides: empty
%is a pruned branch and not-reducible is an unevaluated term, and reading
%both as "nothing happened" is what made an earlier strict mode fire on
%(empty) and on a match with no candidates. An error is the fourth outcome
%there and is not reported here, because the caller already receives it as
%an exception.
%
%The head decides between value and not-reducible, using the same test the
%translator uses when it chooses between emitting a call and building data,
%so this reports the branch the engine actually took rather than guessing
%from the answer [tested test_eval_status_reports_the_four_outcomes].
%The reducibility question ASKED rather than answered by evaluating. It is
%the same head test eval_status uses, published on its own because a caller
%who wants to decide about an unreduced term should not have to run the term
%to find out. The Node seat has had m.reducible since it existed and this
%seat had only eval_status, which evaluates to tell you
%[measured 2026-08-31].
metta_py_reducible(Space, Tagged, Reducible) :-
    metta_py_target_term(Space, Tagged, Term),
    metta_py_module(Space, Module),
    %Status is asked UNBOUND, the way eval_status asks it: binding it to
    %`value` first skips the clause that reports a function whose heads do
    %not match, and every such term came back reducible.
    metta_py_eval_status(Module, Term, Status),
    (   Status == value
    ->  Reducible = true
    ;   Reducible = false
    ).

metta_py_eval_status_all(Space, Tagged, Results) :-
    metta_py_target_term(Space, Tagged, Term),
    metta_py_eval_status_term(Space, Term, Results).

metta_py_eval_status_using_all(Space, Tagged, Pairs, Results) :-
    metta_py_target_term(Space, Tagged, Term0),
    maplist(metta_py_using_pair, Pairs, Bindings),
    metta_host_substitute(Bindings, Term0, Term),
    metta_py_eval_status_term(Space, Term, Results).

metta_py_eval_status_term(Space, Term, Results) :-
    metta_py_module(Space, Module),
    metta_py_eval_status(Module, Term, Status),
    findall([Status, E], metta_py_eval_term_bounded(Space, Term, E), Answers),
    ( Answers == []
      -> ( Status == 'not-reducible',
           metta_py_preserve_unmatched(Space, Term, Original)
           -> Results = [[Status, Original]]
           ;  Results = [[empty, none]] )
      ;  Results = Answers ).

metta_py_eval_status(Module, [F|Args], 'not-reducible') :-
    atom(F),
    %A deferred function has no fun_meta rows until its equations
    %translate, and this door's whole question is about those rows.
    spaces:metta_ensure_compiled(F),
    translator:fun_meta_module(Module, F, _),
    \+ translator:dispatch_any_head_matches(Module, F, Args),
    !.
metta_py_eval_status(Module, Term, Status) :-
    ( metta_reducible_head(Module, Term) -> Status = value
                                          ; Status = 'not-reducible' ).
