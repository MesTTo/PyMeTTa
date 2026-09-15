PyDoc_STRVAR(build_class_doc,
"__build_class__(func, name, /, *bases, [metaclass], **kwds) -> class\n\
\n\
Internal helper function used by the class statement.");
PyDoc_STRVAR(breakpoint_doc,
"breakpoint($module, /, *args, **kws)\n\
--\n\
\n\
Call sys.breakpointhook(*args, **kws).  sys.breakpointhook() must accept\n\
whatever arguments are passed.\n\
\n\
By default, this drops you into the pdb debugger.");
PyDoc_STRVAR(reduce_doc, "Return state information for pickling.");
PyDoc_STRVAR(filter_doc,
"filter(function, iterable, /)\n\
--\n\
\n\
Return an iterator yielding those items of iterable for which function(item)\n\
is true. If function is None, return the items that are true.");
PyDoc_STRVAR(dir_doc,
"dir([object]) -> list of strings\n"
"\n"
"If called without an argument, return the names in the current scope.\n"
"Else, return an alphabetized list of names comprising (some of) the attributes\n"
"of the given object, and of attributes reachable from it.\n"
"If the object supplies a method named __dir__, it will be used; otherwise\n"
"the default dir() logic is used and returns:\n"
"  for a module object: the module's attributes.\n"
"  for a class object:  its attributes, and recursively the attributes\n"
"    of its bases.\n"
"  for any other object: its attributes, its class's attributes, and\n"
"    recursively the attributes of its class's base classes.");
PyDoc_STRVAR(getattr_doc,
"getattr(object, name[, default]) -> value\n\
\n\
Get a named attribute from an object; getattr(x, 'y') is equivalent to x.y.\n\
When a default argument is given, it is returned when the attribute doesn't\n\
exist; without it, an exception is raised in that case.");
PyDoc_STRVAR(setstate_doc, "Set state information for unpickling.");
PyDoc_STRVAR(map_doc,
"map(function, iterable, /, *iterables, strict=False)\n\
--\n\
\n\
Make an iterator that computes the function using arguments from\n\
each of the iterables.  Stops when the shortest iterable is exhausted.\n\
\n\
If strict is true and one of the arguments is exhausted before the others,\n\
raise a ValueError.");
PyDoc_STRVAR(next_doc,
"next(iterator[, default])\n\
\n\
Return the next item from the iterator. If default is given and the iterator\n\
is exhausted, it is returned instead of raising StopIteration.");
PyDoc_STRVAR(iter_doc,
"iter(iterable) -> iterator\n\
iter(callable, sentinel) -> iterator\n\
\n\
Get an iterator from an object.  In the first form, the argument must\n\
supply its own iterator, or be a sequence.\n\
In the second form, the callable is called until it returns the sentinel.");
PyDoc_STRVAR(min_doc,
"min(iterable, *[, default=obj, key=func]) -> value\n\
min(arg1, arg2, *args, *[, key=func]) -> value\n\
\n\
With a single iterable argument, return its smallest item. The\n\
default keyword-only argument specifies an object to return if\n\
the provided iterable is empty.\n\
With two or more positional arguments, return the smallest argument.");
PyDoc_STRVAR(max_doc,
"max(iterable, *[, default=obj, key=func]) -> value\n\
max(arg1, arg2, *args, *[, key=func]) -> value\n\
\n\
With a single iterable argument, return its biggest item. The\n\
default keyword-only argument specifies an object to return if\n\
the provided iterable is empty.\n\
With two or more positional arguments, return the largest argument.");
builtin_round_impl(PyObject *module, PyObject *number, PyObject *ndigits)
/*[clinic end generated code: output=ff0d9dd176c02ede input=275678471d7aca15]*/
{
    PyObject *result;
    if (ndigits == Py_None) {
        result = _PyObject_MaybeCallSpecialNoArgs(number, &_Py_ID(__round__));
    }
    else {
        result = _PyObject_MaybeCallSpecialOneArg(number, &_Py_ID(__round__),
                                                  ndigits);
    }
    if (result == NULL && !PyErr_Occurred()) {
        PyErr_Format(PyExc_TypeError,
                     "type %.100s doesn't define __round__ method",
                     Py_TYPE(number)->tp_name);
    }
    return result;
}
PyDoc_STRVAR(builtin_sorted__doc__,
"sorted($module, iterable, /, *, key=None, reverse=False)\n"
"--\n"
"\n"
"Return a new list containing all items from the iterable in ascending order.\n"
"\n"
"A custom key function can be supplied to customize the sort order, and the\n"
"reverse flag can be set to request the result in descending order.");
#define BUILTIN_SORTED_METHODDEF    \
    {"sorted", _PyCFunction_CAST(builtin_sorted), METH_FASTCALL | METH_KEYWORDS, builtin_sorted__doc__},
