% Purpose: encode, decode and share tagged terms and answer forms.
% Assumes: loaded through _binding/shim.pl in its host module.

%%%%%%%%%% Wire encoding %%%%%%%%%%
%
% janus maps both a Prolog atom and a Prolog string to a Python str, and maps
% the booleans to strings too, so a bare term crossing the boundary loses its
% metatype. Every term crosses tagged instead: ["s",Name] symbol, ["g",Text]
% string, ["n",N] Number or BigInt, ["b",true|false] boolean,
% ["v",Name] variable, ["e",[...]] expression, ["p",Name] space reference,
% ["o",Ref] Python object reference. The tag list itself is nested lists, which janus converts
% natively in both directions.

%Encode a Prolog term as a tagged wire term:
%The clauses are mutually exclusive and every one of them cuts, so their order
%is a pure COST decision, and py_is_object/1 was in the wrong place: it is a
%foreign call into janus and it ran on every argument, and on every ELEMENT of
%every list, before anything asked whether the value was a number. It costs 915
%instructions where number/1 and string/1 are VM instructions costing nothing
%measurable [measured 2026-08-17, 3,000,000 iterations, min of 3: 1,765,021,710
%for the bare loop, 4,510,067,594 with py_is_object/1, 2,914,057,131 with
%blob/2]. Moving it behind the free tests is worth most on exactly the argument
%shape the encoded path is worst at, since a 64-item list paid it 64 times.
%
%Sound because a janus reference satisfies NONE of the tests now in front of
%it: it is atomic and not atom, number, string, is_list, compound or callable
%[measured 2026-08-17 against py_call(builtins:object(), Obj), blob type py].
%That is the same fact get_type_candidate/2 relies on where it writes
%`atomic(X), \+ atom(X), python_object_blob(X)` to keep ordinary values out of
%janus. Nothing else about the encoding moves; the relative order of every
%other clause is unchanged.
%The wire name is an IDENTITY, never a display name: the same cell must
%encode the same on every crossing, and two different cells must never
%collide, so the source-name attribute (metta_var_name) deliberately does
%NOT reach here. Sending it was measured breaking round-trip identity
%(a variable through a registered op stopped unifying home) and aliasing
%distinct answer variables that shared a spelling.
%A wire name is FIRST-OCCURRENCE POSITIONAL, the numbering engine/writer.c
%and numbervars/3 already give a term's variables. It used to be the printed
%form, and SWI prints an unbound variable as its STACK OFFSET:
%  if (p > (Word) lBase) iref = ((Word)p - (Word)lBase)*2+1;
%  else                  iref = ((Word)p - (Word)gBase)*2;
%  Ssprintf(name, "_%lld", (int64_t)iref);
%[source: swipl-9.3.33/src/pl-write.c:127-140, var_name_ptr()]. An offset
%moves when the cell moves and is handed to whatever lands there next, so the
%spelling broke this contract in both directions: one cell answered _9162
%before a collection and _32 after [measured 2026-08-31], which crossed one
%variable under two names, and a reused offset gives two variables one name.
%A five-deep (fact 5) proof crossed as
%  (= (fact $_17642) (if (> $_17642 0) (* $_17642 (fact (- $_2528 1))) 1))
%whose free $_2528 is not the variable the head binds.
%
%The map is THREADED rather than pre-built, so a term holding no variable
%pays only for passing it and a name is minted the first time its cell is
%met. metta_py_encode/2 remains the door every caller uses.
metta_py_encode(Term, Wire) :- metta_py_encode(Term, [], _, Wire).

