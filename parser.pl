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
:- use_module(library(occurs)). %sub_term/2

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

%A width-aware layout for deep terms: a subterm prints inline when it
%fits the remaining width, and otherwise breaks after its head with each
%child on its own line two deeper, the classic s-expression convention.
%The head itself always inlines, heads being symbols in practice. The
%measuring pass re-renders subterms, quadratic in the worst case, which
%a printer can afford and no hot path calls
%[tested parser_pretty_printing].
swrite_pretty(Term, String) :- swrite_pretty(Term, 78, String).
swrite_pretty(Term, Width, String) :-
    stable_print_term(Term, Printable),
    with_output_to(string(String), petta_pretty_print(Printable, 0, Width)).

petta_pretty_print(T, Indent, Width) :-
    petta_inline_text(T, Inline),
    string_length(Inline, L),
    Budget is Width - Indent,
    (   L =< Budget
    ->  write(Inline)
    ;   is_list(T), T = [H|Rest], Rest \== []
    ->  petta_inline_text(H, HeadText),
        format("(~w", [HeadText]),
        Sub is Indent + 2,
        petta_pretty_children(Rest, Sub, Width),
        write(")")
    ;   write(Inline)
    ).

petta_pretty_children([], _, _).
petta_pretty_children([C|Cs], Indent, Width) :-
    nl, tab(Indent),
    petta_pretty_print(C, Indent, Width),
    petta_pretty_children(Cs, Indent, Width).

petta_inline_text(T, S) :-
    phrase(swrite_numbered(T), Codes),
    string_codes(S, Codes).

