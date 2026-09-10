% Purpose: reflect library declarations and compiled definitions.
% Assumes: loaded through _binding/shim.pl in its host module.

%%%%%%%%%% What a library says about itself %%%%%%%%%%
%
%Everything one Prolog source declares, as [kind, value] pairs rather than the
%coarse verdict metta_py_source_declares/2 answers: the caller here is building
%a description of a library, and "exports" does not say WHICH names, which
%capability the file needs, or what version it states. One scan either way,
%and the source is read and never consulted
%[source: engine/metta/interop.pl, metta_source_declarations/2].
metta_py_source_declarations(Source0, Rows) :-
    ( atom(Source0) -> Source = Source0 ; atom_string(Source, Source0) ),
    metta_source_declarations(Source, Declarations),
    findall([KindS, ValueS],
            ( member(Declaration, Declarations),
              Declaration =.. [Kind, Value],
              atom_string(Kind, KindS),
              metta_py_origin_part(Value, ValueS) ),
            Rows).

%Every head name one MeTTa source registers, with the index of the form that
%registers it, so the caller pairs each with the line its own position walk
%already knows. The engine owns which of its forms register a head; this
%crosses that answer once per source instead of per form
%[source: engine/metta/interop.pl, metta_string_registrations/2].
metta_py_registrations(Source0, Rows) :-
    ( string(Source0) -> Source = Source0 ; atom_string(Source0, Source) ),
    metta_string_registrations(Source, Rows0),
    findall([NameS, Index],
            ( member([Name, Index], Rows0), atom_string(Name, NameS) ),
            Rows).

%The engine's own digest of a file on disk, which is the identity a reload
%compares and therefore the identity a lockfile has to pin. Reading it here
%rather than hashing in the host is what keeps the two answers the same for a
%.gz source and for a fast image, whose digest is declared in its header
%rather than computed over its bytes
%[source: engine/filereader/source_lifecycle.pl, metta_source_digest/2].
metta_py_source_digest(Path0, Digest) :-
    ( atom(Path0) -> Path = Path0 ; atom_string(Path, Path0) ),
    filereader:metta_source_digest(Path, Digest0),
    atom_string(Digest0, Digest).

%Every source this process has loaded, with the space it loaded into and the
%digest it was loaded FROM, read inside one transaction so the table cannot
%change under the walk.
%
%A load in flight answers `loading` and no rows. The table is written at
%publish and a load that is still reading has no row yet, so a lock taken
%during one would record a program that is half loaded and read back as
%complete; refusing is the only honest answer, and the caller retries when the
%load it is racing has finished
%[source: engine/filereader/source_lifecycle.pl, with_source_load/3 asserts
%active_source_load/1 for the duration and publish_source_load/3 writes the
%row].
metta_py_source_loads(Status, Rows) :-
    transaction(
        (   filereader:active_source_load(_)
        ->  Status = "loading", Rows = []
        ;   Status = "settled",
            findall([PathS, SpaceS, DigestS],
                    ( filereader:metta_source_load(Path, Space, _, Digest),
                      atom_string(Path, PathS),
                      metta_py_origin_part(Space, SpaceS),
                      atom_string(Digest, DigestS) ),
                    Rows)
        )).

%Every repository revision this process pinned, by either git route. The
%predicate lives in lib/lib_gitimport/lib_gitimport.pl, which a build without
%library(process) still loads, so the guard is about the predicate EXISTING
%rather than about the platform.
metta_py_git_pins(Rows) :-
    (   current_predicate(git_pinned_dependency/2)
    ->  findall([UrlS, RevS],
                ( git_pinned_dependency(Url, Rev),
                  atom_string(Url, UrlS),
                  atom_string(Rev, RevS) ),
                Rows)
    ;   Rows = []
    ).

%The names one extension installed, asked before releasing them so the caller
%can be told what went.
metta_py_extension_members(Name0, Names) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    findall(S, ( metta_extension_member(Name, Member), atom_string(Member, S) ), Names).

%Everything one extension installed, released together.
metta_py_unregister_extension(Name0) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    unregister_metta_extension(Name).

