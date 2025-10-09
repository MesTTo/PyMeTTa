:- multifile match/4.
:- multifile 'add-atom'/3.

:- ensure_loaded([parser]).


% list_to_pat(+Tokens:list, -Out:string)
% Example: list_to_pat([friend,sam,A], Out).
%          Out = "[3] friend sam $".
list_to_pat(Toks, Out) :-
    length(Toks, N),
    maplist(tok_to_atom, Toks, Norm),              % normalize vars/$n -> '$', numbers -> atoms, etc.
    atomic_list_concat(Norm, ' ', Mid),
    format(string(Out), "[~d] ~w", [N, Mid]).

tok_to_atom(T, '$') :- var(T), !.                  % any Prolog var -> '$'
tok_to_atom(A, '$') :-                             % $1, $2, ... -> '$'
    atom(A), atom_concat('$', Ds, A), Ds \= '',
    atom_chars(Ds, Cs), maplist(char_type_digit, Cs), !.
tok_to_atom(N, A)  :- number(N), !, atom_number(A, N).
tok_to_atom(S, A)  :- string(S), !, atom_string(A, S).
tok_to_atom(A, A)  :- atom(A), !.
tok_to_atom(T, A)  :- term_string(T, Str), atom_string(A, Str).

char_type_digit(C) :- char_type(C, digit).

% list_to_sexpr(+List, -SExprString)
list_to_sexpr(List, S) :-
    sexpr_tokens(List, Ts),
    atomic_list_concat(Ts, ' ', Mid),
    format(string(S), "(~w)", [Mid]).

sexpr_tokens([], []).
sexpr_tokens([H|T], [Tok|Ts]) :-
    sexpr_token(H, Tok),
    sexpr_tokens(T, Ts).

sexpr_token(X, '$') :- var(X), !.
sexpr_token(X, Tok) :-
    is_list(X), !,
    sexpr_tokens(X, In),
    atomic_list_concat(In, ' ', Mid),
    format(atom(Tok), "(~w)", [Mid]).
sexpr_token(X, Tok) :- term_to_atom(X, Tok).

% mork_query(+Pattern:list, +OutPattern:list(with one var), -Instantiated:list)
mork_query(Pattern, OutPattern, Instantiation) :-
    % build MORK query pattern from already-parsed list
    list_to_pat(Pattern, MorkPat),
    % run query
    mork("query", MorkPat, Temp),
    % split results, drop trailing empty line
    split_string(Temp, "\n", "", Raw),
    exclude(==(""), Raw, Lines),
    % parse each returned value with your s-expr reader
    maplist(sread, Lines, Values),
    % instantiate the single var in OutPattern with each value
    maplist(instantiate_one(OutPattern), Values, Instantiated),
    member(Instantiation, Instantiated).

instantiate_one(Template0, Value, Instantiated) :-
    copy_term(Template0, T),
    term_variables(T, [V|_]),   % assumes exactly one variable
    V = Value,
    Instantiated = T.

'add-atom'('&mork', Atom, true) :- !, list_to_sexpr(Atom, S), 
                                   re_replace("'"/g, "", S, SClean),
                                   mork("load",SClean,B), !.
                                   %format(string(SB), "load result: ~w ~n", [B]),
                                   %writeln(SB).

%Match for pattern:
match('&mork', Pattern, OutPattern, Result) :- !, mork_query(Pattern, OutPattern, Result).

%Execute MM2 calculus
'mm2-exec'('&mork', Result) :- mork("exec","wu",A), Result=true.
            
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

mork_init :- use_foreign_library('./morklib.so'),
             mork("init","",A),
             format(string(SA), "init result: ~w ~n", [A]),
             writeln(SA).

mork_test :- 'mork_add-atom'('&mork', [friend,sam,tim], true),
             'mork_add-atom'('&mork', [friend,sam,joe], true),
             findall(C, mork_query([friend,sam,X], [friend,sam,X], C), Cs),
             format(string(SC), "query result: ~w ~n", [Cs]), writeln(SC).