PyDoc_STRVAR(vars_doc,
"vars([object]) -> dictionary\n\
\n\
Without arguments, equivalent to locals().\n\
With an argument, equivalent to object.__dict__.");
PyDoc_STRVAR(zip_doc,
"zip(*iterables, strict=False)\n\
--\n\
\n\
The zip object yields n-length tuples, where n is the number of iterables\n\
passed as positional arguments to zip().  The i-th element in every tuple\n\
comes from the i-th iterable argument to zip().  This continues until the\n\
shortest argument is exhausted.\n\
\n\
If strict is true and one of the arguments is exhausted before the others,\n\
raise a ValueError.\n\
\n\
   >>> list(zip('abcdefg', range(3), range(4)))\n\
   [('a', 0, 0), ('b', 1, 1), ('c', 2, 2)]");
static PyMethodDef builtin_methods[] = {
    {"__build_class__", _PyCFunction_CAST(builtin___build_class__),
     METH_FASTCALL | METH_KEYWORDS, build_class_doc},
    BUILTIN___IMPORT___METHODDEF
    BUILTIN_ABS_METHODDEF
    BUILTIN_ALL_METHODDEF
    BUILTIN_ANY_METHODDEF
    BUILTIN_ASCII_METHODDEF
    BUILTIN_BIN_METHODDEF
    {"breakpoint", _PyCFunction_CAST(builtin_breakpoint), METH_FASTCALL | METH_KEYWORDS, breakpoint_doc},
    BUILTIN_CALLABLE_METHODDEF
    BUILTIN_CHR_METHODDEF
    BUILTIN_COMPILE_METHODDEF
    BUILTIN_DELATTR_METHODDEF
    {"dir", builtin_dir, METH_VARARGS, dir_doc},
    BUILTIN_DIVMOD_METHODDEF
    BUILTIN_EVAL_METHODDEF
    BUILTIN_EXEC_METHODDEF
    BUILTIN_FORMAT_METHODDEF
    {"getattr", _PyCFunction_CAST(builtin_getattr), METH_FASTCALL, getattr_doc},
    BUILTIN_GLOBALS_METHODDEF
    BUILTIN_HASATTR_METHODDEF
    BUILTIN_HASH_METHODDEF
    BUILTIN_HEX_METHODDEF
    BUILTIN_ID_METHODDEF
    BUILTIN_INPUT_METHODDEF
    BUILTIN_ISINSTANCE_METHODDEF
    BUILTIN_ISSUBCLASS_METHODDEF
    {"iter", _PyCFunction_CAST(builtin_iter), METH_FASTCALL, iter_doc},
    BUILTIN_AITER_METHODDEF
    BUILTIN_LEN_METHODDEF
    BUILTIN_LOCALS_METHODDEF
    {"max", _PyCFunction_CAST(builtin_max), METH_FASTCALL | METH_KEYWORDS, max_doc},
    {"min", _PyCFunction_CAST(builtin_min), METH_FASTCALL | METH_KEYWORDS, min_doc},
    {"next", _PyCFunction_CAST(builtin_next), METH_FASTCALL, next_doc},
    BUILTIN_ANEXT_METHODDEF
    BUILTIN_OCT_METHODDEF
    BUILTIN_ORD_METHODDEF
    BUILTIN_POW_METHODDEF
    BUILTIN_PRINT_METHODDEF
    BUILTIN_REPR_METHODDEF
    BUILTIN_ROUND_METHODDEF
    BUILTIN_SETATTR_METHODDEF
    BUILTIN_SORTED_METHODDEF
    BUILTIN_SUM_METHODDEF
    {"vars",            builtin_vars,       METH_VARARGS, vars_doc},
    {NULL,              NULL},
};
PyDoc_STRVAR(builtin_doc,
"Built-in functions, types, exceptions, and other objects.\n\
\n\
This module provides direct access to all 'built-in'\n\
identifiers of Python; for example, builtins.len is\n\
the full name for the built-in function len().\n\
\n\
This module is not normally accessed explicitly by most\n\
applications, but can be useful in modules that provide\n\
objects with the same name as a built-in value, but in\n\
which the built-in of that name is also needed.");