swrite_numbered('$petta_variable'(Index)) --> !, "$_", { number_codes(Index, Cs) }, Cs.
swrite_numbered(Num)   --> { number(Num) }, !, { number_codes(Num, Cs) }, Cs.
swrite_numbered(Str)   --> { string(Str) }, !, "\"", { string_codes(Str, Cs), escape_quotes(Cs, Es) }, Es, "\"".
swrite_numbered(Atom)  --> { atom(Atom) }, !, atom(Atom).
swrite_numbered([H|T]) --> { \+ is_list([H|T]) }, !, "(", atom(cons), " ", swrite_numbered(H), " ", swrite_numbered(T), ")".
swrite_numbered([H|T]) --> !, "(", seq_numbered([H|T]), ")".
swrite_numbered([])    --> !, "()".
%Everything below here is not a MeTTa term, and these are the three ways of not
%being one, each guarded and cutting like the clauses above them.
%
%The provider comes first because a Python tuple IS a compound, -/N being
%janus's encoding for one, and `(- 1 2)` names an operator that is not there.
swrite_numbered(Term)  --> { metta_grounded_text(Term, Text) }, !, { string_codes(Text, Cs) }, Cs.
%compound_name_arguments/3 rather than =../2, because =../2 refuses a
%zero-arity compound outright: it raises `compound_non_zero_arity' before the
%empty-argument branch below can be reached, and the raise escapes the writer
%and kills the run. Nothing about that is specific to where the term came from,
%and janus hands one back for Python's `()`, so `!(py-atom "()")` took the whole
%program down [tested: an_empty_compound_prints].
swrite_numbered(Term)  --> { compound(Term), compound_name_arguments(Term, F, Args) }, !, "(", atom(F), ( { Args == [] } -> [] ; " ", seq_numbered(Args) ), ")".
%A grounded value with no provider loaded: its own text, rather than nothing.
%The writer is never the thing that fails.
swrite_numbered(Term)  --> { term_string(Term, Text), string_codes(Text, Cs) }, Cs.
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

%%%% Is this a whole form, or is the user still typing? %%%%
%
%sread/2 answers one way: it parses or it raises. Three different situations
%collapse into that one outcome, and a console needs them apart:
%
%  (f a)     complete           [f, a]
%  (f a      INCOMPLETE         syntax_error('Parse error in form: (f a')
%  (f a))    malformed          syntax_error('Parse error in form: (f a))')
%  ""        an empty line      syntax_error('Parse error in form: ')
%
%CPython names this as THE hard part of a console and answers it three ways:
%"The tricky part is to determine when the user has entered an incomplete
%command that can be completed by entering more text (as opposed to a complete
%command or a syntax error)", and compile_command returns a code object,
%None, or raises [source: CPython, the code and codeop modules]. This is that
%contract: complete(Term), incomplete, or a raise.
%
%Without it examples/basics/repl.metta could not accept a multi-line form at
%all, since 'readln!'/1 is one read_line_to_string then sread/2, and every
%other console has to re-implement bracket counting. Which is not "just count
%parens": a bracket inside a string or a comment must not count, and
%string_state/3 below is what knows the difference
%[tested: parser_command_tells_incomplete_from_malformed].
sread_command(Text, Result) :-
    text_to_command_codes(Text, Codes),
    (   \+ command_has_content(Codes)
    ->  Result = incomplete
    ;   command_wants_more(Codes)
    ->  Result = incomplete
    ;   sread(Text, Term)
    ->  Result = complete(Term)
    ;   sread(Text, _)          % it raises; this reaches its error
    ).

text_to_command_codes(Text, Codes) :-
    ( is_list(Text) -> Codes = Text
    ; string(Text) -> string_codes(Text, Codes)
    ; atom_codes(Text, Codes) ).

%An empty line, or one holding only layout and comments, is INCOMPLETE rather
%than an error: it is the commonest input in any console and it should
%re-prompt.
command_has_content(Codes) :- command_content(Codes, outside).

command_content([C|Rest], State0) :-
    string_state(State0, C, State1),
    (   State0 == outside, \+ code_type(C, space), C =\= 0';
    ->  true
    ;   State0 == string
    ->  true
    ;   command_content(Rest, State1)
    ).

%Whether more text could still complete this: an open bracket, or an
%unterminated string, which a MeTTa string may legitimately be because a
%newline inside one keeps the string state.
%
%An unterminated COMMENT is not: a comment ends at end of input as readily as
%at a newline, so `(f a) ; trailing` is a whole form and treating the comment
%state as "wants more" made it hang the console.
command_wants_more(Codes) :-
    command_balance(Codes, 0, outside, Depth, State),
    ( Depth > 0 -> true ; memberchk(State, [string, escaped]) ).

%A closing bracket too many is MALFORMED, not incomplete: no amount of further
%typing repairs it, so this fails and the reader's own error is the answer.
command_balance([], Depth, State, Depth, State).
command_balance([C|Rest], Depth0, State0, Depth, State) :-
    string_state(State0, C, State1),
    (   State0 == outside
    ->  ( C =:= 0'( -> Depth1 is Depth0 + 1
        ; C =:= 0') -> Depth1 is Depth0 - 1
        ;               Depth1 = Depth0 )
    ;   Depth1 = Depth0
    ),
    Depth1 >= 0,
    command_balance(Rest, Depth1, State1, Depth, State).

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

%Whether a symbol's spelling reads back as that same symbol. Both readers
%above answer, so this cannot drift from either: a name that reads as a
%number, a variable, a string, a boolean, or as more than one token has no
%text form that carries it, and neither has one that opens a string for the
%form scanner, which would swallow the rest of the form.
%
%A character blacklist stood here in three places and missed three classes,
%each a silent change of meaning wherever an atom crossed as text. $x read
%back as a variable, a;b truncated at the comment it starts, 42 read as the
%number, and True read as the boolean [tested: parser_symbol_text].
%Reading the whole grammar back costs about three times a single token
%scan, and every save and every digest asks this of every symbol it
%carries, so the ordinary name answers without it: once a name is one
%token holding no quote, only a first character that could begin a number,
%a variable or a string, or a boolean's own spelling, can make it read
%back as something else [measured 2026-08-15: the grammar alone cost
%+18.9% inferences and +16.8% instructions on space-digest].
metta_symbol_writable(Symbol) :-
    atom(Symbol),
    atom_codes(Symbol, Codes),
    Codes = [First|_],
    phrase(writable_token(Codes), Codes),
    (   metta_symbol_ordinary(First, Symbol)
    ->  true
    ;   phrase(sexpr_token(Read, [], _), Codes),
        Read == Symbol ).

%One token, and no quote either: the form scanner opens a string on a quote
%and would swallow the rest of the form, which sread/2 alone never sees. One
%scan answers both, since every symbol carried as text pays for it.
writable_token(Cs) --> string_without(" \t\r\n();\"", Cs), { Cs \= [] }.

metta_symbol_ordinary(First, Symbol) :-
    \+ metta_symbol_reserved_start(First),
    Symbol \== 'True',
    Symbol \== 'False'.

%$ opens a variable, . - + and a digit can open a number. A name starting
%with one of them is read in full before it is believed.
metta_symbol_reserved_start(0'$).
metta_symbol_reserved_start(0'.).
metta_symbol_reserved_start(0'-).
metta_symbol_reserved_start(0'+).
metta_symbol_reserved_start(Code) :- code_type(Code, digit).

%The first symbol in a term that has no round-trip text spelling.
%sub_term/2 walks it; a MeTTa expression is a list, so its head symbol is
%an element and is reached, and a non-list compound is written functor
%first by swrite/2, so that name is checked too
%[source: SWI-Prolog 10.1 Reference Manual A.31, library(occurs)].
metta_unwritable_symbol(Term, Bad) :-
    sub_term(Sub, Term),
    metta_unwritable_here(Sub, Bad), !.

metta_unwritable_here(Sub, Sub) :- atom(Sub), !, \+ metta_symbol_writable(Sub).
metta_unwritable_here(Sub, Name) :- compound(Sub), \+ is_list(Sub),
                                    functor(Sub, Name, _),
                                    \+ metta_symbol_writable(Name).

%Just string literal handling from here-on:
string_lit(S) --> "\"", string_chars(Cs), "\"", { string_codes(S, Cs) }.
string_chars([]) --> [].
string_chars([C|Cs]) --> [C], { C =\= 0'", C =\= 0'\\ }, !, string_chars(Cs).
string_chars([C|Cs]) --> "\\", [X], { (X=0'n->C=10; X=0't->C=9; X=0'r->C=13; C=X) }, string_chars(Cs).
