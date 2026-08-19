% Purpose: parse and print MeTTa atoms with shared variable identity, string
%   escapes, and semicolon comments outside strings.
% Guarantees:
%   - sread/2 and the file loader apply the same semicolon-comment rules
%     without a comment-stripping prepass [tested 2026-08-15:
%     parser_comments, filereader_comments].
%   - swrite/2 names variables by first occurrence, independent of SWI's
%     process-local variable identifiers [tested 2026-08-14:
%     parser_stable_variables].
%   - a token ends at exactly the Unicode White_Space property plus `(`, `)`
%     and `;`, and at nothing else, which is upstream MeTTa's own rule.
%     metta_token_boundary/2 is the one place that says so, and the layout
%     skipper, the number terminator and metta_symbol_writable/1 all read
%     it, so a symbol holding whitespace has no text form and the swrite/2
%     to sread/2 round trip stays inverse [tested 2026-08-19:
%     parser_unicode_layout,
%     test_every_unicode_whitespace_separates_atoms].
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

:- use_module(library(dcg/basics)). %atom//1, number//1, eos//0
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
    (   State0 == outside, \+ metta_token_boundary(C, layout), C =\= 0';
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

%Every code that ends a token, and which kind of boundary it is. One table
%answers both questions the reader asks of a character, because two answers
%to one of them is the defect it replaces: the layout skipper took whitespace
%from code_type/2 while the token scanner carried its own list of seven ASCII
%characters, and wherever the two disagreed the token swallowed the
%separator. 21 of the 25 whitespace characters left `(1<c>2)` a single symbol,
%and silently, which is what makes it worth fixing rather than noting.
%NO-BREAK SPACE is what HTML's `&nbsp;` renders to, so `(foo bar)` pasted out
%of a browser became one symbol, matched nothing, and reported no problem
%[tested: parser_unicode_layout].
%
%Both kinds together are upstream MeTTa's own boundary rule, not a wider
%class chosen here: its reader ends a word at `c.is_whitespace() || c ==
%'(' || c == ')' || c == ';'` and at nothing else [source:
%hyperon-experimental v0.2.10-25-g0559a5e2, lib/src/metta/text.rs,
%parse_word]. So the layout rows are the Unicode White_Space property,
%char::is_whitespace being that property exactly [source: Rust std,
%char::is_whitespace, "Returns true if this char has the White_Space
%property", specified in https://www.unicode.org/Public/UCD/latest/ucd/
%PropList.txt, PropList-17.0.0, "Total code points: 25"].
%
%Written out rather than read from code_type/2, for two reasons.
%
%SWI's class is neither the property nor fixed. code_type/2 reads the C
%library's tables, so it MOVES with the locale: 21 codes under en_AU.UTF-8
%and under C.UTF-8, and 6 under LC_ALL=C [measured 2026-08-19, enumerated
%over the whole range]. Which characters separate atoms is a property of the
%language, not of the environment a process happens to start in, and a
%container or a cron job running under LC_ALL=C is ordinary. Even at its
%widest the class is four short of White_Space: it omits NEL and the three
%NO-BREAK spaces, reporting them as cntrl and punct.
%
%And the table has to be ground facts to be indexed. A clause body is a
%call, and worse, one clause with a variable head argument costs the index
%outright: SWI does not build a hash on an argument where more than 10% of
%the clauses are unbound there, because such a clause has to be linked into
%every bucket [source: SWI-Prolog 10.1 Reference Manual 2.17, "Just-in-time
%clause indexing"]. So `metta_token_boundary(C, layout) :- code_type(C,
%space)` beside four named codes would be a five-clause linear scan, not a
%lookup. As 28 ground facts it is a 64-bucket hash [measured 2026-08-19:
%jiti_list/1 reports index 1, speedup 28.0], and reading every shipped
%example while asking metta_unwritable_symbol/2 about each form costs 22.06M
%inferences and 13.01G instructions:u against 24.30M and 18.38G for the
%string_without//2 scan this replaces [measured 2026-08-19, min of 3
%interleaved runs]. parser_unicode_layout holds the table to the property
%and to SWI's own class, so neither can drift unseen.
metta_token_boundary(0x0009, layout).  %CHARACTER TABULATION
metta_token_boundary(0x000A, layout).  %LINE FEED
metta_token_boundary(0x000B, layout).  %LINE TABULATION
metta_token_boundary(0x000C, layout).  %FORM FEED
metta_token_boundary(0x000D, layout).  %CARRIAGE RETURN
metta_token_boundary(0x0020, layout).  %SPACE
metta_token_boundary(0x0085, layout).  %NEXT LINE
metta_token_boundary(0x00A0, layout).  %NO-BREAK SPACE
metta_token_boundary(0x1680, layout).  %OGHAM SPACE MARK
metta_token_boundary(0x2000, layout).  %EN QUAD
metta_token_boundary(0x2001, layout).  %EM QUAD
metta_token_boundary(0x2002, layout).  %EN SPACE
metta_token_boundary(0x2003, layout).  %EM SPACE
metta_token_boundary(0x2004, layout).  %THREE-PER-EM SPACE
metta_token_boundary(0x2005, layout).  %FOUR-PER-EM SPACE
metta_token_boundary(0x2006, layout).  %SIX-PER-EM SPACE
metta_token_boundary(0x2007, layout).  %FIGURE SPACE
metta_token_boundary(0x2008, layout).  %PUNCTUATION SPACE
metta_token_boundary(0x2009, layout).  %THIN SPACE
metta_token_boundary(0x200A, layout).  %HAIR SPACE
metta_token_boundary(0x2028, layout).  %LINE SEPARATOR
metta_token_boundary(0x2029, layout).  %PARAGRAPH SEPARATOR
metta_token_boundary(0x202F, layout).  %NARROW NO-BREAK SPACE
metta_token_boundary(0x205F, layout).  %MEDIUM MATHEMATICAL SPACE
metta_token_boundary(0x3000, layout).  %IDEOGRAPHIC SPACE
metta_token_boundary(0x0028, punctuation).  %LEFT PARENTHESIS
metta_token_boundary(0x0029, punctuation).  %RIGHT PARENTHESIS
metta_token_boundary(0x003B, punctuation).  %SEMICOLON, which opens a comment

%Semicolon comments are inter-token layout. Keeping them in the DCG avoids a
%separate source-sized code list before parsing. These clauses combine blank
%and comment scanning so the ordinary no-comment path has no wrapper grammar.
metta_layout --> ";", !, metta_comment_body, metta_layout.
metta_layout --> [C], { metta_token_boundary(C, layout) }, !, metta_layout.
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

%A number token has to end where any token ends, or at end of input. Without
%this, 1_2_3 would read as the number 1 followed by junk.
number_ends([], []) :- !.
number_ends([Code|Rest], [Code|Rest]) :- metta_token_boundary(Code, _).

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

%A token is a non-empty run of characters that end no token. The shape is
%string_without//2's own, a greedy scan committed per character, with the
%membership test replaced by the boundary table, so where a token ends is
%one definition rather than a literal repeated here.
token(Cs) --> token_codes(Cs), { Cs \= [] }.

token_codes([C|Cs]) --> [C], { \+ metta_token_boundary(C, _) }, !, token_codes(Cs).
token_codes([]) --> [].

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
writable_token([C|Cs]) --> [C], { C =\= 0'", \+ metta_token_boundary(C, _) }, !,
                            writable_token(Cs).
writable_token([]) --> [].

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