metta_py_encode(T, N0, N, ["v", Name]) :- var(T), !, metta_py_wire_name(T, N0, N, Name).
metta_py_encode(T, N, N, ["n", T])    :- number(T), !.
metta_py_encode(T, N, N, ["g", T])    :- string(T), !.
metta_py_encode(T, N, N, ["b", T])    :- ( T == true ; T == false ), !.
%WHICH QUESTION THE `p` TAG ASKS, asked of the engine rather than answered
%here. `p` is a SPECIES tag: what it decodes into is a Space where `s` decodes
%into a Symbol, so the question is the engine's own species question, which is
%metta_space_operand/1 and which get_type_candidate/2 asks for the same set
%[source: engine/metta/types.pl, get_type_candidate(X, 'SpaceType') :-
%atom(X), metta_space_operand(X)]. It is NOT get-metatype, which since
%2026-09-05 answers upstream PeTTa's question instead, whether the engine
%holds a FUNCTION of the name, and calls `&self` a Symbol
%[source: PeTTa@43705f5d src/metta.pl:202]. The wire and the metatype answer
%different questions about a space and both are right about their own.
%
%The pair '&self' and '&metta' used to be written out here, which tagged
%exactly two names, so a space !(new-space) had just made crossed as an
%ordinary symbol and Python could not use it as a space
%[measured 2026-08-27: &metta-space-1 encoded ["s", "&metta-space-1"] while
%being listed by metta_space_names/1 and answering Grounded to get-metatype].
%
%NOT metta_space_name/1, the WIDER test that is-space/2 answers. That one is
%about operand admissibility, not species: it accepts any ampersand name
%because a space is created on demand, so it calls '&bar' a space where
%get-type answers %Undefined%, and it calls a State cell a space too
%[measured 2026-09-05: metta_space_name('&state-#0') is true and get-type
%answers (StateMonad Number) for the same atom]. Tagging either as `p` would
%make the wire disagree with the language in the one dimension the tag
%encodes.
%
%NOT metta_space_names/1 either, which is the same set as a sorted LIST:
%two findalls, an append and a sort per call where this is one indexed lookup.
%
%atom(T) first because the wire's `p` payload is TEXT (CODEC.md), while
%metta_space_operand/1 also accepts a PARAMETRIC space, which is a compound
%and crosses as the expression it is. The order is this file's cost rule: the
%test costs 6 inferences on an ordinary symbol and 5 on '&self'
%[measured 2026-08-27, 100,000 iterations against a bare loop of 100,002:
%700,002 for a non-space atom, 600,002 for '&self'].
metta_py_encode(T, N, N, ["p", S]) :- atom(T), metta_space_operand(T), !, atom_string(T, S).
metta_py_encode(T, N, N, ["s", S])    :- atom(T), !, atom_string(T, S).
metta_py_encode(T, N, N, ["o", T])    :- py_is_object(T), !.
metta_py_encode(T, N0, N, ["e", Es])  :- is_list(T), !, metta_py_encode_each(T, N0, N, Es).
metta_py_encode([H|T], N0, N, ["e", [["s", "cons"], EH, ET]]) :- !,
    metta_py_encode(H, N0, N1, EH),
    metta_py_encode(T, N1, N, ET).
%Janus's default tuple translation is -/N. It is the carrier for a structural
%MeTTa expression here, not a callable named `-`; a Grounded tuple never
%reaches this clause because its Python reference is claimed above.
metta_py_encode(T, N0, N, ["e", Es]) :-
    metta_py_tuple_arguments(T, Raw), !,
    maplist(metta_py_result, Raw, Elements),
    metta_py_encode_each(Elements, N0, N, Es).
%A non-list compound encodes as (f a b). compound_name_arguments/3 rather
%than =../2, because =.. RAISES on a ZERO-ARITY compound and janus hands us
%one for every empty Python tuple: py_call(builtins:tuple(), X) binds X to
%-() [measured 2026-08-18]. That reached here as
%`Domain error: compound_non_zero_arity expected, found -()` out of an
%ordinary Python return value, ''.split() of an empty string among them,
%and only through the LIBRARY: the engine has its own writer and never ran
%this clause [tested: test_wire_round_trip].
%
metta_py_encode(T, N0, N, ["e", [["s", FS] | Es]]) :-
    compound(T),
    compound_name_arguments(T, F, Args),
    atom(F), !,
    atom_string(F, FS),
    metta_py_encode_each(Args, N0, N, Es).
%Anything else (a blob, a dict) is carried as text, the printer's last resort:
%A native handle (a C blob) crosses as a registry reference plus its own
%printed text, so Python holds it opaquely and can hand back the very
%same blob: identity, not a serialisation. It used to fall through to
%the term_string clause below, which silently stringified it and made
%the round trip impossible: 'vector-length' on what came back saw a
%string [measured 2026-08-17]. The clause sits HERE, at the tail, so
%only a term every other clause refused pays the blob/2 probe: placed
%before the list clauses it taxed every encoded list node, and SWI's []
%is itself a reserved non-text blob, so it also registered every () as
%a handle, caught by the wire round-trip property over Expr('()'). A
%blob is atomic, so nothing above claims one: atom/1 is false for
%non-text blobs, and the compound clause needs compound/1.
metta_py_encode(T, N, N, ["h", Id, S]) :- blob(T, Type), Type \== text, T \== [], !,
    metta_py_handle_keep(T, Id),
    term_string(T, S).
