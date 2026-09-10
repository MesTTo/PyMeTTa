% Purpose: expose source terms and locations for the binding interface checker.
% Guarantees: Janus zero-arity compounds, operators, variables and strings keep
% their distinct source shapes
% [tested: test_binding_source_keeps_call_shapes; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
% Owns resources: each source stream closes on success, failure and exception.

:- module(binding_source, [source_records/2]).
:- use_module(library(prolog_source),
              [prolog_open_source/2, prolog_close_source/1,
               prolog_read_source_term/4]).
:- use_module(library(janus)).
:- use_module(library(http/json), [json_write_dict/3]).
:- use_module(library(apply), [maplist/3]).

source_records(File, Records) :-
    % Use Janus syntax for included units, then track each file's directives.
    % prolog_source:read_directives_setup/4 uses the same source-module scope:
    % https://github.com/SWI-Prolog/swipl-devel/blob/V10.1.13/library/prolog_source.pl
    setup_call_cleanup(
        ( prolog_open_source(File, Stream),
          '$set_source_module'(Previous, binding_source) ),
        read_records(Stream, Records),
        ( '$set_source_module'(Previous), prolog_close_source(Stream) )).

read_records(Stream, Records) :-
    prolog_read_source_term(Stream, Term, _,
                           [subterm_positions(Position), syntax_errors(error)]),
    ( Term == end_of_file
    -> Records = []
    ; arg(1, Position, Start), arg(2, Position, End),
      numbervars(Term, 0, _),
      term_data(Term, Data),
      argument_ranges(Position, Arguments),
      Records = [_{start:Start, end:End, arguments:Arguments, term:Data}|Rest],
      read_records(Stream, Rest)
    ).

argument_ranges(term_position(_, _, _, _, Positions), Ranges) :- !,
    maplist(position_range, Positions, Ranges).
argument_ranges(_, []).

position_range(Position, [Start, End]) :-
    arg(1, Position, Start), arg(2, Position, End).

term_data('$VAR'(N), _{var:N}) :- !.
term_data(Term, _{string:Term}) :- string(Term), !.
term_data([], []) :- !.
term_data(Term, [Label|Data]) :- compound(Term), !,
    compound_name_arguments(Term, Name, Arguments),
    ( atom(Name) -> atom_string(Name, Label) ; term_string(Name, Label) ),
    maplist(term_data, Arguments, Data).
term_data(Term, Text) :- atom(Term), !, atom_string(Term, Text).
term_data(Term, Term) :- number(Term), !.
term_data(Term, _{literal:Text}) :- term_string(Term, Text, [quoted(true)]).

file_data(File, _{file:File, records:Records}) :- source_records(File, Records).

main :-
    current_prolog_flag(argv, Files),
    maplist(file_data, Files, Data),
    json_write_dict(current_output, Data, [width(0)]), nl.

:- initialization(main, main).
