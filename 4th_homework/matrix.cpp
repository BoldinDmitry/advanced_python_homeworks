#include <Python.h>
#include <iostream>
#include <vector>
#include <string>
using namespace std;

// staticforward PyTypeObject matrix_Type;
// PyTypeObject matrix_Type;

typedef struct
{
    PyObject_HEAD
    /* Type-specific fields go here. */
    vector<vector<double>>
            m;
} matrix_t;

PyMODINIT_FUNC PyInit_matrix(void);
static PyObject *__add__(matrix_t *self, PyObject *w);
static PyObject *__sub__(matrix_t *self, PyObject *w);
static PyObject *__mul__(matrix_t *self, PyObject *w);

static int matrix_contains(matrix_t *self, PyObject *arg);
static Py_ssize_t matrix_length(matrix_t *self);

static PyObject *matrix_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
static int __init__(matrix_t *self, PyObject *args, PyObject *kwds);
static int matrix_traverse(matrix_t *o, visitproc visit, void *arg);
static void matrix_dealloc(matrix_t *o);
static PyObject *__repr__(matrix_t *self);
static PyObject * __str__(matrix_t *self);
static PyObject *transpose(matrix_t *self);

static PySequenceMethods matrix_as_sequence = {
        (lenfunc)matrix_length,      /* sq_length */
        0,                           /* sq_concat */
        0,                           /* sq_repeat */
        0,                           /* sq_item */
        0,                           /* sq_slice */
        0,                           /* sq_ass_item */
        0,                           /* sq_ass_slice */
        (objobjproc)matrix_contains, /* sq_contains */
};

static PyNumberMethods matrix_as_number = {
        (binaryfunc)__add__, // nb_add
        (binaryfunc)__sub__, // nb_subtract
        (binaryfunc)__mul__, // nb_multiply
        0,                      // nb_remainder
        0,                      // nb_divmod
        0,                      // nb_power
        0,                      // nb_negative
        0,                      // nb_positive
        0,                      // nb_absolute
        0,                      // nb_bool
        0,                      // nb_invert
        0,                      // nb_lshift
        0,                      // nb_rshift
        0,                      // nb_and
        0,                      // nb_xor
        0,                      // nb_or
        0,                      // nb_int
        0,                      // nb_reserved
        0,                      // nb_float
        0,                      // nb_inplace_add
        0,                      // nb_inplace_subtract
        0,                      // nb_inplace_multiply
        0,                      // nb_inplace_remainder
        0,                      // nb_inplace_power
        0,                      // nb_inplace_lshift
        0,                      // nb_inplace_rshift
        0,                      // nb_inplace_and
        0,                      // nb_inplace_xor
        0,                      // nb_inplace_or
        0,                      // nb_floor_divide
        0,                      // nb_true_divide
        0,                      // nb_inplace_floor_divide
        0,                      // nb_inplace_true_divide
        0,                      // nb_index
        0,                      // nb_matrix_multiply
        0,                      // nb_inplace_matrix_multiply
};

static PyMethodDef matrix_methods[] = {
        {"transpose", (PyCFunction)transpose, METH_NOARGS},
        {NULL, NULL} /* sentinel */
};

PyTypeObject matrix_Type = {
        PyVarObject_HEAD_INIT(NULL, 0) "matrix.Matrix", /* tp_name */
        sizeof(matrix_t),      /* tp_basic_size */
        0,      /* tp_itemsize */
        (destructor)matrix_dealloc,      /* tp_dealloc */
        0,      /* tp_print */
        0,      /* tp_getattr */
        0,      /* tp_setattr */
        0,      /* tp_reserved */
        (reprfunc)__repr__,   /* tp_repr */
        &matrix_as_number,      /* tp_as_number */
        &matrix_as_sequence,      /* tp_as_sequence */
        0,      /* tp_as_mapping */
        0,      /* tp_hash */
        0,      /* tp_call */
        reinterpret_cast<reprfunc>((binaryfunc) __str__),      /* tp_str */
        0,      /* tp_getattro */
        0,      /* tp_setattro */
        0,      /* tp_as_buffer */
        Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,      /* tp_flags */
        0,      /* tp_doc */
        (traverseproc)matrix_traverse,      /* tp_traverse */
        0,      /* tp_clear */
        0,      /* tp_richcompare */
        0,      /* tp_weaklistoffset */
        0,      /* tp_iter */
        0,      /* tp_iternext */
        matrix_methods,      /* tp_methods */
        0,      /* tp_members */
        0,      /* tp_getset */
        0,      /* tp_base */
        0,      /* tp_dict */
        0,      /* tp_descr_get */
        0,      /* tp_descr_set */
        0,      /* tp_dictoffset */
        (initproc)__init__,   /* tp_init */
        0,      /* tp_alloc */
        matrix_new,      /* tp_new */
        0,      /* tp_free */
};

