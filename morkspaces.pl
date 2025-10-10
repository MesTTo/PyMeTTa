:- multifile match/4.
:- multifile 'add-atom'/3.

%Add an atom to the space:
'add-atom'('&mork', Atom, true) :- !, swrite(Atom, S),
                                   re_replace("'"/g, "", S, SClean),
                                   mork("load",SClean,B), !.

%Match for pattern:
match('&mork', Pattern, OutPattern, Result) :- !, swrite(Pattern, MorkPat),
                                                  mork("query", MorkPat, Temp),
                                                  split_string(Temp, "\n", "", Raw),
                                                  exclude(==(""), Raw, Lines),
                                                  maplist(sread, Lines, Values),
                                                  member(Result, Values),
                                                  copy_term(Pattern-OutPattern, P2-O2),
                                                  P2 = Result,
                                                  OutPattern = O2.

%Execute MM2 calculus
'mm2-exec'('&mork', Steps, true) :- number_string(Steps, St),
                                    mork("exec", St, A).
            
%Remove all same atoms:
%'remove-atom'('&mork', [Rel|Args], true) :- length(Args, N), Arity is N + 2,
%                                          ensure_dynamic_arity(Space, Arity),
%                                          Term =.. [Space, Rel | Args],
%                                          ( clause(Term, true)
%                                            -> retractall(Term) ).


%Get all atoms in space, irregard of arity:
%'get-atoms'(Space, Pattern) :- current_predicate(Space/Arity),
%                               functor(Head, Space, Arity),
%                               clause(Head, true),
%                               Head =.. [Space | Pattern].

mork_init :- use_foreign_library('./mork_ffi/morklib.so'),
             writeln("MORK init: done").

mork_test :- 'add-atom'('&mork', [friend,sam,tim], true),
             'add-atom'('&mork', [friend,sam,joe], true),
             findall(C, match('&mork',[friend,sam,X], [friend,sam,X], C), Cs),
             format(string(SC), "MORK query result: ~w ~n", [Cs]), writeln(SC).
