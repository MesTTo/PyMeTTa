% Purpose: reason about term rewriting systems: rewrite one step, reduce to a
%   normal form, enumerate critical overlaps, order terms by a recursive path
%   order, and complete a set of equations into a convergent system. The
%   compile-time translator rule set is a rewrite system, and this is the
%   machinery that says whether it terminates and whether it is confluent.
%
%   This is an ADAPTATION, not a reimplementation. The core is Markus Triska's
%   trs.pl, "Reason about Term Rewriting Systems", written 2015-2022, PUBLIC
%   DOMAIN, tested with Scryer Prolog [source: https://www.metalevel.at/trs/,
%   file https://www.metalevel.at/trs/trs.pl, read 2026-08-19]. What the port
%   to SWI-Prolog 10 changed, and nothing else:
%
%   - library(clpz) becomes library(clpfd). #=/2 is spelled the same in both,
%     so only the import line differs.
%   - library(dcgs), library(iso_ext) and library(format) are dropped: DCG
%     notation and phrase/2 are built into SWI and nothing here uses the other
%     two.
%   - the file becomes a module, which is a fence rather than a fix. Every src/
%     file the engine loads is consulted into `user`, and step/3, ord/4, lex/4,
%     mul/4, context/3 and group/1 are names generic enough that something
%     there will want one eventually [measured 2026-08-19: none of them is
%     defined in `user` today, so nothing collides yet]. The engine does not
%     load this file; a caller asks for it by name.
%   - critical_pairs//2 becomes overlaps//3, which emits an overlap RECORD
%     naming the two rules and the position instead of the bare pair, and
%     critical_pairs/2 projects the pair back out. A report about a rule set
%     has to say which two rules overlapped and where, and a bare pair cannot.
%     Projecting rather than adding a second enumerator keeps the enumeration
%     defined exactly once, which is what makes the agreement with the Lean
%     enumerator (below) an agreement about the thing completion/5 uses.
%
%   The additions below the ported part carry their own citations and are kept
%   in one section so the port stays diff-able against the original, whose
%   layout and 8-column continuation style this file therefore keeps.
%
%   Its step/3 matches with subsumes_term/2 and then copies with copy_term/2,
%   which is the same matching discipline the engine's own rule heads use: a
%   rule may not bind a variable of the term it is matched against. P2.1 makes
%   MeTTa heads matched rather than called; P2.16 re-checks that match after a
%   guard runs. This is the third place the discipline shows up, and the reason
%   an adopted rewriting library needed no change to fit.
% Assumes:
%   - a rule is L ==> R with variables represented by Prolog variables, so two
%     rules that must not share variables are copy_term/2'd apart before they
%     meet. Every predicate here that brings two rules together does that
%     [source: Triska's own note above the ==> operator].
%   - confluence_check/3 numbers the peak's variables and then compares reducts
%     with =@=/2, so a variable a rule with an extra variable invented on the
%     way does not make two equal terms look different, while the peak's own
%     variables stay distinguishable. rhs_vars_in_lhs/1 is the predicate that
%     says whether a system has such rules at all
%     [tested: tests/prolog/trs.plt,
%     an_invented_variable_does_not_make_a_pair_look_divergent].
%   - overlaps/2 enumerates the same family as
%     MeTTaILProofs.CPExecutable.criticalPairs: every ordered pair of rules at
%     every non-variable position of the first rule's left-hand side, the root
%     included, with the second rule renamed apart. Positions are counted from
%     1 here and from 0 there, which is the one difference. Agreement is
%     measured over 84 systems, 24 written for the shapes that separate the two
%     enumerators and 60 generated
%     [tested 2026-08-19:
%     test_the_two_enumerators_compute_the_same_critical_pairs].
% Guarantees:
%   - critical_pairs/2, step/3, normal_form/3, rpo/5, completion/5,
%     equations_trs/2 and equations_order/2 behave as the original does.
%     equations_trs/2 turns the three group axioms into the documented 10-rule
%     convergent system [tested: tests/prolog/trs.plt,
%     the_group_axioms_complete_to_the_documented_ten_rules].
%   - normal_form/3 MAY NOT TERMINATE. That is the original's own wording and
%     its counter-example is kept: with R = { a ==> a, f(X) ==> b } the term
%     f(a) does have a normal form, and normal_form/3 does not find it, because
%     it reduces arguments first and a is its own reduct. Nothing here hides
%     that behind a fuel parameter; bounded_join/4 is the bounded predicate and
%     it says so in its name
%     [tested: tests/prolog/trs.plt,
%     normal_form_loops_on_the_documented_counter_example].
%   - overlaps/2 and critical_pairs/2 enumerate the SAME family, because
%     critical_pairs/2 is a projection of overlaps/2 rather than a second
%     enumerator
%     [tested: tests/prolog/trs.plt, critical_pairs_is_a_projection_of_overlaps].
% Decides:
%   - a bound is an argument, never a constant. reachable_up_to/4,
%     bounded_join/4 and confluence_check/3 all take their fuel from the
%     caller, so an `unknown` is always attributable to a number the caller
%     chose.
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

:- module(trs, [ op(800, xfx, ==>),
                 step/3,
                 normal_form/3,
                 critical_pairs/2,
                 overlaps/2,
                 ord/4,
                 lex/4,
                 mul/4,
                 rpo/5,
                 completion/5,
                 equations_trs/2,
                 equations_trs/3,
                 equations_order/2,
                 equations_functors/2,
                 group/1,
                 one_steps/3,
                 reachable_up_to/4,
                 bounded_join/4,
                 confluence_check/3,
                 left_linear/1,
                 rhs_vars_in_lhs/1
               ]).

:- use_module(library(clpfd)).
:- use_module(library(lists)).
:- use_module(library(pairs)).

/* - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
   Ported from Triska's trs.pl. Variables in equations and rules are Prolog
   variables, which is what lets built-in unification do the work, and what
   makes copy_term/2 obligatory wherever two rules meet.
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */

:- op(800, xfx, ==>).

/* Perform one rewriting step at the root position, using the first
   matching rule, if any. */

step([L==>R|Rs], T0, T) :-
        (   subsumes_term(L, T0) ->
            copy_term(L-R, T0-T)
        ;   step(Rs, T0, T)
        ).

/* Reduce to normal form. May not terminate!
   For example: R = { a -> a, f(x) -> b },
   although f(a) does have a normal form! */

normal_form(Rs, T0, T) :-
        (   var(T0) -> T = T0
        ;   T0 =.. [F|Args0],
            maplist(normal_form(Rs), Args0, Args1),
            T1 =.. [F|Args1],
            (   step(Rs, T1, T2) ->
                normal_form(Rs, T2, T)
            ;   T = T1
            )
        ).

/* Critical pairs, as overlap records.

   overlap(Outer, Inner, Position, Peak, Left, Right): rule number Outer of the
   first list overlaps rule number Inner of the second at Position of Outer's
   left-hand side, both numbered from 1, the position read from the root as a
   list of argument indices. Peak is the overlapped term, Left is Outer applied
   at the root, Right is Inner applied at Position.

   Two arguments travel unchanged through the whole descent and are bundled so
   the added indices do not turn six arguments into nine: from(OuterIndex,
   InnerRules), and where(Frames, Position), which are the one thing "where we
   are" written twice, once as reconstruction frames and once as a path. */

critical_pairs(Rs, CPs) :-
        overlaps(Rs, Overlaps),
        maplist(overlap_pair, Overlaps, CPs).

overlap_pair(overlap(_,_,_,_,L,R), L=R).

overlaps(Rs, Overlaps) :- phrase(overlaps_(Rs, 1, Rs), Overlaps).

overlaps_([], _, _) --> [].
overlaps_([R|Rs], I, Rules) -->
        rule_cps(R, from(I,Rules), where([],[])),
        { I1 is I + 1 },
        overlaps_(Rs, I1, Rules).

rule_cps(T ==> R, From, Where) -->
        (   { var(T) } -> []
        ;   { From = from(_, Rules) },
            roots_cps(Rules, 1, T ==> R, From, Where),
            { T =.. [F|Ts] },
            inner_cps(Ts, 1, F, [], R, From, Where)
        ).

roots_cps([], _, _, _, _) --> [].
roots_cps([Left0==>Right0|Rules], J, L0==>R0, from(I,All), where(Cs0,Pos)) -->
        {  copy_term(f(L0,R0,Cs0), f(L,R,Cs)),
           copy_term(Left0-Right0, Left-Right) },
        (   { unify_with_occurs_check(L, Left) } ->
            {  foldl(context, Cs, Right, Reduced),
               foldl(context, Cs, L, Peak) },
            [overlap(I,J,Pos,Peak,R,Reduced)]
        ;   []
        ),
        { J1 is J + 1 },
        roots_cps(Rules, J1, L0==>R0, from(I,All), where(Cs0,Pos)).

inner_cps([], _, _, _, _, _, _) --> [].
inner_cps([T|Ts], N, F, Left0, R, From, where(Cs,Pos)) -->
        {  reverse(Left0, Left),
           append(Pos, [N], Pos1),
           N1 is N + 1 },
        rule_cps(T ==> R, From, where([conc(F,Left,Ts)|Cs], Pos1)),
        inner_cps(Ts, N1, F, [T|Left0], R, From, where(Cs,Pos)).

context(conc(F,Ts1,Ts2), Arg, T) :-
        append(Ts1, [Arg|Ts2], Ts),
        T =.. [F|Ts].

/* Lexicographic order. */

ord(Fs, F1, F2, Ord) :-
        once((nth0(N1, Fs, F1),
              nth0(N2, Fs, F2))),
        compare(Ord, N1, N2).

lex(Cmp, Xs, Ys, Ord) :- lex_(Xs, Ys, Cmp, Ord).

lex_([], [], _, =).
lex_([X|Xs], [Y|Ys], Cmp, Ord) :-
        call(Cmp, X, Y, Ord0),
        (   Ord0 == (=) -> lex_(Xs, Ys, Cmp, Ord)
        ;   Ord = Ord0
        ).

/* Multiset order. */

multiset_diff(Cmp, Xs0, Ys, Xs) :-
        foldl(subtract_element(Cmp), Ys, Xs0, Xs).

subtract_element(Cmp, Y, Xs0, Xs) :- subtract_first(Xs0, Y, Cmp, Xs).

subtract_first([], _, _, []).
subtract_first([X|Xs], Y, Cmp, Rs) :-
        (   call(Cmp, X, Y, =) -> Rs = Xs
        ;   Rs = [X|Rest],
            subtract_first(Xs, Y, Cmp, Rest)
        ).

mul(Cmp, Ms, Ns, Ord) :-
        multiset_diff(Cmp, Ns, Ms, NMs),
        multiset_diff(Cmp, Ms, Ns, MNs),
        (   NMs == [], MNs == [] -> Ord = (=)
        ;   forall(member(N, NMs),
                   (   member(M, MNs), call(Cmp, M, N, >))) -> Ord = (>)
        ;   Ord = (<)
        ).

/* Recursive path order with status. Stats is a list of pairs [f-mul, g-lex]. */

rpo(Fs, Stats, S, T, Ord) :-
        (   var(T) ->
            (   S == T -> Ord = (=)
            ;   term_variables(S, Vs), member(V, Vs), V == T -> Ord = (>)
            ;   Ord = (<)
            )
        ;   var(S) -> Ord = (<)
        ;   S =.. [F|Ss], T =.. [G|Ts],
            (   forall(member(Si, Ss), rpo(Fs, Stats, Si, T, <)) ->
                ord(Fs, F, G, Ord0),
                (   Ord0 == (>) ->
                    (   forall(member(Ti, Ts), rpo(Fs, Stats, S, Ti, >)) ->
                        Ord = (>)
                    ;   Ord = (<)
                    )
                ;   Ord0 == (=) ->
                    (   forall(member(Ti, Ts), rpo(Fs, Stats, S, Ti, >)) ->
                        memberchk(F-Stat, Stats),
                        call(Stat, rpo(Fs, Stats), Ss, Ts, Ord)
                    ;   Ord = (<)
                    )
                ;   Ord0 == (<) -> Ord = (<)
                )
            ;   Ord = (>)
            )
        ).

/* Huet / Knuth-Bendix completion. */

rule_size(T, S) :-
        (   var(T) -> S #= 1
        ;   T =.. [_|Args],
            foldl(rule_size_, Args, 0, S0),
            S #= S0 + 1
        ).

rule_size_(T, S0, S) :-
        rule_size(T, TS),
        S #= S0 + TS.

smallest_rule_first(Rs0, Rs) :-
        maplist(rule_size, Rs0, Sizes0),
        pairs_keys_values(Pairs0, Sizes0, Rs0),
        keysort(Pairs0, Pairs),
        pairs_keys_values(Pairs, _, Rs).

orient([], _, Ss, Ss, Rs, Rs).
orient([S0=T0|Es0], Cmp, Ss0, Ss, Rs0, Rs) :-
        append(Rs0, Ss0, Rules),
        maplist(normal_form(Rules), [S0,T0], [S,T]),
        (   S == T -> orient(Es0, Cmp, Ss0, Ss, Rs0, Rs)
        ;   (   call(Cmp, S, T, >) -> Rule = (S ==> T)
            ;   call(Cmp, T, S, >) -> Rule = (T ==> S)
            ;   false /* identity cannot be oriented */
            ),
            foldl(simpler(Rule, Rules), Ss0, Es0-[], Es1-Ss1),
            foldl(simpler(Rule, Rules), Rs0, Es1-[], Es-Rs1),
            orient(Es, Cmp, [Rule|Ss1], Ss, Rs1, Rs)
        ).

simpler(Rule, Rules, L0==>R0, Es0-Us0, Es-Us) :-
        normal_form([Rule], L0, L),
        (   L0 == L ->
            normal_form([Rule|Rules], R0, R),
            Es-Us = Es0-[L==>R|Us0]
        ;   Es-Us = [L=R0|Es0]-Us0
        ).

completion(Es0, Cmp, Ss0, Rs0, Rs) :-
        orient(Es0, Cmp, Ss0, Ss1, Rs0, Rs1),
        (   Ss1 == [] -> Rs = Rs1
        ;   smallest_rule_first(Ss1, [R|Ss]),
            phrase((overlaps_([R], 1, Rs1),
                    overlaps_(Rs1, 1, [R]),
                    overlaps_([R], 1, [R])), Overlaps),
            maplist(overlap_pair, Overlaps, CPs),
            completion(CPs, Cmp, Ss, [R|Rs1], Rs)
        ).

/* Try to find a suitable order to create a convergent TRS from a list of
   equations. This SEARCHES for a workable precedence by permutation and for a
   per-symbol status, so it enumerates n! * 2^n candidates for n symbols and is
   meant for the small systems it was written for. */

equations_trs(Es, Rs) :-
        equations_order(Es, Cmp),
        equations_trs(Cmp, Es, Rs).

equations_trs(Cmp, Es, Rs) :-
        completion(Es, Cmp, [], [], Rs).

equations_order(Es, rpo(Sorted,Stats)) :-
        equations_functors(Es, Fs),
        pairs_keys_values(Stats, Fs, Values),
        maplist(ord_status, Values),
        permutation(Fs, Sorted).

ord_status(lex).
ord_status(mul).

/* Functors occurring in given equations. */

equations_functors(Eqs, Fs) :-
        phrase(eqs_functors_(Eqs), Fs0),
        sort(Fs0, Fs).

eqs_functors_([]) --> [].
eqs_functors_([A=B|Es]) -->
        term_functors(A),
        term_functors(B),
        eqs_functors_(Es).

term_functors(Var) --> { var(Var) }, !.
term_functors(T) -->
        { T =.. [F|Args] },
        [F],
        functors_(Args).

functors_([]) --> [].
functors_([T|Ts]) -->
        term_functors(T),
        functors_(Ts).

/* The original's motivating example: a set closed under a binary operation *
   with a left identity, left inverses and associativity. The three equations
   complete to the documented convergent 10-rule system. */

group([e*X = X,
       i(X)*X = e,
       A*(B*C) = (A*B)*C]).

/* - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
   Additions. Everything above this line is the port; everything below is this
   repository's, and mirrors the executable Knuth-Bendix-Huet criterion that
   MeTTaILProofs/CPExecutable.lean proves correct, predicate for definition:
   one_steps/3 is oneSteps, reachable_up_to/4 is reachableUpTo, bounded_join/4
   is boundedJoin?, confluence_check/3 is checkConfluence's per-pair verdict,
   and overlaps/2 above is criticalPairs. Mirroring it is the point: the two
   are run against each other on a corpus and the Lean side is kernel-checked
   [source: Knuth and Bendix, "Simple Word Problems in Universal Algebras",
   Computational Problems in Abstract Algebra, Pergamon (1970), 263-297, for
   the critical-pair test deciding confluence of a terminating finite system].
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */

/* Every one-step reduct of a term: every rule, at every position, by
   MATCHING. step/3 rewrites only at the root and only with the first rule that
   matches, which is a strategy; this is the whole relation. */

one_steps(Rs, T, Us) :- findall(U, one_step(Rs, T, U), Us).

one_step(Rs, T, U) :-
        member(L==>R, Rs),
        subsumes_term(L, T),
        copy_term(L-R, T-U).
one_step(Rs, T, U) :-
        compound(T),
        T =.. [F|Args],
        nth1(N, Args, Arg, Rest),
        one_step(Rs, Arg, Arg1),
        nth1(N, Args1, Arg1, Rest),
        U =.. [F|Args1].

/* Terms reachable in at most Fuel steps, the starting term included. */

reachable_up_to(Rs, Fuel, T, Ts) :-
        (   Fuel =:= 0 -> Ts = [T]
        ;   Fuel0 is Fuel - 1,
            reachable_up_to(Rs, Fuel0, T, Prior),
            foldl(reducts_of(Rs), Prior, Prior, Ts0),
            dedup(Ts0, Ts)
        ).

reducts_of(Rs, T, Acc0, Acc) :-
        one_steps(Rs, T, Us),
        append(Acc0, Us, Acc).

dedup([], []).
dedup([T|Ts], [T|Rest]) :-
        exclude(=@=(T), Ts, Ts1),
        dedup(Ts1, Rest).

/* Search for a common reduct within an explicit depth bound on each branch.
   Failure says the search found none within the bound, never that none
   exists. */

bounded_join(Rs, Fuel, A, B) :-
        reachable_up_to(Rs, Fuel, A, As),
        reachable_up_to(Rs, Fuel, B, Bs),
        member(C, As),
        memberchk_variant(C, Bs),
        !.

memberchk_variant(X, [Y|Ys]) :-
        (   X =@= Y -> true ;   memberchk_variant(X, Ys) ).

/* Classify every critical pair of a system: joined within the bound, a
   certified counterexample (two DISTINCT normal forms, which no further
   rewriting can join), or unknown (the bounded search missed and at least one
   side still has a reduct). The three-way split is the Lean side's
   ConfluenceCheck, and keeping `unknown` apart from `counterexample` is what
   stops a bound the caller chose from reading as a negative result.

   The peak's own variables are numbered before the search, which is what makes
   =@=/2 the right comparison rather than a sloppy one. Two reducts of the same
   peak may differ only in variables that a rule with an extra variable made up
   on the way, and those ARE the same term; the peak's own variables are not
   interchangeable and numbering them says so. With no extra variables in the
   system both sides of every pair are ground after numbering, =@=/2 collapses
   to ==/2, and the answers are the Lean side's exactly. */

confluence_check(Rs, Fuel, Verdicts) :-
        overlaps(Rs, Overlaps),
        maplist(pair_verdict(Rs, Fuel), Overlaps, Verdicts).

pair_verdict(Rs, Fuel, Overlap, verdict(I,J,Pos,L,R,Verdict)) :-
        copy_term(Overlap, overlap(I,J,Pos,Peak,L,R)),
        numbervars(Peak, 0, _),
        (   bounded_join(Rs, Fuel, L, R) -> Verdict = joined
        ;   one_steps(Rs, L, []),
            one_steps(Rs, R, []),
            L \=@= R
        ->  Verdict = counterexample
        ;   Verdict = unknown
        ).

/* The two side conditions the criterion needs, checked rather than assumed. A
   system failing either gets an answer about a different system. */

left_linear(Rs) :-
        forall(member(L==>_, Rs),
               (   var_occurrences(L, 0, N),
                   term_variables(L, Vs),
                   length(Vs, N) )).

var_occurrences(T, N0, N) :-
        (   var(T) -> N is N0 + 1
        ;   compound(T) -> T =.. [_|Args], foldl(var_occurrences, Args, N0, N)
        ;   N = N0
        ).

rhs_vars_in_lhs(Rs) :-
        forall(member(L==>R, Rs),
               (   term_variables(R, RVs),
                   term_variables(L, LVs),
                   forall(member(V, RVs),
                          ( member(W, LVs), W == V )) )).