%Every function or translator special-form name the language knows, for
%completion and docs. The special forms come from the translator's published
%service rather than from its clause table: this used to read
%clause(Engine:translate_special_dl(...), _) directly, and the moment the
%compiler's clauses moved into a module of their own the read matched nothing
%and m.builtins() quietly answered 31 names short, with no error anywhere
%[measured 2026-08-22: 268 names before the translator became a module, 237
%after, 268 again through the service].
metta_py_builtins(Names) :-
    findall(N, fun(N), Functions),
    metta_py_special_form_names(SpecialForms),
    append(Functions, SpecialForms, Language0),
    sort(Language0, Language),
    maplist(atom_string, Language, Names).

%The same union narrowed to what ONE space can call. fun/1 is process-wide by
%design (the translator reads it to decide call against data wherever a term
%compiles), so the union above lists a head every space has registered,
%including one whose equations live in a module this space never sees. A
%namespace built on it advertised those heads, resolved them, and produced
%calls that answered themselves unreduced; and once the process had registered
%more than 750 names CPython stopped offering a suggestion for a typo at all,
%because its traceback machinery declines a candidate pool that large
%[measured 2026-09-07: 800 equations in one space made another space's
%namespace list 1,107 names and lose "Did you mean: 'dbl'?"; the same space
%alone lists 306]. The rule is the engine's own fun_here/1 with the module
%made explicit, metta_host_function_callable_from/2: an unscoped name (a
%builtin, a Python operation registered into &self, a prelude rule) answers
%everywhere, a scoped one answers where its clauses are visible from, which is
%its own module, a parent it inherits from, or &self.
metta_py_builtins(Space0, Names) :-
    ( atom(Space0) -> Space = Space0 ; atom_string(Space, Space0) ),
    metta_py_module(Space, Module),
    findall(N, metta_host_function_callable_from(Module, N), Functions),
    metta_py_special_form_names(SpecialForms),
    append(Functions, SpecialForms, Language0),
    sort(Language0, Language),
    maplist(atom_string, Language, Names).

metta_py_function_generation(Generation) :-
    metta_host_function_generation(Generation).

%Whether ANY deprecation declaration exists, as 1/0 through the apply seam.
%The catalog is almost always empty, and the callable doors' first-call
%deprecation read through a fresh once/1 goal string measured 1,311
%inferences where this apply-seam probe is double digits, the same
%once-versus-apply gap metta_py_catalogue_member/1 documents below
%[tested: test_an_empty_deprecation_catalog_costs_one_cheap_probe].
metta_py_deprecation_declared(Flag) :-
    ( metta_deprecation(_, _, _) -> Flag = 1 ; Flag = 0 ).

metta_py_special_form_names(Names) :-
    findall(Name, metta_special_form_head(Name), Names0),
    sort(Names0, Names).

metta_py_is_function(Name0) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    fun(Name).

%Point membership in the catalogue metta_py_builtins/2 lists for one space:
%one indexed fun/1 probe and the callable-from-here walk, then the
%special-form heads, instead of materializing and string-converting the
%whole catalogue. The bound namespace asks this on every attribute
%resolution, and the full read it replaces measured 1,347 inferences on the
%first access after any definition where this probe is double digits
%[measured 2026-08-24; consumer _FunctionNamespace._known].
metta_py_catalogue_member(Space0, Name0) :-
    ( atom(Space0) -> Space = Space0 ; atom_string(Space, Space0) ),
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    (   fun(Name)
    ->  metta_py_module(Space, Module),
        metta_host_function_callable_from(Module, Name)
    ;   once(metta_special_form_head(Name))
    ).

%Whether a function ANSWERS from this space: it has clauses its module can
%see, its own or inherited from user. Another space's equations live in that
%space's module and are invisible here, so they do not count.
metta_py_function_visible(Space0, Name0) :-
    ( atom(Space0) -> Space = Space0 ; atom_string(Space, Space0) ),
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    fun(Name),
    %The question is about clauses, and a deferred function has none until
    %its equations translate; the clause probe below is a read the
    %undefined-predicate net never fires for.
    spaces:metta_ensure_compiled(Name),
    metta_py_module(Space, Module),
    catch_recover(( current_predicate(Module:Name/Arity),
                    functor(Head, Name, Arity),
                    clause(Module:Head, _, _) ),
                  fail), !.