static struct PyModuleDef matrix_module = {
        PyModuleDef_HEAD_INIT,
        "matrix", /* name of module */
        NULL,     /* module documentation, may be NULL */
        -1,       /* size of per-interpreter state of the module,
                 or -1 if the module keeps state in global variables. */
};

static void
matrix_dealloc(matrix_t *o)
{
    Py_TYPE(o)->tp_free((PyObject *)o);
}

static int
matrix_traverse(matrix_t *o, visitproc visit, void *arg)
{
    return 0;
}

static PyObject *
matrix_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    matrix_t *self;

    self = (matrix_t *)type->tp_alloc(type, 0);
    if (self == NULL)
    {
        return PyErr_NoMemory();
    }

    self->m = vector<vector<double>>();
    return (PyObject *)self;
}

static int
__init__(matrix_t *self, PyObject *args, PyObject *kwds)
{
    PyObject *ll;    // list of lists
    PyObject *l;     // list
    PyObject *litem; // list item
    Py_ssize_t ni, nj;

    if (!PyArg_ParseTuple(args, "O!", &PyList_Type, &ll))
    {
        PyErr_SetString(PyExc_TypeError, "parameter must be a list.");
        return -1;
    }

    ni = PyList_Size(ll);
    // to check that on every row has the same count of element
    Py_ssize_t els_on_row_count = 0;

    for (int i = 0; i < ni; i++)
    {
        l = PyList_GetItem(ll, i);
        Py_INCREF(l);
        if (PyList_Check(l))
        {
            nj = PyList_Size(l);

            if (nj == 0) {
                PyErr_SetString(PyExc_TypeError, "list cannot be empty");
                return -1;
            }

            if (els_on_row_count == 0) {
                els_on_row_count = nj;
            }
            else {
                if (nj != els_on_row_count) {
                    PyErr_SetString(PyExc_TypeError, "matrix must have fixed els count on every row");
                    return -1;
                }
            }

            for (int j = 0; j < nj; j++)
            {
                litem = PyList_GetItem(l, j);
                Py_INCREF(litem);
                if (!PyLong_Check(litem) && !PyFloat_Check(litem))
                {
                    PyErr_SetString(PyExc_TypeError, "list items must be integers or float.");
                    return -1;
                }
                Py_DECREF(litem);
            }
        }
        else
        {
            PyErr_SetString(PyExc_TypeError, "list items must be integers or float.");
            return -1;
        }
        Py_DECREF(l);
    }

    self->m.clear();
    self->m.resize(ni, vector<double>(nj));

    for (int i = 0; i < ni; i++)
    {
        l = PyList_GetItem(ll, i);
        Py_INCREF(l);
        for (int j = 0; j < nj; j++)
        {
            litem = PyList_GetItem(l, j);
            Py_INCREF(litem);
            self->m[i][j] = PyFloat_AsDouble(litem);
            Py_DECREF(litem);
        }
        Py_DECREF(l);
    }
    return 0;
}

static Py_ssize_t
matrix_length(matrix_t *self)
{
    if (self->m.empty())
    {
        return Py_ssize_t(0);
    }
    else
    {
        return Py_ssize_t(self->m.size() * self->m[0].size());
    }
}

