:- use_module(library(dcg/basics)). %blanks/0, number/1, string_without/2

%Generate a MeTTa S-expression string from the Prolog list (inverse parsing):
swrite(List, SExpr) :- with_output_to(string(S0), write(List)),
                       re_replace("\\["/g, "(", S0, S1),
                       re_replace("\\]"/g, ")", S1, S2),
                       re_replace(","/g, " ", S2, S3),
                       re_replace("_"/g, "$$1", S3, SExpr).

%Read S string or atom, extract codes, and apply DCG:
sread(S,T) :- atom_string(A,S),
              atom_codes(A,Cs),
              phrase(sexpr(T,[],_), Cs).

%An S-Expression is a parentheses-nesting of S-Expressions that are either numbers, variables, sttrings, or atoms:
sexpr(S,E,E)  --> blanks, string_lit(S), blanks, !.
sexpr(T,E0,E) --> blanks, "(", blanks, seq(T,E0,E), blanks, ")", blanks, !.
sexpr(N,E,E)  --> blanks, number(N), blanks, !.
sexpr(V,E0,E) --> blanks, var_symbol(V,E0,E), blanks, !.
sexpr(A,E,E)  --> blanks, atom_symbol(A), blanks.

%Recursive processing of S-Expressions within S-Expressions:
seq([X|Xs],E0,E2) --> sexpr(X,E0,E1), blanks, seq(Xs,E1,E2).
seq([],E,E)       --> [].

%Variables start with $, and keep track of them: re-using exising Prolog variables for variables of same name:
var_symbol(V,E0,E) --> "$", token(Cs), { atom_chars(N, Cs), ( memberchk(N-V0, E0) -> V=V0, E=E0 ; V=_, E=[N-V|E0] ) }.

%Atoms are derived from tokens:
atom_symbol(A) --> token(Cs), { string_codes("\"", [Q]), ( Cs = [Q|_] -> append([Q|Body], [Q], Cs), %"str" as string
                                                                         string_codes(A, Body)
                                                                       ; atom_codes(R, Cs),         %others are atoms
                                                                         ( R = 'True' -> A = true
                                                                                       ; R = 'False'
                                                                                         -> A = false
                                                                                          ; A = R ))}.

%A token is a non-empty string without whitespace:
token(Cs) --> string_without(" \t\r\n()", Cs), { Cs \= [] }.

%Just string literal handling from here-on:
string_lit(S) --> "\"", string_chars(Cs), "\"", { string_codes(S, Cs) }.
string_chars([]) --> [].
string_chars([C|Cs]) --> normal_char(C), !, string_chars(Cs).
string_chars([C|Cs]) --> escape_char(C), string_chars(Cs).
normal_char(C) --> [C], { C =\= 0'", C =\= 0'\\ }.
escape_char(C) --> "\\", [X], { ( X=0'n->C=10 ; X=0't->C=9 ; X=0'r->C=13 ; C=X ) }.
