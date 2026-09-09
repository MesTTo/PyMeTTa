% Purpose: expose derivation trees and their named bindings.
% Assumes: loaded through _binding/shim.pl in its host module.

%%%%%%%%%% Derivation trees %%%%%%%%%%
%
% The classic proof-tree meta-interpreter, rendered in MeTTa terms: every
% compiled clause remembers its source equation through translated_from/2,
% so each node names the equation that fired, a stored atom is a leaf, and a
% builtin call is an opaque leaf. Control constructs recurse into the branch
% they execute. A finite depth emits a truncated node rather than claiming no
% proof. Negative depth means unbounded; Python puts that search behind the
% same time and inference guards as evaluation.

metta_py_derivations(Space, Tagged, Depth, Trees) :-
    findall(Tree, metta_py_derivation(Space, Tagged, Depth, Tree), Trees).

metta_py_derivation(Space, Tagged, Depth, TreeTagged) :-
    metta_py_decode_shared(Tagged, Term, _),
    Term = [F|Args],
    atom(F),
    append(Args, [Out], FullArgs),
    Goal =.. [F|FullArgs],
    metta_py_module(Space, Module),
    metta_py_in_module(Module, metta_py_solve(Module, Goal, Depth, Tree)),
    metta_py_encode_tree(Tree, [F|Args], Out, TreeTagged).

metta_py_solve(M, Goal, D, Tree) :-
    metta_py_solve_barrier(M, Goal, D, Tree, _).

%A cut prunes the clauses that follow it and the choicepoints that precede
%it in the same body. Recorded as a leaf and simply called, it pruned
%neither, so the tree proved conclusions the program cannot reach: two
%equations for one head, the first cutting, proved both while run answered
%only the first.
%
%That is the naive incorporation the literature names and rejects: "A naive
%incorporation of cuts treats them as a builtin predicate, effectively
%adding a clause solve(!) <- !. This clause does not achieve the correct
%behavior of cut. The cut in the clause commits to the current solve clause
%rather than pruning the search tree." What has to be modelled instead is
%the cut's SCOPE, the clause in which the cut is a goal
%[source: Sterling and Shapiro, The Art of Prolog, 2nd ed., p327, ch17].
%That page states the problem and refers the solution out, so the technique
%below is this engine's own.
%
%Passing a cut signal upward prunes the later clauses but not the earlier
%goals, so the cut throws instead. Every construct that is a cut barrier in
%Prolog, a clause body, call/1, once/1, \+/1, findall/3 and an if-then-else
%condition, catches its own throw and turns it into failure, which discards
%the goals inside it and the clauses beside it together. That is what a cut
%does [tested: test_derivation_honours_a_cut].
metta_py_solve_barrier(M, Goal, D, Tree, Status) :-
    gensym('$metta_py_cut_', Barrier),
    catch(metta_py_solve_(M, Goal, D, Tree, Status, Barrier),
          metta_py_cut(Barrier),
          fail).

metta_py_solve_(_, Goal, 0, [truncated(Goal)], truncated, _) :- !.
metta_py_solve_(_, true, _, [], complete, _) :- !.
metta_py_solve_(_, '!', _, [builtin(!)], complete, Barrier) :- !,
    ( true ; throw(metta_py_cut(Barrier)) ).
metta_py_solve_(M, (If -> Then ; Else), D, Tree, Status, Barrier) :- !,
    ( metta_py_solve_barrier(M, If, D, IfTree, IfStatus)
      -> ( IfStatus == truncated
           -> Tree = IfTree, Status = truncated
         ; metta_py_solve_(M, Then, D, ThenTree, Status, Barrier),
           append(IfTree, ThenTree, Tree) )
    ; metta_py_solve_(M, Else, D, Tree, Status, Barrier) ).
metta_py_solve_(M, (If -> Then), D, Tree, Status, Barrier) :- !,
    ( metta_py_solve_barrier(M, If, D, IfTree, IfStatus)
      -> ( IfStatus == truncated
           -> Tree = IfTree, Status = truncated
         ; metta_py_solve_(M, Then, D, ThenTree, Status, Barrier),
           append(IfTree, ThenTree, Tree) )
    ; fail ).
