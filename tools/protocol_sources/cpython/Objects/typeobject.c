#define TPSLOT(NAME, SLOT, FUNCTION, WRAPPER, DOC) \
    {#NAME, offsetof(PyTypeObject, SLOT), (void *)(FUNCTION), WRAPPER, \
     PyDoc_STR(DOC), .name_strobj = &_Py_ID(NAME)}
#define FLSLOT(NAME, SLOT, FUNCTION, WRAPPER, DOC, FLAGS) \
    {#NAME, offsetof(PyTypeObject, SLOT), (void *)(FUNCTION), WRAPPER, \
     PyDoc_STR(DOC), FLAGS, .name_strobj = &_Py_ID(NAME) }
#define ETSLOT(NAME, SLOT, FUNCTION, WRAPPER, DOC) \
    {#NAME, offsetof(PyHeapTypeObject, SLOT), (void *)(FUNCTION), WRAPPER, \
     PyDoc_STR(DOC), .name_strobj = &_Py_ID(NAME) }
#define BUFSLOT(NAME, SLOT, FUNCTION, WRAPPER, DOC) \
    ETSLOT(NAME, as_buffer.SLOT, FUNCTION, WRAPPER, DOC)
#define AMSLOT(NAME, SLOT, FUNCTION, WRAPPER, DOC) \
    ETSLOT(NAME, as_async.SLOT, FUNCTION, WRAPPER, DOC)
#define SQSLOT(NAME, SLOT, FUNCTION, WRAPPER, DOC) \
    ETSLOT(NAME, as_sequence.SLOT, FUNCTION, WRAPPER, DOC)
#define MPSLOT(NAME, SLOT, FUNCTION, WRAPPER, DOC) \
    ETSLOT(NAME, as_mapping.SLOT, FUNCTION, WRAPPER, DOC)
#define NBSLOT(NAME, SLOT, FUNCTION, WRAPPER, DOC) \
    ETSLOT(NAME, as_number.SLOT, FUNCTION, WRAPPER, DOC)
