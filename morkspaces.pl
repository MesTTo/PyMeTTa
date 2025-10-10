:- multifile match/4.
:- multifile 'add-atom'/3.

% mork_query(+Pattern:list, +OutPattern:list(with one var), -Instantiated:list)
mork_query(Pattern, OutPattern, Instantiation) :-
    % build MORK query pattern from already-parsed list
    %list_to_pat(Pattern, MorkPat),
    list_to_sexpr(Pattern, MorkPat),
    writeln(MorkPat).%,
    % run query
    %mork("query", MorkPat, Temp).
%    % split results, drop trailing empty line
%    split_string(Temp, "\n", "", Raw),
%    exclude(==(""), Raw, Lines),
%    % parse each returned value with your s-expr reader
%    maplist(sread, Lines, Values),
%    % instantiate the single var in OutPattern with each value
%    maplist(instantiate_one(OutPattern), Values, Instantiated),
%    member(Instantiation, Instantiated).

instantiate_one(Template0, Value, Instantiated) :-
    copy_term(Template0, T),
    term_variables(T, [V|_]),   % assumes exactly one variable
    V = Value,
    Instantiated = T.

'add-atom'('&mork', Atom, true) :- !, swrite(Atom, S), writeln(S),
                                   re_replace("'"/g, "", S, SClean),
                                   mork("load",SClean,B), !.
                                   %format(string(SB), "load result: ~w ~n", [B]),
                                   %writeln(SB).

%Match for pattern:
match('&mork', Pattern, OutPattern, Result) :- !, mork_query(Pattern, OutPattern, Result).

%Execute MM2 calculus
'mm2-exec'('&mork', Steps, Result) :- number_string(Steps, St), mork("exec", St, A), Result=true.
            
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
             mork("init","",A),
             format(string(SA), "init result: ~w ~n", [A]),
             writeln(SA).

mork_test :- 'mork_add-atom'('&mork', [friend,sam,tim], true),
             'mork_add-atom'('&mork', [friend,sam,joe], true),
             findall(C, mork_query([friend,sam,X], [friend,sam,X], C), Cs),
             format(string(SC), "query result: ~w ~n", [Cs]), writeln(SC).