metta_py_encode(T, N, N, ["g", S]) :- term_string(T, S).

metta_py_encode_each([], N, N, []).
metta_py_encode_each([T|Ts], N0, N, [E|Es]) :-
    metta_py_encode(T, N0, N1, E),
    metta_py_encode_each(Ts, N1, N, Es).

%The name this cell already has, or a fresh one. Compared by ==, because
%identity of a Prolog variable is only answerable by comparison
%[source: engine/writer.c, METTA_WRITER_VARS], which is why this scan and
%writer.c's are both linear in the count of DISTINCT variables a term holds.
metta_py_wire_name(Variable, Names0, Names, Name) :-
    (   metta_py_var_name(Names0, Variable, Found)
    ->  Names = Names0,
        atom_string(Found, Name)
    ;   metta_py_fresh_name(Names0, Fresh),
        Names = [Fresh-Variable|Names0],
        atom_string(Fresh, Name)
    ).

%A fresh name comes from a SESSION counter, not from this term's own count.
%Both halves of the contract have to hold at once and they pull apart:
%  - within a crossing, one cell is one name, which is what the MAP gives and
%    what the printed form could not, because a collection moves the offset it
%    is made of;
%  - across crossings, two cells are never one name, which is what the COUNTER
%    gives. A host atom compares by spelling, so two variables answered by two
%    separate matches and then put in one expression would be one variable if
%    each crossing had started its own numbering at _0 [measured 2026-08-31:
%    `(p (f $x))` and `(p (g $y))` answered `(f $_0)` and `(g $_0)`].
%Numbering per term satisfies the first and breaks the second; the address did
%the reverse. gensym/2 is the counter the cut barriers below already use.
%
%The seeded names are stepped over: a caller may seed the map with the
%reader's own spellings, and $_3 is one a program is allowed to write.
metta_py_fresh_name(Names, Name) :-
    gensym('_', Candidate),
    (   memberchk(Candidate-_, Names)
    ->  metta_py_fresh_name(Names, Name)
    ;   Name = Candidate
    ).

%Encode with an explicit Name-Var list, so parsed variables keep their names.
%The list SEEDS the same map every encode threads, so a variable the seed
%does not name is minted beside the named ones rather than through a second
%naming rule that could disagree with them.
metta_py_encode_named(T, Pairs, W) :- metta_py_encode(T, Pairs, _, W).

%Every argument of one call under ONE map, and the map itself, because the
%reply is decoded against it. Encoding argument by argument would restart the
%numbering at each one, so two DISTINCT variables in two arguments would both
%be named _0 and the decoder would share them into one.
metta_py_encode_arguments(Arguments, Encoded, Names) :-
    metta_py_encode_each(Arguments, [], Names, Encoded).

metta_py_var_name([N-V|_], T, N) :- V == T, !.
metta_py_var_name([_|Pairs], T, N) :- metta_py_var_name(Pairs, T, N).

%A tag arrives back as an atom or a string depending on the sender; accept both:
metta_py_tag(T, T) :- atom(T), !.
metta_py_tag(T, A) :- string(T), atom_string(A, T).

%A HOST ANSWER read as a boolean: a Python predicate answers whatever it
%answers and everything that is not one of the true spellings is false, the
%truthiness reading. This is for a RETURN VALUE, not for a wire payload; the
%b tag has its own strict reader below, because a payload the grammar does
%not admit is a malformed term and turning it into `false` would answer a
%question nobody asked.
metta_py_bool(B, true)  :- B == true, !.
metta_py_bool(B, false) :- B == false, !.
metta_py_bool(B, true)  :- B == '@'(true), !.
metta_py_bool(B, false) :- B == '@'(false), !.
metta_py_bool(B, true)  :- B == "true", !.
metta_py_bool(_, false).

