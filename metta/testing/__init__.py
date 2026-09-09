"""Purpose: expose strategies, fixtures and conformance kits on demand.

Guarantees: importing this namespace requires neither Hypothesis nor pytest;
named exports retain their implementation objects [tested:
test_the_testing_module_names_both_suites_without_importing_them;
commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
"""

from typing import TYPE_CHECKING

from metta._lazy import package as _package

if TYPE_CHECKING:
    from ._codec_kit import CodecDriver as CodecDriver
    from ._codec_kit import check_codec as check_codec
    from ._codec_kit import codec_corpus as codec_corpus
    from ._codec_kit import codec_plan as codec_plan
    from ._fixtures import check_minted_handles as check_minted_handles
    from ._fixtures import check_replay as check_replay
    from ._fixtures import check_twin as check_twin
    from ._fixtures import record_replay as record_replay
    from ._gateway import GatewayComplianceSuite as GatewayComplianceSuite
    from ._kits import assert_answers as assert_answers
    from ._kits import assert_includes as assert_includes
    from ._kits import check_space_provider as check_space_provider
    from ._machine import SpaceMachine as SpaceMachine
    from ._properties import Case as Case
    from ._properties import Cases as Cases
    from ._properties import Laws as Laws
    from ._properties import cases as cases
    from ._properties import laws as laws
    from ._providers import SpaceComplianceSuite as SpaceComplianceSuite
    from ._strategies import atoms as atoms
    from ._strategies import expressions as expressions
    from ._strategies import from_pattern as from_pattern
    from ._strategies import ground_atoms as ground_atoms
    from ._strategies import grounded as grounded
    from ._strategies import library_scalars as library_scalars
    from ._strategies import names as names
    from ._strategies import numbers as numbers
    from ._strategies import patterns as patterns
    from ._strategies import programs as programs
    from ._strategies import symbols as symbols
    from ._strategies import texts as texts
    from ._strategies import variables as variables

__all__ = ['Case', 'Cases', 'CodecDriver', 'GatewayComplianceSuite', 'Laws', 'SpaceComplianceSuite', 'SpaceMachine', 'assert_answers', 'assert_includes', 'atoms', 'cases', 'check_codec', 'check_minted_handles', 'check_replay', 'check_space_provider', 'check_twin', 'codec_corpus', 'codec_plan', 'expressions', 'from_pattern', 'ground_atoms', 'grounded', 'laws', 'library_scalars', 'names', 'numbers', 'patterns', 'programs', 'record_replay', 'symbols', 'texts', 'variables']

__getattr__, __dir__ = _package(__name__)
