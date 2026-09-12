% Purpose: save, load, digest and attribute persisted spaces.
% Assumes: loaded through _binding/shim.pl in its host module.
% Guarantees: source and program views use the engine's authored occurrences
%   and graph relocation [tested: test_convert_imports_a_python_program_and_round_trips_its_source;
%   commit=WORKTREE].

metta_py_source_atoms(Space, Wires) :-
    metta_host_source_atoms(Space, Atoms),
    maplist(metta_py_encode, Atoms, Wires).

metta_py_program_source(Space, Result) :-
    metta_host_program_source(Space, Outcome),
    metta_py_persist_result(Outcome, Result).

%%%%%%%%%% Trusted fast cache I/O %%%%%%%%%%
%
%One fast_write carries the whole atom list. The text header pins both this
%container contract and the SWI release whose private term encoding produced
%the payload. Python validates it before calling the reader, and this section
%checks it again on the same stream before fast_read can see any payload byte.

%The fast cache and the digest are engine machinery now, the host run and
%load surface in engine/filereader.pl: this side maps the term outcomes to
%the wire and answers the ONE host question the engine asks through the
%seam:host_object/1 seam, whether a term is a live Python object (the
%bridge contributes that clause). Results: object(Atom) and symbol(Atom)
%name a refusing offender; saved(Count), digest(Hash) and program(Term) land.

%The first atom in a space with no round-trip text spelling, so a host
%validating a save asks the grammar instead of keeping a second copy of its
%rules, which is how the host's copy came to miss three classes.
%
%This asked about the atoms' NAMES until 2026-08-19 and so missed a fourth
%class, which is not a name at all: a number whose printed form is not read
%back as that number. A space holding `(py-atom "float('inf')")`'s answer saved
%to a .metta file and loaded back came back holding the SYMBOL of that
%spelling, silently [measured 2026-08-19]. metta_unwritable_symbol/2 is the
%grammar's own answer about a whole atom, one of the four text services in
%engine/ext_points.pl, and it is the same question metta_py_fast_save/3 and
%metta_py_digest/2 below already ask.
metta_py_unwritable_atom(Space, Bad) :-
    'get-atoms'(Space, Atom),
    metta_unwritable_symbol(Atom, Unwritable), !,
    metta_py_encode(Unwritable, Bad).

%One boolean crossing for consumers that must validate a name before they
%mutate host state. The parser remains the authority, including reader token
%classes registered after startup.
metta_py_symbol_writable(Name, '@'(true)) :- metta_symbol_writable(Name), !.
metta_py_symbol_writable(_, '@'(false)).

%A refusal witness for a host error. Testing each one-character spelling
%against the grammar finds a delimiter or reserved literal opener without a
%second delimiter table; when only the whole token is reserved (True or a
%registered token class), its first character locates the competing token.
metta_py_symbol_refusal(Name0, Refusal) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    \+ metta_symbol_writable(Name),
    metta_py_symbol_refusal_detail(Name, Refusal).

metta_py_symbol_refusal_detail('', [empty]) :- !.
metta_py_symbol_refusal_detail(Name, [token, Character]) :-
    atom_string(Name, Text),
    metta_reader_token_source(Text, custom),
    atom_codes(Name, [First|_]),
    atom_codes(Character, [First]),
    !.
metta_py_symbol_refusal_detail(Name, [character, Character]) :-
    atom_codes(Name, Codes),
    member(Code, Codes),
    atom_codes(Character, [Code]),
    \+ metta_symbol_writable(Character),
    !.
metta_py_symbol_refusal_detail(Name, [token, Character]) :-
    atom_codes(Name, [First|_]),
    atom_codes(Character, [First]).

metta_py_fast_save(File, Space, Result) :-
    metta_host_save_fast(File, Space, Outcome),
    metta_py_persist_result(Outcome, Result).

binding_forward(metta_py_fast_load/2).
metta_py_persist_result(object(Atom), ["object", Encoded]) :- !,
    metta_py_encode(Atom, Encoded).
metta_py_persist_result(symbol(Atom), ["symbol", Encoded]) :- !,
    metta_py_encode(Atom, Encoded).
metta_py_persist_result(saved(Count), ["saved", Count]) :- !.
metta_py_persist_result(program(Program), ["program", Encoded]) :- !,
    metta_py_encode(Program, Encoded).
metta_py_persist_result(digest(Hash), ["digest", Hash]).

%%%%%%%%%% Content digest %%%%%%%%%%
%
%A space's content as one sha256: each atom canonicalized (fresh copy,
%numbered variables, quoted write) so alpha-equivalent equations print
%identically in every process, the lines multiset-sorted so insertion
%order cannot matter, then hashed as one utf8 document. Live objects
%print by address and are refused, the save contract.

metta_py_digest(Space, Result) :-
    metta_host_digest(Space, Outcome),
    metta_py_persist_result(Outcome, Result).

metta_py_blame(Space, Wire, Rows) :-
    metta_py_decode_shared(Wire, Pattern, _),
    metta_host_blame(Space, Pattern, Tokens),
    maplist(metta_py_encode, Tokens, Rows).