%The b tag's payload, and nothing else. Facts rather than a chain of ==/2
%with cuts, so first-argument indexing decides in one step and an
%inadmissible payload has no clause to fall into.
metta_py_wire_bool(true,       true).
metta_py_wire_bool(false,      false).
metta_py_wire_bool('@'(true),  true).
metta_py_wire_bool('@'(false), false).
metta_py_wire_bool("true",     true).
metta_py_wire_bool("false",    false).

%Decode a tagged wire term; every v tag becomes its own fresh variable.
%
%The tag decides the clause, so it is normalised once and dispatched on.
%Asking metta_py_tag/2 whether the tag is o, then s, then g, then n, walks
%that list of alternatives and re-runs atom/1 and string/1 at every step,
%which is how deciding that ['n',1] holds a number came to cost nine
%inferences. Every Python term crossing into the engine is decoded this way,
%so the walk was on the query path, the run path and the eval path alike
%[measured 2026-08-16: (m6f 1) evaluated from Python, 72.00 inferences to
%63.00 and 5.45us to 4.98us, of which the wire term's own decode fell 22.00
%to 13.00 and a single number leaf 9.00 to 4.00].
metta_py_decode([T0|Rest], Term) :-
    ( atom(T0) -> T = T0 ; string(T0) -> atom_string(T, T0) ),
    metta_py_decode_(T, Rest, Term).

metta_py_decode_(o, [Obj], Obj).
%A handle reference resolves to the registered blob itself. A stale id
%is an existence error naming it, never a fresh or empty value: the
%handle's release is explicit on the Python side, so reaching a released
%one is the caller's bug and silence would turn it into a wrong answer.
metta_py_decode_(h, [Id|_], Blob) :-
    (   metta_py_handle_store(Id, Blob)
    ->  true
    ;   throw(error(existence_error(metta_native_handle, Id),
                    context(metta_py_decode_/3,
                            'the handle was released or never issued')))
    ).
%Each payload is checked against the class its tag names, and a payload of
%another class has no decoding: the term is malformed and the decode fails,
%which is what every malformed shape above already did. Without the checks
%the tag was a label rather than a claim, and six payloads decoded to
%something instead: ["s",1] to the symbol '1', ["g",1] to "1", ["n","1/3"]
%to a string wearing the number tag, ["v",1] to a fresh variable, and
%["b",<anything>] to FALSE, which is the one that answers rather than fails
%[measured 2026-08-20, both spellings, against extensions/python/metta/_atoms/wire.py,
%which refuses all six]. A wire term is written by an encoder, so nothing
%conforming loses a shape here; what changes is that a boundary bug now
%reports as one [tested: shim_wire_decoding:a_payload_outside_its_tags_class_fails].
%Every check is a TYPE TEST WRITTEN OUT, never a call to a shared one, and
%that is a measurement rather than a preference: number/1, atom/1 and
%string/1 compile to VM instructions costing no inference, while a call to
%a predicate wrapping them costs one on a path that runs per leaf of every
%answer. Per-leaf inferences, before against after, as the atom payload /
%as the string payload, both being spellings janus delivers
%[measured 2026-08-20, 10,000 decodes each, three runs identical]:
%
%  s        4.00/5.00  ->  3.00/5.00     g   4.00/4.00  ->  4.00/4.00
%  v        3.00/4.00  ->  3.00/4.00     n   4.00       ->  4.00
%  v shared 8.00/10.00 ->  8.00/10.00    b   4.00/8.00  ->  4.00/5.00
%
%Faster or equal on every tag and every spelling: the boolean payload
%replaced a chain of ==/2 with indexed facts, and the symbol payload stopped
%calling atom_string/2 on an atom that already is the symbol.
%
%A shared metta_py_wire_text/1 helper was written first and cost +1.00 on s
%and on v, which the alpha-unique benchmark saw as +1.54% and the counter
%gate refused. The A/B behind it had measured zero and was wrong: its
%synthetic term held 1000 s, 500 v and 500 b leaves, whose +1000 +500 -1500
%cancels exactly. A per-tag change needs a per-tag measurement.
metta_py_decode_(s, [S], A)     :- ( atom(S) -> A = S ; string(S), atom_string(A, S) ).
metta_py_decode_(g, [S], Str)   :- ( string(S) -> Str = S ; atom(S), atom_string(S, Str) ).
metta_py_decode_(n, [N], N)     :- number(N).
metta_py_decode_(b, [B], A)     :- metta_py_wire_bool(B, A).
metta_py_decode_(v, [Name], _)  :- ( atom(Name) -> true ; string(Name) ).
metta_py_decode_(e, [Es], Term) :- maplist(metta_py_decode, Es, Term).
%A p payload is a space NAME, and any symbol a host writes through is one: a
%space operation is built as `Term =.. [Space, Rel|Args]`, so
%`(= (space) my_space_name)` with a write through it registers `my_space_name`
%and metta_space_names/1 lists it [source: engine/spaces/catalog.pl,
%metta_space_writable_name/1, which accepts any atom; commit=de8c99f0a6deedfc00e2a9fcb100e5ac3025d9be]. The
%ampersand is how the engine SPELLS the spaces it mints, not a rule of the tag,
%and demanding it here refused a name the engine's own registry had handed
%out: a host that opened one and sent it back lost the whole term, because a
%leaf that does not decode fails the decode of everything containing it. The
%Node seat carried the same demand in its own decoder and dropped it on
%2026-09-07; this clause was the opposite ruling on the other seat
%[source: extensions/node/bridge.pl, metta_node_decode_/5's p clause;
%commit=de8c99f0a6deedfc00e2a9fcb100e5ac3025d9be].
%
%The decode is the s tag's, and costs what it costs: -1.00 inference per p
%leaf in both payload spellings, the sub_atom/5 that is gone
%[measured 2026-09-07 by the per-tag protocol the paragraph above records,
%10,000 decodes minus a bare loop of the same count, three identical runs:
%atom 3.00 -> 2.00, string 4.00 -> 3.00, and a BARE name went from 4.00/5.00
%spent failing to the same 2.00/3.00; fixture=the probe recorded in
%docs/journal/2026-09-07-a-bare-name-poisons-the-plane.md;
%commit=de8c99f0a6deedfc00e2a9fcb100e5ac3025d9be]. Every other tag is untouched and measured so
%[tested: shim_wire_decoding:every_tag_decodes,
%shim_wire_decoding:a_bare_space_name_decodes_like_a_symbol; commit=de8c99f0a6deedfc00e2a9fcb100e5ac3025d9be].
metta_py_decode_(p, [S], Space) :-
    ( atom(S) -> Space = S ; string(S), atom_string(Space, S) ).

