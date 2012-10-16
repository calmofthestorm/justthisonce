import ctypes

class _Range(ctypes.Structure):
    _fields = [("start", ctypes.c_size_t),
               ("length", ctypes.c_size_t)]

class _File(ctypes.Structure):
    _fields_ = [("n_ranges", ctypes.c_size_t),
                ("filepath", ctypes.c_char_p),
                ("ranges", ctypes.c_void_p),
                ("fd", ctypes.c_void_p),
                ("buffer", ctypes.c_char_p),
                ("size", ctypes.c_size_t)]
                ("range_left", ctypes.c_size_t)]
                ("cur_range", ctypes.c_size_t)]

_xorlib=ctypes.cdll.LoadLibrary("./cxor.so")

files = (_File * 2)()
outfile = _File

files[0].n_ranges = 1;
