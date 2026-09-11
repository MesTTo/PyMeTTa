% Purpose: read a library's exported PlDoc interfaces without loading its code.
% Guarantees: source initializers never run and public declarations retain
% argument names, types and answer multiplicity in their metadata
% [tested: tests/checks/check_prologface_selftest.py; commit=9b22993447a5ddba93643895e3025661ba9f693e].
% Owns resources: prolog_xref closes source streams; xref_clean/1 releases each
% source's metadata after its record is built.

:- module(prologface_source, [face_record/2]).
:- use_module(library(prolog_xref),
              [xref_source/2, xref_module/2, xref_exported/2,
               xref_comment/4, xref_mode/3, xref_clean/1]).
:- use_module(library(pldoc/doc_process), [is_structured_comment/2]).
:- use_module(library(pldoc/doc_modes), [process_modes/6]).
:- use_module(library(pldoc/doc_wiki), [indented_lines/3]).
:- use_module(library(http/json), [json_write_dict/3]).
:- use_module(library(apply), [maplist/3]).
:- use_module(library(lists), [member/2]).

% PlDoc already parses names, operators and typed modes. Its source reader
% records directives without running the library's initialization goals.
% https://github.com/SWI-Prolog/swipl-devel/blob/V10.1.13/library/prolog_xref.pl
face_record(File, Record) :-
    setup_call_cleanup(
        xref_source(File, [silent(false), comments(collect)]),
        source_record(File, Record),
        xref_clean(File)).

source_record(File, Record) :-
    ( xref_module(File, Module) -> true ; Module = '' ),
    findall(Name/Arity,
            (xref_exported(File, Head), functor(Head, Name, Arity)), Exports0),
    sort(Exports0, Exports),
    maplist(export_record(File, Module), Exports, Entries),
    ( xref_mode(File, _, _) -> Described = true ; Described = false ),
    Record = _{source:File, module:Module, described:Described, exports:Entries}.

export_record(File, Module, Name/Arity, Record) :-
    functor(Head, Name, Arity),
    (   xref_comment(File, Head, _, Comment)
    ->  comment_data(Comment, Module, File, Modes, Body),
        ( private_document(Body)
        -> Record = _{name:Name, arity:Arity, private:true, modes:[], doc:Body}
        ;  findall(Data, mode_record(Modes, Name, Arity, Data), Data0),
           sort(Data0, Data),
           Record = _{name:Name, arity:Arity, private:false, modes:Data, doc:Body}
        )
    ;   Record = _{name:Name, arity:Arity, private:false, modes:[], doc:""}
    ).

comment_data(Comment, Module, File, Modes, Body) :-
    is_structured_comment(Comment, Prefixes),
    string_codes(Comment, Codes),
    indented_lines(Codes, Prefixes, Lines),
    process_modes(Lines, Module, File:0, Modes, _, Rest),
    maplist(comment_line, Rest, TextLines),
    atomics_to_string(TextLines, '\n', Text),
    normalize_space(string(Body), Text).

comment_line(_-Codes, Line) :- string_codes(Line, Codes).

private_document(Body) :-
    split_string(Body, " \t\n", " \t\n", Words),
    member("@private", Words).

mode_record(Modes, Name, Arity, Data) :-
    member(mode(Declared, Bindings), Modes),
    ( Declared = (Head0 is Det) -> true ; Head0 = Declared, Det = unknown ),
    ( Head0 = _Module:Head -> true ; Head = Head0 ),
    callable(Head), functor(Head, Name, Arity),
    Head =.. [_|Arguments],
    maplist(argument_record(Bindings), Arguments, Args),
    Data = _{determinism:Det, args:Args}.

argument_record(Bindings, Declared, Record) :-
    ( compound(Declared), Declared =.. [Mode0, Typed], mode_indicator(Mode0)
    -> Mode = Mode0
    ;  Mode = '?', Typed = Declared
    ),
    ( nonvar(Typed), Typed = Variable:Type0
    -> Type = Type0, Explicit = true
    ;  Variable = Typed, Type = any, Explicit = false
    ),
    ( member(Label=Original, Bindings), Original == Variable
    -> true
    ;  atom(Variable) -> Label = Variable
    ;  Label = ''
    ),
    term_string(Type, TypeText, [quoted(true)]),
    Record = _{name:Label, mode:Mode, type:TypeText, explicit:Explicit}.

mode_indicator('+').
mode_indicator('++').
mode_indicator('-').
mode_indicator('--').
mode_indicator('?').
mode_indicator(':').
mode_indicator('@').
mode_indicator('!').

main :-
    current_prolog_flag(argv, Files),
    maplist(face_record, Files, Records),
    json_write_dict(current_output, Records, [width(0)]), nl.

:- initialization(main, main).
