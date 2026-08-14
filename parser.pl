% Purpose: parse and print MeTTa atoms with shared variable identity, string
%   escapes, and semicolon comments outside strings.
% Guarantees:
%   - sread/2 and the file loader apply the same semicolon-comment rules
%     [tested 2026-08-14: parser_comments].
% Open Obligations:
%   To Do: Make printed unbound-variable names reproducible.
%   Hacks: None
%   Future Enhancements: None

:- use_module(library(dcg/basics)). %blanks/0, number/1, string_without/2

%Generate a MeTTa S-expression string from the Prolog list (inverse parsing):
swrite(Term, String) :- phrase(swrite_exp(Term), Codes),
                        string_codes(String, Codes).
swrite_exp(Var)   --> { var(Var) }, !, "$", { term_to_atom(Var, A), atom_codes(A, Cs) }, Cs.
swrite_exp(Num)   --> { number(Num) }, !, { number_codes(Num, Cs) }, Cs.
swrite_exp(Str)   --> { string(Str) }, !, "\"", { string_codes(Str, Cs), escape_quotes(Cs, Es) }, Es, "\"".
swrite_exp(Atom)  --> { atom(Atom) }, !, atom(Atom).
swrite_exp([H|T]) --> { \+ is_list([H|T]) }, !, "(", atom(cons), " ", swrite_exp(H), " ", swrite_exp(T), ")".
swrite_exp([H|T]) --> !, "(", seq([H|T]), ")".
swrite_exp([])    --> !, "()".
swrite_exp(Term)  --> { Term =.. [F|Args] }, "(", atom(F), ( { Args == [] } -> [] ; " ", seq(Args) ), ")".
seq([X])    --> swrite_exp(X).
seq([X|Xs]) --> swrite_exp(X), " ", seq(Xs).
%The five escapes hyperon's Str Display emits and this reader already
%decodes (string_chars): quote, backslash, newline, tab, carriage
%return. Writing them keeps a printed string literal on one line, so
%every line-oriented consumer of swrite text (the MORK bridge splits
%dumps on newlines) re-parses it to itself.
escape_quotes([], []).
escape_quotes([0'\\|T], [0'\\,0'\\|R]) :- !, escape_quotes(T, R).
escape_quotes([0'"|T], [0'\\,0'"|R]) :- !, escape_quotes(T, R).
escape_quotes([0'\n|T], [0'\\,0'n|R]) :- !, escape_quotes(T, R).
escape_quotes([0'\t|T], [0'\\,0't|R]) :- !, escape_quotes(T, R).
escape_quotes([0'\r|T], [0'\\,0'r|R]) :- !, escape_quotes(T, R).
escape_quotes([H|T], [H|R]) :- escape_quotes(T, R).

%Read S string or atom, extract codes, and apply DCG (parsing):
sread(S, T) :- ( atom_string(A, S),
                 atom_codes(A, RawCodes),
                 strip(RawCodes, outside, Cs),
                 phrase(sexpr(T, [], _), Cs)
               -> true ; format(atom(Msg), 'Parse error in form: ~w', [S]), throw(error(syntax_error(Msg), none)) ).

%The reader and top-level loader share one string-aware comment pass. A
%backslash escapes exactly the next character while inside a string.
string_state(outside, 0'", string) :- !.
string_state(string, 0'\\, escaped) :- !.
string_state(string, 0'", outside) :- !.
string_state(escaped, _, string) :- !.
string_state(State, _, State).

strip([], _, []).
strip([0'\n|R], State, [0'\n|O]) :- !,
    string_state(State, 0'\n, State1),
    strip(R, State1, O).
strip([0';|R], outside, Out) :- !,
    ( append(_, [0'\n|Rest], R) -> strip([0'\n|Rest], outside, Out)
                                   ; Out = [] ).
strip([C|R], State, [C|O]) :-
    string_state(State, C, State1),
    strip(R, State1, O).

%An S-Expression is a parentheses-nesting of S-Expressions that are either numbers, variables, sttrings, or atoms:
sexpr(S,E,E)  --> blanks, string_lit(S), blanks, !.
sexpr(T,E0,E) --> blanks, "(", blanks, seq(T,E0,E), blanks, ")", blanks, !.
sexpr(N,E,E)  --> blanks, number(N), ( lookahead_any(" ()\t\n\r") ; \+ [_] ), blanks, !.
sexpr(V,E0,E) --> blanks, var_symbol(V,E0,E), blanks, !.
sexpr(A,E,E)  --> blanks, atom_symbol(A), blanks.

%Helper for strange atoms that aren't numbers, e.g. 1_2_3:
lookahead_any(Terms, S, E) :- string_codes(Terms,SC), S = [Head | _], member(Head,SC), !, S = E.

%Recursive processing of S-Expressions within S-Expressions:
seq([X|Xs],E0,E2) --> sexpr(X,E0,E1), blanks, seq(Xs,E1,E2).
seq([],E,E)       --> [].

%Variables start with $, and keep track of them: re-using exising Prolog variables for variables of same name:
var_symbol(V,E0,E) --> "$", token(Cs), { atom_chars(N, Cs), ( N == '_' -> V = _, E = E0 ; memberchk(N-V0, E0) -> V = V0, E = E0 ; V = _, E = [N-V|E0] ) }.

%Atoms are derived from tokens:
atom_symbol(A) --> token(Cs), { string_codes("\"", [Q]), ( Cs = [Q|_] -> append([Q|Body], [Q], Cs), %"str" as string
                                                                         string_codes(A, Body)
                                                                       ; atom_codes(R, Cs),         %others are atoms
                                                                         ( R = 'True' -> A = true
                                                                                       ; R = 'False'
                                                                                         -> A = false
                                                                                          ; A = R ))}.

%A token is a non-empty string without whitespace or comment delimiters:
token(Cs) --> string_without(" \t\r\n();", Cs), { Cs \= [] }.

%Just string literal handling from here-on:
string_lit(S) --> "\"", string_chars(Cs), "\"", { string_codes(S, Cs) }.
string_chars([]) --> [].
string_chars([C|Cs]) --> [C], { C =\= 0'", C =\= 0'\\ }, !, string_chars(Cs).
string_chars([C|Cs]) --> "\\", [X], { (X=0'n->C=10; X=0't->C=9; X=0'r->C=13; C=X) }, string_chars(Cs).
