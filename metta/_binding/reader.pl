% Purpose: parse source and decode prepared evaluation targets.
% Assumes: loaded through _binding/shim.pl in its host module.
% Owns resources: reader token registrations until metta_py_unregister_token/1 removes them
% [source: extensions/python/metta/_binding/reader.pl:35; commit=WORKTREE].

%%%%%%%%%% Parse and print %%%%%%%%%%

%Read one form into a tagged term, keeping variable names. sread/2 discards the
%name map its own DCG builds; calling sexpr//3 directly keeps it:
metta_py_parse(Source, Tagged) :-
    metta_py_read_form(Source, Term, VarMap),
    metta_py_encode_named(Term, VarMap, Tagged).

%The reader half of metta_py_parse/2, on its own. An evaluation handed source
%text needs the TERM, and reaching it through the wire form costs an encode
%and a decode of a term that never left the engine, on top of the second janus
%crossing Python makes to parse before it evaluates [measured 2026-08-16:
%(structured (pair a b)) cost 516.00 inferences as parse-then-evaluate and
%449.00 read straight to a term].
metta_py_read_form(Source, Term, VarMap) :-
    ( string(Source) -> S = Source ; atom_string(Source, S) ),
    ( sread_with_names(S, Term, VarMap)
      -> true
    ; format(atom(Msg), 'Parse error in form: ~w', [S]),
      metta_py_raise(syntax, Msg) ).

%Registering a token stores the callable itself in the engine's mapping. The
%dynamic clause's Janus blob owns its Python reference, so there is no Python
%registry to synchronize; Prolog's normal clause and blob reclamation owns a
%retired constructor's lifetime.
metta_py_register_token(Pattern, Constructor) :-
    seam:host_object(Constructor),
    metta_host_register_reader_token(Pattern, Constructor).

metta_py_unregister_token(Pattern) :-
    metta_host_unregister_reader_token(Pattern).

%Ownership is established by the live Python object before the cut implicit in
%the caller's first-success seam. Constructors receive the complete lexeme and
%return an Atom wire; shared decoding preserves repeated variables if a custom
%class deliberately constructs them.
seam:host_reader_token_construct(Constructor, Text, Term) :-
    seam:host_object(Constructor),
    catch(py_call(metta_ops:construct_token(Constructor, Text), Wire),
          Error, metta_py_failure(['reader-token', Text], Error)),
    metta_py_decode_shared(Wire, Term, _).

%An evaluation target arrives either as a wire term or, when the caller passed
%source text, as that text. The test is whether it is a wire term, not what
%type the text has: Janus hands a Python str over as an ATOM, so asking
%string/1 sent every source evaluation down the decoder, where it failed and
%findall/3 turned that into an empty answer list indistinguishable from a
%query that truly answered nothing. Reading it here also keeps the variables
%the reader shared by name, which is what the wire round trip was rebuilding.
%Every wire term is exactly two elements, so the shape is decided here in O(1)
%and the decode below is NOT wrapped in the test. Wrapping it, as an earlier
%version did to turn a failed decode into a refusal, left a choice point over
%the whole recursive walk and cost 11% of alpha-unique, whose operation
%decodes one large term: 3,699,768,516 instructions became 4,106,476,179
%[measured 2026-08-16]. That is the same last-call optimisation the plunit
%gate's own choicepoint check exists to catch.
%&self resolves to the evaluation receiver at both input doors. Text uses the
%reader rewrite, gated by a C substring probe so text without &self pays two
%inferences rather than a term walk. A wire target is decoded through the
%receiver-aware decoder above, which substitutes in the decode walk rather than
%walking the complete term again. metta_py_parse/2 has no receiver and still
%reads unpinned, as does stored data: this policy belongs only to execution
%targets.
metta_py_target_term(Space, Target, Term) :-
    metta_py_target_term_bindings(Space, Target, Term, _).

metta_py_target_term_bindings(Space, Target, Term, Bindings) :-
    (   Target = [_, _]
    ->  metta_py_decode_target(Space, Target, Term, Bindings)
    ;   \+ is_list(Target)
    ->  metta_py_read_form(Target, Term0, Bindings),
        (   Space == '&self'
        ->  Term = Term0
        ;   atom(Target), sub_atom(Target, _, _, _, '&self')
        ->  metta_substitute_self(Space, Term0, Term)
        ;   string(Target), sub_string(Target, _, _, _, "&self")
        ->  metta_substitute_self(Space, Term0, Term)
        ;   Term = Term0
        )
    ;   throw(error(domain_error(metta_py_wire_term, Target), none))
    ).