%The SOFT cut, which the engine writes wherever a call must keep every answer
%and still have an else arm: the typed-dispatch fallback is
%`( <branches> *-> true ; dispatch_mismatch_result(...) )` and the error
%short circuit is `( <call> *-> true ; <recovery> )`. Without these two clauses
%the pair below reads the whole construct as one opaque builtin, so a proof
%stopped at the wrapper instead of descending into the call it wraps: the
%recursive branch of a conditional equation showed one rule where three fired
%[tested: test_conditional_derivation_exposes_the_recursive_branch]. They sit
%ABOVE the plain disjunction because `( If *-> Then ; Else )` IS a disjunction
%whose left side is the soft cut, and that reading loses the else arm's
%condition.
metta_py_solve_(M, (If *-> Then ; Else), D, Tree, Status, Barrier) :- !,
    (   metta_py_solve_barrier(M, If, D, IfTree, IfStatus)
    *-> ( IfStatus == truncated
          -> Tree = IfTree, Status = truncated
        ; metta_py_solve_(M, Then, D, ThenTree, Status, Barrier),
          append(IfTree, ThenTree, Tree) )
    ;   metta_py_solve_(M, Else, D, Tree, Status, Barrier) ).
metta_py_solve_(M, (If *-> Then), D, Tree, Status, Barrier) :- !,
    metta_py_solve_barrier(M, If, D, IfTree, IfStatus),
    ( IfStatus == truncated
      -> Tree = IfTree, Status = truncated
    ; metta_py_solve_(M, Then, D, ThenTree, Status, Barrier),
      append(IfTree, ThenTree, Tree) ).
metta_py_solve_(M, (A ; B), D, Tree, Status, Barrier) :- !,
    ( metta_py_solve_(M, A, D, Tree, Status, Barrier)
    ; metta_py_solve_(M, B, D, Tree, Status, Barrier) ).
metta_py_solve_(M, (A, B), D, Tree, Status, Barrier) :- !,
    metta_py_solve_(M, A, D, TA, SA, Barrier),
    ( SA == truncated
      -> Tree = TA, Status = truncated
    ; metta_py_solve_(M, B, D, TB, Status, Barrier),
      append(TA, TB, Tree) ).
metta_py_solve_(M, call(A), D, Tree, Status, _) :- !,
    metta_py_solve_barrier(M, A, D, Tree, Status).
metta_py_solve_(M, once(A), D, Tree, Status, _) :- !,
    once(metta_py_solve_barrier(M, A, D, Tree, Status)).
metta_py_solve_(M, \+ A, D, Tree, Status, _) :- !,
    ( once(metta_py_solve_barrier(M, A, D, TA, SA))
      -> ( SA == truncated
           -> Tree = TA, Status = truncated
         ; fail )
    ; Tree = [builtin(\+ A)], Status = complete ).
metta_py_solve_(M, findall(Template, Goal, List), D, Tree, Status, _) :- !,
    findall([Template, SubTree, SubStatus],
            metta_py_solve_barrier(M, Goal, D, SubTree, SubStatus),
            Results),
    metta_py_findall_results(Results, Values, Tree, Status),
    ( Status == complete -> List = Values ; true ).

%The P3 dispatcher is engine machinery, but its shipped fast path wraps an
%ordinary generated goal. Treating the wrapper as a generic Prolog predicate
%enumerated its implementation clauses as separate proofs and ran the wrapped
%recursion through call/1, outside the derivation depth counter. Open the fast
%path and keep its direct goal inside this interpreter. A non-default policy is
%still executed by the authoritative dispatcher and recorded as one opaque
%builtin; duplicating its retained-clause interpreter here would let proofs and
%evaluation drift on the six policy axes.
metta_py_solve_(_,
                dispatch_policy_execute(Module, Fun, Args, Goal, Out),
                D, Tree, Status, Barrier) :-
    !,
    metta_host_dispatch_proof_step(Module, Fun, Args, Goal, Out, Route),
    (   Route == direct
    ->  metta_py_solve_(Module, Goal, D, Tree, Status, Barrier)
    ;   Route == opaque,
        Tree = [builtin(dispatch_policy_execute(Module, Fun, Args, Goal, Out))],
        Status = complete
    ).

