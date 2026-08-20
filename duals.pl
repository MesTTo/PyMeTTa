% Purpose: constructive negation. Compile a MeTTa function's equations into a
%   dual function that succeeds exactly for the arguments the original cannot
%   prove, and expose it as (not-provable Expr).
%
%   Before this the engine had no negation at all. (not X) is a boolean
%   function: it maps True to False and False to True, and a MeTTa expression
%   that no equation matches does not reduce to False, it stays as data. So
%   with (= (penguin polly) True) declared, (penguin tweety) has no answer and
%   (not (penguin tweety)) has no answer either. There was nothing to write.
%
%   The construction is s(CASP)'s dual-rule transformation, taken as a
%   structure rather than as code [source: SWI-Prolog/sCASP, Apache-2.0,
%   prolog/scasp/comp_duals.pl]: dual each equation separately, take the
%   conjunction of those duals, negate a body by De Morgan while keeping every
%   preceding goal positive, and universally quantify the variables that occur
%   in a body but not in the head. Their program representation (c_rule/3,
%   predicate/3, defined_rule/4) is not ours, so nothing is copied.
%
%   Two places where SWI does it better than a port would:
%
%   - disequality is dif/2, not s(CASP)'s clp_disequality. dif/2 constrains a
%     whole compound as one unit, delays on two non-ground terms, and is
%     documented as "a more general and more declarative alternative for \=/2"
%     [source: SWI-Prolog 10.1 Reference Manual, section 8.2]. s(CASP)'s
%     .\=./2 fails outright on two non-ground variables, a restriction their
%     own section 3.1.5 records.
%   - the residual constraints of a solution are read back with copy_term/3,
%     which is what makes the universal quantification implementable in fifty
%     lines instead of s(CASP)'s constraint-store dump.
%
%   What an answer here IS has a name and a framework: a CONSTRAINED ANSWER, a
%   syntactic part plus a constraint in solved form rather than a substitution
%   [source: Kirchner, Kirchner and Rusinowitch, "Deduction with symbolic
%   constraints", Revue d'Intelligence Artificielle 4(3):9-52, 1990]. That is
%   why "which node has no outgoing edge" comes back as a variable carrying
%   dif/2 goals instead of an enumeration, and why 'residual-goals'/2 exists to
%   read one. dif/2 is that framework's discharge rule already implemented:
%   decide the constraint the moment the bindings decide it, defer it
%   otherwise.
%
%   What this repairs is named in The Art of Prolog, 2nd ed, section 11.3
%   (pages 199-201): negation as failure "is not guaranteed to work correctly
%   for nonground goals", so
%       unmarried_student(X) :- not married(X), student(X).
%   fails with student(bill) and married(joe) in the database, "ignoring that
%   X=bill is a solution logically implied by the rule and two facts", and
%   `not (X=1), X=2` fails although X=2 is a solution. Both come out right
%   here, because the dual of a head argument is dif/2 rather than a failed
%   proof [tested: duals_art_of_prolog].
% Assumes:
%   - translator.pl:fun_meta_clause/4 retains one fact per compiled equation
%     holding its head arguments and its unevaluated MeTTa body
%     [source: src/translator.pl, record_fun_meta/3].
%   - a head argument that constrain_args/3 compiles into a GOAL rather than
%     into structure, which is the in-place type annotation `(: $x T)`, is
%     recorded by fun_head_goals/2 so this file can refuse it rather than
%     dualise a head it cannot see [tested: an_annotated_head_has_no_dual].
%   - MeTTa True and False are the Prolog atoms true and false
%     [source: src/parser.pl:133].
% Guarantees:
%   - (not-provable G) answers False once per way G reduces to True and True
%     once per solution of G's dual, so for a ground G exactly one of the two
%     holds and for a non-ground G the two partition the answers
%     [tested: duals_partition].
%   - every form this cannot dualise soundly raises rather than answering from
%     an incomplete dual [tested: duals_refusals].
%   - a dual is rebuilt when the equations it was built from change, through
%     the same metta_on_function_changed/1 hook the memo tables use
%     [tested: duals_invalidation].
% Owns: the generated dual clauses. record_source_assertion/1 registers each
%   one so a failed source load erases them with everything else.
% Decides: the supported body forms are True, False, and, or, not,
%   not-provable, and-then, or-else, if, case, let, let*, chain, match,
%   collapse, superpose, quote, the six comparisons and their CLP(FD)
%   counterparts, ==, != and calls to other MeTTa functions.
%   Everything else raises. A wider set would mean guessing at a dual, and a
%   wrong dual answers "not provable" for something that is provable.
%   let and match are the two GENERATORS, and they are quantified over what
%   they produce rather than over every term: a variable of theirs that the
%   rest of the clause cannot see is quantified away, and one it can see is
%   narrowed and answered [tested: duals_let, duals_match].
% Fails when:
%   - a case's cases or a let*'s bindings only arrive when the program runs.
%     A dual is built once, out of the equation as it was written, so there
%     is nothing there to expand and both forms refuse; let* used to expand
%     an unarrived bindings list into the empty one instead and answer from a
%     dual with the bindings dropped
%     [tested: a_let_star_whose_bindings_have_not_arrived_has_no_dual].
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

:- use_module(library(dif)).
%For the domain-coverage branch below: fd_dom/2, fd_size/2, #\ and in/2. The
%engine already loads clpfd, and this file is consulted before that import
%runs, so the operators are not otherwise in scope here.
:- use_module(library(clpfd)).
:- use_module(library(lists)).
:- use_module(library(apply)).

%%%%%%%%%%%%%%%%%%%%%% Constraints the duals are built from %%%%%%%%%%%%%%%%%%%

%The MeTTa spelling of dif/2, under SWI's own name for it because it is the
%standard CLP(H) disequality and it is what the residual goals of an answer
%print as. (dif $a $b) answers True and constrains the two terms never to
%become identical, which is what makes a dual constructive: the answer to
%"which x is not a penguin" is every x except polly, carried as a constraint
%rather than enumerated.
%
%NOT the same question as (!= $a $b), and both are worth having. `!=` is
%Prolog's \==: are these two terms identical NOW. On an unbound variable it
%answers True and a later binding may contradict it, because it is a
%meta-logical TEST rather than a claim about unifiability. `dif` answers True
%and makes that later binding FAIL instead. The Art of Prolog's Program 11.8
%warns that its \= "is only guaranteed to work correctly for ground goals"
%(page 201), and reading `!=` as the test rather than the claim is what keeps
%both sound; it is not the predicate that warning is about.
%
%So `!=` was deliberately not turned into `dif`. Changing an existing
%builtin's meaning is not a fix, and a program that wants the constraint can
%write it under its own name.
dif(A, B, true) :- dif(A, B).

%The constraints an answer is still carrying, as MeTTa expressions. A
%constructive negation answers over an infinite domain, so its answer is a
%constraint and not an enumeration: "which node has no outgoing edge" comes
%back as an unbound variable that is nothing else's source. Printed on its own
%that reads as no answer at all, and SWI calls such an answer floundering
%[source: SWI-Prolog 10.1 Reference Manual, section 8.2, "Remaining
%constraints ... are called residual goals"]. This is how to read one.
%
%copy_term/3 hands back the constraints over a fresh copy; unifying the copy
%with the original puts them back over the variable the caller holds, so the
%answer names the same variable it constrained.
'residual-goals'(Term, Goals) :-
    copy_term(Term, Copy, Residual),
    Copy = Term,
    maplist(residual_expression, Residual, Goals).

residual_expression(Goal, [Name|Args]) :- Goal =.. [Name|Args].

%"X is not an F/N term". Reached only when a head pattern holds a compound
%that still contains variables, where dif/2 is the wrong tool: dif(X, f(A,B))
%with A and B fresh asks for X to differ from SOME f-term, and the dual needs
%X to differ from EVERY f-term. That is not expressible as a constraint over
%an unbound X and an open signature, so an unbound X raises here instead of
%answering. s(CASP) reaches the same wall and drops the branch silently
%[source: prolog/scasp/clp/disequality.pl, not_unify2/2 fails on a non-ground
%right-hand side].
metta_not_functor(X, Name, Arity) :-
    (   nonvar(X)
    ->  functor(X, XName, XArity),
        \+ ( XName == Name, XArity =:= Arity )
    ;   throw(error(instantiation_error,
                    context(metta_not_functor/3,
                            'a dual needs this argument instantiated to decide \c
                             whether it matches a structured pattern')))
    ).

%%%%%%%%%%%%%%%%%%%%%%%%% Constructive universal quantification %%%%%%%%%%%%%%%

%A variable that occurs in an equation's body but not in its head is
%existential in the original, so it is universal in the dual: (= (p $x) (q $x
%$y)) proves p when SOME y works, so not-p holds when NO y works.
%
%forall/2 cannot express that, because it needs a generator and the point of a
%dual is not to enumerate a domain. This is s(CASP)'s forall algorithm
%[source: Arias et al., "Constraint Answer Set Programming without Grounding",
%section 2.3, implemented in prolog/scasp/solve.pl as solve_var_forall_/11]:
%solve the goal once and look at what the variable came back as.
%
%  - still unconstrained: the goal held without needing anything of it, so it
%    holds for every value. Done.
%  - constrained to differ from a finite set of values: it holds for
%    everything outside that set, so check the set, one value at a time.
%  - instantiated: this solution covers one value only. Backtrack and look for
%    a more general one.
%
%copy_term/4 copies only the quantified variables, leaving the head variables
%shared, which is exactly s(CASP)'s my_copy_term/4.
%Every one of these carries a goal that was COMPILED IN A SPACE'S MODULE and
%is being called from this file, which is the engine's. Without the
%declaration the call resolves here instead, and a dual over a function the
%program defined raised Unknown procedure for it
%[tested: examples/reasoning/constructive_negation.metta]. It was invisible
%while &self compiled into this same module and would have bitten any named
%space that used a dual; the declaration is the manual's own remedy
%[source: SWI-Prolog 10.1 Reference Manual, chapter 6, defining a
%meta-predicate].
:- meta_predicate metta_forall_c(+, 0),
                  forall_cover(?, 0),
                  domain_coverage(?, ?, 0),
                  forall_excluded(+, ?, 0).
metta_forall_c([], Goal) :- !, call(Goal).
metta_forall_c([Var|Vars], Goal) :-
    forall_cover(Var, metta_forall_c(Vars, Goal)).

forall_cover(Var, Goal) :-
    copy_term(Var, Goal, Var1, Goal1),
    call(Goal1),
    (   var_coverage(Var1, Excluded)
    ->  !,
        forall_excluded(Excluded, Var, Goal)
    ;   domain_coverage(Var1, Var, Goal)
    ).

%A finite-domain residual is the third kind of coverage, beside "unconstrained"
%and "differs from a finite set". The covering solution restricted the variable
%to a DOMAIN, so the values it excluded are the domain's COMPLEMENT, and clpfd
%computes that rather than this walking intervals by hand: `#\ (X in Dom)`
%posts the complement and fd_dom/2 reads it back. `inf..6\/8..sup` complements
%to `7..7` and `4..sup` to `inf..3` [measured 2026-08-16].
%
%Which splits the case in two, and the split is worth having because half of
%it is a COMPLETE answer.
%
%A FINITE complement is exactly the situation the dif/2 branch already handles:
%enumerate it and check each value with a fresh call, and the quantification is
%decided both ways. `(#\= $x 7)` complements to the single value 7.
%
%An INFINITE one can only be decided in one direction, and that asymmetry is
%deliberate. One value out of it is a candidate counterexample: if the goal
%FAILS there, no value makes it hold everywhere and the quantification is
%False, soundly and with a proof. If it HOLDS there, nothing follows, because
%the rest of an infinite set is unchecked and this covering solution was simply
%not general enough. That case still raises, so this is strictly a decision
%where there was a refusal and never a refusal turned into a wrong answer.
%
%`(not-provable (#< $x 4))` is the shape this was for. Its dual is
%`(#>= $x 4)`, the covering solution posts `4..sup`, the complement `inf..3` is
%infinite, its witness 3 fails `3 #>= 4`, and the answer is False where it used
%to be `Domain error: enumerable_constraint`
%[tested: duals_domain_coverage].
%
%SWI's not_exists/1 was the other candidate and is not taken. It decides the
%same case correctly, 166 inferences for a satisfiable bound and 184 for an
%unsatisfiable one [measured 2026-08-16], and the manual defines it as
%`tnot(exists X p(X))`, which is exactly the quantification wanted. What rules
%it out is the obligation that comes with it: "each Goal variant populates a
%table for tabled_call/1. Applications may need to abolish such tables ... to
%guarantee consistency after the world changed" [source: SWI-Prolog 10.1
%Reference Manual, not_exists/1]. A MeTTa space's world changes on every write,
%so adopting it would put a staleness hazard on the negation path in place of a
%raise. This decides the same case with no table at all.
domain_coverage(Var1, Var, Goal) :-
    domain_complement(Var1, Complement, Size),
    integer(Size),
    !,
    findall(Value, complement_value(Complement, Value), Excluded),
    forall_excluded(Excluded, Var, Goal).
domain_coverage(Var1, Var, Goal) :-
    domain_complement(Var1, Complement, _),
    complement_witness(Complement, Witness),
    copy_term(Var, Goal, Var2, Goal2),
    Var2 = Witness,
    \+ call(Goal2),
    !,
    fail.
domain_coverage(Var1, _, _) :-
    copy_term(Var1, Copy, Residual),
    refuse_unenumerable_residual(Residual, Copy).

domain_complement(Var, Complement, Size) :-
    fd_dom(Var, Domain),
    #\ (Fresh in Domain),
    fd_dom(Fresh, Complement),
    fd_size(Fresh, Size).

complement_value(Complement, Value) :-
    Value in Complement,
    label([Value]).

%One value the domain does not admit, read off whichever end of the complement
%is bounded.
complement_witness(Complement, Witness) :-
    Probe in Complement,
    (   fd_inf(Probe, Witness), integer(Witness)
    ->  true
    ;   fd_sup(Probe, Witness), integer(Witness)
    ).

%Each value the covering solution excluded has to be checked on its own.
forall_excluded([], _, _).
forall_excluded([Value|Values], Var, Goal) :-
    copy_term(Var, Goal, Var1, Goal1),
    Var1 = Value,
    call(Goal1),
    forall_excluded(Values, Var, Goal).

%What a solution left of the quantified variable. Fails when the solution
%bound it, which sends forall_cover/2 back for a more general one.
var_coverage(Var, Excluded) :-
    var(Var),
    copy_term(Var, Copy, Residual),
    excluded_values(Residual, Copy, Excluded).

excluded_values([], _, []).
excluded_values([Goal|Goals], Copy, [Value|Values]) :-
    nonvar(Goal),
    Goal = dif(Left, Right),
    (   Left == Copy, ground(Right) -> Value = Right
    ;   Right == Copy, ground(Left) -> Value = Left
    ),
    !,
    excluded_values(Goals, Copy, Values).
%FAILS on a residual it cannot enumerate rather than raising, so
%forall_cover/2 can try domain_coverage/3 on it. The raise moved there, to the
%clause reached once that has run out of ways to decide.
excluded_values([Goal|_], _, _) :-
    \+ enumerable_residual(Goal),
    fail.

enumerable_residual(Goal) :- nonvar(Goal), Goal = dif(_, _).

refuse_unenumerable_residual([Goal|_], _) :-
    throw(error(domain_error(enumerable_constraint, Goal),
                context(metta_forall_c/2,
                        'a dual cannot decide a universally quantified variable \c
                         carrying this constraint'))).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% The negation form %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%(not-provable G) answers both ways round, which is what makes it compose with
%if and with and: False for each way G reduces to True, True for each solution
%of G's dual. For a ground G exactly one branch answers. For a non-ground G
%they partition it, so (not-provable (penguin $x)) answers False with $x=polly
%and True with $x constrained away from polly.
%Compiled rather than interpreted, so (not-provable (== $x 1)) becomes a dif/2
%constraint and (not-provable (and A B)) becomes De Morgan, instead of every
%negation going through one runtime dispatcher. Only a call to a MeTTa
%function is left to run time, because that is the only part that depends on
%equations which may not be compiled yet.
%Local is deliberately fresh here: which variables are local to this negation
%is a property of the whole clause, and quantify_negations/2 fills it in once
%the clause exists. It is threaded into the dual as well as recorded on the
%marker, so a generator inside the negation reads the SAME answer about which
%of its variables the rest of the clause can see.
%The dualisability check runs BEFORE the positive goal, which is an ordering
%change and not a new mechanism. metta_negation/5 tries `call(True)` first and
%only reaches the dual when that fails, so a refusal built into the dual fired
%after the positive goal had already run: `!(not-provable (okop 2))` invoked
%okop and THEN reported that okop has no dual, and `!(not-provable (raiser 2))`
%reported the operation's own RuntimeError instead, so the same call shape gave
%two different errors depending on whether Python happened to raise
%[source: ai-metta-python-seams.md item 2].
%
%A refusal that fires after the side effect is not a refusal. Whether a function
%is dualisable depends on its definition and not on its arguments, so nothing is
%lost by asking first. It stays at RUNTIME rather than moving to compile time,
%because the equations a dual summarises are not settled when the call compiles:
%a rule may be written before the equations it negates, and two functions may
%negate each other.
metta_not_provable_goal(Expr, (Ensure, Negation), Out) :-
    current_metta_module(Module),
    term_variables(Expr, SourceVars),
    body_true(Expr, True),
    body_nottrue(Expr, Module, Local, Dual),
    dual_preconditions(Dual, Ensure),
    Negation = metta_negation(Local, SourceVars, True, Dual, Out).

%Every dual the negation could need, read off the dual body that was just
%built. Reading them from the BODY rather than from the source expression is
%what makes this cover a nested one: `(not-provable (and (p) (okop 2)))` builds
%a dual holding both calls, and both are established before either runs.
dual_preconditions(Dual, Ensure) :-
    findall(Fun/Arity,
            ( sub_term(Sub, Dual),
              nonvar(Sub),
              Sub = metta_dual_goal(Fun, Args),
              atom(Fun),
              is_list(Args),
              length(Args, Arity) ),
            Needed0),
    sort(Needed0, Needed),
    (   Needed == []
    ->  Ensure = true
    ;   Ensure = metta_ensure_duals(Needed)
    ).

%The module is read HERE rather than baked in at translation, so a call
%compiled in one space and run under another asks about the right equations,
%which is the same rule metta_dual_goal/2 follows.
metta_ensure_duals(Needed) :-
    current_metta_module(Module),
    forall(member(Fun/Arity, Needed), ensure_dual(Fun, Arity, Module)).

%Local holds the variables quantify_negations/3 found to occur nowhere but
%inside this negation. It stays unbound when nothing analysed the site, which
%is the same as having none.
%True and Dual are compiled in the space's module and called from here, so
%they carry it in. Local is a variable list and Out a result, neither of them
%a goal.
:- meta_predicate metta_negation(?, ?, 0, 0, ?).
metta_negation(Local, _, True, Dual, Out) :-
    %The world flag rides the whole negation, both the provability probe
    %and the dual: either side consulting an open-world foreign context
    %reads its silence as a truth value, which is the unsound step the
    %closed-world gate refuses. Backtrackable, so nesting and redo
    %restore themselves.
    b_setval('$petta_in_negation', true),
    (   call(True),
        Out0 = false
    ;   ( var(Local) -> Quantified = [] ; Quantified = Local ),
        metta_forall_c(Quantified, Dual),
        Out0 = true
    ),
    b_setval('$petta_in_negation', false),
    Out = Out0.

%A variable that occurs only inside a negated goal is existential there, so it
%is universal under the negation: Art of Prolog's
%    entitlement(X,nothing) :- not pension(X,Y).
%means "no pension at all", not "some Y that is not a pension" (section 11.5,
%page 207). Without this the rule answers `nothing` for a person who has three
%pensions, once per equation of pension [tested: default_rule_answers_relationally].
%
%Which variables those are is a property of the whole clause, not of the
%negated expression, so it cannot be decided where the form is translated. The
%source variables are recorded there and resolved here, against the head and
%against every other goal, including the other negations.
quantify_negations(Head, Body) :-
    strip_negations(Body, Skeleton, Sites, []),
    assign_locals(Sites, [], Head, Skeleton).

assign_locals([], _, _, _).
assign_locals([Site|Sites], Before, Head, Skeleton) :-
    append(Before, Sites, Others),
    assign_local(Site, Head, Skeleton, Others),
    append(Before, [Site], Before1),
    assign_locals(Sites, Before1, Head, Skeleton).

assign_local(metta_negation(Local, _, _, _, _), _, _, _) :- nonvar(Local), !.
assign_local(metta_negation(Local, SourceVars, _, _, _), Head, Skeleton, Others) :-
    term_variables(Head-Skeleton-Others, Elsewhere),
    exclude(occurs_among(Elsewhere), SourceVars, Local).

%The skeleton keeps each negation's output variable, which the rest of the
%clause reads, and drops the compiled goals, whose intermediate variables are
%not the source's and must not count as occurrences.
strip_negations(Term, Term, Sites, Sites) :- ( var(Term) ; atomic(Term) ), !.
strip_negations(Term, '$negation_site'(Out), [Term|Sites], Sites) :-
    Term = metta_negation(_, _, _, _, Out),
    !.
strip_negations(Term, Stripped, Sites0, Sites) :-
    Term =.. [Name|Args],
    strip_negations_list(Args, StrippedArgs, Sites0, Sites),
    Stripped =.. [Name|StrippedArgs].

strip_negations_list([], [], Sites, Sites).
strip_negations_list([Arg|Args], [Stripped|Rest], Sites0, Sites) :-
    strip_negations(Arg, Stripped, Sites0, Sites1),
    strip_negations_list(Args, Rest, Sites1, Sites).

%The dual of one call, with the function's equations read when it runs.
%
%A dual is read COINDUCTIVELY, at the greatest fixpoint rather than the least,
%and that is not a refinement but the difference between an answer and a hang.
%(= (spin) (spin)) has no derivation, so under the well-founded semantics spin
%is false and (not-provable (spin)) is True; read inductively the dual clause
%not-spin :- not-spin just loops, which it did [measured 2026-08-15].
%
%So a call that recurs to a variant of itself is decided by the PARITY of the
%negations crossed on the way, which is s(CASP)'s rule [source:
%prolog/scasp/solve.pl, check_CHS_/6: "coinduction success <- cycles
%containing even loops may succeed" and "coinduction fails <- the goal is
%entailed by its negation in the call stack"]. Even, including none, succeeds;
%odd fails. An odd loop is (= (p) (not-provable (p))), which the well-founded
%semantics leaves undefined and which therefore must not be answered True.
metta_dual_goal(Fun, Args) :-
    must_be(atom, Fun),
    current_metta_module(Module),
    length(Args, InputArity),
    ensure_dual(Fun, InputArity, Module),
    dual_name(Fun, DualName),
    append(Args, [true], CallArgs),
    Goal =.. [DualName|CallArgs],
    dual_stack(Stack),
    (   recurrence_parity(Stack, Fun, Args, Parity)
    ->  Parity =:= 0
    ;   push_dual_frame(Stack, goal(Fun, Args), call(Module:Goal))
    ).

%A negation crossed inside a body being dualised. Only `not` and
%`not-provable` create one: every other edge a dual follows is the dual OF a
%positive goal, which is the same node seen from the other side and not a
%negation of the program.
:- meta_predicate metta_crossed_negation(0), push_dual_frame(?, ?, 0).
metta_crossed_negation(Goal) :-
    dual_stack(Stack),
    push_dual_frame(Stack, negation, Goal).

dual_stack(Stack) :-
    (   nb_current(metta_dual_stack, Current)
    ->  Stack = Current
    ;   Stack = []
    ).

%b_setval/2 unwinds the frame on backtracking, and the restore after the call
%takes it back off on success. Both are undone when the call is redone, which
%leaves the stack right for the retry.
push_dual_frame(Stack, Frame, Goal) :-
    b_setval(metta_dual_stack, [Frame|Stack]),
    call(Goal),
    b_setval(metta_dual_stack, Stack).

%How many negations lie between here and the nearest variant of this call.
%Fails when there is no recurrence at all, which is the ordinary case.
recurrence_parity(Stack, Fun, Args, Parity) :-
    recurrence_parity(Stack, Fun, Args, 0, Parity).

recurrence_parity([goal(Fun, Earlier)|_], Fun, Args, Crossed, Parity) :-
    Earlier =@= Args,
    !,
    Parity is Crossed mod 2.
recurrence_parity([negation|Rest], Fun, Args, Crossed, Parity) :-
    !,
    Next is Crossed + 1,
    recurrence_parity(Rest, Fun, Args, Next, Parity).
recurrence_parity([_|Rest], Fun, Args, Crossed, Parity) :-
    recurrence_parity(Rest, Fun, Args, Crossed, Parity).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%% Building a dual %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

:- dynamic dual_ready/3.
:- dynamic dual_building/3.
%Which generated names are ours. Survives invalidation, because a rebuild
%reuses the name, and is erased with the source load that created it.
:- dynamic dual_generated/3.

dual_name(Fun, DualName) :- atom_concat('not-', Fun, DualName).

%Built on first use rather than for every function, because most MeTTa
%functions are not predicates and a dual for each would be waste. A recursive
%reference finds the in-progress marker and emits the call anyway: the clause
%exists by the time it runs.
%Building is a side effect and happens exactly once, which once/1 states
%rather than leaves to whether every predicate underneath happens to be
%deterministic. It was not: build_dual/3 was REDONE on backtracking and
%asserted a second, identical clause, so every call to the dual then answered
%twice [traced 2026-08-15 with trace/2 on build_dual/3, +redo].
%once/1 closed the door a REDO opens; this closes the one a second THREAD
%opens, and they are the same bug twice. The test above is check-then-act, so
%two threads arriving together both saw neither marker and both built: 32
%calls through m.pool(workers=8) left five clauses of not-p/2, five
%dual_ready facts, four dual_hooks_installed and seven
%metta_on_function_changed handlers, and (not-provable (p 0)) answered True
%five times [measured 2026-08-17]. The count varied per run, which is what
%says race rather than off-by-one.
%
%The duplicated hook handlers were the worse half: metta_on_function_changed/1
%is an EVENT hook, so every duplicate ran on every compiled equation, and the
%leak grew by one per racing build with nothing to bound it.
%
%Double-checked, and the fast path is why: a dual is built once and consulted
%on every later call, so paying a mutex on the hit would tax the common case
%to fix the first one. The re-check inside is what makes the fast path sound.
%This is specializer.pl's own answer to the same shape, which is why the mutex
%is named the same way [tested: test_a_dual_is_built_once_under_concurrency].
ensure_dual(Fun, InputArity, Module) :-
    (   dual_ready(Fun, InputArity, Module)
    ->  true
    ;   with_mutex('$petta_duals',
                   ensure_dual_locked(Fun, InputArity, Module))
    ).

ensure_dual_locked(Fun, InputArity, Module) :-
    (   dual_ready(Fun, InputArity, Module) -> true
    ;   dual_building(Fun, InputArity, Module) -> true
    ;   once(build_dual(Fun, InputArity, Module))
    ).

build_dual(Fun, InputArity, Module) :-
    dual_name(Fun, DualName),
    refuse_unsupported_head(Module, Fun),
    refuse_taken_name(Fun, DualName, Module),
    install_dual_hooks,
    assertz(dual_building(Fun, InputArity, Module), BuildRef),
    setup_call_cleanup(
        true,
        build_dual_clause(Fun, DualName, InputArity, Module),
        erase(BuildRef)),
    assertz(dual_ready(Fun, InputArity, Module), ReadyRef),
    record_source_assertion(ReadyRef).

build_dual_clause(Fun, DualName, InputArity, Module) :-
    equations_of_arity(Module, Fun, InputArity, Equations),
    length(DualArgs, InputArity),
    (   Equations == []
    ->  refuse_undefined_builtin(Fun, InputArity, Module),
        Body = true
    ;   maplist(equation_dual(DualArgs, Module), Equations, Disjunctions),
        goals_to_conj(Disjunctions, Body)
    ),
    append(DualArgs, [true], HeadArgs),
    Head =.. [DualName|HeadArgs],
    Clause = (Head :- Body),
    register_fun_in(Module, DualName),
    Arity is InputArity + 1,
    register_arity(DualName, Arity),
    assert_function_clause(Module, Clause, Ref),
    record_source_assertion(Ref),
    format(atom(Label), "metta dual (~w)", [Fun]),
    maybe_print_compiled_clause(Label, ['not-provable', [Fun|DualArgs]], Clause).

equations_of_arity(Module, Fun, InputArity, Equations) :-
    (   fun_meta_clauses(Module, Fun, All)
    ->  include(equation_arity(InputArity), All, Equations)
    ;   Equations = []
    ).

equation_arity(InputArity, fun_meta(Args, _)) :- length(Args, InputArity).

%A name with no equations is either an undefined symbol, whose dual is a fact
%because nothing can prove it, or a builtin or special form, whose behaviour
%lives in Prolog where there is nothing to dual. Guessing that a builtin's
%dual is a fact would make (not-provable (+ 1 2)) answer True for every pair.
refuse_undefined_builtin(Fun, InputArity, Module) :-
    (   \+ fun_here_in(Module, Fun), \+ fun(Fun), \+ metta_special_form(Fun)
    ->  true
    ;   Arity is InputArity + 1,
        throw(error(type_error(dualisable_function, Fun/Arity),
                    context(build_dual/3,
                            'this is a builtin or a special form, so it has no \c
                             MeTTa equations to negate; the comparisons, ==, != \c
                             and the boolean connectives are the ones that do \c
                             have a dual')))
    ).

%constrain_args/3 turns an in-place type annotation in a head argument into a
%goal: (= (f (: $x Number)) $x) compiles to f(A, A) :- has_type(A, 'Number').
%That goal is not part of the recorded body, so a dual built from the recorded
%head would silently ignore the constraint and claim more than it can prove.
refuse_unsupported_head(Module, Fun) :-
    (   fun_head_goals(Module, Fun)
    ->  throw(error(type_error(dualisable_function, Fun),
                    context(build_dual/3,
                            'this function constrains an argument in its head \c
                             with an in-place annotation, and that constraint \c
                             has no dual')))
    ;   true
    ).

%A dual is rebuilt whenever the equations change, so the name being taken by
%an earlier build of the SAME dual is the ordinary case and only a name this
%file did not create is a collision.
refuse_taken_name(Fun, DualName, Module) :-
    (   dual_generated(DualName, Module, Fun)
    ->  true
    ;   ( fun_in(Module, DualName) ; fun(DualName) )
    ->  throw(error(permission_error(define, dual_function, DualName),
                    context(build_dual/3,
                            'the dual would overwrite a function of this name')))
    ;   assertz(dual_generated(DualName, Module, Fun), Ref),
        record_source_assertion(Ref)
    ).

%%%%%%%%%%%%%%%%%%%%%%%%%%% One equation's dual %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%An equation proves the predicate when the call unifies with its head AND its
%body reduces to True. The negation of a conjunction is the disjunction of
%"the first i-1 conditions hold and the i-th does not", which keeps the
%disjuncts mutually exclusive so the dual does not answer twice, and keeps the
%earlier conditions' bindings in place for the later ones.
equation_dual(DualArgs, Module, fun_meta(HeadArgs, Body), Disjunction) :-
    copy_term(HeadArgs-Body, Args-Expr),
    head_equations(DualArgs, Args, Equations),
    equation_disjuncts(Equations, [], HeadDisjuncts),
    equation_positives(Equations, Positive),
    equation_local_variables(DualArgs, Equations, Expr, Local),
    body_nottrue(Expr, Module, Local, BodyDual),
    body_variables(Local, Expr, BodyVars),
    quantify(BodyVars, BodyDual, QuantifiedDual),
    append(HeadDisjuncts, [(Positive, QuantifiedDual)], Disjuncts),
    goals_to_disj(Disjuncts, Disjunction).

%Every variable the body introduces on its own, which is everything the call's
%arguments and the head pattern do not already determine. This is what a
%generator inside the body needs: a variable in it that is NOT local is one
%the rest of the clause reads, so what the generator narrows it to belongs in
%the answer rather than being quantified away.
equation_local_variables(DualArgs, Equations, Expr, Local) :-
    term_variables(DualArgs-Equations, Determined),
    term_variables(Expr, All),
    exclude(occurs_among(Determined), All, Local).

%The subset of those that still need quantifying over the whole Herbrand
%universe. A variable a let or a match BINDS is quantified by that form's own
%generator instead, over the values the generator actually produces.
body_variables(Local, Expr, BodyVars) :-
    generator_bound_variables(Expr, GeneratorBound),
    exclude(occurs_among(GeneratorBound), Local, BodyVars).

%A variable a let binds is bound where it stands, not free in the equation,
%and the let's own dual already quantifies it over the generator that gives it
%values. Quantifying it a second time over the whole Herbrand universe is not
%merely redundant: forall_cover/2 commits to its first covering solution, so
%the second quantifier threw away the answers the first had found. It cost the
%constructive answer to (not-provable (passes $w)), which is bob, and left
%nothing [measured 2026-08-15].
generator_bound_variables(Expr, Variables) :-
    let_bound_variables(Expr, Variables, []).

let_bound_variables(Expr, Vars, Vars) :- ( var(Expr) ; atomic(Expr) ), !.
let_bound_variables([Form, Pattern, _, Body], Vars, Tail) :-
    ( Form == let ; Form == chain ),
    !,
    term_variables(Pattern, PatternVars),
    append(PatternVars, Rest, Vars),
    let_bound_variables(Body, Rest, Tail).
%arrived_pairs/1 rather than is_list/1, because letstar_to_rec_let/3 reads
%each pair as syntax: a pair that is still a variable would be unified with
%the rewrite's own [Pattern, Value] and change the body being walked. Where
%the bindings have not arrived the walk falls through to the generic list
%clause below, which finds the same variables without rewriting anything.
let_bound_variables(['let*', Bindings, Body], Vars, Tail) :-
    arrived_pairs(Bindings),
    !,
    letstar_to_rec_let(Bindings, Body, RecursiveLet),
    let_bound_variables(RecursiveLet, Vars, Tail).
let_bound_variables([Head|Rest], Vars, Tail) :-
    !,
    let_bound_variables(Head, Vars, Middle),
    let_bound_variables(Rest, Middle, Tail).
let_bound_variables(_, Vars, Vars).

occurs_among(Vars, Var) :- memberchk_eq(Var, Vars).

quantify([], Goal, Goal) :- !.
quantify(Vars, Goal, metta_forall_c(Vars, Goal)).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%% Head patterns %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%A head pattern becomes a list of conditions on the dual's own arguments, each
%of which has an exact negation. The pattern's variables are existential: a
%first occurrence matches anything, so it is bound to the dual argument here
%and contributes no condition, which is also how the body comes to refer to
%the dual's arguments. A repeat occurrence is a real condition, and its
%negation is a disequality rather than a failed match, which is the whole
%point [source: prolog/scasp/comp_duals.pl, prep_args/7].
head_equations(DualArgs, HeadArgs, Equations) :-
    head_equations_(DualArgs, HeadArgs, [], _, Equations, []).

head_equations_([], [], Seen, Seen, Tail, Tail).
head_equations_([X|Xs], [P|Ps], Seen0, Seen, Equations, Tail) :-
    pattern_equations(X, P, Seen0, Seen1, Equations, Rest),
    head_equations_(Xs, Ps, Seen1, Seen, Rest, Tail).

pattern_equations(X, P, Seen0, Seen, Equations, Tail) :-
    var(P),
    !,
    (   seen_variable(Seen0, P, First)
    ->  Seen = Seen0,
        Equations = [equal_to(X, First)|Tail]
    ;   P = X,
        Seen = [X|Seen0],
        Equations = Tail
    ).
pattern_equations(X, P, Seen, Seen, [ground_value(X, P)|Tail], Tail) :-
    ground(P),
    !.
pattern_equations(X, P, Seen0, Seen, [structure(X, Shape, Name, Arity)|Eqs], Tail) :-
    compound(P),
    P =.. [Name|SubPatterns],
    length(SubPatterns, Arity),
    length(SubArgs, Arity),
    Shape =.. [Name|SubArgs],
    head_equations_(SubArgs, SubPatterns, Seen0, Seen, Eqs, Tail).

seen_variable([Var|_], P, Var) :- Var == P, !.
seen_variable([_|Vars], P, Var) :- seen_variable(Vars, P, Var).

equation_positives(Equations, Conj) :-
    maplist(equation_positive, Equations, Goals),
    exclude(==(true), Goals, Real),
    goals_to_conj(Real, Conj).

equation_positive(equal_to(X, Y), X = Y).
equation_positive(ground_value(X, Value), X = Value).
equation_positive(structure(X, Shape, _, _), X = Shape).

%One disjunct per condition, each keeping every earlier condition positive.
equation_disjuncts([], _, []).
equation_disjuncts([Equation|Equations], Prefix, Disjuncts) :-
    equation_positive(Equation, Positive),
    append(Prefix, [Positive], Prefix1),
    equation_disjuncts(Equations, Prefix1, Rest),
    (   equation_negative(Equation, Negative)
    ->  exclude(==(true), Prefix, RealPrefix),
        append(RealPrefix, [Negative], DisjunctGoals),
        goals_to_conj(DisjunctGoals, Disjunct),
        Disjuncts = [Disjunct|Rest]
    ;   Disjuncts = Rest
    ).

equation_negative(equal_to(X, Y), dif(X, Y)).
equation_negative(ground_value(X, Value), dif(X, Value)).
equation_negative(structure(X, _, Name, Arity), metta_not_functor(X, Name, Arity)).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% Bodies %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%A goal that succeeds when the body does NOT reduce to True. and, or and not
%are total on booleans because boolean_argument/2 raises on anything else
%[source: src/metta.pl:288], so their duals are the plain De Morgan ones with
%no undefined case left over.
body_nottrue(Body, _, _, fail) :- Body == true, !.
body_nottrue(Body, _, _, true) :- Body == false, !.
body_nottrue(Body, Module, Local, Goal) :-
    nonvar(Body),
    Body = [Head|Args],
    atom(Head),
    body_form_dual(Head, Args, Module, Local, Goal),
    !.
body_nottrue(Body, _, _, _) :-
    throw(error(type_error(dualisable_body, Body),
                context(body_nottrue/4,
                        'no dual for this form; a dualisable body is built from \c
                         True, False, and, or, not, if, the comparisons, ==, != \c
                         and calls to MeTTa functions'))).

body_form_dual(and, [P, Q], Module, Local, (DualP ; TrueP, DualQ)) :-
    body_nottrue(P, Module, Local, DualP),
    body_true(P, TrueP),
    body_nottrue(Q, Module, Local, DualQ).
body_form_dual(or, [P, Q], Module, Local, (DualP, DualQ)) :-
    body_nottrue(P, Module, Local, DualP),
    body_nottrue(Q, Module, Local, DualQ).
%and-then and or-else are the SHORT-CIRCUITING connectives, and they dual
%exactly as and and or do. That is not an approximation: and-then answers
%False without running its second argument when the first is not True, and
%False is not True, which is the disjunct the dual of and already has
%[source: src/translator.pl, translate_special_dl('and-then', ...)]. Where
%they differ from and and or is in what they RUN, and a dual that keeps every
%preceding goal positive runs the same things.
body_form_dual('and-then', [P, Q], Module, Local, Goal) :-
    body_form_dual(and, [P, Q], Module, Local, Goal).
body_form_dual('or-else', [P, Q], Module, Local, Goal) :-
    body_form_dual(or, [P, Q], Module, Local, Goal).
%quote constructs a value headed by quote. That value is never the literal
%True atom, independently of its unevaluated payload.
body_form_dual(quote, [_], _, _Local, true).
%(not P) is True exactly when P is False, so it is not True exactly when P is
%True. No third case survives, because a non-boolean P raises before it gets
%here.
body_form_dual(not, [P], _, _Local, metta_crossed_negation(TrueP)) :-
    body_true(P, TrueP).
%A negation inside a body being negated is double negation, and it eliminates.
%(not-provable E) answers True or False and nothing else, so it is not True
%exactly when it is False, which is exactly when E is provable. It needs no
%dual of its own, which is as well: it has no equations, so asking for one
%raised [measured 2026-08-15].
body_form_dual('not-provable', [Expr], _, _Local, metta_crossed_negation(TrueExpr)) :-
    body_true(Expr, TrueExpr).
%if takes its else branch whenever the condition is anything but True
%[source: src/translator.pl, translate_special_dl(if, [Cond, Then, Else], ...)],
%so the two disjuncts below are exhaustive rather than a sound approximation.
body_form_dual(if, [C, T, E], Module, Local, ((TrueC, DualT) ; (DualC, DualE))) :-
    body_true(C, TrueC),
    body_nottrue(C, Module, Local, DualC),
    body_nottrue(T, Module, Local, DualT),
    body_nottrue(E, Module, Local, DualE).
body_form_dual(if, [C, T], Module, Local, ((TrueC, DualT) ; DualC)) :-
    body_true(C, TrueC),
    body_nottrue(C, Module, Local, DualC),
    body_nottrue(T, Module, Local, DualT).
%(let P V B) is True when SOME answer of V matches P and makes B True, so it
%is not True when EVERY answer that matches makes B not True. That is a
%universal quantification over a GENERATOR rather than over the Herbrand
%universe, which is a different and much cheaper thing than metta_forall_c/2:
%the values are enumerable, so they can simply all be checked.
%
%foreach/2 is exactly that quantification and it is a builtin. Unlike
%forall/2, which is \+ (Cond, \+ Action) and therefore cannot bind, foreach/2
%"undoes only the instantiation of the template and not other instantiations
%created by running Goal" [source: SWI-Prolog 10.1 Reference Manual, section
%A.1], so a constraint the dual posts on a variable of the enclosing clause
%survives. Its own documented example is that behaviour:
%    ?- foreach(between(1,4,X), dif(X,Y)), Y = 5.   succeeds
%    ?- foreach(between(1,4,X), dif(X,Y)), Y = 3.   fails
%An empty generator is vacuously true, which is right: a let whose value has
%no answer has no answer either, so it is not True [verified 2026-08-15].
%
%The quantification is only DETERMINED when the generator is. foreach/2 runs
%its generator under findall/3, so a binding the generator makes to a variable
%that is not shared with the goal is discarded, and the set being quantified
%over is then the union across every value that variable could take rather
%than the set for the one it will take. (not-provable (passes $w)) with $w
%unbound would ask for the dual to hold at BOTH grades at once and answer
%nothing, where $w=bob is a real answer [measured 2026-08-15: it answered ()].
%
%So the value's own free variables are required to be ground, and it says so
%rather than answering incompletely. This is the classic restriction, that
%"it is the responsibility of the programmer to ensure that negated goals are
%ground before they are solved" [The Art of Prolog, 2nd ed, page 199], and it
%applies HERE and not to the rest of this file: a head pattern is negated with
%dif/2 and needs no groundness at all. The complete version needs a second
%dual per function, for "has no answer" rather than "has no True answer", so
%that the generator itself can be negated; that is F14.5b in the ledger.
body_form_dual(let, [Pattern, Value, Body], Module, Local, Goal) :-
    let_generator(Pattern, Value, Generator),
    term_variables(Value, GeneratorVariables),
    body_nottrue(Body, Module, Local, DualBody),
    (   GeneratorVariables == []
    ->  Goal = foreach(Generator, DualBody)
    ;   Goal = metta_generator_forall(GeneratorVariables, Local, Generator,
                                      DualBody, Value)
    ).
%A match over a space is a generator too, and a better behaved one than a let:
%a space is finite, so what it narrows a variable to is always an enumeration
%and never a constraint. (= (has-child $x) (match &self (parent $x $y) True))
%is True when SOME atom matches, so it is not True when every matching atom
%fails, and "which x has no child" is answered by narrowing $x over the atoms
%and taking the complement.
%
%$y here is local to the match and $x is not, which is the whole difference:
%$y is quantified away and $x is answered. Local carries that distinction down
%from the clause, because neither is visible from the match alone.
body_form_dual(match, [SpaceExpr, Pattern, Body], Module, Local, Goal) :-
    translate_expr(SpaceExpr, SpaceGoals, Space),
    goals_to_conj([SpaceGoals, match(Space, Pattern, Enumerated, Enumerated)],
                  Generator),
    body_nottrue(Body, Module, Local, DualBody),
    term_variables(SpaceExpr-Pattern, GeneratorVariables),
    (   GeneratorVariables == []
    ->  Goal = foreach(Generator, DualBody)
    ;   Goal = metta_generator_forall(GeneratorVariables, Local, Generator,
                                      DualBody, [match, SpaceExpr, Pattern])
    ).
body_form_dual(chain, [Pattern, Value, Body], Module, Local, Goal) :-
    body_form_dual(let, [Pattern, Value, Body], Module, Local, Goal).
%let* is nested lets and the translator already says so, so the dual is the
%dual of what it expands to rather than a second implementation of it.
%
%Only where the bindings have arrived. A dual is built ONCE, at compile time,
%out of the recorded MeTTa body, so bindings that arrive at run time are not
%there to expand: unguarded, letstar_to_rec_let/3 unified them with its own
%empty-list base clause and the dual came out with the bindings DROPPED, so
%`(= (f $bs) (let* $bs (> 1 0)))` gave `(not-provable (f ...))` no answer
%where the same bindings written out answered True. Refusing says which of
%the two it was, where falling through to the generic refusal would have
%said only that let* is a special form
%[tested: a_let_star_whose_bindings_have_not_arrived_has_no_dual]. It is the
%same limit case has, for the same reason.
body_form_dual('let*', [Bindings, Body], Module, Local, Goal) :-
    (   arrived_pairs(Bindings)
    ->  letstar_to_rec_let(Bindings, Body, RecursiveLet),
        body_nottrue(RecursiveLet, Module, Local, Goal)
    ;   throw(error(type_error(dualisable_body, ['let*', Bindings, Body]),
                    context(body_form_dual/5,
                            'a dual is built once, out of the equation as it \c
                             was written, so let* bindings that only arrive \c
                             when the program runs have none to expand; \c
                             writing the bindings out gives the form a dual')))
    ).
%A case commits to the FIRST pattern its key matches, which the translator
%writes as a chain of ((Key = Pattern) -> Body ; Next) ending in fail [source:
%src/translator.pl, translate_case/5]. So its dual is the same chain with each
%body replaced by that body's dual, and the final fail replaced by TRUE: a key
%that matches no pattern gives the case no answer at all, and no answer is not
%True.
%
%The key is a generator like a let's value, so the whole chain is quantified
%over the key's answers.
body_form_dual(case, [KeyExpr, Pairs], Module, Local, Goal) :-
    (   is_list(Pairs)
    ->  case_default(Pairs, Cases, Default),
        translate_expr(KeyExpr, KeyGoals, KeyValue),
        goals_to_conj(KeyGoals, Generator),
        case_dual_chain(Cases, KeyValue, Module, Local, Chain),
        term_variables(KeyExpr, GeneratorVariables),
        (   GeneratorVariables == []
        ->  Quantified = foreach(Generator, Chain)
        ;   Quantified = metta_generator_forall(GeneratorVariables, Local,
                                                Generator, Chain, KeyExpr)
        ),
        (   Default == none
        ->  Goal = Quantified
        ;   %An Empty branch answers when the KEY has no answer, and
            %foreach/2 over an empty generator succeeds vacuously, so the
            %two cases have to be told apart before quantifying. This costs
            %one extra evaluation of the key, which is the price of asking
            %whether it answers at all.
            body_nottrue(Default, Module, Local, DualDefault),
            Goal = ( \+ Generator -> DualDefault ; Quantified )
        )
    ;   %Cases that only arrive at run time refuse the way let*'s bindings
        %do, naming the actual reason; falling through said only that case
        %is a special form [tested:
        %a_case_whose_cases_have_not_arrived_has_no_dual].
        throw(error(type_error(dualisable_body, [case, KeyExpr, Pairs]),
                    context(body_form_dual/5,
                            'a dual is built once, out of the equation as it \c
                             was written, so case branches that only arrive \c
                             when the program runs have none to negate; \c
                             writing the cases out gives the form a dual')))
    ).

%A collapse yields a LIST, always, so it is never the atom True and its dual
%is unconditionally true. Confirmed rather than assumed: with (= (f) True)
%declared, (collapse (f)) answers (True), a one-element list; (== (collapse
%(f)) True) answers False; and its metatype is Expression [measured
%2026-08-16]. It compiles to findall/3, whose third argument is a list by
%construction [source: src/translator.pl, translate_special_dl(collapse, ...)].
%
%Nothing is lost by not running it. A collapse in a boolean position is a type
%error in the POSITIVE direction, because boolean_argument/2 raises on a list,
%and metta_negation/5 runs that direction first, so the error still surfaces.
%Where a collapse's VALUE is what matters it is an argument to something else,
%(== (collapse (f $x)) ()) being the usual shape, and that path evaluates it
%through the ordinary translator and never reaches here.
body_form_dual(collapse, [_], _, _Local, true).
%A superpose answers each of its elements in turn, so it is not True exactly
%when none of them is: the conjunction of the elements' duals. The elements
%are known here, so unlike let and match this generator needs no enumeration.
%An empty superpose has no answers at all, and the empty conjunction is true,
%which is the same thing said twice.
body_form_dual(superpose, [Elements], Module, Local, Goal) :-
    is_list(Elements),
    maplist(element_dual(Module, Local), Elements, Duals),
    goals_to_conj(Duals, Goal).
%A comparison is total and its opposite is another comparison, which is
%s(CASP)'s dual_goal/2 table for the same reason.
body_form_dual(Comparison, [A, B], _, _Local, Goal) :-
    comparison_dual(Comparison, Opposite),
    body_true([Opposite, A, B], Goal).
%== answers True when its arguments are identical, so it is not True when they
%differ, and dif/2 states that as a constraint instead of testing it. This is
%what makes `not (X=1), X=2` answer X=2 rather than failing, which The Art of
%Prolog gives as negation as failure's second defect (page 199).
body_form_dual('==', [A, B], _, _Local, (Goals, dif(ValueA, ValueB))) :-
    argument_values([A, B], Goals, [ValueA, ValueB]).
body_form_dual('!=', [A, B], _, _Local, (Goals, ValueA = ValueB)) :-
    argument_values([A, B], Goals, [ValueA, ValueB]).
%Anything else naming a function goes through the dual, resolved when the call
%runs rather than when it compiles. A rule may be written before the equations
%it negates, and two functions may negate each other, so the set of equations a
%dual summarises is not settled at compile time.
body_form_dual(Fun, Args, _, _Local, Goal) :-
    dual_argument_values(Fun, Args, ArgGoals, Values),
    goals_to_conj([ArgGoals, metta_dual_goal(Fun, Values)], Goal).

%The dual passes each argument exactly as the positive call would. A
%position the declared chain types Atom takes the WRITTEN term, the same
%mask translate_args_by_type honours, read off the same machinery the
%positive call compiles from (call_site_type_chains, fitting_type_chains,
%drop_unconstraining_types), so the two paths cannot drift: with
%(: hh (-> Atom Bool)) and (= (hh 10) True), the positive path tries hh at
%the written (dbl 5) and fails, and the dual used to EVALUATE the argument
%to 10, where hh holds, so (not-provable (hh (dbl 5))) answered nothing
%instead of True. With no declaration, or none fitting the arity, every
%argument evaluates as before. Overloaded chains that disagree about a
%position mask it only when ALL of them mask it: the positive path branches
%per chain, the dual asks one metta_dual_goal, and evaluating in the
%ambiguous case only narrows which negations are FOUND, never invents one
%[tested: test_not_provable_honours_the_atom_mask_its_positive_path_honours].
dual_argument_values(Fun, Args, Conj, Values) :-
    length(Args, InputArity),
    dual_atom_mask(Fun, InputArity, Mask),
    maplist(dual_argument_value, Mask, Args, GoalLists, Values),
    append(GoalLists, Goals),
    goals_to_conj(Goals, Conj).

dual_argument_value(atom, Arg, [], Arg) :- !.
dual_argument_value(value, Arg, Goals, Value) :- translate_expr(Arg, Goals, Value).

dual_atom_mask(Fun, InputArity, Mask) :-
    (   atom(Fun),
        call_site_type_chains(Fun, Chains),
        Chains \== [],
        fitting_type_chains(Chains, InputArity, Fitting),
        findall(Kinds, ( member(Chain, Fitting),
                         chain_argument_kinds(Chain, InputArity, Kinds) ),
                KindLists),
        KindLists \== []
    ->  foldl(merge_argument_kinds, KindLists, none, Mask)
    ;   length(Mask, InputArity),
        maplist(=(value), Mask)
    ).

chain_argument_kinds(TypeChain, InputArity, Kinds) :-
    TypeChain = [->|Xs],
    append(ArgTypes0, [_], Xs),
    length(ArgTypes0, InputArity),
    drop_unconstraining_types(TypeChain, ArgTypes0, ArgTypes),
    maplist([T, K]>>( T == 'Atom' -> K = atom ; K = value ), ArgTypes, Kinds).

merge_argument_kinds(Kinds, none, Kinds) :- !.
merge_argument_kinds(Kinds, Acc, Merged) :-
    maplist([A, B, M]>>( A == atom, B == atom -> M = atom ; M = value ),
            Kinds, Acc, Merged).

comparison_dual('<', '>=').
comparison_dual('>', '<=').
comparison_dual('<=', '>').
comparison_dual('>=', '<').
%The CLP(FD) family duals the same way, and there it is not a test but a
%constraint: the dual of (#< $x 5) POSTS $x #>= 5 rather than deciding it, so
%a negated arithmetic bound narrows the domain instead of enumerating it. This
%is s(CASP)'s own dual/2 table, which exists for the same reason [source:
%prolog/scasp/solve.pl and prolog/scasp/comp_duals.pl, dual_goal/2].
comparison_dual('#<', '#>=').
comparison_dual('#>', '#=<').
comparison_dual('#=<', '#>').
comparison_dual('#>=', '#<').
comparison_dual('#=', '#\\=').
comparison_dual('#\\=', '#=').

case_default(Pairs, Cases, Default) :-
    (   select(Found, Pairs, Rest),
        nonvar(Found),
        Found = ['Empty', DefaultExpr]
    ->  Cases = Rest,
        Default = DefaultExpr
    ;   Cases = Pairs,
        Default = none
    ).

%Ending in true rather than fail is the whole point: a key matching nothing
%leaves the case with no answer, and no answer is not True.
case_dual_chain([], _, _, _, true).
case_dual_chain([Pair|Rest], KeyValue, Module, Local, Chain) :-
    nonvar(Pair),
    Pair = [Pattern, Body],
    constrain_args(Pattern, Constrained, PatternGoals),
    PatternGoals == [],
    body_nottrue(Body, Module, Local, DualBody),
    case_dual_chain(Rest, KeyValue, Module, Local, Next),
    Chain = ( KeyValue = Constrained -> DualBody ; Next ).

element_dual(Module, Local, Element, Dual) :-
    body_nottrue(Element, Module, Local, Dual).

%A body that DOES reduce to True is just the body compiled the ordinary way,
%so the dual reuses the whole translator rather than a second evaluator.
body_true(Expr, Goal) :-
    translate_expr(Expr, Goals, Value),
    append(Goals, [Value == true], All),
    goals_to_conj(All, Goal).

%foreach/2 alone is not enough when the generator narrows a variable of the
%enclosing clause. It runs its generator under findall/3, so such a binding is
%discarded and the quantification becomes "the dual holds at every value the
%generator produces for ANY of them at once", which is a different and much
%stronger claim: (not-provable (passes $w)) asked for the dual at both alice's
%grade and bob's at the same time and answered nothing, where $w=bob is a real
%answer [measured 2026-08-15].
%
%What the generator narrows a variable TO belongs in the answer rather than
%being quantified away. That is what MeTTa's own collapse-bind says an answer
%is, one (value, bindings) pair per alternative [source:
%lib/minimal_metta_lib.pl, and LeaTTa's ReduceResult.okBind], and it is the
%constrained-answer framework this file already works in. So: collect the
%narrowings, answer once per DISTINCT one with the dual quantified over just
%that narrowing's values, and once more for the terms the generator narrows to
%nothing, which is where the let has no answer and so is not True.
%
%A narrowing this cannot read is one the generator expressed as a constraint
%rather than as an enumeration, because findall/3 copies out of the constraint
%store. That raises rather than answering incompletely.
%Already determined: there is no narrowing to collect, so this is the plain
%bounded quantification and, just as important, it leaves no choice point.
%foreach/2 "undoes only the instantiation of the template", so a nested
%nondeterministic goal gets RE-ENTERED with that template unbound, and a
%nested let then answered a second time from its own complement branch:
%(not-provable (both bob)) had four answers where it has one [traced
%2026-08-15 with trace/2 on the generator quantifier, +exit].
%The generator and the dual body are both compiled in the space's module and
%reached from here through foreach/2 and findall/3, so both carry it in.
:- meta_predicate metta_generator_forall(?, ?, 0, 0, ?),
                  metta_narrowed_forall(?, 0, 0, ?).
metta_generator_forall(GeneratorVariables, Local, Generator, DualBody, Value) :-
    generator_outer_variables(GeneratorVariables, Local, OuterVariables),
    (   OuterVariables == []
    ->  foreach(Generator, DualBody)
    ;   ground(OuterVariables)
    ->  foreach(Generator, DualBody)
    ;   metta_narrowed_forall(OuterVariables, Generator, DualBody, Value)
    ).

%The generator's variables that the rest of the clause can also see. The ones
%it cannot are bound by this generator and nothing else, so quantifying them
%away is right; the ones it can are part of the answer. Local unbound means
%nothing analysed the site, and treating every variable as visible is the
%conservative reading.
generator_outer_variables(GeneratorVariables, Local, Outer) :-
    (   var(Local)
    ->  Outer = GeneratorVariables
    ;   exclude(occurs_among(Local), GeneratorVariables, Outer)
    ).

metta_narrowed_forall(OuterVariables, Generator, DualBody, Value) :-
    findall(OuterVariables, Generator, Narrowings),
    (   Narrowings == []
    ->  true
    ;   \+ ground(Narrowings)
    ->  throw(error(instantiation_error,
                    context(metta_generator_forall/5,
                            negated_let_value(Value))))
    ;   sort(Narrowings, Distinct),
        (   member(OuterVariables, Distinct),
            foreach(Generator, DualBody)
        ;   differs_from_every(Distinct, OuterVariables)
        )
    ).

differs_from_every([], _).
differs_from_every([Narrowing|Rest], Variables) :-
    dif(Variables, Narrowing),
    differs_from_every(Rest, Variables).

%The same goals translate_let_dl/4 emits, in the same order and with the same
%occurs check, so the generator enumerates exactly the bindings the let itself
%would make [source: src/translator.pl, translate_let_dl/4].
let_generator(Pattern, Value, Generator) :-
    translate_expr(Pattern, PatternGoals, PatternValue),
    translate_expr(Value, ValueGoals, ValueResult),
    goals_to_conj([PatternGoals, ValueGoals,
                   unify_with_occurs_check(PatternValue, ValueResult)],
                  Generator).

argument_values(Args, Conj, Values) :-
    maplist(argument_value, Args, GoalLists, Values),
    append(GoalLists, Goals),
    goals_to_conj(Goals, Conj).

argument_value(Arg, Goals, Value) :- translate_expr(Arg, Goals, Value).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% Assembly %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%A conjunction holding fail is fail, which is not a peephole nicety: the dual
%of a body that is literally True is fail, and without this every fact would
%generate a dead disjunct next to its real one.
goals_to_conj(Goals, Conj) :-
    flatten_goals(Goals, Flat),
    exclude(==(true), Flat, Real),
    (   member(Goal, Real), Goal == fail -> Conj = fail
    ;   Real == []   -> Conj = true
    ;   Real = [One] -> Conj = One
    ;   Real = [G|Gs], goals_to_conj_(Gs, G, Conj)
    ).

goals_to_conj_([], Conj, Conj).
goals_to_conj_([G|Gs], Acc, Conj) :- goals_to_conj_(Gs, (Acc, G), Conj).

goals_to_disj(Goals, Disj) :-
    exclude(==(fail), Goals, Real),
    (   Real == []   -> Disj = fail
    ;   Real = [One] -> Disj = One
    ;   Real = [G|Gs], goals_to_disj_(Gs, G, Disj)
    ).

goals_to_disj_([], Disj, Disj).
goals_to_disj_([G|Gs], Acc, Disj) :- goals_to_disj_(Gs, (Acc ; G), Disj).

flatten_goals([], []).
flatten_goals([G|Gs], Out) :-
    (   is_list(G)
    ->  flatten_goals(G, Head)
    ;   Head = [G]
    ),
    flatten_goals(Gs, Tail),
    append(Head, Tail, Out).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% Invalidation %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%A dual is a compiled summary of a function's equations, so it is stale the
%moment they change. This is the hook the memo tables already use, for the
%same reason [source: lib/lib_memo.pl, metta_on_function_changed/1].
%
%Installed on the first dual rather than on load. The hook runs once per
%compiled equation, so a resident handler is a tax on every program that
%compiles anything, and most programs never negate: measured 2026-08-15, the
%clause cost 4001 inferences over source-load's thousand equations and nothing
%else changed. Installed this way a program that uses no negation pays zero
%and one that does pays on its first dual [tested: duals_invalidation].
:- dynamic dual_hooks_installed/0.

%The same check-then-act, and it needs the lock in its own right rather than
%only through ensure_dual/3's: SWI's mutexes are recursive, so nesting costs
%nothing, and a second caller would otherwise install a second pair of
%handlers into two EVENT hooks.
install_dual_hooks :-
    (   dual_hooks_installed
    ->  true
    ;   with_mutex('$petta_duals', install_dual_hooks_locked)
    ).

install_dual_hooks_locked :-
    (   dual_hooks_installed
    ->  true
    ;   assertz((metta_on_function_changed(Fun) :- drop_duals_of(Fun))),
        assertz((metta_on_function_removed(Fun) :- drop_duals_of(Fun))),
        %Last, so a thread reading the marker without the lock cannot see it
        %set before the handlers it promises are there.
        assertz(dual_hooks_installed)
    ).

%Under the same lock as the build, because it retracts what the build
%publishes: a drop racing a build could erase half of one.
drop_duals_of(Fun) :-
    (   dual_ready(Fun, _, _)
    ->  with_mutex('$petta_duals', drop_duals_of_locked(Fun))
    ;   true
    ).

drop_duals_of_locked(Fun) :-
    (   dual_ready(Fun, _, _)
    ->  dual_name(Fun, DualName),
        forall(retract(dual_ready(Fun, InputArity, Module)),
               ( Arity is InputArity + 1,
                 functor(Head, DualName, Arity),
                 ( current_predicate(Module:DualName/Arity)
                   -> retractall(Module:Head)
                   ;  true ) ))
    ;   true
    ).
