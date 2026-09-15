PyDoc_STRVAR(_functools_cmp_to_key__doc__,
"cmp_to_key($module, /, mycmp)\n"
"--\n"
"\n"
"Convert a cmp= function into a key= function.\n"
"\n"
"  mycmp\n"
"    Function that compares two objects.");
#define _FUNCTOOLS_CMP_TO_KEY_METHODDEF    \
    {"cmp_to_key", _PyCFunction_CAST(_functools_cmp_to_key), METH_FASTCALL|METH_KEYWORDS, _functools_cmp_to_key__doc__},
PyDoc_STRVAR(_functools_reduce__doc__,
"reduce($module, function, iterable, /, initial=<unrepresentable>)\n"
"--\n"
"\n"
"Apply a function of two arguments cumulatively to the items of an iterable, from left to right.\n"
"\n"
"This effectively reduces the iterable to a single value.  If initial is present,\n"
"it is placed before the items of the iterable in the calculation, and serves as\n"
"a default when the iterable is empty.\n"
"\n"
"For example, reduce(lambda x, y: x+y, [1, 2, 3, 4, 5])\n"
"calculates ((((1 + 2) + 3) + 4) + 5).");
#define _FUNCTOOLS_REDUCE_METHODDEF    \
    {"reduce", _PyCFunction_CAST(_functools_reduce), METH_FASTCALL|METH_KEYWORDS, _functools_reduce__doc__},
PyDoc_STRVAR(_functools__lru_cache_wrapper_cache_info__doc__,
"cache_info($self, /)\n"
"--\n"
"\n"
"Report cache statistics");
#define _FUNCTOOLS__LRU_CACHE_WRAPPER_CACHE_INFO_METHODDEF    \
    {"cache_info", (PyCFunction)_functools__lru_cache_wrapper_cache_info, METH_NOARGS, _functools__lru_cache_wrapper_cache_info__doc__},
PyDoc_STRVAR(_functools__lru_cache_wrapper_cache_clear__doc__,
"cache_clear($self, /)\n"
"--\n"
"\n"
"Clear the cache and cache statistics");
#define _FUNCTOOLS__LRU_CACHE_WRAPPER_CACHE_CLEAR_METHODDEF    \
    {"cache_clear", (PyCFunction)_functools__lru_cache_wrapper_cache_clear, METH_NOARGS, _functools__lru_cache_wrapper_cache_clear__doc__},