%Application/result protocol helpers only classify the value the preceding
%goal produced.  They are transparent proof steps: retaining a call or exposing
%NotReducible is not another premise and must not turn a recursive MeTTa call
%into an opaque builtin leaf.
metta_py_solve_(M, metta_application_result(Written, Produced, Out), _,
                [], complete, _) :- !,
    call(M:metta_application_result(Written, Produced, Out)).
metta_py_solve_(M,
                metta_application_result(Source, Runtime, Produced, Out), _,
                [], complete, _) :- !,
    call(M:metta_application_result(Source, Runtime, Produced, Out)).
metta_py_solve_(M, metta_boundary_result(Written, Produced, Out), _,
                [], complete, _) :- !,
    call(M:metta_boundary_result(Written, Produced, Out)).

%A clause compiled from a MeTTa equation is a step worth showing, and its body
%is walked further. Everything else, engine machinery and space facts alike, is
%called whole and appears as one leaf, so the tree stays in MeTTa terms. The
%lookup is module-qualified: a named space's equations live in its module, and
%clause/3 falls back to user through module inheritance for the rest. Only the
%clause INSPECTION is guarded (an uninspectable goal is an opaque leaf); a
%body or builtin that ERRS propagates, because (+ $x $y) failing into "no
%proof" would be a lie about why (integer zero division is Error data):
%One barrier serves every clause of the goal, because a cut in the body of
%one clause discards the clauses after it as well as its own alternatives.
metta_py_solve_(M, Goal, D, Tree, Status, _) :-
    \+ predicate_property(M:Goal, built_in),
    gensym('$metta_py_cut_', Barrier),
    catch(metta_py_solve_clause(M, Goal, D, Tree, Status, Barrier),
          metta_py_cut(Barrier),
          fail).
metta_py_solve_(M, Goal, _, [builtin(Goal)], complete, _) :-
    predicate_property(M:Goal, built_in), !,
    call(M:Goal).

%A clause's body runs in the module that DEFINES the clause, which is the
%space's module for a MeTTa equation and an engine subsystem's for engine
%machinery. Running it in the caller's module worked only while the whole
%engine shared one namespace: once engine/spaces.pl became a module of its own,
%descending into match/4 and calling its body under the space gave
%existence_error(procedure, '$metta_exec:&self':match_native/5), because
%match_native/5 is spaces' own and a base module lends only what it exports
%[measured 2026-08-22, on every test in tests/test_derivation.py].
metta_py_solve_clause(M, Goal, D, Tree, Status, Barrier) :-
    %clause/2 is a read, not a call, so the undefined-predicate net never
    %fires for a deferred callee and the proof walk saw zero clauses where
    %evaluation answers. Force the name at every step: the tree descends
    %into callees the running program may never have reached.
    (   Goal =.. [Predicate|_],
        translator:compiled_function_name(Fun, Predicate)
    ->  spaces:metta_ensure_compiled(Fun)
    ;   true
    ),
    metta_py_clause_owner(M, Goal, Owner),
    catch_recover(clause(Owner:Goal, Body, Ref), fail),
    ( translated_from(Ref, Source)
      -> metta_py_next_depth(D, D1),
         metta_py_body_after_stack_charge(Owner, Body, Premises),
         metta_py_solve_(Owner, Premises, D1, Sub, Status, Barrier),
         Tree = [step(Goal, Source, Sub)]
    ; call(Owner:Body),
      %The LEAF keeps the caller's module, because what it names is the space
      %the fact came from and not the subsystem that ran the goal.
      metta_py_leaf(M, Goal, Tree),
      Status = complete ).

%catch_recover/2 rather than catch/3, because this runs once per level of a
%derivation and a blanket catch swallows the very signals that stop an
%unbounded one: inference_limit_exceeded arriving inside predicate_property/2
%was caught here and the loop ran on to a stack overflow at depth 9,673,261
%instead of raising at 2,000 inferences
%[measured 2026-08-22; tested: test_unbounded_derivation_obeys_resource_guards].
metta_py_clause_owner(M, Goal, Owner) :-
    (   catch_recover(predicate_property(M:Goal,
                                         implementation_module(Definer)),
                      fail)
    ->  Owner = Definer
    ;   Owner = M
    ).

