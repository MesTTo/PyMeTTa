% Purpose: read MeTTa source, split it into complete top-level forms, and
% dispatch each parsed form to the evaluator.
% Guarantees:
%   - A parsed form that cannot translate is not reported as a syntax error
%     [tested 2026-08-14: filereader_translation_errors].
%   - top_forms//2 ignores comment text and keeps parentheses inside escaped
%     string quotes inside their form [tested 2026-08-14:
%     filereader_form_splitter].
%   - Loader diagnostics contain ANSI escapes only on terminal streams
%     [tested 2026-08-14: filereader_terminal_output].
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

:- use_module(library(readutil)). % read_file_to_string/3
:- use_module(library(ansi_term)). % terminal-aware diagnostic colors
:- use_module(library(pcre)). % re_replace/4
:- use_module(library(zlib)). % gzopen/3, .gz program files
%Every compiled clause's source equation; asserted here and by
%add-atom/3, read by removal and the tracer, so it must exist before
%the first function ever compiles (a virgin-engine remove-atom read it
%undefined and crashed).
:- dynamic translated_from/2.

:- multifile prolog:error_message//1.

prolog:error_message(petta_translation_failed(Form)) -->
    [ 'Could not translate MeTTa form: ~p'-[Form] ].
:- current_prolog_flag(argv, Args), ( (memberchk(silent, Args) ; memberchk('--silent', Args) ; memberchk('-s', Args))
                                      -> assertz(silent(true)) ; assertz(silent(false)) ).

%Read Filename into string S and process it (S holds MeTTa code):
load_metta_file(Filename, Results) :- load_metta_file(Filename, Results, '&self').
load_metta_file(Filename, Results, Space) :-
    catch(( read_metta_source(Filename, S),
            process_metta_string(S, Results, Space) ),
          Error,
          rethrow_metta_file_error(Filename, Error)).

rethrow_metta_file_error(_, Error) :- control_exception(Error), !,
                                      throw(Error).
rethrow_metta_file_error(_, Error) :- Error = error(_, context(_, _)), !,
                                      throw(Error).
rethrow_metta_file_error(Filename, error(Type, _)) :- !,
    throw(error(Type, context(Filename, 'while loading MeTTa file'))).
rethrow_metta_file_error(_, Error) :- throw(Error).

%A .gz program reads through the engine's own zlib stream, any other path
%reads plain, so every consumer of MeTTa files, import! and the CLI
%included, accepts gzip-compressed source under its ordinary name. A
%corrupt archive names the file, not the anonymous stream inside it.
read_metta_source(Filename, S) :-
    ( file_name_extension(_, gz, Filename)
      -> catch(setup_call_cleanup(gzopen(Filename, read, In),
                                  read_string(In, _, S),
                                  close(In)),
               error(Type, _),
               throw(error(Type, context(Filename,
                                         'while reading gzip-compressed MeTTa source'))))
    ; read_file_to_string(Filename, S, []) ).

%Extract function definitions, call invocations, and S-expressions part of &self space:
process_metta_string(S, Results) :- process_metta_string(S, Results, '&self').
process_metta_string(S, Results, Space) :- string_codes(S, Cs),
                                           strip(Cs, outside, Codes),
                                           phrase(top_forms(Forms, 1), Codes),
                                           maplist(parse_form, Forms, ParsedForms),
                                           maplist(process_form(Space), ParsedForms, ResultsList), !,
                                           append(ResultsList, Results).

%First pass to convert MeTTa to Prolog Terms and register functions:
parse_form(form(S), parsed(T, S, Term)) :- sread(S, Term),
                                           ( Term = [=, [F|W], _], atom(F) -> register_fun(F), length(W, N), Arity is N + 1, register_arity(F, Arity), T=function
                                                                            ; T=expression ).
parse_form(runnable(S), parsed(runnable, S, Term)) :- sread(S, Term).

%Second pass to compile / run / add the Terms:
process_form(Space, parsed(expression, _, Term), []) :- 'add-atom'(Space, Term, true),
                                                        ( silent(true) -> true ; swrite(Term,STerm),
                                                                                 ansi_format([fg(yellow)], "--> metta sexpr -->~n", []),
                                                                                 ansi_format([fg(cyan)], "~w~n", [STerm]),
                                                                                 ansi_format([fg(yellow)], "^^^^^^^^^^^^^^^^^^^~n", []) ).