#define UNSLOT(NAME, SLOT, FUNCTION, WRAPPER, DOC) \
    ETSLOT(NAME, as_number.SLOT, FUNCTION, WRAPPER, \
           #NAME "($self, /)\n--\n\n" DOC)
#define IBSLOT(NAME, SLOT, FUNCTION, WRAPPER, DOC) \
    ETSLOT(NAME, as_number.SLOT, FUNCTION, WRAPPER, \
           #NAME "($self, value, /)\n--\n\nReturn self" DOC "value.")
#define BINSLOT(NAME, SLOT, FUNCTION, DOC) \
    ETSLOT(NAME, as_number.SLOT, FUNCTION, wrap_binaryfunc_l, \
           #NAME "($self, value, /)\n--\n\nReturn self" DOC "value.")
#define RBINSLOT(NAME, SLOT, FUNCTION, DOC) \
    ETSLOT(NAME, as_number.SLOT, FUNCTION, wrap_binaryfunc_r, \
           #NAME "($self, value, /)\n--\n\nReturn value" DOC "self.")
#define BINSLOTNOTINFIX(NAME, SLOT, FUNCTION, DOC) \
    ETSLOT(NAME, as_number.SLOT, FUNCTION, wrap_binaryfunc_l, \
           #NAME "($self, value, /)\n--\n\n" DOC)
#define RBINSLOTNOTINFIX(NAME, SLOT, FUNCTION, DOC) \
    ETSLOT(NAME, as_number.SLOT, FUNCTION, wrap_binaryfunc_r, \
           #NAME "($self, value, /)\n--\n\n" DOC)

static pytype_slotdef slotdefs[] = {
    TPSLOT(__getattribute__, tp_getattr, NULL, NULL, ""),
    TPSLOT(__getattr__, tp_getattr, NULL, NULL, ""),
    TPSLOT(__setattr__, tp_setattr, NULL, NULL, ""),
    TPSLOT(__delattr__, tp_setattr, NULL, NULL, ""),
    TPSLOT(__repr__, tp_repr, slot_tp_repr, wrap_unaryfunc,
           "__repr__($self, /)\n--\n\nReturn repr(self)."),
    TPSLOT(__hash__, tp_hash, slot_tp_hash, wrap_hashfunc,
           "__hash__($self, /)\n--\n\nReturn hash(self)."),
    FLSLOT(__call__, tp_call, slot_tp_call,
           _Py_FUNC_CAST(wrapperfunc, wrap_call),
           "__call__($self, /, *args, **kwargs)\n--\n\nCall self as a function.",
           PyWrapperFlag_KEYWORDS),
    TPSLOT(__str__, tp_str, slot_tp_str, wrap_unaryfunc,
           "__str__($self, /)\n--\n\nReturn str(self)."),
    TPSLOT(__getattribute__, tp_getattro, _Py_slot_tp_getattr_hook,
           wrap_binaryfunc,
           "__getattribute__($self, name, /)\n--\n\nReturn getattr(self, name)."),
    TPSLOT(__getattr__, tp_getattro, _Py_slot_tp_getattr_hook, NULL,
           "__getattr__($self, name, /)\n--\n\nImplement getattr(self, name)."),
    TPSLOT(__setattr__, tp_setattro, slot_tp_setattro, wrap_setattr,
           "__setattr__($self, name, value, /)\n--\n\nImplement setattr(self, name, value)."),
    TPSLOT(__delattr__, tp_setattro, slot_tp_setattro, wrap_delattr,
           "__delattr__($self, name, /)\n--\n\nImplement delattr(self, name)."),
    TPSLOT(__lt__, tp_richcompare, slot_tp_richcompare, richcmp_lt,
           "__lt__($self, value, /)\n--\n\nReturn self<value."),
    TPSLOT(__le__, tp_richcompare, slot_tp_richcompare, richcmp_le,
           "__le__($self, value, /)\n--\n\nReturn self<=value."),
    TPSLOT(__eq__, tp_richcompare, slot_tp_richcompare, richcmp_eq,
           "__eq__($self, value, /)\n--\n\nReturn self==value."),
    TPSLOT(__ne__, tp_richcompare, slot_tp_richcompare, richcmp_ne,
           "__ne__($self, value, /)\n--\n\nReturn self!=value."),
    TPSLOT(__gt__, tp_richcompare, slot_tp_richcompare, richcmp_gt,
           "__gt__($self, value, /)\n--\n\nReturn self>value."),
    TPSLOT(__ge__, tp_richcompare, slot_tp_richcompare, richcmp_ge,
           "__ge__($self, value, /)\n--\n\nReturn self>=value."),
    TPSLOT(__iter__, tp_iter, slot_tp_iter, wrap_unaryfunc,
           "__iter__($self, /)\n--\n\nImplement iter(self)."),
    TPSLOT(__next__, tp_iternext, slot_tp_iternext, wrap_next,
           "__next__($self, /)\n--\n\nImplement next(self)."),
    TPSLOT(__get__, tp_descr_get, slot_tp_descr_get, wrap_descr_get,
           "__get__($self, instance, owner=None, /)\n--\n\nReturn an attribute of instance, which is of type owner."),
    TPSLOT(__set__, tp_descr_set, slot_tp_descr_set, wrap_descr_set,
           "__set__($self, instance, value, /)\n--\n\nSet an attribute of instance to value."),
    TPSLOT(__delete__, tp_descr_set, slot_tp_descr_set,
           wrap_descr_delete,
           "__delete__($self, instance, /)\n--\n\nDelete an attribute of instance."),
    FLSLOT(__init__, tp_init, slot_tp_init,
           _Py_FUNC_CAST(wrapperfunc, wrap_init),
           "__init__($self, /, *args, **kwargs)\n--\n\n"
           "Initialize self.  See help(type(self)) for accurate signature.",
           PyWrapperFlag_KEYWORDS),
    TPSLOT(__new__, tp_new, slot_tp_new, NULL,
           "__new__(type, /, *args, **kwargs)\n--\n\n"
           "Create and return new object.  See help(type) for accurate signature."),
    TPSLOT(__del__, tp_finalize, slot_tp_finalize, (wrapperfunc)wrap_del,
           "__del__($self, /)\n--\n\n"
           "Called when the instance is about to be destroyed."),

    BUFSLOT(__buffer__, bf_getbuffer, slot_bf_getbuffer, wrap_buffer,
            "__buffer__($self, flags, /)\n--\n\n"
            "Return a buffer object that exposes the underlying memory of the object."),
    BUFSLOT(__release_buffer__, bf_releasebuffer, slot_bf_releasebuffer, wrap_releasebuffer,
            "__release_buffer__($self, buffer, /)\n--\n\n"
            "Release the buffer object that exposes the underlying memory of the object."),

    AMSLOT(__await__, am_await, slot_am_await, wrap_unaryfunc,
           "__await__($self, /)\n--\n\nReturn an iterator to be used in await expression."),
    AMSLOT(__aiter__, am_aiter, slot_am_aiter, wrap_unaryfunc,
           "__aiter__($self, /)\n--\n\nReturn an awaitable, that resolves in asynchronous iterator."),
    AMSLOT(__anext__, am_anext, slot_am_anext, wrap_unaryfunc,
           "__anext__($self, /)\n--\n\nReturn a value or raise StopAsyncIteration."),

    BINSLOT(__add__, nb_add, slot_nb_add,
           "+"),
    RBINSLOT(__radd__, nb_add, slot_nb_add,
           "+"),
    BINSLOT(__sub__, nb_subtract, slot_nb_subtract,
           "-"),
    RBINSLOT(__rsub__, nb_subtract, slot_nb_subtract,
           "-"),
    BINSLOT(__mul__, nb_multiply, slot_nb_multiply,
           "*"),
    RBINSLOT(__rmul__, nb_multiply, slot_nb_multiply,
           "*"),
    BINSLOT(__mod__, nb_remainder, slot_nb_remainder,
           "%"),
    RBINSLOT(__rmod__, nb_remainder, slot_nb_remainder,
           "%"),
    BINSLOTNOTINFIX(__divmod__, nb_divmod, slot_nb_divmod,
           "Return divmod(self, value)."),
    RBINSLOTNOTINFIX(__rdivmod__, nb_divmod, slot_nb_divmod,
           "Return divmod(value, self)."),
    NBSLOT(__pow__, nb_power, slot_nb_power, wrap_ternaryfunc,
           "__pow__($self, value, mod=None, /)\n--\n\nReturn pow(self, value, mod)."),
    NBSLOT(__rpow__, nb_power, slot_nb_power, wrap_ternaryfunc_r,
           "__rpow__($self, value, mod=None, /)\n--\n\nReturn pow(value, self, mod)."),
    UNSLOT(__neg__, nb_negative, slot_nb_negative, wrap_unaryfunc, "-self"),
    UNSLOT(__pos__, nb_positive, slot_nb_positive, wrap_unaryfunc, "+self"),
    UNSLOT(__abs__, nb_absolute, slot_nb_absolute, wrap_unaryfunc,
           "abs(self)"),
    UNSLOT(__bool__, nb_bool, slot_nb_bool, wrap_inquirypred,
           "True if self else False"),
    UNSLOT(__invert__, nb_invert, slot_nb_invert, wrap_unaryfunc, "~self"),
    BINSLOT(__lshift__, nb_lshift, slot_nb_lshift, "<<"),
    RBINSLOT(__rlshift__, nb_lshift, slot_nb_lshift, "<<"),
    BINSLOT(__rshift__, nb_rshift, slot_nb_rshift, ">>"),
    RBINSLOT(__rrshift__, nb_rshift, slot_nb_rshift, ">>"),
    BINSLOT(__and__, nb_and, slot_nb_and, "&"),
    RBINSLOT(__rand__, nb_and, slot_nb_and, "&"),
    BINSLOT(__xor__, nb_xor, slot_nb_xor, "^"),
    RBINSLOT(__rxor__, nb_xor, slot_nb_xor, "^"),
    BINSLOT(__or__, nb_or, slot_nb_or, "|"),
    RBINSLOT(__ror__, nb_or, slot_nb_or, "|"),
    UNSLOT(__int__, nb_int, slot_nb_int, wrap_unaryfunc,
           "int(self)"),
    UNSLOT(__float__, nb_float, slot_nb_float, wrap_unaryfunc,
           "float(self)"),
    IBSLOT(__iadd__, nb_inplace_add, slot_nb_inplace_add,
           wrap_binaryfunc, "+="),
    IBSLOT(__isub__, nb_inplace_subtract, slot_nb_inplace_subtract,
           wrap_binaryfunc, "-="),
    IBSLOT(__imul__, nb_inplace_multiply, slot_nb_inplace_multiply,
           wrap_binaryfunc, "*="),
    IBSLOT(__imod__, nb_inplace_remainder, slot_nb_inplace_remainder,
           wrap_binaryfunc, "%="),
    IBSLOT(__ipow__, nb_inplace_power, slot_nb_inplace_power,
           wrap_ternaryfunc, "**="),
    IBSLOT(__ilshift__, nb_inplace_lshift, slot_nb_inplace_lshift,
           wrap_binaryfunc, "<<="),
    IBSLOT(__irshift__, nb_inplace_rshift, slot_nb_inplace_rshift,
           wrap_binaryfunc, ">>="),
    IBSLOT(__iand__, nb_inplace_and, slot_nb_inplace_and,
           wrap_binaryfunc, "&="),
    IBSLOT(__ixor__, nb_inplace_xor, slot_nb_inplace_xor,
           wrap_binaryfunc, "^="),
    IBSLOT(__ior__, nb_inplace_or, slot_nb_inplace_or,
           wrap_binaryfunc, "|="),
    BINSLOT(__floordiv__, nb_floor_divide, slot_nb_floor_divide, "//"),
    RBINSLOT(__rfloordiv__, nb_floor_divide, slot_nb_floor_divide, "//"),
    BINSLOT(__truediv__, nb_true_divide, slot_nb_true_divide, "/"),
    RBINSLOT(__rtruediv__, nb_true_divide, slot_nb_true_divide, "/"),
    IBSLOT(__ifloordiv__, nb_inplace_floor_divide,
           slot_nb_inplace_floor_divide, wrap_binaryfunc, "//="),
    IBSLOT(__itruediv__, nb_inplace_true_divide,
           slot_nb_inplace_true_divide, wrap_binaryfunc, "/="),
    NBSLOT(__index__, nb_index, slot_nb_index, wrap_unaryfunc,
           "__index__($self, /)\n--\n\n"
           "Return self converted to an integer, if self is suitable "
           "for use as an index into a list."),
    BINSLOT(__matmul__, nb_matrix_multiply, slot_nb_matrix_multiply,
            "@"),
    RBINSLOT(__rmatmul__, nb_matrix_multiply, slot_nb_matrix_multiply,
             "@"),
    IBSLOT(__imatmul__, nb_inplace_matrix_multiply, slot_nb_inplace_matrix_multiply,
           wrap_binaryfunc, "@="),
    MPSLOT(__len__, mp_length, slot_mp_length, wrap_lenfunc,
           "__len__($self, /)\n--\n\nReturn len(self)."),
    MPSLOT(__getitem__, mp_subscript, slot_mp_subscript,
           wrap_binaryfunc,
           "__getitem__($self, key, /)\n--\n\nReturn self[key]."),
    MPSLOT(__setitem__, mp_ass_subscript, slot_mp_ass_subscript,
           wrap_objobjargproc,
           "__setitem__($self, key, value, /)\n--\n\nSet self[key] to value."),
    MPSLOT(__delitem__, mp_ass_subscript, slot_mp_ass_subscript,
           wrap_delitem,
           "__delitem__($self, key, /)\n--\n\nDelete self[key]."),

    SQSLOT(__len__, sq_length, slot_sq_length, wrap_lenfunc,
           "__len__($self, /)\n--\n\nReturn len(self)."),
    /* Heap types defining __add__/__mul__ have sq_concat/sq_repeat == NULL.
       The logic in abstract.c always falls back to nb_add/nb_multiply in
       this case.  Defining both the nb_* and the sq_* slots to call the
       user-defined methods has unexpected side-effects, as shown by
       test_descr.notimplemented() */
    SQSLOT(__add__, sq_concat, NULL, wrap_binaryfunc,
           "__add__($self, value, /)\n--\n\nReturn self+value."),
    SQSLOT(__mul__, sq_repeat, NULL, wrap_indexargfunc,
           "__mul__($self, value, /)\n--\n\nReturn self*value."),
    SQSLOT(__rmul__, sq_repeat, NULL, wrap_indexargfunc,
           "__rmul__($self, value, /)\n--\n\nReturn value*self."),
    SQSLOT(__getitem__, sq_item, slot_sq_item, wrap_sq_item,
           "__getitem__($self, key, /)\n--\n\nReturn self[key]."),
    SQSLOT(__setitem__, sq_ass_item, slot_sq_ass_item, wrap_sq_setitem,
           "__setitem__($self, key, value, /)\n--\n\nSet self[key] to value."),
    SQSLOT(__delitem__, sq_ass_item, slot_sq_ass_item, wrap_sq_delitem,
           "__delitem__($self, key, /)\n--\n\nDelete self[key]."),
    SQSLOT(__contains__, sq_contains, slot_sq_contains, wrap_objobjproc,
           "__contains__($self, key, /)\n--\n\nReturn bool(key in self)."),
    SQSLOT(__iadd__, sq_inplace_concat, NULL,
           wrap_binaryfunc,
           "__iadd__($self, value, /)\n--\n\nImplement self+=value."),
    SQSLOT(__imul__, sq_inplace_repeat, NULL,
           wrap_indexargfunc,
           "__imul__($self, value, /)\n--\n\nImplement self*=value."),

    {NULL}
};
