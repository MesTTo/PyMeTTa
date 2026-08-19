% Purpose: decide termination of NARROWING by deciding termination of
%   REWRITING, which is what the compile-time rule set actually needs. A
%   translator rule is applied by calling its compiled clause, so the rule head
%   and the term UNIFY and the rule may bind a variable of the program being
%   compiled. That is narrowing, not rewriting, and termination of rewriting
%   does not imply it.
%
%   The route is Nishida and Vidal's [source: Naoki Nishida and German Vidal,
%   "Termination of narrowing via termination of rewriting", Applicable Algebra
%   in Engineering, Communication and Computing 21(3):177-225, 2010, read
%   2026-08-19 from https://gvidal.webs.upv.es/confs/tntpaper/paper.pdf]:
%
%   1. state an ABSTRACT TERM, which is a mode: f(g,v) says the first argument
%      of f is ground in every initial call and the second may be a variable;
%   2. INFER, by a binding-time analysis over the call graph, which arguments
%      of every other function are ground (their section 5.2, whose Bv and Be
%      this file transcribes, with the g/v binding-times they use rather than
%      partial evaluation's static/dynamic);
%   3. check the sufficient condition for SAFETY of the resulting argument
%      filtering (their Lemma 11, whose third condition needs the graph of
%      functional dependencies of their Definition 15);
%   4. FILTER every possibly-variable argument away with the argument filtering
%      transformation (their Definition 14), which adds one rule per filtered
%      subterm that still holds a defined symbol, and replaces a variable left
%      unbound by the filtering with a fresh constant;
%   5. hand the filtered system to a termination method for REWRITING. Their
%      Corollary 3 is what makes step 5 answer step 1's question.
%
%   Nothing is copied from their implementation. `mistupv/tnt` on GitHub is the
%   authors' own tool and carries NO licence file, so it is used here only as
%   an ORACLE: its published README session, run on its own AG01 3.12 example
%   with the single declaration app(g,v), is reproduced by this file
%   [tested: tests/prolog/narrowing.plt, the_published_tnt_example_is_reproduced].
%
%   Step 5 is trs.pl's rpo/5, a recursive path order. A path order needs a
%   precedence, and searching all of them is n! * 2^n, so the precedence is
%   CONSTRUCTED from the call graph first (constructors lowest, then every
%   defined symbol above the ones it calls) and only searched when the
%   signature is small enough that searching it is cheap.
% Assumes:
%   - a rule is trs.pl's L ==> R with Prolog variables for term variables.
%   - the theory holds for LEFT-LINEAR CONSTRUCTOR systems with no extra
%     variables, so narrowing_terminates/3 checks all three rather than
%     assuming them and names the rule that breaks one
%     [source: paper section 4.3, "we consider that the input for the
%     termination analysis is a left-linear constructor TRS"].
%   - a symbol has ONE arity. The paper's signature is arity-indexed and the
%     filtering changes arities, so a name used at two arities is reported
%     rather than analysed [source: paper, Definition 8's footnote 9, which
%     keeps the same symbol for the filtered function "with a possibly
%     different arity"].
% Guarantees:
%   - narrowing_terminates/3 answers established(Route) or
%     not_established(Reason) and nothing else, so a rule set is never left in
%     a third state. Route names the filtering, the filtered system and the
%     order that decided; Reason names which step failed and on which rule or
%     symbol [tested: tests/prolog/narrowing.plt].
%   - the binding-time analysis reaches a fixpoint, because a mode only ever
%     moves g -> v and the mode space is finite [source: paper, footnote 14].
% Decides:
%   - '$bottom' is the fresh constant for a variable the filtering leaves
%     unbound, the paper's ⊥ and TNT's printed nullVar. A MeTTa symbol cannot
%     collide with it: a source token starting with $ parses as a variable.
%   - the precedence search is bounded at 6 symbols for permutations and 8 for
%     mixed lexicographic/multiset statuses. Above those the constructed
%     precedence and the two uniform statuses are the whole search, and a
%     failure says no_rpo_order rather than pretending the space was covered.
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

:- module(narrowing, [ narrowing_terminates/3,
                       defined_symbols/2,
                       defined_names/2,
                       binding_time_division/4,
                       division_filtering/2,
                       apply_filtering/3,
                       aft/3,
                       rpo_order/2
                     ]).

:- use_module(library(lists)).
:- use_module(library(apply)).
:- use_module(library(occurs)).
:- use_module('trs.pl').

%%%% The top level %%%%

% narrowing_terminates(+Rules, +AbstractTerm, -Outcome). AbstractTerm is the
% mode of the initial call written the way the paper and TNT write it, f(g,v),
% or the bare symbol f for a nullary one.
narrowing_terminates(Rules, Abstract, Outcome) :-
    (   precondition_failure(Rules, Reason)
    ->  Outcome = not_established(Reason)
    ;   defined_symbols(Rules, Ds),
        abstract_symbol(Abstract, Symbol, Modes),
        (   memberchk(Symbol, Ds)
        ->  binding_time_division(Rules, Ds, Symbol-Modes, Division),
            division_filtering(Division, Filtering),
            Symbol = Entry/_,
            (   unsafe_filtering(Rules, Entry, Filtering, Where)
            ->  Outcome = not_established(no_safe_filtering(Where))
            ;   aft(Rules, Filtering, Filtered),
                (   rpo_order(Filtered, Order)
                ->  Outcome = established(route(Filtering, Filtered, Order))
                ;   Outcome = not_established(no_rpo_order(Filtered)) ) )
        ;   Outcome = not_established(unknown_entry(Symbol)) ) ).

% A mode that is neither g nor v RAISES. Failing instead would make
% narrowing_terminates/3 fail rather than answer, which is the third state this
% module exists to forbid, and it would be a caller's mistake wearing the
% analysis's clothes.
abstract_symbol(Abstract, F/N, Modes) :-
    Abstract =.. [F|Modes],
    length(Modes, N),
    (   forall(member(M, Modes), memberchk(M, [g,v]))
    ->  true
    ;   throw(error(type_error(abstract_term, Abstract), _)) ).

%%%% What the theory needs of the system, checked rather than assumed %%%%

precondition_failure(Rules, Reason) :-
    (   \+ left_linear(Rules)
    ->  nth1(I, Rules, Rule), \+ left_linear([Rule]), !,
        Reason = not_left_linear(I)
    ;   \+ rhs_vars_in_lhs(Rules)
    ->  nth1(I, Rules, Rule), \+ rhs_vars_in_lhs([Rule]), !,
        Reason = extra_variables(I)
    ;   symbol_at_two_arities(Rules, F)
    ->  Reason = symbol_at_two_arities(F)
    ;   defined_names(Rules, Names),
        nth1(I, Rules, L==>_),
        L =.. [_|Args],
        member(Arg, Args),
        \+ constructor_term(Arg, Names)
    ->  Reason = not_constructor_system(I) ).

symbol_at_two_arities(Rules, F) :-
    findall(F0/N0, ( member(Rule, Rules), term_symbol(Rule, F0/N0) ), Ss0),
    sort(Ss0, Ss),
    member(F/N, Ss),
    member(F/M, Ss),
    N \== M,
    !.

term_symbol(Rule, S) :- sub_term(T, Rule), nonvar(T), T \= (_ ==> _),
                        functor(T, F, N), S = F/N.

% The defined symbols are the roots of the left-hand sides; everything else in
% the signature is a constructor. The analysis needs both spellings: the
% division is per NAME/ARITY because a mode list has the symbol's length, while
% every question asked of a FILTERED term is per NAME, since filtering changes
% arities and symbol_at_two_arities/2 has already made a name unambiguous.
defined_symbols(Rules, Ds) :-
    findall(F/N, ( member(L==>_, Rules), functor(L, F, N) ), Ds0),
    sort(Ds0, Ds).

defined_names(Rules, Names) :-
    findall(F, ( member(L==>_, Rules), functor(L, F, _) ), Ns0),
    sort(Ns0, Names).

constructor_term(T, _) :- var(T), !.
constructor_term(T, Names) :-
    functor(T, F, _),
    \+ memberchk(F, Names),
    T =.. [_|Args],
    forall(member(A, Args), constructor_term(A, Names)).

%%%% Step 2: the binding-time analysis, section 5.2 %%%%

% binding_time_division(+Rules, +Ds, +Symbol-Modes, -Division). Division maps
% every defined F/N to a list of N binding-times, and is the least fixpoint
% above the initial division that the abstract term fixes.
binding_time_division(Rules, Ds, Symbol-Modes, Division) :-
    findall(D-Ms, ( member(D, Ds),
                    (   D == Symbol -> Ms = Modes
                    ;   D = _/N, length(Ms, N), maplist(=(g), Ms) ) ),
            Div0),
    division_fixpoint(Rules, Ds, Div0, Division).

division_fixpoint(Rules, Ds, Div0, Division) :-
    maplist(division_of_symbol(Rules, Ds, Div0), Div0, Div1),
    (   Div1 == Div0
    ->  Division = Div0
    ;   division_fixpoint(Rules, Ds, Div1, Division) ).

division_of_symbol(Rules, Ds, Div0, Symbol-Modes0, Symbol-Modes) :-
    foldl(division_of_rule(Symbol, Ds, Div0), Rules, Modes0, Modes).

division_of_rule(Symbol, Ds, Div0, L==>R, Modes0, Modes) :-
    binding_environment(Div0, L, Env),
    bv(R, Symbol, Env, Div0, Ds, Modes1),
    maplist(lub, Modes0, Modes1, Modes).

lub(g, g, g).
lub(g, v, v).
lub(v, g, v).
lub(v, v, v).

% e(div, f(t1..tn)): the binding-time environment a rule's left-hand side
% induces. A repeated variable takes the least upper bound of its occurrences,
% which only arises in a system left_linear/1 has already refused.
binding_environment(Div, L, Env) :-
    functor(L, F, N),
    memberchk(F/N-Modes, Div),
    L =.. [_|Args],
    foldl(environment_argument, Args, Modes, [], Env).

environment_argument(Arg, Mode, Env0, Env) :-
    term_variables(Arg, Vs),
    foldl(environment_variable(Mode), Vs, Env0, Env).

environment_variable(Mode, V, Env0, Env) :-
    (   select(W-M0, Env0, Rest), W == V
    ->  lub(M0, Mode, M), Env = [V-M|Rest]
    ;   Env = [V-Mode|Env0] ).

% Bv[[t]] h/n rho div: the binding-times of the calls to h/n that occur in t.
bv(T, _/N, _, _, _, Modes) :-
    var(T),
    !,
    length(Modes, N),
    maplist(=(g), Modes).
bv(T, H/N, Env, Div, Ds, Modes) :-
    functor(T, F, K),
    T =.. [_|Args],
    length(Bottom, N),
    maplist(=(g), Bottom),
    foldl(bv_argument(H/N, Env, Div, Ds), Args, Bottom, Below),
    (   F/K == H/N
    ->  maplist(be_argument(Env, Div, Ds), Args, Here),
        maplist(lub, Below, Here, Modes)
    ;   Modes = Below ).

bv_argument(H, Env, Div, Ds, T, Modes0, Modes) :-
    bv(T, H, Env, Div, Ds, Modes1),
    maplist(lub, Modes0, Modes1, Modes).

be_argument(Env, Div, Ds, T, B) :- be(T, Env, Div, Ds, B).

% Be[[t]] rho div: g when the FILTERED term holds no possibly-variable
% variable, v otherwise. Reading the current division here is the one place
% where this differs from a textbook binding-time analysis: an argument the
% filtering will drop must not make the term dynamic.
be(T, Env, _, _, B) :-
    var(T),
    !,
    (   member(W-M, Env), W == T -> B = M ;   B = v ).
be(T, Env, Div, Ds, B) :-
    functor(T, F, N),
    T =.. [_|Args],
    (   memberchk(F/N-Modes, Div)
    ->  ground_arguments(Modes, Args, Kept)
    ;   Kept = Args ),
    foldl(be_lub(Env, Div, Ds), Kept, g, B).

be_lub(Env, Div, Ds, T, B0, B) :- be(T, Env, Div, Ds, B1), lub(B0, B1, B).

ground_arguments([], [], []).
ground_arguments([M|Ms], [A|As], Kept) :-
    ground_arguments(Ms, As, Rest),
    (   M == g -> Kept = [A|Rest] ;   Kept = Rest ).

% The argument filtering a division induces: keep the ground positions of every
% defined symbol. A constructor keeps all of its arguments, which the paper
% states and which apply_filtering/3 gets by the symbol being absent here.
division_filtering(Division, Filtering) :-
    maplist(kept_positions, Division, Filtering).

kept_positions(Symbol-Modes, Symbol-Positions) :-
    findall(I, nth1(I, Modes, g), Positions).

%%%% Step 3: is the filtering safe? Lemma 11's third condition %%%%

% The first two conditions of Lemma 11 hold by construction of the division
% (their Lemma 12). The third is a genuine check: every rule reachable from a
% defined symbol NESTED inside the filtered right-hand side of a reachable rule
% must keep every variable its filtered right-hand side needs.
unsafe_filtering(Rules, Entry, Filtering, condition3(Name)) :-
    defined_names(Rules, Names),
    member(L==>R, Rules),
    functor(L, F, _),
    reaches(Rules, Entry, F),
    apply_filtering(R, Filtering, FilteredR),
    nested_defined(FilteredR, Names, Inner),
    reaches(Rules, Inner, Name),
    member(L2==>R2, Rules),
    functor(L2, Name, _),
    apply_filtering(L2, Filtering, FL2),
    apply_filtering(R2, Filtering, FR2),
    term_variables(FR2, RVs),
    term_variables(FL2, LVs),
    member(V, RVs),
    \+ ( member(W, LVs), W == V ),
    !.

% Definition 15's graph of functional dependencies, reflexive-transitively
% closed. Reflexive is the conservative reading: it puts the entry's own rules
% inside the condition rather than outside it.
reaches(Rules, From, To) :- reaches_(Rules, [From], To).

reaches_(_, Seen, To) :- memberchk(To, Seen).
reaches_(Rules, Seen, To) :-
    member(From, Seen),
    calls(Rules, From, Next),
    \+ memberchk(Next, Seen),
    reaches_(Rules, [Next|Seen], To).

calls(Rules, F, G) :-
    defined_names(Rules, Names),
    member(L==>R, Rules),
    functor(L, F, _),
    sub_term(T, R),
    nonvar(T),
    functor(T, G, _),
    memberchk(G, Names).

nested_defined(T, Names, Inner) :-
    sub_term(Outer, T),
    nonvar(Outer),
    functor(Outer, F, _),
    memberchk(F, Names),
    Outer =.. [_|Args],
    member(Arg, Args),
    sub_term(Below, Arg),
    nonvar(Below),
    functor(Below, Inner, _),
    memberchk(Inner, Names).

%%%% Step 4: the argument filtering transformation, Definition 14 %%%%

apply_filtering(T, _, T) :- var(T), !.
apply_filtering(T, Filtering, Filtered) :-
    functor(T, F, N),
    T =.. [_|Args],
    maplist(filter_argument(Filtering), Args, Args1),
    (   memberchk(F/N-Positions, Filtering)
    ->  split_positions(Args1, Positions, Kept, _)
    ;   Kept = Args1 ),
    Filtered =.. [F|Kept].

filter_argument(Filtering, T, T1) :- apply_filtering(T, Filtering, T1).

% The arguments at the listed positions, and the rest. Written out rather than
% done with findall/3, which COPIES: a filtered right-hand side that no longer
% shares its variables with the filtered left-hand side turns every rule into a
% rule with extra variables, and the whole analysis then answers about that.
split_positions(Args, Positions, Kept, Dropped) :-
    split_positions(Args, 1, Positions, Kept, Dropped).

split_positions([], _, _, [], []).
split_positions([A|As], I, Positions, Kept, Dropped) :-
    I1 is I + 1,
    split_positions(As, I1, Positions, Kept0, Dropped0),
    (   memberchk(I, Positions)
    ->  Kept = [A|Kept0], Dropped = Dropped0
    ;   Kept = Kept0, Dropped = [A|Dropped0] ).

% aft(+Rules, +Filtering, -Filtered): the filtered rules, plus one rule per
% subterm the filtering dropped whose filtered form still holds a defined
% symbol, because dropping it would otherwise hide a recursive call.
aft(Rules, Filtering, Filtered) :-
    defined_names(Rules, Names),
    findall(Rule, ( member(Original, Rules),
                    aft_rule(Original, Filtering, Names, Rule) ),
            Filtered).

aft_rule(Original, Filtering, _, L1 ==> R1) :-
    copy_term(Original, L==>R),
    apply_filtering(L, Filtering, L1),
    apply_filtering(R, Filtering, R1),
    bottom_extra_variables(L1, R1).
aft_rule(Original, Filtering, Names, L1 ==> S1) :-
    copy_term(Original, _==>Probe),
    dropped_subterms(Probe, Filtering, Found),
    nth1(I, Found, _),
    copy_term(Original, L==>R),
    dropped_subterms(R, Filtering, Subs),
    nth1(I, Subs, S),
    apply_filtering(S, Filtering, S1),
    \+ constructor_term(S1, Names),
    apply_filtering(L, Filtering, L1),
    bottom_extra_variables(L1, S1).

% dec_pi(t): every subterm the filtering drops, at any depth.
dropped_subterms(T, _, []) :- var(T), !.
dropped_subterms(T, Filtering, Subs) :-
    functor(T, F, N),
    T =.. [_|Args],
    (   memberchk(F/N-Positions, Filtering)
    ->  split_positions(Args, Positions, _, Here)
    ;   Here = [] ),
    foldl(dropped_below(Filtering), Args, Here, Subs).

dropped_below(Filtering, T, Acc0, Acc) :-
    dropped_subterms(T, Filtering, Subs),
    append(Acc0, Subs, Acc).

% [l -> r]⊥: a variable the filtered left-hand side no longer binds becomes the
% fresh constant, since it plays no part in the computation being analysed.
% maplist/2 rather than forall/2, which is a double negation and would undo
% every binding it just made.
bottom_extra_variables(L, R) :-
    term_variables(R, RVs),
    term_variables(L, LVs),
    maplist(bottom_unless_bound(LVs), RVs).

bottom_unless_bound(LVs, V) :-
    (   member(W, LVs), W == V -> true ;   V = '$bottom' ).

%%%% Step 5: termination of the filtered system, by recursive path order %%%%

% rpo_order(+Rules, -Order) succeeds when Order orients every rule left to
% right. The filtered system's defined names are the original's, because
% filtering changes a symbol's arity and never its root.
rpo_order(Rules, rpo(Fs, Stats)) :-
    rule_signature(Rules, Symbols),
    defined_names(Rules, Names),
    rpo_precedence(Rules, Names, Symbols, Fs),
    rpo_statuses(Fs, Stats),
    forall(member(L==>R, Rules), rpo(Fs, Stats, L, R, >)),
    !.

rule_signature(Rules, Symbols) :-
    findall(F, ( member(Rule, Rules), sub_term(T, Rule), nonvar(T),
                 T \= (_ ==> _), functor(T, F, _) ),
            Fs0),
    sort(Fs0, Symbols).

% The call graph's own precedence first: constructors lowest, then every
% defined symbol above the ones it calls. Cheap, and it is the precedence a
% terminating rule set almost always wants. Permutations only when the
% signature is small enough that enumerating them costs nothing.
rpo_precedence(Rules, Names, Symbols, Fs) :-
    intersection(Symbols, Names, Defined),
    subtract(Symbols, Defined, Constructors),
    callee_first(Defined, Rules, [], Sorted),
    append(Constructors, Sorted, Fs).
rpo_precedence(_, _, Symbols, Fs) :-
    length(Symbols, N),
    N =< 6,
    permutation(Symbols, Fs).

callee_first([], _, Acc, Sorted) :- reverse(Acc, Sorted).
callee_first([D|Ds], Rules, Acc, Sorted) :-
    (   select(F, [D|Ds], Rest),
        forall(( calls(Rules, F, G), G \== F ), memberchk(G, Acc))
    ->  true
    ;   F = D, Rest = Ds ),
    callee_first(Rest, Rules, [F|Acc], Sorted).

rpo_statuses(Fs, Stats) :- maplist(uniform_status(lex), Fs, Stats).
rpo_statuses(Fs, Stats) :- maplist(uniform_status(mul), Fs, Stats).
rpo_statuses(Fs, Stats) :-
    length(Fs, N),
    N =< 8,
    maplist(mixed_status, Fs, Stats).

uniform_status(Status, F, F-Status).

mixed_status(F, F-lex).
mixed_status(F, F-mul).