%Whether a head this space does NOT define answers here through the space
%chain: a space it inherits from defines it, or &self does and this is some
%other space, which is the sharing rule fun_here_in/2 states. This is the
%question `@typing.override` asks, so a definition that shadows nothing is
%refused where it is written instead of answering beside the one it meant to
%replace.
%
%A BUILTIN is deliberately not an answer, which is why this walks the chain
%rather than calling fun_here_in/2: that predicate's last clause admits every
%engine name, and shadowing a builtin is the same-space collision
%metta_py_function_visible/2 already refuses with its own message.
%
%fun_in/2 is a REGISTRATION fact rather than a clause fact -- register_fun_in/2
%asserts it when the equation lands -- so unlike the clause probe above this
%needs no metta_ensure_compiled/1 to be right on a definition nothing has
%evaluated yet [measured 2026-09-07: fun_in holds immediately after
%space.run("(= (area $r) ...)") with no evaluation in between].
metta_py_function_inherited(Space0, Name0) :-
    ( atom(Space0) -> Space = Space0 ; atom_string(Space, Space0) ),
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    fun(Name),
    metta_py_module(Space, Module),
    \+ spaces:fun_in(Module, Name),
    metta_py_inherited_definer(Module, Name), !.

metta_py_inherited_definer(Module, Name) :-
    spaces:metta_exec_module_parent(Module, Parent),
    (   spaces:fun_in(Parent, Name)
    ->  true
    ;   metta_py_inherited_definer(Parent, Name)
    ).
metta_py_inherited_definer(Module, Name) :-
    spaces:metta_self_module(Self),
    Module \== Self,
    spaces:fun_in(Self, Name).

metta_py_arities(Name0, As) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    %Compiled arities are registered at translation, so the read forces.
    spaces:metta_ensure_compiled(Name),
    findall(A, arity(Name, A), As).

%Every stored equation for a name, live from the space. Pattern-directed:
%a native space answers by first-argument index on '=', a foreign space
%enumerates and unifies, and the open tail in the head pattern is Prolog
%unification against stored lists, not the MeTTa matcher.
metta_py_equations(Space, Name0, Encoded) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    Pattern = [=, [Name|_], _],
    findall(E, ( metta_host_stored(Space, Pattern),
                 metta_py_encode(Pattern, E) ), Encoded).

%The (cost ...) row a head declares about itself, as the pair the engine
%RESOLVED: the declared class, and the measure the row named or the head's
%arrow decided. `none` when the head declares no row. The derivation stays in
%the engine so the docstring here, (explain ...) and the cost-rows benchmark
%lane all read one answer instead of three implementations of one rule.
metta_py_cost_declaration(Name0, Claim) :-
    current_metta_space(Space), metta_py_cost_declaration(Space, Name0, Claim).
metta_py_cost_declaration(Space, Name0, Claim) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    (   metta_head_property(Space, Name, [cost, Class, Measure])
    ->  Claim = [Class, Measure]
    ;   Claim = none
    ).

% One property bag per head, encoded by the existing atom wire. Context is a
% space name or a library's source-path list; the engine resolves the home.
metta_py_head_claims(Names, Rows) :-
    metta_py_head_claims('&self', Names, Rows).
metta_py_head_claims(Context, Names0, Rows) :-
    maplist(metta_py_claim_name, Names0, Names),
    ( is_list(Context)
    -> maplist(metta_py_claim_name, Context, Paths), Scope = sources(Paths)
    ; metta_py_claim_name(Context, Space), Scope = space(Space) ),
    metta_head_claims(Scope, Names, Claims),
    findall([NameS, Encoded],
            ( member([Name, Properties], Claims), atom_string(Name, NameS),
              maplist(metta_py_encode, Properties, Encoded) ), Rows).

metta_py_claim_name(Value, Name) :-
    ( atom(Value) -> Name = Value ; atom_string(Name, Value) ).

%The Prolog clauses a name compiled to, dis for the translator: one
%listing per registered arity, resolved in this space's module so a named
%space shows the clauses it would run. Fails on a name the engine never
%compiled, and the Python side turns that into its own refusal.
metta_py_disassemble(Space, Name0, Text) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    %The listing below is a read, so a deferred function would show nothing
    %and register no arity; the disassembly IS the demand.
    spaces:metta_ensure_compiled(Name),
    findall(A, arity(Name, A), As0),
    As0 \== [],
    sort(As0, As),
    space_module(Space, Module),
    with_output_to(string(Text),
                   forall(member(A, As),
                          (   current_predicate(Module:Name/A)
                          ->  listing(Module:Name/A)
                          ;   true ))).