process_form(Space, parsed(runnable, FormStr, Term), Result) :- space_module(Space, Module),
                                                            with_metta_module(Module, translate_expr([collapse, Term], Goals, Result)),
                                                            ( silent(true) -> true ; ansi_format([fg(yellow)], "--> metta runnable  -->~n", []),
                                                                                     ansi_format([fg(cyan)], "!~w~n", [FormStr]),
                                                                                     ansi_format([fg(yellow)], "-->  prolog goal  -->", []),
                                                                                     ansi_format([fg(magenta)], " ~n", []),
                                                                                     forall(member(G, Goals),
                                                                                            ansi_format([fg(magenta)], "~@", [portray_clause((:- G))])),
                                                                                     ansi_format([fg(yellow)], "^^^^^^^^^^^^^^^^^^^^^^^~n", []) ),
                                                            call_goals_in(Module, Goals).
process_form(Space, parsed(function, FormStr, Term), []) :- add_sexp(Space, Term),
                                                            Term = [=, [F|_], _],
                                                            space_module(Space, Module),
                                                            register_fun_in(Module, F),
                                                            with_metta_module(Module, translate_clause(Term, Clause)),
                                                            assertz(Module:Clause, Ref),
                                                            assertz(translated_from(Ref, Term)),
                                                            forall(metta_on_function_changed(F), true),
                                                            ( silent(true) -> true ; ansi_format([fg(yellow)], "--> metta function -->~n", []),
                                                                                     ansi_format([fg(cyan)], "~w~n", [FormStr]),
                                                                                     ansi_format([fg(yellow)], "--> prolog clause -->~n", []),
                                                                                     clause(Head, Body, Ref),
                                                                                     ( Body == true -> Show = Head; Show = (Head :- Body) ),
                                                                                     ansi_format([fg(green)], "~@", [portray_clause(current_output, Show)]),
                                                                                     ansi_format([fg(yellow)], "^^^^^^^^^^^^^^^^^^^^^^~n", []) ).
process_form(_, In, _) :-
    throw(error(petta_translation_failed(In),
                context(process_form/3, 'could not translate MeTTa form'))).

%Like blanks but counts newlines:
newlines(C0, C2) --> blanks_to_nl, !, {C1 is C0+1}, newlines(C1,C2).
newlines(C, C) --> blanks.

%Collect characters until all parentheses are balanced (depth 0), accumulating codes, and also counting newlines:
grab_until_balanced(D, Acc, Cs, LC0, LC2, State) --> [C],
    { string_state(State, C, State1),
      ( State = outside -> ( C=0'( -> D1 is D+1
                                  ; C=0') -> D1 is D-1
                                           ; D1 = D )
                        ; D1 = D ),
      Acc1=[C|Acc],
      ( C=10 -> LC1 is LC0+1 ; LC1 = LC0 ) },
    ( { D1=:=0, State1=outside } -> { reverse(Acc1,Cs), LC2 = LC1 }
                                    ; grab_until_balanced(D1,Acc1,Cs,LC1,LC2,State1) ).

%Read a balanced (...) block if available, turn into string, then continue with rest, ignoring comments:
top_forms([],_) --> blanks, eos.
top_forms([Term|Fs], LC0) --> newlines(LC0, LC1),
                              ( "!" -> {Tag = runnable} ; {Tag = form} ),
                              ( "(" -> [] ; string_without("\n", Rest), { format(atom(Msg), "expected '(' or '!(', line ~w:~n~s", [LC1, Rest]), throw(error(syntax_error(Msg), none)) } ),
                              ( grab_until_balanced(1, [0'(], Cs, LC1, LC2, outside)
                                -> { true } ; string_without("\n", Rest), { format(atom(Msg), "missing ')', starting at line ~w:~n~s", [LC1, Rest]), throw(error(syntax_error(Msg), none)) } ),
                              { string_codes(FormStr, Cs), Term =.. [Tag, FormStr] },
                              top_forms(Fs, LC2).
