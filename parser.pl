% Purpose: parse and print MeTTa atoms with shared variable identity, string
%   escapes, and semicolon comments outside strings.
% Guarantees:
%   - sread/2 and the file loader apply the same semicolon-comment rules
%     without a comment-stripping prepass [tested 2026-08-15:
%     parser_comments, filereader_comments].
%   - swrite/2 names variables by first occurrence, independent of SWI's
%     process-local variable identifiers [tested 2026-08-14:
%     parser_stable_variables].
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

:- use_module(library(dcg/basics)). %blanks/0, number/1, string_without/2

%Generate a MeTTa S-expression string from the Prolog list (inverse parsing):
swrite(Term, String) :- stable_print_term(Term, Printable),
                        phrase(swrite_numbered(Printable), Codes),
                        string_codes(String, Codes).
%Keep the writer DCGs usable by direct parser clients while the internal
%forms operate on a numbered copy of the source term.
swrite_exp(Term) --> { stable_print_term(Term, Printable) },
                      swrite_numbered(Printable).
seq(Terms) --> { stable_print_term(Terms, Printable) },
               seq_numbered(Printable).

stable_print_term(Term, Printable) :-
    copy_term_nat(Term, Printable),
    numbervars(Printable, 0, _, [functor_name('$petta_variable')]).

swrite_numbered('$petta_variable'(Index)) --> !, "$_", { number_codes(Index, Cs) }, Cs.
swrite_numbered(Num)   --> { number(Num) }, !, { number_codes(Num, Cs) }, Cs.
swrite_numbered(Str)   --> { string(Str) }, !, "\"", { string_codes(Str, Cs), escape_quotes(Cs, Es) }, Es, "\"".
swrite_numbered(Atom)  --> { atom(Atom) }, !, atom(Atom).
swrite_numbered([H|T]) --> { \+ is_list([H|T]) }, !, "(", atom(cons), " ", swrite_numbered(H), " ", swrite_numbered(T), ")".
swrite_numbered([H|T]) --> !, "(", seq_numbered([H|T]), ")".
swrite_numbered([])    --> !, "()".
swrite_numbered(Term)  --> { Term =.. [F|Args] }, "(", atom(F), ( { Args == [] } -> [] ; " ", seq_numbered(Args) ), ")".
seq_numbered([X])    --> !, swrite_numbered(X).
seq_numbered([X|Xs]) --> swrite_numbered(X), " ", seq_numbered(Xs).
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

%Read S string or atom, extract codes, and apply the parsing DCG.
%atom_codes/2 reads the text of a string directly. Going through
%atom_string/2 first interned an atom for every string parsed, and the
%library parses one per m.run(): 20000 distinct strings through
%atom_string/2 left 9953 atoms behind, through atom_codes/2 none.
sread(S, T) :- atom_codes(S, Cs),
               sread_codes(Cs, S, T).

sread_codes(Cs, Source, T) :-
    ( phrase(sexpr(T, [], _), Cs)
      -> true
       ; format(atom(Msg), 'Parse error in form: ~w', [Source]),
         throw(error(syntax_error(Msg), none)) ).

%The top-level form scanner uses the same string and comment states as the
%token grammar. A backslash escapes exactly the next string character.
string_state(outside, 0'", string) :- !.
string_state(outside, 0';, comment) :- !.
string_state(string, 0'\\, escaped) :- !.
string_state(string, 0'", outside) :- !.
string_state(escaped, _, string) :- !.
string_state(comment, 0'\n, outside) :- !.
string_state(comment, _, comment) :- !.
string_state(State, _, State).

%Semicolon comments are inter-token layout. Keeping them in the DCG avoids a
%separate source-sized code list before parsing. These clauses combine blank
%and comment scanning so the ordinary no-comment path has no wrapper grammar.
metta_layout --> ";", !, metta_comment_body, metta_layout.
metta_layout --> [C], { code_type(C, space) }, !, metta_layout.
metta_layout --> [].

metta_comment_body --> "\n", !.
metta_comment_body --> eos, !.
metta_comment_body --> [_], metta_comment_body.

%An S-Expression is a parentheses-nesting of S-Expressions that are either
%numbers, variables, strings, or atoms. Surrounding whitespace is skipped once
%here rather than at the start of each alternative: with a leading blanks//0 in
%every clause, reading an atom, the commonest token, rescanned the same
%whitespace five times because the four alternatives ahead of it each skipped
%it before failing.
sexpr(T,E0,E) --> metta_layout, sexpr_token(T,E0,E), metta_layout.

sexpr_token(S,E,E)  --> string_lit(S), !.
sexpr_token(T,E0,E) --> "(", metta_layout, seq(T,E0,E), metta_layout, ")", !.
sexpr_token(N,E,E)  --> number(N), number_ends, !.
sexpr_token(V,E0,E) --> var_symbol(V,E0,E), !.
sexpr_token(A,E,E)  --> atom_symbol(A).

%A number token has to end at whitespace, a parenthesis, or end of input.
%Without this, 1_2_3 would read as the number 1 followed by junk. The
%terminators are facts rather than a scan of a literal string, so the check is
%one indexed lookup instead of rebuilding the same six codes per number.
number_ends([], []) :- !.
number_ends([Code|Rest], [Code|Rest]) :- number_terminator(Code).

number_terminator(0' ).
number_terminator(0'().
number_terminator(0')).
number_terminator(0'\t).
number_terminator(0'\n).
number_terminator(0'\r).
number_terminator(0';).

%Recursive processing of S-Expressions within S-Expressions. sexpr//3 has
%already consumed the whitespace after its own token, so this does not repeat it:
seq([X|Xs],E0,E2) --> sexpr(X,E0,E1), seq(Xs,E1,E2).
seq([],E,E)       --> [].

%Variables start with $, and keep track of them: reusing existing Prolog variables for variables of same name:
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
