%Arity expander for JIT-indexing-efficient representation of space entries:
ensure_dynamic_arity(Space,Arity) :- ( current_predicate(Space/Arity)
                                       -> true ; dynamic(Space/Arity) ).

%Add a function atom:
'add-atom'('&self', Term, true) :- Term = [=,[FAtom|_],_],
                                   register_fun(FAtom),
                                   translate_clause(Term, Clause),
                                   assertz(Clause), !.

%Add an atom to the space:
'add-atom'(Space, [Rel|Args], true) :- length(Args, N), Arity is N + 2,
                                       ensure_dynamic_arity(Space, Arity),
                                       Term =.. [Space, Rel | Args],
                                       assertz(Term).

%%Remove a function atom:
'remove-atom'('&self', Term, Removed) :- Term = [=,[F|Ins],_],
                                         translate_clause(Term, Cl),
                                         ( retract(Cl) -> length(Ins, K),
                                                          unregister_fun(F/K),
                                                          Removed=true
                                                        ; Removed=false ).

%Remove all same atoms:
'remove-atom'(Space, [Rel|Args], true) :- length(Args, N), Arity is N + 2,
                                          ensure_dynamic_arity(Space, Arity),
                                          Term =.. [Space, Rel | Args],
                                          ( clause(Term, true)
                                            -> retractall(Term) ).

%Function evaluation matches, where the unification returned true, so it unified:
match('&self', true, Arg2, Result) :- Result = Arg2.

%Match for pattern:
match(Space, [Rel|PatArgs], OutPattern, Result) :-
  \+ (Rel == ','),
  Term =.. [Space, Rel | PatArgs],
  Term, \+ cyclic_term(OutPattern),
  copy_term(OutPattern, Result).

match(Space, [','|Args], OutPattern, Result) :-
    [Head|Tail] = Args,
    append([Space], Head, List),
    Term =.. List,
    Term, \+ cyclic_term(OutPattern),
    match(Space, [','|Tail], OutPattern, Result).

match(_, [','], OutPattern, Result) :-
  copy_term(OutPattern, Result).

%Get all atoms in space, irregard of arity:
'get-atoms'(Space, Pattern) :- current_predicate(Space/Arity),
                               functor(Head, Space, Arity),
                               clause(Head, true),
                               Head =.. [Space | Pattern].