static PyObject *
__repr__(matrix_t *self)
{
    _PyUnicodeWriter writer;
    _PyUnicodeWriter_Init(&writer);
    writer.overallocate = 1;
    writer.min_length = 10;
    PyObject *el_str = NULL;

    if (_PyUnicodeWriter_WriteASCIIString(&writer, "<Matrix {", 9) < 0)
    {
        goto error;
    }

    el_str = PyUnicode_FromFormat("%dx%d", self->m.size(), self->m[0].size());
    if (_PyUnicodeWriter_WriteStr(&writer, el_str))
    {
        Py_DECREF(el_str);
        goto error;
    }
    Py_DECREF(el_str);

    writer.overallocate = 0;
    if (_PyUnicodeWriter_WriteASCIIString(&writer, "}>", 2) < 0)
    {
        goto error;
    }
    return _PyUnicodeWriter_Finish(&writer);

    error:
    Py_XDECREF(el_str);
    _PyUnicodeWriter_Dealloc(&writer);
    PyErr_SetString(PyExc_TypeError, "smth went wrong");
    return NULL;
}

static PyObject *
__str__(matrix_t *self)
{
    _PyUnicodeWriter writer;
    _PyUnicodeWriter_Init(&writer);
    writer.overallocate = 1;
    writer.min_length = 10;
    PyObject *py_str = NULL;

    string matrix_str;
    for (const std::vector<double> &v : self->m)
    {
        for (double x : v)
        {
            matrix_str.push_back((char) x);
            matrix_str.push_back(' ');
            cout << x;
        }
        matrix_str.push_back('\n');
    }
    const char *matrix_char = matrix_str.c_str();
    py_str = PyUnicode_FromFormat("%s", matrix_char);
    _PyUnicodeWriter_WriteStr(&writer, py_str);

    return _PyUnicodeWriter_Finish(&writer);
}


static PyObject *
transpose(matrix_t *self)
{
    if (self->m.empty())
    {
        PyErr_SetString(PyExc_TypeError, "matrix is empty");
        return NULL;
    }
    else
    {
        PyObject *args = nullptr, *kwds = nullptr;
        PyObject *new_ = matrix_new(&matrix_Type, args, kwds);
        matrix_t *obj = (matrix_t *)new_;
        obj->m.resize(self->m[0].size(), vector<double>(self->m.size()));

        for(unsigned long i = 0; i < self->m[0].size(); ++i) {
            for(unsigned long j = 0; j < self->m.size(); ++j)
                obj->m[i][j] = self->m[j][i];
        }

        return (PyObject *) obj;
    }
}

static int
matrix_contains(matrix_t *self, PyObject *arg)
{
    if (!PyLong_Check(arg) && !PyFloat_Check(arg))
    {
        PyErr_SetString(PyExc_TypeError, "object must be number");
        return -1;
    }

    double num = PyFloat_AsDouble(arg);

    for (const std::vector<double> &l : self->m)
    {
        for (double el : l)
        {
            if (num == el)
                return 1;
        }
    }

    return 0;
}

static PyObject *
__mul__(matrix_t *self, PyObject *w)
{
    PyObject *args = nullptr, *kwds = nullptr;
    PyObject *new_ = matrix_new(&matrix_Type, args, kwds);
    matrix_t *obj = (matrix_t *)new_;

    if (PyLong_Check(w) || PyFloat_Check(w))
    {
        obj->m.resize(self->m.size(), vector<double>(self->m[0].size()));

        for (unsigned long i = 0; i < self->m.size(); i++)
        {
            for (unsigned long j = 0; j < self->m[i].size(); j++)
                obj->m[i][j] = self->m[i][j] * PyFloat_AsDouble(w);
        }
    }
    else if (string(w->ob_type->tp_name) == "matrix.Matrix")
    {
        matrix_t* mw = (matrix_t *) w;
        obj->m.resize(self->m.size(), vector<double>(mw->m[0].size()));
        // cols of self must be equal to rows of mw
        if (self->m[0].size() != mw->m.size())
        {
            PyErr_SetString(PyExc_TypeError, "cols of first matrix must be equal to rows of second");
            return NULL;
        }

        for (auto &i : obj->m)
            fill(i.begin(), i.end(), 0);

        for (unsigned long i = 0; i < self->m.size(); ++i)
            for (unsigned long j = 0; j < mw->m[0].size(); ++j)
                for (unsigned long k = 0; k < self->m[0].size(); ++k) {
                    obj->m[i][j] += self->m[i][k] * mw->m[k][j];
                }
    }
    else {
        PyErr_SetString(PyExc_TypeError, "Matrix can only be multiple with a number or matrix.");
        return NULL;
    }

    return (PyObject *)obj;
}

