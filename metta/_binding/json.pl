% Purpose: resolve and cross the engine JSON codec.
% Assumes: loaded through _binding/shim.pl in its host module.

%%%%%%%%%% JSON %%%%%%%%%%
%
%The JSON codec is the engine's own, through the one JSON door in
%engine/json_codec.pl, which is library(json) with a C fast path beside
%it. What this file adds is the janus value conventions: @(true),
%@(false) and @(none) are what janus makes of Python True, False and
%None, and naming them here teaches the reader and writer that exact
%vocabulary, so a Python value crosses, serializes and comes back with
%no Python-side JSON implementation existing anywhere. SWI integers are
%unbounded, which is what makes wide integers exact in both directions
%without any guard.

%Found from THIS file's own directory rather than by counting levels, because
%the two ship at different depths: the shim is extensions/python/metta/_binding/shim.pl
%three levels under the engine in a checkout, and metta/_binding/shim.pl one level OVER
%it, at metta/_runtime/engine/, in an installed wheel. The old directive spelled
%the checkout's depth, and a use_module that resolves to nothing only WARNS, so
%the wheel loaded, booted, answered arithmetic, and failed every metta._binding.json
%call with Unknown procedure: json_codec_write/3 [measured 2026-08-29 against a
%wheel installed into a fresh venv outside the checkout].
%
%Resolved here rather than through an alias the ENGINE publishes, because this
%file loads engine-free by contract: tests/prolog/suites/host/shim.plt consults
%it and nothing else, so an alias registered by engine/metta.pl does not exist
%in that session and the directive raised
%`source_sink metta_engine(json_codec) does not exist`
%[tested: test_the_shim_reaches_the_engine_by_alias_rather_than_by_depth].
:- prolog_load_context(directory, Here),
   % policy-inventory-exempt: mechanism-internal; reason=the two entries are the only layouts this package ships in, a checkout and an installed wheel, rather than a choice an operator makes; evidence=extensions/python/tests/ch01_getting_started/test_packaging.py:test_the_shim_reaches_the_engine_by_alias_rather_than_by_depth
   (   member(Relative, ['../../../../engine/json_codec.pl',
                         '../_runtime/engine/json_codec.pl']),
       absolute_file_name(Relative, Codec,
                          [relative_to(Here), access(read), file_errors(fail)])
   ->  use_module(Codec, [ json_codec_read/3, json_codec_write/3 ])
   ;   throw(error(existence_error(source_sink, json_codec),
                   context(shim, 'no engine/json_codec.pl beside this shim')))
   ).

metta_py_json_options([shape(dicts), true(@(true)), false(@(false)),
                       null(@(none))]).

%Encode one janus-shaped value to JSON text. Errors leave through the
%reserved envelope so the Python side raises ValueError and TypeError by
%kind rather than by message text; the refusals themselves, of a
%non-finite number and of a term JSON cannot carry, belong to the codec.
metta_py_json_encode(Value, Text) :-
    catch(metta_py_json_encode_(Value, Text), Error,
          metta_py_json_rethrow(Error)).

metta_py_json_encode_(Value, Text) :-
    metta_py_json_options(Options),
    json_codec_write(Value, Text, Options).

%Decode JSON text to a janus-shaped value. The codec stops after one
%value and refuses a remainder that is not layout, so a second value in
%the same text is an error rather than silently dropped.
%
%This used to pass tag(py) to json_read_dict/3, which does not do what
%its comment claimed. tag/1 names the object KEY whose value becomes the
%dict's tag, so a document with a "py" key lost it: '{"py": "x", "a": 1}'
%decoded to {'a': 1} [measured 2026-08-28]. Nothing needed the option --
%an ordinary object never has that key, so the tag stayed unbound either
%way, and janus makes a Python dict of a tagged and an untagged dict
%alike [tested: test_json_codec_keeps_a_key_named_py].
metta_py_json_decode(Text, Value) :-
    catch(metta_py_json_decode_(Text, Value), Error,
          metta_py_json_rethrow(Error)).

metta_py_json_decode_(Text, Value) :-
    metta_py_json_options(Options),
    json_codec_read(Text, Value, Options).

%Each error class keeps its own clause, so Python raises by kind: a
%value that JSON cannot carry is a ValueError, a term that is not JSON
%data at all is a TypeError, and anything unrecognized stays a raw
%engine error rather than being dressed as one of those.
metta_py_json_rethrow(error(domain_error(finite_number, Culprit), _)) :-
    format(string(Message),
           "JSON cannot carry the non-finite number ~w", [Culprit]),
    metta_py_raise(value, Message).
metta_py_json_rethrow(error(type_error(Type, Culprit), _)) :-
    format(string(Message),
           "JSON cannot carry ~p, which is not a ~w", [Culprit, Type]),
    metta_py_raise(type, Message).
metta_py_json_rethrow(error(domain_error(Domain, Culprit), _)) :-
    format(string(Message),
           "JSON cannot carry ~p, which is not a ~w", [Culprit, Domain]),
    metta_py_raise(type, Message).
metta_py_json_rethrow(error(syntax_error(What), _)) :-
    format(string(Message), "not valid JSON: ~w", [What]),
    metta_py_raise(value, Message).
metta_py_json_rethrow(error(duplicate_key(Key), _)) :-
    format(string(Message), "JSON object repeats the key ~w", [Key]),
    metta_py_raise(value, Message).
metta_py_json_rethrow(Error) :-
    throw(Error).
