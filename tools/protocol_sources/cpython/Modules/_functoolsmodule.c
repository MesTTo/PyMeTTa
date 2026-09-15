PyDoc_STRVAR(placeholder_doc,
"The type of the Placeholder singleton.\n\n"
"Used as a placeholder for partial arguments.");
PyDoc_STRVAR(partial_doc,
"partial(func, /, *args, **keywords)\n--\n\n\
Create a new function with partial application of the given arguments\n\
and keywords.");
PyDoc_STRVAR(lru_cache_doc,
"Create a cached callable that wraps another function.\n\
\n\
user_function:      the function being cached\n\
\n\
maxsize:  0         for no caching\n\
          None      for unlimited cache size\n\
          n         for a bounded cache\n\
\n\
typed:    False     cache f(3) and f(3.0) as identical calls\n\
          True      cache f(3) and f(3.0) as distinct calls\n\
\n\
cache_info_type:    namedtuple class with the fields:\n\
                        hits misses currsize maxsize\n"
);
PyDoc_STRVAR(_functools_doc,
"Tools that operate on functions.");
static PyMethodDef _functools_methods[] = {
    _FUNCTOOLS_REDUCE_METHODDEF
    _FUNCTOOLS_CMP_TO_KEY_METHODDEF
    {NULL,              NULL}           /* sentinel */
};