%A recursive equation's clause opens with the stack charge that
%engine/spaces/foreign.pl's metta_instrument_recursive_clause/3 writes in front
%of the translated body, built by engine/metta/control.pl's
%metta_fuel_step_goal/3. That charge is the engine counting its own recursion
%depth, not a premise of the program being proved, so it contributes no node.
%Walked as ordinary goals it put `builtin
%system:b_getval('$metta_fuel_remaining',off)` and `builtin off==off` in front
%of every premise of every recursive equation
%[tested: test_a_recursive_proof_omits_the_engine_stack_charge].
%
%RECOGNISED by the engine, not by a shape spelled again here. Every binding
%that walks compiled clauses meets this charge, so the recogniser is
%metta_host_stack_charge/3 beside the generator that writes it and the next
%seat does not re-pay it. It hands the charge back rather than running it,
%because a clause body runs in the module that DEFINES the clause and only this
%caller knows which that is.
%
%CALLED rather than skipped, at the point the body would have run it. A proof
%walk opens no fuel scope of its own, so the balance reads `off` and the charge
%decides nothing today; derivation bounds its search with the timeout and
%inference guards instead [tested:
%test_unbounded_derivation_obeys_resource_guards]. Calling it keeps that a
%property of the SCOPE rather than of this predicate, so a proof walked inside
%an open scope is charged exactly as evaluation is.
%
metta_py_body_after_stack_charge(Owner, Body, Premises) :-
    metta_host_stack_charge(Body, Charge, Premises), !,
    call(Owner:Charge).
metta_py_body_after_stack_charge(_, Body, Body).

metta_py_findall_results([], [], [], complete).
metta_py_findall_results(
    [[Value, SubTree, SubStatus]|Results], [Value|Values], Tree, Status) :-
    metta_py_findall_results(Results, Values, RestTree, RestStatus),
    append(SubTree, RestTree, Tree),
    ( SubStatus == truncated -> Status = truncated ; Status = RestStatus ).

metta_py_next_depth(D, D) :- D < 0, !.
metta_py_next_depth(D, D1) :- D1 is D - 1.

%A match over a space names the atom it found; anything else names its goal:
metta_py_leaf(_, match(Space, Pattern, _, _), [fact(Space, Pattern)]) :- !.
metta_py_leaf(Module, Goal, [fact(Space, Fact)]) :-
    metta_host_native_fact(Module, Goal, Space, Fact), !.
metta_py_leaf(_, Goal, [fact('&self', Fact)]) :-
    functor(Goal, Space, _),
    atom_concat('&', _, Space), !,
    Goal =.. [Space|Fact].
metta_py_leaf(_, Goal, [builtin(Goal)]).

%The tree crosses as nested tagged expressions:
%  (derivation Conclusion Steps...) with each step
%  (step Conclusion (= Head Body) Substeps...), (fact Atom), (builtin Text),
%  or (truncated Goal).
%NAMED, because metta_py_encode/2 spells a variable with term_to_atom/2 and
%SWI derives that spelling from the cell's global-stack offset, which a
%garbage collection moves. One variable therefore crossed under two names
%when a collection landed between two of its occurrences, and the sharing
%decoder, which aliases by name, read two variables. A five-deep (fact 5)
%proof crossed as
%  (= (fact $_17642) (if (> $_17642 0) (* $_17642 (fact (- $_2528 1))) 1))
%whose free $_2528 made the body non-ground, so the consumer's substitution
%left (- $_2528 1) and evaluating it raised the CLP(FD) refusal rather than
%answering [measured 2026-08-31 against a proof tree of six steps].
%
%A whole tree is one term, so its variables are named ONCE from
%term_variables/2's order, which is a property of the term and not of the
%stack. That is engine/tracer.pl's metta_trace_variable_names/3 exactly: _0,
%_1 and so on by first occurrence, carried beside the term as Name-Var pairs
%and resolved by metta_py_var_name/3's identity lookup
%[source: engine/tracer.pl, metta_trace_variable_names/3].
metta_py_encode_tree(Steps, Root, Out, ["e", [["s", "derivation"], RootE | StepEs]]) :-
    metta_py_encode([Root, '=', Out], [], Names0, ["e", [R, _, O]]),
    RootE = ["e", [["s", "answer"], R, O]],
    metta_py_encode_steps(Steps, Names0, _, StepEs).