% Index names once per term and retain the ordered answer bindings.
% library(hashtable) uses backtrackable updates, so failure rolls back both
% the index and the term. The existing wide-query decoder owns that frame
% [source: extensions/python/metta/_binding/wire.pl:428;
% commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
metta_py_decode_shared(Tagged, Term, Bindings) :-
    metta_py_decode_shared_(Tagged, Term, indexed([], Index), indexed(Bindings, Index)).

metta_py_decode_shared_([T0|Rest], Term, B0, B) :-
    ( atom(T0) -> T = T0 ; string(T0) -> atom_string(T, T0) ),
    metta_py_decode_shared_tagged(T, Rest, Term, B0, B).

%Only v and e differ from the plain decode: one shares a variable by name and
%the other has to thread the bindings through its elements. Every leaf below
%them carries no bindings, so it is the plain decode with B unchanged.
metta_py_decode_shared_tagged(v, [Name0], Var,
                              indexed(B0, Index), indexed(B, Index)) :- !,
    ( string(Name0) -> atom_string(Name, Name0) ; atom(Name0), Name = Name0 ),
    ( Name == '_' -> Var = _, B = B0
    ; metta_py_index_variable(Name, Var, B0, B, Index) ).
metta_py_decode_shared_tagged(v, [Name0], Var, Table, B) :- !,
    %The atom branch carries the payload check with it: a name arriving as
    %anything but text has no identity to share by, and testing it here
    %rather than ahead of the table keeps the check on a branch that was
    %already being taken.
    ( string(Name0) -> atom_string(Name, Name0) ; atom(Name0), Name = Name0 ),
    %The anonymous variable is fresh at every occurrence and never binds,
    %exactly as the reader treats $_ in source; recording it would make two
    %underscores constrain each other.
    ( Name == '_' -> Var = _, B = Table
    ; memberchk(Name-Shared, Table) -> Var = Shared, B = Table
    ; B = [Name-Var|Table] ).
metta_py_decode_shared_tagged(e, [Es], Term, B0, B) :- !,
    foldl_decode(Es, Term, B0, B).
metta_py_decode_shared_tagged(T, Rest, Term, B, B) :-
    metta_py_decode_(T, Rest, Term).

% The existing pair answers a singleton lookup without a hash allocation.
% On the second distinct name, move that first binding into the index once.
% A supplied wide-query index remains complete even for a singleton query
% [tested: shared_decode_index; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
metta_py_index_variable(Name, Var, [], [Name-Var], Index) :- !,
    ( var(Index) -> true ; ht_put(Index, Name, Var) ).
metta_py_index_variable(Name, Var, B0, B, Index) :-
    B0 = [First-Shared|_],
    (   Name == First
    ->  Var = Shared, B = B0
    ;   ( var(Index) -> ht_new(Index), ht_put(Index, First, Shared) ; true ),
        ( ht_get(Index, Name, Known) -> Var = Known, B = B0
        ; ht_put(Index, Name, Var), B = [Name-Var|B0] )
    ).

foldl_decode([], [], B, B).
foldl_decode([E|Es], [T|Ts], B0, B) :-
    metta_py_decode_shared_(E, T, B0, B1),
    foldl_decode(Es, Ts, B1, B).

%Decode an evaluation target in its receiver context. The ordinary &self
%receiver takes the exact hot decoder above. A named receiver uses the same
%single decode walk and replaces either ["s","&self"] written by an Atom
%builder or ["p","&self"] returned by parse. The reserved name is contextual
%inside an execution target even though p remains an executable handle in
%stored data and through the ordinary codec.
%Doing the replacement during decode avoids the second O(n) term walk that
%formerly cost alpha-unique about 400k inferences, while still preserving the
%shared variable table [source:
%extensions/python/benchmarks/target_self_decode.py;
%commit=f8453b013a603de9f9d4c7606c95ca7210229e78]. The
%replacement walk is linear; variable identity uses the same index as the
%ordinary decoder.
metta_py_decode_target('&self', Tagged, Term, Bindings) :- !,
    metta_py_decode_shared(Tagged, Term, Bindings).
metta_py_decode_target(Space, Tagged, Term, Bindings) :-
    metta_py_decode_target_(Tagged, Space, Term,
                           indexed([], Index), indexed(Bindings, Index)).

metta_py_decode_target_([T0|Rest], Space, Term, B0, B) :-
    ( atom(T0) -> T = T0 ; string(T0) -> atom_string(T, T0) ),
    metta_py_decode_target_tagged(T, Rest, Space, Term, B0, B).

metta_py_decode_target_tagged(e, [Es], Space, Term, B0, B) :- !,
    foldl_decode_target(Es, Space, Term, B0, B).
metta_py_decode_target_tagged(s, ['&self'], Space, Space, B, B) :- !.
metta_py_decode_target_tagged(s, ["&self"], Space, Space, B, B) :- !.
metta_py_decode_target_tagged(p, ['&self'], Space, Space, B, B) :- !.
metta_py_decode_target_tagged(p, ["&self"], Space, Space, B, B) :- !.
metta_py_decode_target_tagged(T, Rest, _, Term, B0, B) :-
    metta_py_decode_shared_tagged(T, Rest, Term, B0, B).

foldl_decode_target([], _, [], B, B).
foldl_decode_target([E|Es], Space, [T|Ts], B0, B) :-
    metta_py_decode_target_(E, Space, T, B0, B1),
    foldl_decode_target(Es, Space, Ts, B1, B).

%THE SEED TABLE IS GONE, and with it the reason a decode had to be handed
%something to expand. It rebuilt the argument variables' names AFTER the
%crossing, while the names Python was given had been written BEFORE it, and a
%name was the cell's stack offset: a collection anywhere in encode-call-decode
%renamed the very variables the table existed to find, so a returned variable
%stopped resolving to the caller's. metta_py_encode_arguments/3 hands back the
%map it wrote and the decode is given that map, so the two sides cannot name
%one cell differently and nothing is built a second time. The laziness this
%replaces was worth one inference on a thirteen-inference call
%[measured 2026-08-17]; threading costs a call with no variable nothing at
%all, because the map stays [] and no name is ever minted.

% A wide query retains first-appearance pairs for acyclicity and answer
% semantics while using a backtrackable hash table for variable identity and
% projection lookup.
metta_py_decode_indexed(Tagged, Term, Bindings) :-
    ht_new(Index),
    metta_py_decode_shared_(Tagged, Term, indexed([], Index), Bindings).

%%%%%%%%%% The explicit answer form %%%%%%%%%%
%
%["a", Theta, Residue, K] and ["a", Theta, Residue, K, Value]: bindings
%for the query's variables, crossing beside plain atom wires in one
%stream. Theta pairs are [Name, ValueWire]; the names are the ones
%metta_py_encode/2 wrote for the query's variables, so binding by name is
%binding the caller's own variable. This is Hyperon's execute_bindings: an
%answer atom together with the bindings
%it is returned under, each set merged into the current frame. The wire
%is transport-agnostic; janus is one carrier of it, and a Prolog-side
%provider needs none of it because unification already binds.
%
%The head asks for four elements before it looks at the tag, so every
%plain two-element wire falls through on the list spine without reaching
%the comparison; the explicit form stays off the hot path's price.
metta_py_answer_form([Tag, Theta, Residue, K], Theta, Residue, K, none) :-
    ( Tag == "a" -> true ; Tag == a ).
metta_py_answer_form([Tag, Theta, Residue, K, Value], Theta, Residue, K,
                     value(Value)) :-
    ( Tag == "a" -> true ; Tag == a ).

%The annotation slot: the degenerate point is the carrier's one and costs
%nothing; a real k is admitted exactly when its context declared a non-Boolean
%algebra. Provider rows REPLACE the cell because match_foreign_routed/6 captures
%each row locally and extends the conjuncts itself. Operation answers EXTEND the
%cell because sequential evaluation is the join: replacing there made the last
%call's weight win. An undeclared k is refused loudly because silently dropping
%it would misweigh the answer and silently keeping it would smuggle a carrier
%the context never declared.
metta_py_answer_kappa('@'(none), _) :- !.
metta_py_answer_kappa(K0, Ctx) :-
    metta_py_answer_kappa_value(K0, Ctx, K),
    b_setval('$metta_answer_k', K).

metta_py_answer_compose_kappa('@'(none), _) :- !.
metta_py_answer_compose_kappa(K0, Ctx) :-
    metta_py_answer_kappa_value(K0, Ctx, K),
    metta_annotation(Ctx, Previous),
    metta_k_extend(Ctx, Previous, K, Joint),
    b_setval('$metta_answer_k', Joint).

metta_py_answer_kappa_value(K0, Ctx, K) :-
    (   metta_effective_algebra(Ctx, Algebra),
        Algebra \== bool
    ->  ( K0 = [_|_] -> metta_py_decode_shared(K0, K, _) ; K = K0 )
    ;   throw(error(metta_answer_annotation_undeclared(Ctx, K0), none))
    ).

%Close an answer's residue: the part of the query the provider did not
%discharge, evaluated by the engine under the bindings already made. The
%residue decodes against the same name table, so its variables ARE the
%query's, and each evaluation result that is not false contributes one
%closure, composing bindings by ordinary sharing; false contributes
%nothing. That rule is the language's own: a condition like (> $y 3)
%reduces to a boolean and false drops the answer, a match form inside the
%residue contributes one closure per solution, and a term with no
%equation answers itself, exactly as !(edge a b) does at the top level.
%This residue is only the part a provider did not discharge. Constraint goals
%remain language-internal through residual-goals/2, and a WFS answer carries
%its delay condition; neither creates a second Python return shape.
metta_py_answer_close('@'(true), _) :- !.
metta_py_answer_close(ResidueW, Table) :-
    metta_py_decode_shared_(ResidueW, Residue, Table, _),
    eval(Residue, Out),
    Out \== false.

%A conditional answer under a pushed bound under-answers: the provider
%truncated at the caller's k, and a residue can still drop answers after
%that, so fewer than k arrive while more existed. Exact licensed the
%bound; a residue is exactly what Exact rules out.
metta_py_answer_bounded('@'(true), _, _) :- !.
metta_py_answer_bounded(_, '@'(none), _) :- !.
metta_py_answer_bounded(Residue, _, Pattern) :-
    throw(error(metta_answer_conditional_under_bound(Pattern, Residue),
                none)).

%Merge Theta into the query frame: seed the name table with the query's
%own variables, decode each bound value against it, so values may
%reference the query's variables and each other while unknown names stay
%fresh, and unify. A failing unification drops the ANSWER, exactly as a
%candidate that does not unify is dropped, and is equally sound.
%Table0 is the map the encoder wrote for the term this answer replies to,
%so theta's bindings extend the caller's own variables rather than a second
%naming of them.
metta_py_answer_theta(Pairs, Table0, Table) :-
    foldl(metta_py_answer_binding, Pairs, Table0, Table).

metta_py_answer_binding([NameW, ValueW], Table0, Table) :-
    ( atom(NameW) -> Name = NameW ; atom_string(Name, NameW) ),
    metta_py_decode_shared_(ValueW, Value, Table0, Table1),
    ( memberchk(Name-Variable, Table1) -> Table = Table1
    ; Table = [Name-Variable|Table1] ),
    Variable = Value.

%One item of a provider's match stream against the query pattern. The
%explicit form applies theta to the pattern's variables; its value, when
%present, is the candidate-with-bindings reading and unifies under them,
%and its residue closes through the engine, one answer per closure.
metta_py_answer_match(Item, Pattern, Table0, Ctx) :-
    metta_py_answer_match(Item, Pattern, '@'(none), Table0, Ctx).
metta_py_answer_match(Item, Pattern, Limit, Table0, Ctx) :-
    (   metta_py_answer_form(Item, Theta, Residue, K, ValueW)
    ->  metta_py_answer_kappa(K, Ctx),
        metta_py_answer_bounded(Residue, Limit, Pattern),
        metta_py_answer_theta(Theta, Table0, Table),
        (   ValueW = value(VW)
        ->  metta_py_decode_shared_(VW, Value, Table, _),
            Pattern = Value
        ;   true
        ),
        metta_py_answer_close(Residue, Table)
    ;   %The crossing's own map, so a reply's names mean one thing on both
        %branches rather than the map here and a fresh table there. It changes
        %no answer, and that is a measurement rather than an expectation: a
        %candidate that repeats the crossing's own name, one that invents a
        %name, a ground one and one that echoes the variable it was handed all
        %answer identically either way [measured 2026-08-31, four providers
        %against (match &probe (edge a $y) $y)]. The unification below is why:
        %a plain candidate is unified with the pattern immediately, which
        %aliases exactly what resolving the names would have. Unlike the theta
        %branch, where the value is returned rather than unified and the map is
        %the only link, this branch cannot go wrong either way.
        metta_py_decode_shared_(Item, Candidate, Table0, _),
        Pattern = Candidate
    ).

%One result of an operation dispatch: the explicit form binds the CALL's
%variables and reduces to its value, () when none, the relational
%reading; a plain wire is the value itself, decoded with the lazy seed.
metta_py_answer_result(Item, Name, Table0, Result) :-
    (   metta_py_answer_form(Item, Theta, Residue, K, ValueW)
    ->  metta_py_answer_compose_kappa(K, Name),
        metta_py_answer_theta(Theta, Table0, Table),
        (   ValueW = value(VW)
        ->  metta_py_decode_shared_(VW, Result, Table, _)
        ;   Result = []
        ),
        metta_py_answer_close(Residue, Table)
    ;   metta_py_decode_shared_(Item, Result, Table0, _)
    ).

:- multifile prolog:error_message//1.
prolog:error_message(metta_answer_conditional_under_bound(Pattern, Residue)) -->
    [ 'an answer for ~q carries a residue (~q) while the caller\'s bound \c
       was pushed to the provider. A conditional answer can still drop \c
       after the provider truncated, which under-answers; a residue is \c
       exactly what an Exact claim rules out, so declare this shape \c
       Sound instead'-[Pattern, Residue] ].
prolog:error_message(metta_answer_annotation_undeclared(Ctx, K)) -->
    [ 'this answer carries an annotation (~q) and ~w declares no \c
       semiring for it. Declare (annotations ~w ranked) to admit ordered \c
       annotations there; silently dropping k would misweigh the answer \c
       and silently keeping it would smuggle an order the context never \c
       declared'-[K, Ctx, Ctx] ].