static PyObject *
__add__(matrix_t *self, PyObject *w)
{
    PyObject *args = nullptr, *kwds = nullptr;
    PyObject *new_ = matrix_new(&matrix_Type, args, kwds);
    matrix_t *obj = (matrix_t *)new_;
    obj->m.resize(self->m.size(), vector<double>(self->m[0].size()));

    if (PyLong_Check(w) || PyFloat_Check(w))
    {
        for (unsigned long i = 0; i < self->m.size(); i++)
        {
            for (unsigned long j = 0; j < self->m[i].size(); j++)
                obj->m[i][j] = self->m[i][j] + PyFloat_AsDouble(w);
        }
    }
    else if (string(w->ob_type->tp_name) == "matrix.Matrix")
    {
        matrix_t* mw = (matrix_t *) w;

        if (self->m.size() != mw->m.size() && self->m[0].size() != mw->m[0].size())
        {
            PyErr_SetString(PyExc_TypeError, "matrix cols and rows must be equal");
            return NULL;
        }
        for (unsigned long i = 0; i < obj->m.size(); i++)
        {
            for (unsigned long j = 0; j < obj->m[i].size(); j++)
                obj->m[i][j] =self->m[i][j] + mw->m[i][j];
        }
    }
    else {
        PyErr_SetString(PyExc_TypeError, "Matrix can only be folded with a number or matrix.");
        return NULL;
    }
    return (PyObject *)obj;
}

static PyObject *
__sub__(matrix_t *self, PyObject *w)
{
    PyObject *args = nullptr, *kwds = nullptr;
    PyObject *new_ = matrix_new(&matrix_Type, args, kwds);
    matrix_t *obj = (matrix_t *)new_;
    obj->m.resize(self->m.size(), vector<double>(self->m[0].size()));

    if (PyLong_Check(w) || PyFloat_Check(w))
    {
        for (unsigned long i = 0; i < self->m.size(); i++)
        {
            for (unsigned long j = 0; j < self->m[i].size(); j++)
                obj->m[i][j] = self->m[i][j] - PyFloat_AsDouble(w);
        }
    }
    else if (string(w->ob_type->tp_name) == "matrix.Matrix")
    {
        matrix_t* mw = (matrix_t *) w;

        if (self->m.size() != mw->m.size() && self->m[0].size() != mw->m[0].size())
        {
            PyErr_SetString(PyExc_TypeError, "matrix cols and rows must be equal");
            return NULL;
        }
        for (unsigned long i = 0; i < obj->m.size(); i++)
        {
            for (unsigned long j = 0; j < obj->m[i].size(); j++)
                obj->m[i][j] =self->m[i][j] - mw->m[i][j];
        }
    }
    else {
        PyErr_SetString(PyExc_TypeError, "Matrix can only be folded with a number or matrix.");
        return NULL;
    }
    return (PyObject *)obj;
}


PyMODINIT_FUNC
PyInit_matrix(void)
{
    PyObject *m;
    if (PyType_Ready(&matrix_Type) < 0)
        return NULL;

    m = PyModule_Create(&matrix_module);
    if (m == NULL)
        return NULL;

    Py_INCREF(&matrix_Type);
    PyModule_AddObject(m, "Matrix", (PyObject *)&matrix_Type);
    return m;
}