metta_py_encode_steps([], N, N, []).
metta_py_encode_steps([Step|Steps], N0, N, [E|Es]) :-
    metta_py_encode_step(Step, N0, N1, E),
    metta_py_encode_steps(Steps, N1, N, Es).

metta_py_encode_step(step(Goal, Source, Sub), N0, N,
                     ["e", [["s", "step"], GoalE, SourceE | SubEs]]) :-
    metta_py_encode_goal(Goal, N0, N1, GoalE0),
    metta_py_goal_term(GoalE0, GoalE),
    metta_py_encode(Source, N1, N2, SourceE),
    metta_py_encode_steps(Sub, N2, N, SubEs).
%A leaf's space is the NAME of the space the fact came from, an atom, so the
%map reaches it and comes back unchanged. Threaded rather than asserted
%unchanged, because pinning it would turn a space that is somehow not an atom
%into a silent failure instead of an encoding.
metta_py_encode_step(fact(Space, Fact), N0, N,
                     ["e", [["s", "fact"], SpaceE, FactE]]) :-
    metta_py_encode(Space, N0, N1, SpaceE),
    metta_py_encode(Fact, N1, N, FactE).
metta_py_encode_step(builtin(Goal), N0, N,
                     ["e", [["s", "builtin"], ["g", Text]]]) :-
    metta_py_written_goal(Goal, N0, N, Text).
metta_py_encode_step(truncated(Goal), N0, N,
                     ["e", [["s", "truncated"], ["g", Text]]]) :-
    metta_py_written_goal(Goal, N0, N, Text).

%A leaf that crosses as TEXT rather than as structure still holds the tree's
%variables: the solver records goals such as builtin(\+ A) whose A an
%equation beside it also holds. term_string/2 wrote the cell's address there
%while the equation carried the tree's name for the same variable, so a
%reader could not see that the two are one. write_term/2's variable_names
%option takes the same map spelled Name=Var.
metta_py_written_goal(Goal, Names0, Names, Text) :-
    term_variables(Goal, Variables),
    metta_py_wire_names(Variables, Names0, Names),
    metta_py_name_assignments(Names, Assignments),
    term_string(Goal, Text, [variable_names(Assignments)]).

%A written leaf mints its variables' names the way an encoded one does, so
%the two spell one cell the same. Only the map moves; nothing is encoded.
metta_py_wire_names([], N, N).
metta_py_wire_names([Variable|Rest], N0, N) :-
    metta_py_wire_name(Variable, N0, N1, _),
    metta_py_wire_names(Rest, N1, N).

metta_py_name_assignments([], []).
metta_py_name_assignments([Name-Variable|Pairs], [Name=Variable|Assignments]) :-
    metta_py_name_assignments(Pairs, Assignments).

%metta_py_encode_named/3 carries its pairs through variables and lists and
%hands every other compound to the unscoped encoder, and a step's goal is a
%compiled call f(A1..An, Out), which is one. Encoding it unscoped inside a
%tree that is otherwise named is worse than naming nothing: a variable a
%parent's equation and a child's goal share would cross under two names and
%stop being one variable. Goal is a clause head, so it is an atom or a
%compound with an atom functor, and the list [f, A1..An, Out] encodes to the
%same ["e", [["s", f] | Es]] the compound clause writes.
metta_py_encode_goal(Goal, N0, N, Encoded) :-
    compound(Goal),
    compound_name_arguments(Goal, Functor, Arguments),
    atom(Functor), !,
    metta_py_encode([Functor|Arguments], N0, N, Encoded).
metta_py_encode_goal(Goal, N0, N, Encoded) :-
    metta_py_encode(Goal, N0, N, Encoded).

%A compiled goal f(A1..An,Out) renders as the call (f A1..An) with its answer:
metta_py_goal_term(["e", [F | ArgsAndOut]], ["e", [["s", "call"], ["e", [F|Args]], Out]]) :-
    append(Args, [Out], ArgsAndOut), !.
metta_py_goal_term(E, ["e", [["s", "call"], E, ["s", "?"]]]).
